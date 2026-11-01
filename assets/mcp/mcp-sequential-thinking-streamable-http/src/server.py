from mcp.server.fastmcp import FastMCP
import logging
import asyncio
from dotenv import load_dotenv
import atexit
import signal
import sys
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# 加载环境变量 - 移到最前面确保所有模块导入前环境变量已加载
load_dotenv()

# 导入自定义模块 - 确保在load_dotenv之后导入
from src.config import ServerConfig, LogConfig
from src.tools.sequential_thinking_tool import register_sequential_thinking_tool

# 配置日志
LogConfig.setup_logging()
logger = logging.getLogger("sequential_thinking_server")

# 记录环境变量加载情况（简化日志）
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("已加载环境变量")
    logger.debug(f"服务器配置: host={ServerConfig.HOST}, port={ServerConfig.PORT}")

# 从配置获取服务器配置
host = ServerConfig.HOST
port = ServerConfig.PORT

# 创建MCP服务器实例（Streamable HTTP）
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("正在创建MCP服务器实例...")
mcp = FastMCP(
    "Sequential Thinking Server",
    "1.0.0",
    host=host,
    port=port,
    debug=False,
    stateless_http=True,
)
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("MCP服务器实例创建完成")


def auto_register_tools(mcp_instance):
    """自动注册所有工具"""
    try:
        register_sequential_thinking_tool(mcp_instance)
        logger.info("Sequential Thinking工具注册成功")
    except Exception as e:
        logger.error(f"工具注册失败: {str(e)}")
        raise


# 自动注册工具
auto_register_tools(mcp)
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("已自动注册所有Sequential Thinking工具")

# 服务器数据存储
_server_data = {
    "loop": None,
    "initialized": False,
}


def cleanup_resources():
    """清理资源"""
    _server_data["initialized"] = False
    if not LogConfig.SIMPLIFIED_LOGGING:
        logger.debug("资源清理完成")


# 注册清理函数
atexit.register(cleanup_resources)


# 信号处理器
def signal_handler(sig, frame):
    """处理系统信号"""
    logger.info(f"接收到信号 {sig}，正在关闭服务器...")
    cleanup_resources()
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill


async def init_server():
    """异步初始化服务器"""
    try:
        if not LogConfig.SIMPLIFIED_LOGGING:
            logger.debug("开始异步初始化服务器...")

        _server_data["initialized"] = True

        if not LogConfig.SIMPLIFIED_LOGGING:
            logger.debug("服务器异步初始化完成")
    except Exception as e:
        logger.error(f"服务器初始化失败: {str(e)}")
        raise


async def run_server():
    """运行Streamable HTTP服务器的异步函数"""
    await init_server()

    starlette_app = mcp.streamable_http_app()

    class RequestLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if not LogConfig.SIMPLIFIED_LOGGING:
                logger.debug(f"收到请求: {request.method} {request.url.path}")
            response = await call_next(request)
            return response

    starlette_app.add_middleware(RequestLoggingMiddleware)
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    config = uvicorn.Config(starlette_app, host=host, port=port, access_log=False)
    server = uvicorn.Server(config)
    await server.serve()


def start_server():
    """启动Streamable HTTP服务器的同步包装器"""
    if not LogConfig.SIMPLIFIED_LOGGING:
        logger.debug("开始启动Sequential Thinking服务器...")

    print("启动Sequential Thinking Streamable HTTP MCP服务器...")
    print(f"服务器监听: http://{host}:{port}")

    try:
        _server_data["loop"] = asyncio.get_event_loop()
        _server_data["loop"].run_until_complete(run_server())
    except Exception as e:
        logger.exception(f"服务器运行错误: {str(e)}")
        print(f"服务器运行错误: {str(e)}")
    finally:
        cleanup_resources()


if __name__ == "__main__":
    start_server()
