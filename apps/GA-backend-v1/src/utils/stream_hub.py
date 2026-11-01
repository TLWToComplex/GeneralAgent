"""
StreamHub：会话输出流管理（简化版）

设计目标：
- 任务执行与 HTTP 连接解耦：producer（asyncio.Task 或后台线程）把帧 publish 到 hub，
  HTTP 响应只是订阅者；客户端断开 SSE 不影响任务执行与对话记录落库。
- 断线重连：前端先查 status 端点判断该 session_thread_id 的 turn 是否结束：
  * 未结束（starting/running）→ 调 resume 端点，从内存全量回放本轮事件流
    （原始格式，回放后无缝转入实时），直到流关闭；
  * 已结束 → turn 已落库且内存流已清除，前端走历史对话记录接口。
- 线格式零改动：不注入 id 行、不插入元事件、不发心跳，
  帧按 producer 产出的原样存储与转发，保持各对话接口原有的流输出格式。
- 内存有界：turn 结束（finish/abort）即从内存清除；buffer 仅保留最近
  max_events 帧；starting 状态卡死超过 ttl 的流由 claim 惰性清理。

线程安全：所有状态变更在 RLock 内完成（锁内零 await）；
async 订阅者通过 loop.call_soon_threadsafe 跨线程通知，sync 订阅者用 queue.Queue。
"""
import asyncio
import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Iterator, Optional, Set, Tuple

logger = logging.getLogger("stream_hub")

STATUS_STARTING = "starting"    # 已占坑，producer 尚未产出首个业务事件
STATUS_RUNNING = "running"      # 执行中
STATUS_COMPLETED = "completed"  # 正常结束（结束即清内存）
STATUS_ERROR = "error"          # 异常结束（结束即清内存）


@dataclass
class StreamEvent:
    """内部缓冲事件：seq 仅用于快照回放与实时队列的去重，不上线"""
    seq: int
    frame: str


