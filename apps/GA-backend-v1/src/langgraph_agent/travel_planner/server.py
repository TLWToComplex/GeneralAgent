import asyncio
import json
import logging
import threading
import uuid
import uvicorn
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.accessors.ai_user_accessor import AIUser
from src.accessors.ai_user_group_accessor import ai_user_group_accessor
from src.accessors.ai_user_group_relation_accessor import ai_user_group_relation_accessor
from src.config import TravelPlannerConfig
from src.langgraph_agent.travel_planner.graphs.travel_graph import get_travel_graph, cleanup_checkpointer
from src.langgraph_agent.common.utils.astream_events_tools import process_event
from src.utils.langfuse_utils import get_langfuse_handler, langfuse_trace_context
from src.utils.chat_record_collector import ChatRecordCollector, extract_last_user_question, extract_last_user_images
from src.utils.stream_hub import stream_hub, run_producer
from src.utils.interrupt_utils import check_interrupt, clear_interrupt_flag


logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize graph on server startup
    await get_travel_graph()
    yield
    # Shutdown: Cleanup if needed
    await cleanup_checkpointer()

class ChatRequest(BaseModel):
    messages: List[dict]
    session_thread_id: str = None
    user_id: str = None  # 可选字段，用于 Langfuse trace 的 user_id
    turn_id: str = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. 转换输入消息
    langchain_messages = []
    for m in request.messages:
        if m["role"] == "user":
            langchain_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            langchain_messages.append(AIMessage(content=m["content"]))

    # 从请求中获取或生成thread_id
    thread_id = request.session_thread_id or str(uuid.uuid4())

    # StreamHub 占坑：帧原样透传（标签行协议保持不变，无附加结构）。
    # 注意：前端未传 session_thread_id 时 key 为服务端生成的 uuid，前端无从得知
    # → 无法 resume，建议前端总是传 session_thread_id
    # claim 必须先于 DB 查询等慢准备逻辑同步调用，保证并发请求不会双开任务
    stream, is_new = stream_hub.claim(thread_id, request.turn_id or "")
    if not is_new:
        logger.info(f"[hub] session={thread_id} 已有活跃流(turn={stream.turn_id})，"
                    f"本次请求(turn={request.turn_id})直接 attach")
        return StreamingResponse(
            stream_hub.subscribe(thread_id),
            media_type="application/x-ndjson")

    clear_interrupt_flag(thread_id)
    try:
        user_success, user_result = AIUser.get_user(uuid=request.user_id)
        user_name = user_result.get('username') if user_success else ''

        real_name = user_result.get('realname') if user_success else ''
        user_group_success, user_group_ids = ai_user_group_relation_accessor.get_user_groups_by_user_id(user_id=request.user_id)
        user_groups = []
        for user_group_id in user_group_ids:
            success, group_info = ai_user_group_accessor.get_user_group(group_uuid=user_group_id)
            if success:
                user_groups.append(str(group_info.get('name', '')))
        user_groups = ', '.join(user_groups)
        user_info = {'user_name': user_name, 'real_name': real_name, 'user_groups': user_groups}

        llm_config = {'model': TravelPlannerConfig.LLMConfig.MODEL_NAME,
                      'api_key': TravelPlannerConfig.LLMConfig.API_KEY,
                      'base_url': TravelPlannerConfig.LLMConfig.API_BASE_URL}

        # 对话记录采集器（travel_planner 类型，无 agent_id）
        record_collector = ChatRecordCollector(
            chat_type='travel_planner',
            user_id=request.user_id,
            user_name=user_name,
            session_thread_id=thread_id,
            agent_id='',
            turn_id=request.turn_id or '',
            user_question=extract_last_user_question(request.messages),
            user_images=extract_last_user_images(request.messages),
            llm_config=llm_config
        )
        threading.Thread(target=record_collector.summarize_first_question, daemon=True).start()
    except Exception:
        stream_hub.abort(thread_id)  # 准备失败必须清坑，避免后续请求 attach 到死流
        raise


    async def generate():
        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"TravelPlanner-{thread_id}",
        }
        langfuse_handler = get_langfuse_handler()
        logger.info(f"[TravelPlanner] langfuse_handler={langfuse_handler!r}")
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]
        travel_graph = await get_travel_graph()
        last_todos_fingerprint = {"value": None}
        last_stage = {"value": None}
        node_stage_by_name = {
            "search_user_info": "信息查询",
            "collection": "信息收集",
            "itinerary_planner": "行程规划",
            "order_confirmation": "订单确认",
            "summary": "行程总结",
        }

        # 检查用户是否回复了确认或取消
        last_user_msg = None
        if langchain_messages and isinstance(langchain_messages[-1], HumanMessage):
            last_user_msg = langchain_messages[-1].content

        # 直接判断用户回复是否为确认或取消，不依赖于获取当前节点状态
        if last_user_msg and (last_user_msg.strip() == "确认预订" or last_user_msg.strip() == "取消预订"):
            command = Command(resume=last_user_msg)
            message = command
        else:
            message = {"messages": langchain_messages}

        try:
            with langfuse_trace_context(
                name=f"TravelPlanner-{thread_id}",
                user_id=request.user_id,
                session_id=thread_id,
                metadata=user_info
            ):
                async for event in travel_graph.astream_events(message, config, version="v2"):
                    if check_interrupt(thread_id):
                        break
                    async for output in process_event(event, thread_id, node_stage_by_name, last_todos_fingerprint, last_stage):
                        # 累积对话记录（原始标签行）
                        record_collector.feed_line(output)
                        yield output
        finally:
            # 本轮对话结束，实时落库对话记录（幂等，失败不影响流式输出）
            record_collector.finalize()
            clear_interrupt_flag(thread_id)


    # 交给后台任务执行（客户端断开不影响任务与 record_collector.finalize 落库），
    # 本请求作为第一个订阅者
    task = asyncio.create_task(
        run_producer(stream_hub, thread_id, generate()),
        name=f"travel-turn-{thread_id}"
    )
    stream_hub.attach_task(thread_id, task)
    return StreamingResponse(
        stream_hub.subscribe(thread_id),
        media_type="application/x-ndjson")

