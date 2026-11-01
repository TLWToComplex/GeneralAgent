from mcp.server.fastmcp import FastMCP
import logging
import asyncio
from dotenv import load_dotenv
import atexit
import signal
import importlib
import pkgutil
import inspect
import threading
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
from src.config import ServerConfig, LogConfig, ChatChatConfig
from src.tools.search_tool import register_search_tools

# 配置日志
LogConfig.setup_logging()
logger = logging.getLogger("chatchat_server")

# 记录环境变量加载情况（简化日志）
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("已加载环境变量")
    logger.debug(f"ChatChat API基础URL: {ChatChatConfig.API_BASE_URL}")
    logger.debug(f"API超时时间: {ChatChatConfig.API_TIMEOUT}秒")

# 检查httpx可用性
try:
    import httpx
    if not LogConfig.SIMPLIFIED_LOGGING:
        logger.debug("httpx HTTP客户端导入成功")
    http_available = True
except ImportError as e:
    logger.critical(f"无法导入httpx HTTP客户端: {str(e)}")
    logger.critical("请确保已安装httpx包: pip install httpx")
    http_available = False

# 从配置获取服务器配置
host = ServerConfig.HOST
port = ServerConfig.PORT
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug(f"服务器配置: host={host}, port={port}")

# 创建MCP服务器实例
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("正在创建MCP服务器实例...")
mcp = FastMCP("ChatChat Knowledge Base Server", "1.0.0", host=host, port=port, debug=False, endpoint='/sse')
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("MCP服务器实例创建完成")

def auto_register_tools(mcp):
    """
    自动扫描src.tools目录下所有register_开头的函数并注册到mcp
    """
    import src.tools
    package = src.tools
    for finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if ispkg:
            continue
        module = importlib.import_module(name)
        for func_name, func in inspect.getmembers(module, inspect.isfunction):
            if func_name.startswith("register_") and (func_name.endswith("tool") or func_name.endswith("tools")):
                try:
                    func(mcp)
                    logger.info(f"自动注册工具: {name}.{func_name}")
                except Exception as e:
                    logger.error(f"自动注册工具失败: {name}.{func_name} - {e}")

# 注册ChatChat搜索工具
auto_register_tools(mcp)
if not LogConfig.SIMPLIFIED_LOGGING:
    logger.debug("已自动注册所有ChatChat工具")

# 用于保存事件循环和初始化状态
_server_data = {
    'loop': None,
    'initialized': False
}

def cleanup_resources():
    """清理资源"""
    if _server_data['initialized']:
        try:
            logger.info("正在清理服务器资源...")
            # 这里可以添加其他清理逻辑
            logger.info("服务器资源已清理")
        except Exception as e:
            logger.error(f"清理服务器资源时出错: {str(e)}")

# 注册退出处理函数
atexit.register(cleanup_resources)

# 注册信号处理
def signal_handler(sig, frame):
    """处理终止信号"""
    logger.info(f"收到信号 {sig}，正在清理资源...")
    cleanup_resources()
    # 正常退出
    exit(0)

# 注册常见的终止信号
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill

async def init_server():
    """初始化服务器"""
    try:
        logger.info("初始化ChatChat MCP服务器...")
        
        # 测试ChatChat API连接
        try:
            from src.client.chatchat_client import get_chatchat_client
            client = get_chatchat_client()
            
            # 尝试获取知识库列表来测试连接
            knowledge_bases = await client.list_knowledge_bases()
            logger.info(f"API连接成功 - 发现 {len(knowledge_bases)} 个知识库")
        except Exception as e:
            logger.warning(f"API连接测试失败: {str(e)}")
            logger.warning("服务器将继续启动，但API调用可能会失败")
        
        # 等待一小段时间确保所有组件都准备就绪
        await asyncio.sleep(0.5)
        
        logger.info("服务器初始化完成")
        _server_data['initialized'] = True
        
    except Exception as e:
        logger.error(f"服务器初始化失败: {str(e)}")
        print(f"错误: 服务器初始化失败: {str(e)}")
        _server_data['initialized'] = False
        raise

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """创建一个可以通过SSE提供MCP服务的Starlette应用程序"""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        # 确保服务器已经初始化
        if not _server_data['initialized']:
            logger.warning("服务器尚未完全初始化，等待初始化完成...")
            # 等待初始化完成，最多等待30秒
            for _ in range(30):
                if _server_data['initialized']:
                    break
                await asyncio.sleep(1)
            
            if not _server_data['initialized']:
                logger.error("服务器初始化超时")
                raise RuntimeError("服务器初始化超时")
        
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
        logger.debug("开始启动ChatChat知识库搜索服务器...")
    
    print(f"启动ChatChat MCP服务器...")
    print(f"服务器地址: http://{host}:{port}/sse")
    
    try:
        # 创建新的事件循环用于初始化
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _server_data['loop'] = loop
        
        # 检查HTTP客户端配置是否有效并初始化
        if http_available:
            # 执行异步初始化函数
            loop.run_until_complete(init_server())
        else:
            logger.warning("HTTP客户端不可用，跳过API连接测试")
            _server_data['initialized'] = True
        
        # 确保初始化完成
        if not _server_data['initialized']:
            logger.error("服务器初始化失败")
            return
        
        logger.info("服务器初始化完成，开始启动HTTP服务...")
        
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