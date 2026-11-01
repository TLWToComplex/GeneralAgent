"""
MCP客户端工具模块
提供统一的MCP服务连接和工具获取功能
"""
import asyncio
import functools
import logging
from typing import List, Dict, Any, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


def _flatten_text_blocks(blocks: Any) -> Any:
    """将 ``list[{'type': 'text', 'text': ...}]`` 展平为单一字符串。

    背景：langchain-mcp-adapters 把 MCP 工具返回包成 list[ContentBlock]，
    LangChain 把它放进 ``ToolMessage.content`` 后，转 OpenAI/DeepSeek HTTP body
    时会对整个 list 做 ``json.dumps``，默认 ``ensure_ascii=True``，
    导致 body 里中文被字面量化成 ``\\uXXXX``。模型读到这串字面量后，
    在 reasoning 中按"原样复述"，生僻字采样会漂移成形近字（如 皓→霖、铖→锴）。

    展平为纯字符串后，``ToolMessage.content`` 直接就是 str，
    LangChain 不会再做二次 ``json.dumps``，body 里就是真中文。
    """
    if not isinstance(blocks, list) or not blocks:
        return blocks
    if not all(isinstance(b, dict) and isinstance(b.get('text'), str) for b in blocks):
        return blocks
    return '\n'.join(b['text'] for b in blocks)


def _flatten_tool_result(result: Any) -> Any:
    """覆盖 MCP 工具返回的两种形态：``list[block]`` 与 ``(list[block], artifact)``。"""
    if isinstance(result, list):
        return _flatten_text_blocks(result)
    if isinstance(result, tuple) and len(result) == 2:
        content, artifact = result
        flat = _flatten_text_blocks(content)
        if flat is not content:
            return flat, artifact
    return result


def wrap_tool_flatten_content(tool: Any) -> Any:
    """包装 MCP 工具：把 ``list[text_block]`` 形态的返回值在我们这层就拍平为字符串。"""
    original_coroutine = getattr(tool, 'coroutine', None)
    if original_coroutine is not None:
        @functools.wraps(original_coroutine)
        async def flattened_coroutine(*args, **kwargs):
            return _flatten_tool_result(await original_coroutine(*args, **kwargs))

        try:
            tool.coroutine = flattened_coroutine
        except Exception:
            try:
                tool = tool.model_copy(update={"coroutine": flattened_coroutine})
            except Exception:
                logger.warning(
                    f"无法替换工具 {getattr(tool, 'name', '?')} 的 coroutine，将走 ainvoke 兜底"
                )

    original_ainvoke = getattr(tool, 'ainvoke', None)
    if callable(original_ainvoke):
        @functools.wraps(original_ainvoke)
        async def flattened_ainvoke(*args, **kwargs):
            return _flatten_tool_result(await original_ainvoke(*args, **kwargs))

        try:
            tool.ainvoke = flattened_ainvoke
        except Exception:
            try:
                tool = tool.model_copy(update={"ainvoke": flattened_ainvoke})
            except Exception:
                pass

    return tool


def normalize_transport(transport: str) -> str:
    """
    标准化MCP传输协议名称
    
    将各种命名格式转换为langchain_mcp_adapters支持的格式：
    - streamableHttp -> streamable-http
    - StreamableHttp -> streamable-http  
    - streamable_http -> streamable-http
    - SSE -> sse
    
    Args:
        transport: 原始传输协议名称
        
    Returns:
        标准化后的传输协议名称
    """
    if not transport:
        return 'sse'
    
    # 转换为小写
    normalized = transport.lower()
    
    # 处理常见的命名变体
    if normalized in ['streamablehttp', 'streamable_http']:
        return 'streamable-http'
    
    return normalized