@dataclass
class TurnStream:
    session_thread_id: str
    turn_id: str = ""
    status: str = STATUS_STARTING
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    buffer: deque = field(default_factory=deque)
    seq_counter: int = 0
    # async 订阅者：(队列, 所在 event loop)，跨线程用 call_soon_threadsafe 通知
    async_subscribers: Set[Tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = field(default_factory=set)
    # sync 订阅者：线程安全队列（Flask/WSGI 线程消费）
    sync_subscribers: Set[queue.Queue] = field(default_factory=set)
    task: Optional[asyncio.Task] = None
    producer_thread: Optional[threading.Thread] = None

    @property
    def is_active(self) -> bool:
        return self.status in (STATUS_STARTING, STATUS_RUNNING)

    @property
    def has_subscribers(self) -> bool:
        return bool(self.async_subscribers) or bool(self.sync_subscribers)


class StreamHub:
    """按 session_thread_id 管理对话输出流的中心（进程内单例）"""

    def __init__(self, max_events: int = 5000, ttl_seconds: float = 600):
        self._lock = threading.RLock()
        self._streams: Dict[str, TurnStream] = {}
        self.max_events = max_events          # 单 turn 缓冲帧数上限（超出淘汰最旧）
        self.ttl_seconds = ttl_seconds        # starting 卡死流的安全网清理阈值

    # ------------------------------------------------------------------
    # 生产侧
    # ------------------------------------------------------------------

    def claim(self, session_thread_id: str, turn_id: str = "") -> Tuple[TurnStream, bool]:
        """对话入口占坑。

        - 已有 starting/running 流：返回 (该流, False)，调用方应直接 attach（订阅），
          不启动新任务；
        - 否则创建新流返回 (新流, True)。

        必须在耗时的准备逻辑（沙盒创建、DB 查询、LLM 构建）之前同步调用，
        保证并发请求不会双开任务。
        """
        with self._lock:
            self._sweep_expired()
            existing = self._streams.get(session_thread_id)
            if existing is not None and existing.is_active:
                return existing, False
            stream = TurnStream(session_thread_id=session_thread_id,
                                turn_id=turn_id,
                                buffer=deque(maxlen=self.max_events))
            self._streams[session_thread_id] = stream
            return stream, True

    def publish(self, session_thread_id: str, frame: str) -> int:
        """producer 产出一帧（原始线格式文本），缓冲并广播给所有订阅者"""
        with self._lock:
            stream = self._streams.get(session_thread_id)
            if stream is None or not stream.is_active:
                return 0  # 流已结束/清除，丢弃
            if stream.status == STATUS_STARTING:
                stream.status = STATUS_RUNNING
            stream.seq_counter += 1
            event = StreamEvent(seq=stream.seq_counter, frame=frame)
            stream.buffer.append(event)
            self._broadcast(stream, event)
            return event.seq

    def _broadcast(self, stream: TurnStream, item) -> None:
        """item 为 StreamEvent（业务帧）或 None（结束哨兵）；调用方持锁"""
        for q in list(stream.sync_subscribers):
            try:
                q.put_nowait(item)
            except Exception:
                stream.sync_subscribers.discard(q)
        for sub in list(stream.async_subscribers):
            q, loop = sub
            try:
                loop.call_soon_threadsafe(q.put_nowait, item)
            except RuntimeError:
                # loop 已关闭（订阅者所在线程/循环退出），移除订阅者
                stream.async_subscribers.discard(sub)

    def finish(self, session_thread_id: str, status: str = STATUS_COMPLETED) -> None:
        """turn 结束：通知在线订阅者关闭，并把流从内存清除。

        调用时机保证在对话记录落库之后（run_producer 先关闭业务生成器
        触发其 finally 落库，再调 finish），因此"内存清除"天然晚于"落库"。
        清除后 status/resume 均返回无流，前端回落历史对话记录。
        """
        with self._lock:
            stream = self._streams.pop(session_thread_id, None)
            if stream is None:
                return
            stream.status = status
            stream.finished_at = time.time()
            self._broadcast(stream, None)  # 哨兵：订阅者收到后正常关闭

    def abort(self, session_thread_id: str) -> None:
        """准备阶段失败清坑（等价于以 error 结束），避免后续请求 attach 到死流"""
        self.finish(session_thread_id, STATUS_ERROR)

    def attach_task(self, session_thread_id: str, task: asyncio.Task) -> None:
        """持有 async producer 任务引用，防止被 GC 提前回收"""
        with self._lock:
            stream = self._streams.get(session_thread_id)
            if stream is not None:
                stream.task = task

    def attach_thread(self, session_thread_id: str, thread: threading.Thread) -> None:
        """持有线程 producer 引用（仅信息用途；daemon 线程随进程退出）"""
        with self._lock:
            stream = self._streams.get(session_thread_id)
            if stream is not None:
                stream.producer_thread = thread

    # ------------------------------------------------------------------
    # 查询侧
    # ------------------------------------------------------------------

    def get(self, session_thread_id: str) -> Optional[TurnStream]:
        with self._lock:
            return self._streams.get(session_thread_id)

    def status(self, session_thread_id: str) -> Optional[dict]:
        """流状态快照（JSON 可序列化），供 status 端点判断 turn 是否结束。

        返回 None 表示无流（未开始 / 已结束并落库清除），前端应走历史记录。
        """
        with self._lock:
            stream = self._streams.get(session_thread_id)
            if stream is None:
                return None
            return {
                "exists": True,
                "status": stream.status,
                "turn_id": stream.turn_id,
                "created_at": stream.created_at,
            }

    def _sweep_expired(self) -> None:
        """惰性清理：starting 卡死超 ttl 且无订阅者的流（producer 未能启动的残留）。

        正常结束的流在 finish 时已清除，无需 TTL 保留期。调用方持锁。
        """
        now = time.time()
        for key in [k for k, s in self._streams.items()
                    if s.status == STATUS_STARTING
                    and now - s.created_at > self.ttl_seconds
                    and not s.has_subscribers]:
            self._streams.pop(key, None)

    # ------------------------------------------------------------------
    # 订阅
    # ------------------------------------------------------------------

    def _register(self, session_thread_id: str, sync: bool):
        """锁内原子完成：取快照 + 挂订阅队列。返回 (snapshot, queue, stream) 或 None"""
        with self._lock:
            stream = self._streams.get(session_thread_id)
            if stream is None:
                return None
            snapshot = list(stream.buffer)
            if sync:
                q = queue.Queue()
                stream.sync_subscribers.add(q)
            else:
                q = asyncio.Queue()
                stream.async_subscribers.add((q, asyncio.get_running_loop()))
            return snapshot, q, stream

    def register(self, session_thread_id: str):
        return self._register(session_thread_id, sync=False)

    def register_sync(self, session_thread_id: str):
        return self._register(session_thread_id, sync=True)

    async def subscribe(self, session_thread_id: str) -> AsyncIterator[str]:
        """订阅指定会话的输出流（供 FastAPI StreamingResponse）。

        先全量回放内存缓冲（原始帧），再实时续订直到流结束（收到哨兵关闭）。
        无流时不产出任何帧直接关闭（resume 端点会先做 404 预检）。
        客户端断开时生成器被取消，finally 中仅退订，producer 不受影响。
        """
        registration = self.register(session_thread_id)
        if registration is None:
            return
        snapshot, q, stream = registration
        last_sent = 0
        try:
            for event in snapshot:
                yield event.frame
                last_sent = event.seq
            while True:
                item = await q.get()
                if item is None:
                    break  # 哨兵：turn 已结束
                if item.seq <= last_sent:
                    continue  # 快照与实时队列重叠部分去重
                yield item.frame
                last_sent = item.seq
        finally:
            with self._lock:
                for sub in list(stream.async_subscribers):
                    if sub[0] is q:
                        stream.async_subscribers.discard(sub)

    def subscribe_sync(self, session_thread_id: str) -> Iterator[str]:
        """同步版 subscribe：普通生成器，可在任意线程中被 WSGI 响应消费。

        阻塞等待下一帧（无心跳帧：保持原线格式）。客户端断开由 WSGI 层在
        下次写失败时 close() 生成器退订；producer 已结束时会收到哨兵正常退出。
        """
        registration = self.register_sync(session_thread_id)
        if registration is None:
            return
        snapshot, q, stream = registration
        last_sent = 0
        try:
            for event in snapshot:
                yield event.frame
                last_sent = event.seq
            while True:
                item = q.get()
                if item is None:
                    break
                if item.seq <= last_sent:
                    continue
                yield item.frame
                last_sent = item.seq
        finally:
            with self._lock:
                stream.sync_subscribers.discard(q)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def shutdown(self, grace: float = 10) -> None:
        """优雅收尾：等待进行中的 async producer 任务结束（各自 finish 清内存），
        超时才取消。线程 producer 为 daemon，随进程退出（被杀时该轮按其
        生成器 finally 的语义处理，与进程崩溃场景同级）。
        """
        with self._lock:
            tasks = [s.task for s in self._streams.values()
                     if s.task is not None and not s.task.done()]
        if not tasks:
            return
        done, pending = await asyncio.wait(tasks, timeout=grace)
        for t in pending:
            logger.warning(f"[stream_hub] shutdown 超时，取消任务: {t.get_name()}")
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def run_producer(hub: StreamHub, session_thread_id: str, agen) -> None:
    """后台消费异步生成器并 publish 到 hub（帧原样转发，不附加任何结构）。

    结束顺序保证：先关闭业务生成器（触发其 finally 中的对话记录落库），
    再 finish（清内存），确保内存清除晚于落库。
    """
    status = STATUS_COMPLETED
    try:
        async for frame in agen:
            hub.publish(session_thread_id, frame)
    except asyncio.CancelledError:
        logger.warning(f"[stream_hub] producer 被取消: session={session_thread_id}")
        status = STATUS_ERROR
    except Exception as e:
        logger.error(f"[stream_hub] producer 异常: session={session_thread_id}, err={e}")
        status = STATUS_ERROR
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass
        hub.finish(session_thread_id, status)


def run_producer_sync(hub: StreamHub, session_thread_id: str, gen) -> None:
    """后台线程消费同步生成器并 publish 到 hub（供 Flask 侧使用）。
    结束顺序保证同 run_producer。
    """
    status = STATUS_COMPLETED
    try:
        for frame in gen:
            hub.publish(session_thread_id, frame)
    except Exception as e:
        logger.error(f"[stream_hub] sync producer 异常: session={session_thread_id}, err={e}")
        status = STATUS_ERROR
    finally:
        close = getattr(gen, "close", None)
        if close:
            try:
                close()
            except Exception:
                pass
        hub.finish(session_thread_id, status)


# 进程内单例：单进程部署下 Flask(/)、travel(/travel)、deepagent(/skill) 共享
stream_hub = StreamHub()
