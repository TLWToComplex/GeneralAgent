"""
思考过程（reasoning）流式输出缓冲工具。

按 run_id 分桶，使用"末尾标点 + 兜底字符数"双重策略控制 flush 时机，
避免思考内容逐字符推送给前端。
"""
import json
from typing import Optional

# _FLUSH_PUNCT: frozenset = frozenset('。！？\n!?;')
_FLUSH_PUNCT: frozenset = frozenset('，。！？；：——-_{}【】[]‘’“”"\n\',.:!?;')
_MAX_BUFFER: int = 200


class ReasoningBuffer:
    """按 run_id 分桶的 reasoning 流式缓冲器。

    只对 ``1:`` 前缀的 reasoning 帧做缓冲聚合，其他帧原样返回。
    SSE 包装（``data: ...\\n\\n``）由调用方负责。

    用法::

        buf = ReasoningBuffer()

        async for event in agent.astream_events(...):
            run_id = event.get("run_id", "") or ""
            async for output in process_event(event, ...):
                line = buf.feed(run_id, output)
                if line is not None:
                    yield f"data: {line}\\n\\n" if wrap_sse else line

        for line in buf.flush_all():
            yield f"data: {line}\\n\\n" if wrap_sse else line
    """

    def __init__(self):
        # 键格式: (run_id, tag) -> 缓冲文本, tag 为 "0" 或 "1"
        self._buffers: dict[tuple[str, str], str] = {}

    def _should_flush(self, text: str) -> bool:
        # 只要遇到标点就 flush，不要求长度
        return bool(text) and text[-1] in _FLUSH_PUNCT
        # return bool(text) and (text[-1] in _FLUSH_PUNCT and len(text) >= _MAX_BUFFER)

    def _make_line(self, text: str, tag: str) -> str:
        return f"{tag}:{json.dumps(text, ensure_ascii=False)}\n"

    def feed(self, run_id: str, output: str) -> Optional[str]:
        """处理一条 process_event 输出行。

        - ``0:`` / ``1:``  帧：累积到对应标签的缓冲区，满足 flush 条件时返回聚合后的行。
        - 其他帧：原样返回。

        Returns:
            需要发送给前端的行；暂不需要输出时返回 None。
        """
        if output[:2] not in ("0:", "1:"):
            return output

        tag = output[0]
        try:
            text = json.loads(output[2:].rstrip("\n"))
        except Exception:
            text = ""

        if not isinstance(text, str) or not text:
            return None

        key = (run_id, tag)
        self._buffers[key] = self._buffers.get(key, "") + text

        if self._should_flush(self._buffers[key]):
            return self._flush_run(key)
        return None

    def flush_all(self) -> list[str]:
        """flush 所有 (run_id, tag) 的残余缓冲，流结束时调用。

        Returns:
            需要发送给前端的行列表。
        """
        result = []
        for key in list(self._buffers.keys()):
            line = self._flush_run(key)
            if line:
                result.append(line)
        return result

    def _flush_run(self, key: tuple[str, str]) -> Optional[str]:
        text = self._buffers.get(key, "")
        if text:
            self._buffers[key] = ""
            return self._make_line(text, key[1])
        return None
