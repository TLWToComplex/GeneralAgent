"""
文件下载链接注入器 — 拦截 tool_end 事件，自动注入下载链接。

从 executor 工具输出的文本中检测已生成的文件路径（如 /workspace/report.docx），
在整个对话流结束时统一追加 ``0:`` 格式的下载链接行，使前端无需依赖大模型自行拼接 URL。
"""

import json
import logging
import re
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 文件路径检测 — 从 tool 输出中提取生成的文件名
# ---------------------------------------------------------------------------
_FILE_PATTERN_DOC = re.compile(
    r'/workspace/([\w\-\.\u4e00-\u9fff]+'
    r'\.(?:docx?|pptx?|xlsx?|pdf|md|txt|csv|json|html?'
    r'|png|jpe?g|svg|webp|gif'
    r'|xml|ya?ml|zip|log))'
)


def _extract_generated_files(text: str) -> set[str]:
    """从工具输出文本中提取已生成的文件名（去重）。"""
    return set(_FILE_PATTERN_DOC.findall(text))


# ---------------------------------------------------------------------------
# 注入器
# ---------------------------------------------------------------------------
class FileLinkInjector:
    """收集 tool_end 事件中的文件路径，流结束时统一输出下载链接。

    同一 thread_id 多次对话时，已报告过的文件不会重复注入。
    使用类级别存储 ``_reported_store`` 跨请求持久化。

    用法::

        injector = FileLinkInjector(server_host, server_port)

        # 流式输出循环中：只收集，不产出
        injector.feed(output, thread_id)

        # 流结束后：统一 flush
        for line in injector.flush():
            ...

        # 保存已报告的文件，供后续同 thread_id 的对话去重
        FileLinkInjector.save_reported(thread_id, injector.seen_files)
    """

    # 类级别存储：thread_id -> 已报告过的文件名集合
    _reported_store: dict[str, set[str]] = {}

    @classmethod
    def load_reported(cls, thread_id: str) -> set[str]:
        """获取指定 thread_id 已报告过的文件名集合。"""
        return cls._reported_store.get(thread_id, set()).copy()

    @classmethod
    def save_reported(cls, thread_id: str, files: set[str]):
        """保存指定 thread_id 已报告的文件名集合。"""
        cls._reported_store[thread_id] = files.copy()

    @classmethod
    def clear_reported(cls, thread_id: str):
        """清理指定 thread_id 的记录。"""
        cls._reported_store.pop(thread_id, None)

    def __init__(self, server_host: str, server_port: str | int,
                 existing_files: set[str] = None):
        self._host = server_host
        self._port = server_port
        self._thread_id: Optional[str] = None
        # _known: 用于去重（包含历史文件 + 本次已收集的）
        self._known: set[str] = set(existing_files) if existing_files else set()
        # _new: 仅本次对话中新检测到的，flush 时输出
        self._new: set[str] = set()
        # _content_accum: 累积所有 0: content 文本，应对跨 chunk 路径
        self._content_accum: str = ""

    @property
    def seen_files(self) -> set[str]:
        """本次对话中最终要输出的文件名集合（合并已知 + 本次新增）。"""
        return self._known.copy()

    def feed(self, output: str, thread_id: str):
        """处理一行 process_event 输出，收集其中出现的文件路径。

        同时检测：
        - ``2:`` tool_end 事件的 output 字段（单次检查）
        - ``0:`` 模型 content — 累积后检查，避免路径跨 chunk 被切开
        """
        self._thread_id = thread_id
        self._collect_from(output, "2:", self._extract_tool_output)

        # 累积 0: content，然后在完整文本上做正则
        if output.startswith("0:"):
            try:
                text = json.loads(output[2:])
                if isinstance(text, str) and text:
                    self._content_accum += text
                    for fname in _extract_generated_files(self._content_accum):
                        if fname not in self._known:
                            self._known.add(fname)
                            self._new.add(fname)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tool_output(payload) -> str:
        """从 tool_end payload 中提取 output 字段文本。"""
        items = json.loads(payload)
        items = items if isinstance(items, list) else [items]
        for item in items:
            if isinstance(item, dict) and item.get("type") == "tool_end":
                return item.get("output", "") or ""
        return ""

    def _collect_from(self, output: str, prefix: str, extractor) -> None:
        """从指定标签的输出中检测文件路径（适用于非累积型来源如 tool_end）。"""
        if not output.startswith(prefix):
            return
        try:
            text = extractor(output[2:])
            if not text:
                return
            for fname in _extract_generated_files(text):
                if fname not in self._known:
                    self._known.add(fname)
                    self._new.add(fname)
        except Exception:
            pass

    def flush(self, sandbox_backend=None) -> list[str]:
        """流结束时返回本次对话中新文件的下载链接行（0: 格式）。

        Args:
            sandbox_backend: 沙箱后端实例（可选）。提供时直接查询 /workspace 目录，
                将正则匹配遗漏的文件一并补上下载链接。

        Returns:
            需要发送给前端的行列表；无新文件时返回空列表。
        """
        if not self._host or not self._port:
            return []

        # ★ 兜底：直接查询沙箱 /workspace 目录，捕获正则匹配遗漏的文件
        if sandbox_backend is not None:
            try:
                entries = sandbox_backend.ls_info("/workspace")
                for entry in entries:
                    if entry.get("is_dir"):
                        continue
                    display_path = entry.get("path", "")
                    fname = display_path.rsplit("/", 1)[-1] if "/" in display_path else display_path
                    if not fname or fname in self._known:
                        continue
                    # 排除 temp 目录下的临时上传文件
                    if display_path.startswith("temp/") or "/temp/" in display_path:
                        continue
                    self._known.add(fname)
                    self._new.add(fname)
                if self._new:
                    logger.info(
                        "[FileLinkInjector] sandbox fallback: %d new files detected: %s",
                        len(self._new), self._new,
                    )
            except Exception as e:
                logger.warning("[FileLinkInjector] sandbox fallback failed: %s", e)

        if not self._new:
            return []

        links = [
            f"[{fn}]"
            f"(http://{self._host}:{self._port}"
            f"/skill/api/files/{urllib.parse.quote(fn)}"
            f"?session_thread_id={self._thread_id})"
            for fn in sorted(self._new)
        ]
        inject_msg = f"\n\n生成的文件：{' '.join(links)}"
        logger.info("[FileLinkInjector] flush inject_msg: %s", inject_msg)
        return [f"0:{json.dumps(inject_msg, ensure_ascii=False)}\n"]