async def get_mcp_tools(
    server_name: str, 
    url: str, 
    transport: str = 'sse',
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None
) -> List[Any]:
    """
    从MCP服务器获取工具列表
    
    Args:
        server_name: MCP服务名称
        url: MCP服务URL
        transport: 传输协议 (默认: sse)
        timeout: 超时时间(秒)
        headers: 请求头
        
    Returns:
        工具列表,失败返回空列表
    """
    try:
        # 标准化transport名称
        transport = normalize_transport(transport)
        
        config = {'url': url, 'transport': transport}
        
        # 为 streamable-http 协议添加必要的请求头
        if transport == 'streamable-http':
            # FastMCP 要求同时接受 application/json 和 text/event-stream
            accept_header = 'application/json, text/event-stream'
            if headers:
                headers['Accept'] = accept_header
                config['headers'] = headers
            else:
                config['headers'] = {'Accept': accept_header}
        elif headers:
            config['headers'] = headers
            
        client = MultiServerMCPClient({server_name: config})
        tools = await asyncio.wait_for(client.get_tools(), timeout=timeout)

        if tools:
            tools = [wrap_tool_flatten_content(t) for t in tools]
            logger.info(f"成功从 {server_name} 获取 {len(tools)} 个工具")
        else:
            logger.warning(f"{server_name} 未返回任何工具")

        return tools or []
        
    except asyncio.TimeoutError:
        logger.error(f"连接 {server_name} 超时 ({timeout}秒): {url}")
        return []
    except Exception as e:
        # 处理 ExceptionGroup (Python 3.11+ anyio 库可能抛出)
        error_msg = str(e)
        # 提取最内层的实际错误信息
        if hasattr(e, 'exceptions') and e.exceptions:
            # ExceptionGroup,取第一个子异常
            inner_exception = e.exceptions[0]
            error_msg = str(inner_exception)
            # 进一步提取httpx错误
            if hasattr(inner_exception, '__cause__') and inner_exception.__cause__:
                error_msg = str(inner_exception.__cause__)
        
        logger.warning(f"从 {server_name} 获取工具失败: {error_msg}")
        logger.debug(f"完整错误堆栈", exc_info=True)
        return []


