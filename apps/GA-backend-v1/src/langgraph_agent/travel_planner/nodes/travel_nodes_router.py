from typing import Literal
from src.langgraph_agent.travel_planner.states.travel_state import AgentState
from langchain_core.messages import AIMessage, RemoveMessage, HumanMessage
from langchain_core.messages import ToolMessage

def start_router(state: AgentState) -> Literal["search_user_info", "compress_messages", "clear_stage"]:
    stage = state.get("stage", "")
    if stage == "行程规划":
        return "compress_messages"
    elif stage == "行程总结":
        return "clear_stage"
    else:
        return "search_user_info"

def collection_router(state: AgentState) -> Literal[ "compress_messages", "__end__"]:
    last_msg = state["messages"][-1]
    
    # 根据不同的条件决定路由
    if isinstance(last_msg, AIMessage):
        content = str(last_msg.content)
        
        # 如果信息收集完成，先进入删除消息阶段
        if "COLLECTION_FINISHED" in content:
            return "compress_messages"
    
    # 默认结束
    return "__end__"

def order_confirmation_router(state: AgentState) -> Literal["order_operation", "summary"]:
    last_msg = state["messages"][-1]
    # 判断最后一条消息是否为 HumanMessage 且为确认
    if isinstance(last_msg, HumanMessage) and str(last_msg.content).strip() == "确认预订":
            return "order_operation"
    return "summary"

def compress_messages(state: AgentState):
    messages = state["messages"]
    if not messages:
        return {"messages": [], "todos": state["todos"]}

    to_keep = []
    seen_human_content = set()  # 用于HumanMessage去重
    in_write_todos_context = False  # 跟踪是否在write_todos工具调用上下文中

    for m in messages:
        if isinstance(m, AIMessage):
            # 检查是否包含write_todos工具调用
            has_write_todos_call = False
            if hasattr(m, "tool_calls") and m.tool_calls:
                has_write_todos_call = any(
                    tool_call.get("name") == "write_todos" for tool_call in m.tool_calls
                )
            
            # 仅保留包含write_todos工具调用的AIMessage
            if has_write_todos_call:
                to_keep.append(m)
                in_write_todos_context = True  # 进入write_todos上下文
            else:
                in_write_todos_context = False
        
        elif isinstance(m, ToolMessage):
            # 仅保留write_todos上下文内的ToolMessage
            if in_write_todos_context:
                to_keep.append(m)
        
        elif isinstance(m, HumanMessage):
            content = str(m.content)
            # HumanMessage去重后保留所有
            if content not in seen_human_content:
                seen_human_content.add(content)
                to_keep.append(m)
            # 人类消息结束write_todos上下文
            in_write_todos_context = False

    # 构建要删除的消息列表
    to_remove = [m for m in messages if m not in to_keep]
    return {"messages": [RemoveMessage(id=m.id) for m in to_remove], "todos": state["todos"]}

def itinerary_planner_router(state: AgentState) -> Literal["mark_all_tasks_complete", "itinerary_planner"]:  
    last_msg = state["messages"][-1]
    # 检查最后一条消息内容
    if isinstance(last_msg, AIMessage):
        return "mark_all_tasks_complete"
    else:
        return "itinerary_planner"