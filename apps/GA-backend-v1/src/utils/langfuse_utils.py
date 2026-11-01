import json
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def _patch_langfuse_serialize():
    """Monkey-patch Langfuse SDK 的 _serialize 函数，添加 ensure_ascii=False。

    Langfuse SDK 内部使用 json.dumps(obj, cls=EventSerializer) 序列化
    trace 的 input/output，默认 ensure_ascii=True 会将中文转为 \\uXXXX，
    导致 Langfuse UI 中无法用中文搜索。此补丁在模块导入时自动修复。
    """
    try:
        import langfuse._client.attributes as _attrs
        from langfuse._utils.serializer import EventSerializer

        def _serialize_fixed(obj):
            if obj is None or isinstance(obj, str):
                return obj
            return json.dumps(obj, cls=EventSerializer, ensure_ascii=False)

        _attrs._serialize = _serialize_fixed
        logger.debug("已 patch Langfuse _serialize，中文将保留原文而非 \\uXXXX")
    except Exception as e:
        logger.debug(f"Patch Langfuse _serialize 失败（不影响功能）: {e}")


# 模块导入时自动执行 patch
_patch_langfuse_serialize()


def _is_enabled() -> bool:
    return os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"


def get_langfuse_handler():
    """按需创建 Langfuse CallbackHandler，兼容 v2 / v3+。

    返回 None 表示未启用或 SDK 不可用，此时调用方应跳过 callback 注入。
    """
    if not _is_enabled():
        return None
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except ImportError:
        pass
    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler()
    except ImportError:
        logger.warning("Langfuse 已启用但 SDK 未安装，trace 不会上报。请执行 pip install -r requirements.txt")
        return None
    except Exception as e:
        logger.warning(f"创建 Langfuse CallbackHandler 失败: {e}")
        return None


def _get_propagate_attributes():
    try:
        from langfuse import propagate_attributes
        return propagate_attributes
    except Exception as e:
        logger.debug(f"Langfuse propagate_attributes 不可用: {e}")
        return None


@contextmanager
def langfuse_trace_context(name: str,
                           user_id: str = None,
                           session_id: str = None,
                           metadata: dict = None):
    """通过 propagate_attributes 注入 user/session。
    """
    if not _is_enabled():
        yield None
        return

    propagate_attributes = _get_propagate_attributes()
    if propagate_attributes is None:
        logger.debug("当前 Langfuse SDK 不支持 propagate_attributes，user/session 不会写入 trace")
        yield None
        return

    uid = str(user_id) if user_id else "anonymous"
    sid = str(session_id) if session_id else "unknown_session"

    try:
        cm = propagate_attributes(user_id=uid, session_id=sid, trace_name=name, metadata=metadata)
    except Exception as e:
        logger.debug(f"Langfuse propagate_attributes 调用失败: {e}")
        yield None
        return

    with cm:
        yield None
