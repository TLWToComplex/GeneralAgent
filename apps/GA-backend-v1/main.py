"""
主应用程序入口点，集成了Flask管理服务器和FastAPI旅行规划器。
使用ASGI来支持WSGI（Flask）和ASGI（FastAPI）应用程序。
"""
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.config import ServerConfig, LogConfig

# 从admin_server导入Flask应用
from admin_server import app as flask_app

# 从各个服务导入FastAPI应用
from src.langgraph_agent.travel_planner.server import app as fastapi_travel_app
from src.deepagent.server import app as deepagent_fastapi_app
from src.controllers.ai_chat_record_controller import AIChatRecordController
from src.controllers.sandbox_controller import sandbox_controller
from src.utils.stream_hub import stream_hub
from src.config import LangfuseConfig

LangfuseConfig.configure_langfuse()

# 从配置文件读取日志级别
log_level_str = LogConfig.LEVEL.upper()
log_level = getattr(logging, log_level_str, logging.INFO)

# 配置日志
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger("main")

@asynccontextmanager
async def main_lifespan(app: FastAPI):
    """主应用的 lifespan，负责启动全局服务"""
    # 启动沙盒清理调度器
    sandbox_controller.start_scheduler()
    # 启动对话记录过期清理
    AIChatRecordController.start_cleanup_scheduler(flask_app)
    # 启动 Langfuse 数据过期清理
    AIChatRecordController.start_langfuse_cleanup_scheduler()
    yield
    # 停止沙盒清理调度器
    sandbox_controller.stop_scheduler()
    # 优雅收尾进行中的对话流后台任务（先等待 grace 秒，超时才取消）
    await stream_hub.shutdown(grace=10)

# 创建主FastAPI应用程序
main_app = FastAPI(
    title="AI Service Backend",
    description="Integrated Flask Admin + FastAPI Travel Planner + FastAPI Skill Agent",
    lifespan=main_lifespan
)

# 为主应用配置CORS
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 为根路径创建特殊路由用于信息展示
@main_app.get("/")
def root_info():
    return {
        "status": "running",
        "services": {
            "admin": "",  # 原始管理路由在根路径
            "travel_planner": "/travel",
            "deepagent": "/skill"
        }
    }

# 将FastAPI旅行规划器挂载到/travel路径
main_app.mount("/travel", fastapi_travel_app)

# 将FastAPI技能代理挂载到/skill路径
main_app.mount("/skill", deepagent_fastapi_app)

# 将Flask管理服务器挂载到根路径以保持原有路由
main_app.mount("/", WSGIMiddleware(flask_app))

if __name__ == "__main__":
    # 使用与ServerConfig中配置相同的端口以保持一致性
    port = ServerConfig.PORT
    host = ServerConfig.HOST

    print(f"正在 {host}:{port} 启动集成服务器")
    print(f"管理服务可用地址: http://{host}:{port}")
    print(f"旅行规划服务可用地址: http://{host}:{port}/travel")
    print(f"技能代理服务可用地址: http://{host}:{port}/skill")

    # 使用Uvicorn ASGI服务器运行
    uvicorn.run(
        "main:main_app",
        host=host,
        port=port,
        reload=ServerConfig.RELOAD,
        log_level=LogConfig.LEVEL.lower()
    )