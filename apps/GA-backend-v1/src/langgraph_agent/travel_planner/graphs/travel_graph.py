import logging
import aiosqlite
from pathlib import Path
from src.config import TravelPlannerConfig

# TODO: 这是一个临时解决方案，等待langgraph修复这个问题。这个问题是因为langgraph在检查数据库连接是否存活时，调用了is_alive方法，而aiosqlite.Connection没有实现这个方法。
# 正确的解决方法是升级langgraph-checkpoint-sqlite==3.0.0或langgraph的包。
# Monkey patch aiosqlite.Connection for compatibility with langgraph
# See: https://github.com/langchain-ai/langgraph/issues/6583 issue太新，AS of 2025/12/23 该问题还OPEN。
if not hasattr(aiosqlite.Connection, "is_alive"):
    setattr(aiosqlite.Connection, "is_alive", lambda self: True)

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.langgraph_agent.travel_planner.states.travel_state import AgentState
from src.langgraph_agent.travel_planner.nodes.travel_nodes import collection_node, summary_node, search_user_info_node, itinerary_planner_node, order_confirmation_node, mark_all_tasks_complete_node, order_operation_node, clear_stage_node
from src.langgraph_agent.travel_planner.nodes.travel_nodes_router import start_router,collection_router,order_confirmation_router, itinerary_planner_router, compress_messages
logger = logging.getLogger(__name__)

workflow = StateGraph(AgentState)
workflow.add_node("search_user_info", search_user_info_node)
workflow.add_node("collection", collection_node)
workflow.add_node("compress_messages", compress_messages)
workflow.add_node("itinerary_planner", itinerary_planner_node)
workflow.add_node("mark_all_tasks_complete", mark_all_tasks_complete_node)
workflow.add_node("order_confirmation", order_confirmation_node)
workflow.add_node("order_operation", order_operation_node)
workflow.add_node("summary", summary_node)
workflow.add_node("clear_stage", clear_stage_node)

workflow.add_conditional_edges(START, start_router, {"search_user_info": "search_user_info", "compress_messages": "compress_messages", "clear_stage": "clear_stage"})
workflow.add_edge("search_user_info", "collection")
workflow.add_conditional_edges("collection", collection_router, {"compress_messages": "compress_messages", "__end__": END})
workflow.add_edge("compress_messages", "itinerary_planner")
workflow.add_conditional_edges("itinerary_planner", itinerary_planner_router, {"mark_all_tasks_complete": "mark_all_tasks_complete", "itinerary_planner": "itinerary_planner"})
workflow.add_edge("mark_all_tasks_complete", "order_confirmation")
workflow.add_conditional_edges("order_confirmation", order_confirmation_router, {"order_operation": "order_operation", "summary": "summary"})
workflow.add_edge("order_operation", "summary")
workflow.add_edge("summary", END)
workflow.add_edge("clear_stage", "collection")

# workflow.add_edge(START, "search_user_info")
# workflow.add_edge("search_user_info", "order_confirmation")
# workflow.add_conditional_edges("order_confirmation", order_confirmation_router, {"summary": "summary", "search_user_info": "search_user_info"})
# workflow.add_edge("summary", END)

# Store the context manager
_context = None
_checkpointer = None
_travel_graph = None


# TODO: The implementation for using AsyncSqliteSaver of async graph.astream() is fucking so complicated.
# 1. The checkpointer must be created in async context manager.
# 2. The checkpointer must be passed to graph.compile() in sync context.
# 3. The checkpointer must be cleaned up in async context manager.
# We are seeking for a better implementation
async def get_travel_graph():
    global _context, _checkpointer, _travel_graph
    if _travel_graph is None:
        db_path = TravelPlannerConfig.CheckpointConfig.PATH_LOCAL
        logger.info(f"The memory DB Path is: {db_path}")
        # Convert to absolute path and create parent directory
        db_path = str(Path(db_path).resolve())
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
         # Pass the plain file path (not the sqlite+aiosqlite:/// URI)
        _context = AsyncSqliteSaver.from_conn_string(db_path)
        _checkpointer = await _context.__aenter__()
        
        _travel_graph = workflow.compile(checkpointer=_checkpointer)
    return _travel_graph

async def cleanup_checkpointer():
    global _context
    if _context:
        await _context.__aexit__(None, None, None)
