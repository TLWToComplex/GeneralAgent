import os
import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger("sequential_thinking_server")

class EnvironmentType(Enum):
    """环境类型枚举"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class ServerConfig:
    """服务器配置"""
    HOST = os.getenv("HOST", "0.0.0.0")  # Docker中使用0.0.0.0
    PORT = int(os.getenv("PORT", "8849"))  # 使用不同的端口避免冲突

class SecurityConfig:
    """安全配置"""
    ENV_TYPE = EnvironmentType(os.getenv("ENV_TYPE", "development"))
    MAX_THOUGHT_LENGTH = int(os.getenv("MAX_THOUGHT_LENGTH", "5000"))
    MAX_TOTAL_THOUGHTS = int(os.getenv("MAX_TOTAL_THOUGHTS", "100"))
    MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "30000"))  # 最大输出token数
    
    @classmethod
    def validate_thought_params(cls, thought: str, thought_number: int, total_thoughts: int) -> Dict[str, Any]:
        """验证思考参数"""
        errors = []
        
        if len(thought) > cls.MAX_THOUGHT_LENGTH:
            errors.append(f"思考内容长度不能超过{cls.MAX_THOUGHT_LENGTH}个字符")
        
        if total_thoughts > cls.MAX_TOTAL_THOUGHTS:
            errors.append(f"总思考步数不能超过{cls.MAX_TOTAL_THOUGHTS}")
            
        if thought_number < 1:
            errors.append("思考步数必须大于0")
            
        if thought_number > total_thoughts:
            # 自动调整总思考步数
            total_thoughts = thought_number
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "total_thoughts": total_thoughts
            }
        
        return {
            "valid": True,
            "errors": [],
            "total_thoughts": total_thoughts
        }
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """估算文本的token数量（简单估算：1个token约等于4个字符）"""
        return len(text) // 4
    
    @classmethod
    def validate_output_tokens(cls, content: str) -> Dict[str, Any]:
        """验证输出token数量"""
        estimated_tokens = cls.estimate_tokens(content)
        
        if estimated_tokens > cls.MAX_OUTPUT_TOKENS:
            return {
                "valid": False,
                "estimated_tokens": estimated_tokens,
                "max_tokens": cls.MAX_OUTPUT_TOKENS,
                "error": f"输出内容过长，估计{estimated_tokens}个token，超过最大限制{cls.MAX_OUTPUT_TOKENS}"
            }
        
        return {
            "valid": True,
            "estimated_tokens": estimated_tokens,
            "max_tokens": cls.MAX_OUTPUT_TOKENS
        }

class LogConfig:
    """日志配置"""
    LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()  # 默认设置为DEBUG级别
    SIMPLIFIED_LOGGING = os.getenv("SIMPLIFIED_LOGGING", "true").lower() == "true"
    DISABLE_THOUGHT_LOGGING = os.getenv("DISABLE_THOUGHT_LOGGING", "false").lower() == "true"
    
    @classmethod
    def setup_logging(cls):
        """设置日志配置"""
        if cls.SIMPLIFIED_LOGGING:
            # 简化日志格式
            logging.basicConfig(
                level=getattr(logging, cls.LEVEL, logging.INFO),
                format='%(levelname)s: %(message)s',
                handlers=[
                    logging.StreamHandler()
                ]
            )
        else:
            # 详细日志格式
            logging.basicConfig(
                level=getattr(logging, cls.LEVEL, logging.INFO),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler()
                ]
            )