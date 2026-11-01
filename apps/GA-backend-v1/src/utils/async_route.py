"""
Asynchronous route decorator module.
Provides decorator for handling asynchronous Flask routes using asyncio.
"""
import asyncio
from functools import wraps
from typing import Callable, TypeVar, Any, Awaitable

F = TypeVar('F', bound=Callable[..., Awaitable[Any]])

def async_route(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 尝试直接调用函数
            result = f(*args, **kwargs)
            
            # 检查结果是否是可等待对象
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                # 如果是可等待对象，则等待其完成
                return loop.run_until_complete(result)
            else:
                # 如果不是可等待对象，则直接返回
                return result
        finally:
            loop.close()
    return wrapper

