import json
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, RemoveMessage
from src.langgraph_agent.travel_planner.core.llm import llm
from src.langgraph_agent.travel_planner.agents.info_collection_agent import info_collection_agent
from src.langgraph_agent.travel_planner.agents.itinerary_planner_agent import itinerary_planner_agent
from src.langgraph_agent.travel_planner.states.travel_state import AgentState
from src.langgraph_agent.common.utils.travel_api_response import search_user_info
from src.langgraph_agent.common.utils.handle_user_intent import is_user_switch

def clear_stage_node(state: AgentState):
    messages = state.get("messages", [])
    last_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_msg = msg.content
            break
    if is_user_switch(last_msg):
        # true: 清空 state 全部内容
        return {
            "messages": [RemoveMessage(id=msg.id) for msg in state.get("messages", [])],
            "userInfo": {},
            "todos": [],
            "final_planning_result": "",
            "final_planning_confirmed": False,
            "stage": ""
        }
    else:
        # false: 只清空 userInfo 中的出发地、目的地、出发日期、返程日期
        user_info = state.get("userInfo", {}).copy()
        for key in ["departure", "destination", "departure_date", "return_date"]:
            user_info.pop(key, None)
        return {
            "messages": [RemoveMessage(id=msg.id) for msg in state.get("messages", [])],
            "userInfo": user_info,
            "todos": [],
            "final_planning_result": "",
            "final_planning_confirmed": False,
            "stage": ""
        }

async def search_user_info_node(state: AgentState):
    # 调用工具获取用户信息
    # 使用同步调用方式
    tool_result = search_user_info()
    try:
        result_data = json.loads(tool_result)
        if result_data.get("status") == "success":
            user_info = result_data.get("user_info", {})
                
            # 更新 state 中的 userInfo 字段
            return {
                "messages": state.get("messages", []),
                "userInfo": user_info,
                "final_planning_result": state.get("final_planning_result", ""),
                "final_planning_confirmed": state.get("final_planning_confirmed", False),
                "stage": "信息查询"  
            }
        else:
            return {
                "messages": state.get("messages", []),
                "userInfo": state.get("userInfo", {}),
                "final_planning_result": state.get("final_planning_result", ""),
                "final_planning_confirmed": state.get("final_planning_confirmed", False),
                "stage": "信息查询"  
            }
    except Exception as e:
        return {
            "messages": state.get("messages", []),
            "userInfo": state.get("userInfo", {}),
            "final_planning_result": state.get("final_planning_result", ""),
            "final_planning_confirmed": state.get("final_planning_confirmed", False),
            "stage": "信息查询"  
        }

async def collection_node(state: AgentState):
    # 创建包含用户信息的系统消息
    user_info = state.get("userInfo", {})
    if user_info:
        user_info_msg = AIMessage(
            content=f"已获取到以下用户信息：{json.dumps(user_info, ensure_ascii=False)}"
        )
        # 创建一个新的 state 副本，只包含新的系统消息
        agent_state = {
            **state,
            "messages": state.get("messages", []) + [user_info_msg]
        }
    else:
        agent_state = state
    
    # 调用 Agent
    result = await info_collection_agent.ainvoke(agent_state)
    
    # 保留现有的所有 State 字段值
    updated_state = {
        "messages": result["messages"],
        "userInfo": state.get("userInfo", {}),
        "todos": state.get("todos", []),
        "final_planning_result": state.get("final_planning_result", ""),
        "final_planning_confirmed": state.get("final_planning_confirmed", False),
        "stage": "信息收集"  
    }
    
    # 从工具结果中提取新数据，覆盖对应字段
    messages = result["messages"]
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "extract_and_update_info":
            try:
                tool_result = json.loads(msg.content)
                if tool_result.get("status") == "success":
                    extracted = tool_result.get("extracted", {})
                    # 更新 State 中的userInfo字段
                    for key, val in extracted.items():
                        if val:
                            updated_state["userInfo"][key] = val
                break
            except:
                pass
    
    return updated_state

