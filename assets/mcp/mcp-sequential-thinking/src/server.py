from mcp.server.fastmcp import FastMCP
import logging
import asyncio
from dotenv import load_dotenv
import atexit
import signal
import sys
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
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

# 创建MCP服务器实例
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("正在创建MCP服务器实例...")
mcp = FastMCP("Sequential Thinking Server", "1.0.0", host=host, port=port, debug=False, endpoint='/sse')
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("MCP服务器实例创建完成")

def auto_register_tools(mcp):
    """自动注册所有工具"""
    try:
        # 注册Sequential Thinking工具
        register_sequential_thinking_tool(mcp)
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
    'loop': None,
    'initialized': False
}

def cleanup_resources():
    """清理资源"""
    if not LogConfig.SIMPLIFIED_LOGGING:
        logger.debug("正在清理资源...")
    
    if _server_data['loop'] and not _server_data['loop'].is_closed():
        try:
            _server_data['loop'].close()
        except Exception as e:
            logger.error(f"关闭事件循环时出错: {str(e)}")
    
    _server_data['initialized'] = False
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
        
        # 这里可以添加任何需要异步初始化的逻辑
        # 例如：数据库连接、外部API验证等
        
        _server_data['initialized'] = True
        if not LogConfig.SIMPLIFIED_LOGGING:
            logger.debug("服务器异步初始化完成")
            
    except Exception as e:
        logger.error(f"服务器初始化失败: {str(e)}")
        raise

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """创建一个可以通过SSE提供MCP服务的Starlette应用程序"""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    app = Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),  # 客户端通过此端点连接服务器
            Mount("/messages/", app=sse.handle_post_message),  # 客户端通过此端点发送消息到服务器
        ],
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

def start_server():
    """启动SSE服务器的同步包装器"""
    if not LogConfig.SIMPLIFIED_LOGGING:
        logger.debug("开始启动Sequential Thinking服务器...")
    
    print(f"启动Sequential Thinking MCP服务器...")
    print(f"服务器地址: http://{host}:{port}/sse")
    
    try:
        # 使用事件循环执行异步初始化函数
        _server_data['loop'] = asyncio.get_event_loop()
        _server_data['loop'].run_until_complete(init_server())
        
        # 使用Starlette和uvicorn启动服务器
        if not LogConfig.SIMPLIFIED_LOGGING:
            logger.debug("使用Starlette和uvicorn启动服务器...")
        mcp_server = mcp._mcp_server  # 获取内部MCP服务器实例
        
        # 创建Starlette应用程序
        starlette_app = create_starlette_app(mcp_server, debug=False)
        
        # 使用uvicorn运行应用（禁用访问日志）
        uvicorn.run(starlette_app, host=host, port=port, access_log=False)
    except Exception as e:
        logger.exception(f"服务器运行错误: {str(e)}")
        print(f"服务器运行错误: {str(e)}")
    finally:
        # 确保资源被清理
        cleanup_resources()
    
if __name__ == "__main__":
    # 确保初始化后工具才被注册
    start_server()