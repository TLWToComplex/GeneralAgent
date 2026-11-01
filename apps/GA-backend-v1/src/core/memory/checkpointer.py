"""
Checkpointer 单例管理
提供全局复用的 AsyncSqliteSaver 实例
"""
import logging
import aiosqlite
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

# Monkey patch aiosqlite.Connection for compatibility with langgraph
# See: https://github.com/langchain-ai/langgraph/issues/6583
if not hasattr(aiosqlite.Connection, "is_alive"):
    setattr(aiosqlite.Connection, "is_alive", lambda self: True)

_context = None
_checkpointer = None


async def get_checkpointer(db_path: str = None) -> AsyncSqliteSaver:
    """获取或创建全局 checkpointer 单例

    Args:
        db_path: SQLite 数据库路径。首次调用时必须提供，后续调用可省略。

    Returns:
        AsyncSqliteSaver 实例
    """
    global _context, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    if db_path is None:
        raise ValueError("首次调用 get_checkpointer 必须提供 db_path 参数")

    db_path = str(Path(db_path).resolve())
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initializing checkpointer with DB: {db_path}")

    _context = AsyncSqliteSaver.from_conn_string(db_path)
    _checkpointer = await _context.__aenter__()

    return _checkpointer