async def itinerary_planner_node(state: AgentState):
    # 获取完整的消息历史
    messages = state.get("messages", [])
    user_info = state.get("userInfo", {})
    last_message = messages[-1]
    if last_message and hasattr(last_message, "content"):
        if last_message.content.strip().endswith("COLLECTION_FINISHED"):
            # 构造用户描述模板
            user_desc = (
                f"员工{user_info.get('username', '')}（联系电话 {user_info.get('phone', '')}，"
                f"身份证号 {user_info.get('id_card', '')}）计划于 "
                f"{user_info.get('departuature_date', '')} 从{user_info.get('departure', '')}出发"
                f"前往{user_info.get('destination', '')}，"
                f"{user_info.get('destination_date', '')} 返程，"
                f"票务标准为{user_info.get('flight_ticket_standard', '')}机票、"
                f"{user_info.get('rail_ticket_standard', '')}火车票，"
                f"住宿标准为 {user_info.get('hotel_standard', '')}。"
            )
            # 清空state的messages，只保留新的用户描述消息
            agent_input = {
                **state,
                "messages": [HumanMessage(content=user_desc)]
            }
        else:
            agent_input = {
                **state,
                "messages": messages
            }
    # 调用行程规划Agent
    result = await itinerary_planner_agent.ainvoke(agent_input)
    
    # 从结果中提取行程规划内容作为最终规划结果
    final_planning_content = ""
    updated_messages = result["messages"]
    if updated_messages:
        last_updated_message = updated_messages[-1]
        if hasattr(last_updated_message, "content"):
            final_planning_content = last_updated_message.content
    # 判断final_planning_content是否以"PLAN_FINISHED"结束
    is_plan_finished = final_planning_content.strip().endswith("PLAN_FINISHED")
    if is_plan_finished:
        # 行程规划完成，更新状态为订单确认
        stage = "订单确认"
    else:
        # 行程规划未完成，更新状态为行程规划
        stage = "行程规划"
        final_planning_content = ""
    # 更新状态，包含行程规划结果和完整的消息历史
    updated_state = {
        "messages": updated_messages,  # 保留完整消息历史
        "userInfo": user_info,
        "todos": result.get("todos", []) or state.get("todos", []),
        "final_planning_result": final_planning_content,
        "final_planning_confirmed": state.get("final_planning_confirmed", False),
        "stage": stage  
    }
    return updated_state

async def order_confirmation_node(state: AgentState):
    # 从状态中获取行程规划结果
    messages = state.get("messages", [])
    
    # 使用interrupt机制等待用户输入
    from langgraph.types import interrupt
    from langchain_core.messages import HumanMessage
    from langchain_core.callbacks.manager import adispatch_custom_event
    updated_state = {
        "messages": messages,
        "userInfo": state.get("userInfo", {}),
        "final_planning_result": state.get("final_planning_result", ""),
        "final_planning_confirmed": False,
        "stage": "订单确认"  
    }
    isEndWithPlanFinished = state.get("final_planning_result", "").strip().endswith("PLAN_FINISHED")    
    
    # 发送自定义interrupt事件
    await adispatch_custom_event(
        "interrupt",
        {
            "message": {
                "content": "请确认您的行程安排，是否进行订单预订？",
                "isInterrupt": "true",
                "okText": "确认预订",
                "cancelText": "取消预订"
            } if isEndWithPlanFinished else {
                "content": "请确认您的行程安排，是否进行订单预订？",
                "isInterrupt": "false",
                "okText": "确认预订",
                "cancelText": "取消预订"
            }
        }
    )
    # 调用interrupt()函数暂停执行，等待用户输入
    # 当恢复执行时，用户的回复将作为interrupt()的返回值
    user_response = interrupt("请确认您的行程安排，并进行订单预订")
    
    # 将用户回复添加到messages列表中
    updated_state["messages"] = updated_state["messages"] + [HumanMessage(content=user_response)]
    last_user_msg = user_response.strip()
    # 根据用户回复更新状态
    if last_user_msg == "确认预订":
        updated_state["final_planning_confirmed"] = True
    elif last_user_msg == "取消预订":
        updated_state["final_planning_confirmed"] = False
    
    return updated_state

