import json
import logging
from functools import wraps
from typing import Any, Callable
from src.client.chatchat_client import ChatChatAPIError

logger = logging.getLogger("chatchat_server")

class BaseToolMixin:
    """基础工具混入类，提供通用功能"""
    
    @staticmethod
    def handle_api_error(func: Callable) -> Callable:
        """装饰器：处理API错误"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ChatChatAPIError as e:
                error_response = {
                    "error": "ChatChat API调用失败",
                    "message": str(e),
                    "success": False
                }
                logger.error(f"API调用失败: {str(e)}")
                return json.dumps(error_response, ensure_ascii=False, indent=2)
            except Exception as e:
                error_response = {
                    "error": "未知错误",
                    "message": str(e),
                    "success": False
                }
                logger.error(f"未知错误: {str(e)}")
                return json.dumps(error_response, ensure_ascii=False, indent=2)
        return wrapper
    
    @staticmethod
    def format_success_response(data: Any, metadata: dict = None) -> str:
        """格式化成功响应"""
        response = {
            "success": True,
            "data": data
        }
        
        if metadata:
            response["metadata"] = metadata
            
        return json.dumps(response, ensure_ascii=False, indent=2, default=str)
    
    @staticmethod
    def format_error_response(error_msg: str, error_type: str = "ValidationError") -> str:
        """格式化错误响应"""
        response = {
            "success": False,
            "error": error_type,
            "message": error_msg
        }
        return json.dumps(response, ensure_ascii=False, indent=2)