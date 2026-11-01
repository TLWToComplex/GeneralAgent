import asyncio
import uvicorn
import logging
import time
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel, Field
import mimetypes
import urllib.parse

# 导入必要的模块
from admin_server import app as flask_app
from src.controllers.sandbox_controller import sandbox_controller
from src.controllers.ai_chat_controller import AIChatController
from src.controllers.deepagent_file_controller import deepagent_file_controller
from src.utils.config_manager import config_manager
from src.utils.stream_hub import stream_hub, run_producer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 获取logger
logger = logging.getLogger(__name__)

# 注意：当此 app 被 mount 到 main.py 时，lifespan 不会独立执行
# 沙盒清理调度器由 main.py 的 main_lifespan 统一管理
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    messages: List[dict]
    session_thread_id: str = Field(None, alias="sessionThreadId")  # 支持 camelCase
    file_paths: List[str] = []
    uuid: str = None
    user_id: str = None
    turn_id: str = None

    class Config:
        populate_by_name = True  # 允许同时使用字段名和别名


class SandboxRequest(BaseModel):
    session_thread_id: str


def _extract_token_from_header(authorization: Optional[str] = Header(None, alias="Authorization"),
                                x_access_token: Optional[str] = Header(None, alias="X-ACCESS-TOKEN")) -> Optional[str]:
    """从请求头中提取 token，参考 jwt_required 的逻辑"""
    if authorization and authorization.startswith('Bearer '):
        return authorization[len('Bearer '):]
    if x_access_token:
        return x_access_token
    return None


