"""
Tool agent utilities module.
Provides helper functions and utilities for the tool agent system.
"""
import asyncio
import logging

from src.core.tool_agent.tool_agent_engine import ToolAgentEngine

logger = logging.getLogger(__name__)

def initialize_tool_agent() -> ToolAgentEngine:
    # 获取ToolAgentEngine实例
    engine = ToolAgentEngine.get_instance()

    # 创建新的事件循环来运行异步初始化
    init_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(init_loop)
    try:
        init_loop.run_until_complete(engine.ensure_initialized())
    except Exception as e:
        logger.exception(f"详细异常信息: {str(e)}")
    finally:
        init_loop.close()

    return engine