async def mark_all_tasks_complete_node(state: AgentState):
    # 获取最后一条消息
    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    
    # 从state中获取todos列表
    todos = state.get("todos", [])
    
    # 检查最后一条消息的content是否以PLAN_FINISHED结束
    is_plan_finished = False
    if last_message and hasattr(last_message, "content"):
        is_plan_finished = last_message.content.strip().endswith("PLAN_FINISHED")
    
    # 只有当is_plan_finished为True时，才将所有任务的状态更新为completed
    updated_todos = []
    for task in todos:
        updated_task = task.copy()
        if is_plan_finished:
            updated_task["status"] = "completed"
        updated_todos.append(updated_task)
    
    # 返回更新后的状态
    return {
        "messages": state.get("messages", []),
        "userInfo": state.get("userInfo", {}),
        "todos": updated_todos,
        "final_planning_result": state.get("final_planning_result", ""),
        "final_planning_confirmed": state.get("final_planning_confirmed", False),
        "stage": state.get("stage", "")
    }

async def order_operation_node(state: AgentState):
    # 订单操作节点：处理预订订单的逻辑
    final_planning_result = state.get("final_planning_result", "")
    final_planning_confirmed = state.get("final_planning_confirmed", False)
    
    # 这里可以添加实际的订单预订逻辑
    # 例如调用订单服务API、保存订单信息等
    
    # 更新状态，设置订单已预订标记
    return {
        "messages": state.get("messages", []),
        "userInfo": state.get("userInfo", {}),
        "todos": state.get("todos", []),
        "final_planning_result": final_planning_result,
        "final_planning_confirmed": final_planning_confirmed,
        "stage": "行程总结"
    }

async def summary_node(state: AgentState):
    # 获取final_planning_result和final_planning_confirmed的值
    final_planning_result = state.get("final_planning_result", "")
    final_planning_confirmed = state.get("final_planning_confirmed", False)
    # 根据final_planning_confirmed的值生成不同的内容
    if final_planning_confirmed:
        # 确认状态：生成以"已为您预订行程"为开始的确认单
        prompt = f"""
基于以下行程规划内容：
{final_planning_result}
生成一份清晰规整的表格形式行程确认单（信息图），需严格遵循以下要求：
1. 固定开篇第一句：已为您预订行程
2. 内容极致简洁，仅完整呈现行程内的全部核心事实信息，不添加任何建议、贴士、补充说明类文字
3. **必须完整保留并清晰排版展示行程中接驳路线规划的全部细节，以及对应的地图链接完整内容**，该部分信息不可省略、不可简化
4. 表格需将行程信息进行合理分类陈列，包含上述行程规划里的所有内容，无任何信息遗漏
5. 整体表述保持专业、礼貌、友好的正式语气，纯客观事实罗列
"""
    else:
        # 未确认状态：只总结行程内容
        prompt = f"""
基于以下行程规划内容：
{final_planning_result}
生成一份清晰规整的表格形式行程确认单（信息图），需严格遵循以下要求：
1. 固定开篇第一句：帮您总结了以下行程规划内容
2. 内容极致简洁，仅完整呈现行程内的全部核心事实信息，不添加任何建议、贴士、补充说明类文字
3. **必须完整保留并清晰排版展示行程中接驳路线规划的全部细节，以及对应的地图链接完整内容**，该部分信息不可省略、不可简化
4. 表格需将行程信息进行合理分类陈列，包含上述行程规划里的所有内容，无任何信息遗漏
5. 整体表述保持专业、礼貌、友好的正式语气，纯客观事实罗列
"""
    # 调用LLM生成结果
    res = await llm.ainvoke(prompt)
    
    updated_state = {
        "messages": [res],
        "final_planning_result": res.content,
        "final_planning_confirmed": final_planning_confirmed,
        "stage": "行程总结"  
    }
    return updated_state