@app.post("/api/deepagent/chat")
async def chat_with_deepagent(request: ChatRequest,
                              authorization: Optional[str] = Header(None, alias="Authorization"),
                              x_access_token: Optional[str] = Header(None, alias="X-ACCESS-TOKEN")):
    """
    使用已创建的沙盒处理聊天请求/或者重新创建沙盒来处理聊天请求
    """
    token = _extract_token_from_header(authorization, x_access_token)
    start_time = time.time()
    logger.info(f"收到聊天请求: {start_time}")

    # 1. 验证 session_thread_id
    session_thread_id = request.session_thread_id
    if not session_thread_id:
        end_time = time.time()
        logger.info(f"请求处理完成: {end_time}, 耗时: {end_time - start_time}秒, 状态: 缺少 session_thread_id")
        return {"code": 400, "message": "缺少 session_thread_id 参数"}

    # 2. 验证 uuid
    if not request.uuid:
        return {"code": 400, "message": "缺少 uuid 参数"}

    # 3. user_uuid（用于 per-user 记忆隔离）
    # 注意：仅 deepagent 使用记忆，user_uuid 缺失不阻断对话，但会跳过记忆挂载
    user_uuid = request.user_id
    if user_uuid:
        logger.info(f"对话用户 user_uuid={user_uuid}")
    else:
        logger.info("无用户ID，对话将以无记忆模式运行")

    # 4. 转换输入消息格式
    messages = []
    for msg in request.messages:
        # 添加文件路径信息
        if request.file_paths:
            temp_dir = config_manager.get_temp_dir()
            file_info = f"\n\n上传的文件 {', '.join(request.file_paths)} 位于 {temp_dir} 文件夹中，请在该文件夹下寻找对应文件。"
            messages.append({"role": "user", "content": msg["content"] + file_info})
        else:
            messages.append(msg)

    # 5. StreamHub 占坑：已有活跃流（starting/running）时不启动新任务，直接 attach 订阅
    # 注意：claim 必须在 await controller 之前同步调用（prepare 含沙盒创建等慢操作，
    # 期间用户重试/双开标签页的第二次请求应 attach 而非双开任务）
    stream, is_new = stream_hub.claim(session_thread_id, request.turn_id or "")
    if not is_new:
        logger.info(f"[hub] session={session_thread_id} 已有活跃流(turn={stream.turn_id})，"
                    f"本次请求(turn={request.turn_id})直接 attach")
        if request.turn_id and stream.turn_id and request.turn_id != stream.turn_id:
            logger.warning(f"[hub] attach 时 turn_id 不一致: 请求={request.turn_id}, 活跃={stream.turn_id}")
        return StreamingResponse(
            stream_hub.subscribe(session_thread_id),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
        )

    # 6. 调用 controller 方法获取异步生成器
    # 使用 Flask app_context 来访问数据库（DB 访问全部发生在 await controller 期间；
    # 生成器的实际消费在后台任务中进行，无需 app_context，
    # ChatRecordCollector.finalize 等落库逻辑自带 context 检查）
    try:
        with flask_app.app_context():
            # chat_with_deepagent 是 async 函数，需要 await 来获取生成器对象
            async_generator = await AIChatController.chat_with_deepagent(
                request.uuid, messages, session_thread_id, user_uuid=user_uuid, token=token, turn_id=request.turn_id
            )
    except Exception as e:
        stream_hub.abort(session_thread_id)  # 准备失败必须清坑，避免后续请求 attach 到死流
        logger.error(f"Error in chat_with_deepagent: {e}")
        return {"code": 500, "message": f"Internal server error: {str(e)}"}

    # 7. 交给后台任务执行（客户端断开 SSE 不影响任务），本请求作为第一个订阅者
    task = asyncio.create_task(
        run_producer(stream_hub, session_thread_id, async_generator),
        name=f"turn-{session_thread_id}"
    )
    stream_hub.attach_task(session_thread_id, task)
    return StreamingResponse(
        stream_hub.subscribe(session_thread_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )

@app.post("/api/agent/chat")
async def chat_with_agent(request: ChatRequest):
    """
    普通 Agent 对话接口（FastAPI 异步版本）
    """

    # 获取agent UUID和对话信息
    agent_uuid = request.uuid
    messages = request.messages
    
    # 如果前端没有传入 session_thread_id，使用 uuid 作为会话 ID
    session_thread_id = request.session_thread_id or agent_uuid
    logger.info(f"[server] 最终使用的 session_thread_id={session_thread_id}")
    # StreamHub 占坑：已有活跃流（starting/running）时不启动新任务，直接 attach 订阅
    stream, is_new = stream_hub.claim(session_thread_id, request.turn_id or "")
    if not is_new:
        logger.info(f"[hub] session={session_thread_id} 已有活跃流(turn={stream.turn_id})，"
                    f"本次请求(turn={request.turn_id})直接 attach")
        if request.turn_id and stream.turn_id and request.turn_id != stream.turn_id:
            logger.warning(f"[hub] attach 时 turn_id 不一致: 请求={request.turn_id}, 活跃={stream.turn_id}")
        return StreamingResponse(
            stream_hub.subscribe(session_thread_id),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
        )

    # 使用 Flask app_context 来访问数据库（DB 访问全部发生在 await controller 期间；
    # 生成器的实际消费在后台任务中进行，无需 app_context）
    try:
        with flask_app.app_context():
            # chat_with_agent_async 是 async 函数，需要 await 来获取生成器对象
            async_generator = await AIChatController.chat_with_agent_async(
                agent_uuid, messages, session_thread_id, user_uuid=request.user_id, turn_id=request.turn_id
            )
    except Exception as e:
        stream_hub.abort(session_thread_id)  # 准备失败必须清坑，避免后续请求 attach 到死流
        logger.error(f"Error in chat_with_agent: {e}")
        return {"code": 500, "message": f"Internal server error: {str(e)}"}

    # 交给后台任务执行（客户端断开 SSE 不影响任务），本请求作为第一个订阅者
    task = asyncio.create_task(
        run_producer(stream_hub, session_thread_id, async_generator),
        name=f"turn-{session_thread_id}"
    )
    stream_hub.attach_task(session_thread_id, task)
    return StreamingResponse(
        stream_hub.subscribe(session_thread_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )

@app.post("/api/deepagent/create")
async def create_sandbox(request: SandboxRequest):
    """
    创建沙盒
    """
    session_thread_id = request.session_thread_id
    if not session_thread_id:
        return {"code": 400, "message": "缺少 session_thread_id 参数"}

    # 使用 Flask app_context 来访问数据库
    # 注意：创建 Docker 容器是慢操作，放入线程池执行，避免阻塞事件循环
    with flask_app.app_context():
        result, status_code = await asyncio.to_thread(
            sandbox_controller.create_sandbox, session_thread_id
        )
        return result

@app.post("/api/deepagent/release")
async def release_sandbox(request: SandboxRequest):
    """
    释放沙盒
    """
    session_thread_id = request.session_thread_id
    if not session_thread_id:
        return {"code": 400, "message": "缺少 session_thread_id 参数"}

    # 使用 Flask app_context 来访问数据库
    # 注意：停止/删除 Docker 容器是慢操作（最长可等待 30 秒），放入线程池执行
    with flask_app.app_context():
        result, status_code = await asyncio.to_thread(
            sandbox_controller.release_sandbox, session_thread_id
        )
        return result

@app.post("/api/chat/interrupt")
async def interrupt_chat(request: SandboxRequest):
    """
    中断正在进行的对话（通用接口，支持 DeepAgent 和普通 Agent）
    """
    session_thread_id = request.session_thread_id
    if not session_thread_id:
        return {"code": 400, "message": "缺少 session_thread_id 参数"}

    # 设置中断标志
    from src.utils.interrupt_utils import set_interrupt_flag
    set_interrupt_flag(session_thread_id)
    logger.info(f"收到中断请求: {session_thread_id}")
    
    return {"code": 0, "message": "中断请求已发送"}


@app.get("/api/chat/stream/resume")
async def resume_chat_stream(
        session_thread_id: str = Query(..., description="会话线程 ID")):
    """重连/续订对话任务的输出流（SSE 断线重连，全量回放）。

    - 本轮未结束（starting/running）：从内存全量回放本轮事件（与原始流格式
      完全一致，无附加结构），随后无缝转入实时，直到流关闭（流关闭即本轮
      已结束并落库）；
    - 无活跃流（已结束清除 / 从未开始）：返回 404，前端应兜底查询已落库
      的对话记录。

    前端回放前需清空本轮 assistant 消息的进行中渲染。
    """
    stream = stream_hub.get(session_thread_id)
    if stream is None or not stream.is_active:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "no active stream",
                     "data": {"exists": False}})
    logger.info(f"[hub] resume 请求: session={session_thread_id}")

    return StreamingResponse(
        stream_hub.subscribe(session_thread_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    )


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


@app.get("/api/files/list")
async def list_files(
        session_thread_id: Optional[str] = Query(None, description="会话线程 ID，用于指定沙盒")):
    """列出沙箱 /workspace 目录下已生成的文件（排除 temp 子目录）。

    前端可调用此接口构建文件浏览器，作为聊天流中文本注入下载链接的兜底方案。
    """
    try:
        if not session_thread_id:
            raise HTTPException(status_code=400, detail="Missing session_thread_id parameter")

        server_host = config_manager.get_public_host()
        server_port = config_manager.get_public_port()

        # 文件扫描涉及 Docker exec（阻塞 I/O），放入线程池执行
        result = await asyncio.to_thread(
            lambda: deepagent_file_controller.list_workspace_files(
                session_thread_id=session_thread_id,
                server_host=server_host,
                server_port=server_port,
            )
        )

        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出工作区文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{filename}")
async def download_file(filename: str,
                        session_thread_id: Optional[str] = Query(None, description="会话线程 ID，用于指定沙盒")):
    try:
        # Prevent path traversal
        logger.info(f"Downloading file1: {filename} from sandbox: {session_thread_id}")
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        logger.info(f"Downloading file2: {filename} from sandbox: {session_thread_id}")
        # 选择后端实例
        if not session_thread_id:
            raise HTTPException(status_code=400, detail="Missing session_thread_id parameter")
        logger.info(f"Downloading file3: {filename} from sandbox: {session_thread_id}")
        # 使用沙盒后端（会自动创建）
        # 注意：沙盒不存在时会同步创建 Docker 容器（慢操作），
        # 放入线程池执行，避免阻塞事件循环影响其它接口
        target_backend = await asyncio.to_thread(
            sandbox_controller.get_sandbox_backend, session_thread_id
        )
        logger.info(f"Downloading file: {filename} from sandbox: {session_thread_id}")
        # Use simple filename as path, let backend handle resolution to work_dir
        responses = await asyncio.to_thread(target_backend.download_files, [filename])

        if not responses:
            raise HTTPException(status_code=404, detail="File not found")

        file_response = responses[0]
        # Check for error attribute if it exists
        if hasattr(file_response, 'error') and file_response.error:
            # Check for specific error types if possible, or generic 404
            if "not found" in str(file_response.error).lower():
                raise HTTPException(status_code=404, detail=f"File not found: {file_response.error}")
            raise HTTPException(status_code=500, detail=f"Error reading file: {file_response.error}")

        content = file_response.content

        media_type, _ = mimetypes.guess_type(filename)
        if not media_type:
            media_type = "application/octet-stream"

        # Encode filename for Content-Disposition header
        encoded_filename = urllib.parse.quote(filename)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    健康检查
    """
    return {
        "status": "healthy",
        "service": "skill-agent"
    }

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...),
        session_thread_id: Optional[str] = Query(None, description="会话线程 ID，用于指定沙盒"),
        turn_id: Optional[str] = Query(None, description="对话轮次 ID")
):
    """
    上传文件到沙盒的临时目录
    """
    try:
        # 验证 session_thread_id
        if not session_thread_id:
            raise HTTPException(status_code=400, detail="Missing session_thread_id parameter")

        # 读取文件内容
        content = await file.read()

        # 调用文件控制器上传文件
        # 注意：内部会获取沙盒后端（不存在时自动创建 Docker 容器，慢操作），
        # 放入线程池执行，避免阻塞事件循环
        upload_result = await asyncio.to_thread(
            lambda: deepagent_file_controller.upload_file_to_sandbox(
                session_thread_id=session_thread_id,
                file_content=content,
                filename=file.filename,
                turn_id=turn_id,
            )
        )

        return {
            "code": 0,
            "message": "success",
            "data": upload_result
        }
    except Exception as e:
        if "Sandbox not found" in str(e):
            raise HTTPException(status_code=404, detail="Sandbox not found")
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/{filename}")
async def delete_file(filename: str,
        session_thread_id: Optional[str] = Query(None, description="会话线程 ID，用于指定沙盒")
):
    """
    从沙盒的临时目录删除文件
    """
    try:
        # 验证 session_thread_id
        if not session_thread_id:
            raise HTTPException(status_code=400, detail="Missing session_thread_id parameter")

        # Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # 调用文件控制器删除文件（涉及 Docker exec 阻塞 I/O，放入线程池执行）
        delete_result = await asyncio.to_thread(
            lambda: deepagent_file_controller.delete_file_from_sandbox(
                session_thread_id=session_thread_id,
                filename=filename
            )
        )

        return {
            "code": 0,
            "message": "success",
            "data": delete_result
        }
    except Exception as e:
        if "Sandbox not found" in str(e):
            raise HTTPException(status_code=404, detail="Sandbox not found")
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# cd XXX/ai-service-backend (root folder)
# python -m src.deepagent.server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8101)