async def test_mcp_connection(
    server_name: str, 
    url: str, 
    transport: str,
    timeout: float = 5.0,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    测试MCP服务连接
    
    Args:
        server_name: MCP服务名称
        url: MCP服务URL
        transport: 传输协议 (sse 或 streamable-http)
        timeout: 超时时间(秒)
        headers: 请求头（用于认证）
        
    Returns:
        包含连接结果的字典
    """
    logger.info(f"开始测试MCP连接: {server_name}, URL: {url}, Transport: {transport}")
    if headers:
        logger.info(f"使用自定义Headers: {list(headers.keys())}")
        # 记录header的key，但不记录value（安全考虑）
        for key in headers.keys():
            logger.debug(f"Header key: {key}")
    
    try:
        # 标准化transport名称
        transport = normalize_transport(transport)
        
        # 根据 transport 类型构建配置
        config = {'url': url}
        if transport:
            config['transport'] = transport

        # 为 streamable-http 协议添加必要的请求头
        if transport == 'streamable-http':
            # FastMCP 要求同时接受 application/json 和 text/event-stream
            accept_header = 'application/json, text/event-stream'
            if headers:
                headers['Accept'] = accept_header
                config['headers'] = headers
            else:
                config['headers'] = {'Accept': accept_header}
        elif headers:
            config['headers'] = headers
            
        logger.info(f"MCP配置: {config}")
        
        # 创建客户端
        client = MultiServerMCPClient({server_name: config})
        
        # 打印客户端连接配置，用于调试
        logger.info(f"客户端连接配置: {client.connections}")
        
        tools = await asyncio.wait_for(client.get_tools(), timeout=timeout)
        
        if tools:
            tools_info = [{
                'name': getattr(tool, 'name', 'unknown'),
                'description': getattr(tool, 'description', 'unknown'),
                'id': getattr(tool, 'name', 'unknown'),
                'args_schema': getattr(tool, 'args_schema', 'unknown'),
            } for tool in tools]
            return {
                'success': True,
                'message': f'连接成功，获取到 {len(tools)} 个工具',
                'tool_count': len(tools),
                'tools': tools_info
            }
        else:
            return {
                'success': True,
                'message': '连接成功，但未获取到任何工具',
                'tool_count': 0,
                'tools': []
            }
            
    except asyncio.TimeoutError:
        return {
            'success': False,
            'message': f'连接超时({timeout}秒)，请检查服务地址是否正确: {url}',
            'error_type': 'timeout'
        }
    except Exception as e:
        # 处理 ExceptionGroup (Python 3.11+ anyio 库可能抛出)
        error_msg = str(e)
        error_type = type(e).__name__
        
        # 提取最内层的实际错误信息
        if hasattr(e, 'exceptions') and e.exceptions:
            # ExceptionGroup,取第一个子异常
            inner_exception = e.exceptions[0]
            error_msg = str(inner_exception)
            error_type = type(inner_exception).__name__
            
            # 进一步提取httpx错误
            if hasattr(inner_exception, '__cause__') and inner_exception.__cause__:
                error_msg = str(inner_exception.__cause__)
                error_type = type(inner_exception.__cause__).__name__
            elif hasattr(inner_exception, 'response') and inner_exception.response:
                # 如果有HTTP响应，记录详细信息
                resp = inner_exception.response
                logger.error(f"HTTP响应状态码: {resp.status_code}")
                logger.error(f"HTTP响应头: {dict(resp.headers)}")
                try:
                    error_body = resp.text
                    logger.error(f"HTTP响应体: {error_body[:500]}")
                except:
                    pass
        elif hasattr(e, 'response') and e.response:
            # 直接是HTTP错误
            resp = e.response
            logger.error(f"HTTP响应状态码: {resp.status_code}")
            logger.error(f"HTTP响应头: {dict(resp.headers)}")
            try:
                error_body = resp.text
                logger.error(f"HTTP响应体: {error_body[:500]}")
            except:
                pass
        
        logger.error(f"MCP连接失败 [{error_type}]: {error_msg}")
        logger.debug(f"完整错误堆栈", exc_info=True)
        
        return {
            'success': False,
            'message': f'连接失败: {error_msg}',
            'error_type': error_type
        }


async def initialize_multiple_mcp_servers(
    server_configs: Dict[str, Dict[str, Any]],
    timeout: float = 10.0,
    max_concurrent: int = 5
) -> List[Any]:
    """
    初始化多个MCP服务器并获取所有工具(并行,限流)
    
    Args:
        server_configs: 服务配置字典 {server_name: {url, transport, headers}}
        timeout: 每个服务的超时时间
        max_concurrent: 最大并发数(默认5)
        
    Returns:
        所有工具的列表
    """
    async def init_single_server(server_name: str, config: Dict[str, Any], semaphore: asyncio.Semaphore) -> List[Any]:
        """初始化单个MCP服务器(带限流)"""
        async with semaphore:  # 获取信号量,限制并发
            try:
                url = config.get('url')
                transport = config.get('transport', 'sse')
                headers = config.get('headers')
                
                if not url:
                    logger.warning(f"{server_name} 缺少URL配置，跳过")
                    return []
                    
                tools = await get_mcp_tools(
                    server_name=server_name,
                    url=url,
                    transport=transport,
                    timeout=timeout,
                    headers=headers
                )
                return tools
                
            except Exception as e:
                logger.error(f"初始化 {server_name} 失败: {str(e)}")
                return []
    
    if not server_configs:
        logger.warning("没有MCP服务器配置")
        return []
    
    # 创建信号量,限制最大并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 创建任务
    tasks = [
        init_single_server(server_name, config, semaphore)
        for server_name, config in server_configs.items()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 合并所有工具
    all_tools = []
    for result in results:
        if isinstance(result, list):
            all_tools.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"服务器初始化异常: {result}")
    
    logger.info(f"总共加载 {len(all_tools)} 个MCP工具 (并发数: {max_concurrent})")
    return all_tools