@app.get("/api/chat/stream/resume")
async def resume_chat_stream(
        session_thread_id: str = Query(..., description="会话线程 ID")):
    """重连/续订 travel 对话输出流（断线重连，全量回放）。

    - 本轮未结束（starting/running）：从内存全量回放本轮事件（原样标签行
      0:"文本" / 1:"思考" / 2:[状态] / stage / todos，与原始流格式完全一致，
      无附加结构），随后无缝转入实时，直到流关闭（流关闭即本轮已结束并落库）；
    - 无活跃流（已结束清除 / 从未开始）：返回 404，前端兜底查已落库记录。

    前端回放前需清空本轮 assistant 消息的进行中渲染。
    """
    stream = stream_hub.get(session_thread_id)
    if stream is None or not stream.is_active:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "no active stream",
                     "data": {"exists": False}})
    return StreamingResponse(
        stream_hub.subscribe(session_thread_id),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@app.get("/api/chat/stream/status")
async def chat_stream_status(
        session_thread_id: str = Query(..., description="会话线程 ID")):
    """查询会话当前输出流状态（JSON），用于判断本轮对话是否结束。

    前端进入会话页 / 断线后可先调用本接口：
    - exists=true 且 status=running/starting → 本轮未结束，调 resume 接口
      全量回放 + 实时续订；
    - exists=false → 本轮已结束并落库（或从未开始），走已落库的对话记录。
    """
    data = stream_hub.status(session_thread_id)
    if data is None:
        return {"code": 0, "message": "success", "data": {"exists": False}}
    return {"code": 0, "message": "success", "data": data}


# cd XXX/ai-service-backend (root folder)
# python -m src.langgraph_agent.travel_planner.server
if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8100)