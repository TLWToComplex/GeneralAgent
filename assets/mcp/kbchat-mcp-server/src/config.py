import os
import logging
import yaml
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger("chatchat_server")

class ConfigLoader:
    """配置加载器，支持YAML文件和环境变量"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config_data = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        # 查找配置文件的可能位置（按优先级排序）
        possible_paths = [
            Path("/config") / self.config_file,  # 挂载的配置目录（最高优先级）
            Path("/app") / self.config_file,  # Docker容器中的默认路径（最低优先级）
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config_data = yaml.safe_load(f) or {}
                logger.info(f"已加载配置文件: {config_path}")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，将使用环境变量")
                self.config_data = {}
        else:
            logger.info("未找到配置文件，将使用环境变量")
            self.config_data = {}
    
    def get(self, key_path: str, default: Any = None, env_key: Optional[str] = None) -> Any:
        """
        获取配置值，支持嵌套键路径
        
        Args:
            key_path: 配置键路径，如 'server.host' 或 'chatchat.api_base_url'
            default: 默认值
            env_key: 对应的环境变量名（用于向后兼容）
        
        Returns:
            配置值
        """
        # 首先尝试从环境变量获取（优先级最高）
        if env_key and os.getenv(env_key):
            value = os.getenv(env_key)
            # 尝试转换类型
            if isinstance(default, bool):
                return value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    pass
            elif isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    pass
            return value
        
        # 然后从配置文件获取
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value if value is not None else default

# 全局配置加载器实例
_config_loader = ConfigLoader()

class EnvironmentType(Enum):
    """环境类型枚举"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class ServerConfig:
    """服务器配置"""
    HOST = _config_loader.get("server.host", "0.0.0.0", "HOST")
    PORT = _config_loader.get("server.port", 8848, "PORT")

class ChatChatConfig:
    """ChatChat API配置"""
    API_BASE_URL = _config_loader.get("chatchat.api_base_url", "http://localhost:7861", "CHATCHAT_API_BASE_URL")
    API_TIMEOUT = _config_loader.get("chatchat.api_timeout", 30, "CHATCHAT_API_TIMEOUT")
    @classmethod
    def get_search_docs_url(cls) -> str:
        """获取search_docs API的完整URL"""
        return f"{cls.API_BASE_URL}/knowledge_base/search_docs"
    
    @classmethod
    def get_list_knowledge_bases_url(cls) -> str:
        """获取list_knowledge_bases API的完整URL"""
        return f"{cls.API_BASE_URL}/knowledge_base/list_knowledge_bases"

class SecurityConfig:
    """安全配置"""
    ENV_TYPE = EnvironmentType(_config_loader.get("environment.type", "development", "ENV_TYPE"))
    MAX_QUERY_LENGTH = _config_loader.get("security.max_query_length", 1000, "MAX_QUERY_LENGTH")
    MAX_TOP_K = _config_loader.get("security.max_top_k", 50, "MAX_TOP_K")
    DEFAULT_SCORE_THRESHOLD = _config_loader.get("security.default_score_threshold", 0.5, "DEFAULT_SCORE_THRESHOLD")
    MAX_OUTPUT_TOKENS = _config_loader.get("security.max_output_tokens", 30000, "MAX_OUTPUT_TOKENS")
    
    @classmethod
    def validate_query_params(cls, query: str, top_k: int, score_threshold: float) -> Dict[str, Any]:
        """验证查询参数"""
        errors = []
        
        if len(query) > cls.MAX_QUERY_LENGTH:
            errors.append(f"查询长度不能超过{cls.MAX_QUERY_LENGTH}个字符")
        
        if top_k > cls.MAX_TOP_K:
            errors.append(f"top_k不能超过{cls.MAX_TOP_K}")
        
        if not (0.0 <= score_threshold <= 1.0):
            errors.append("score_threshold必须在0.0到1.0之间")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """估算文本的token数量（简单估算：1个中文字符≈1.5个token，1个英文单词≈1个token）"""
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in text.split() if w.isalpha()])
        other_chars = len(text) - chinese_chars - sum(len(w) for w in text.split() if w.isalpha())
        
        estimated_tokens = int(chinese_chars * 1.5 + english_words + other_chars * 0.5)
        return estimated_tokens
    
    @classmethod
    def validate_output_tokens(cls, content: str) -> Dict[str, Any]:
        """验证输出内容的token数量"""
        estimated_tokens = cls.estimate_tokens(content)
        
        if estimated_tokens > cls.MAX_OUTPUT_TOKENS:
            return {
                "valid": False,
                "estimated_tokens": estimated_tokens,
                "max_tokens": cls.MAX_OUTPUT_TOKENS,
                "error": f"输出内容超过最大token限制（{estimated_tokens} > {cls.MAX_OUTPUT_TOKENS}）"
            }
        
        return {
            "valid": True,
            "estimated_tokens": estimated_tokens,
            "max_tokens": cls.MAX_OUTPUT_TOKENS
        }

class LogConfig:
    """日志配置"""
    LEVEL = _config_loader.get("logging.level", "INFO", "LOG_LEVEL").upper()
    SIMPLIFIED_LOGGING = _config_loader.get("logging.simplified", True, "SIMPLIFIED_LOGGING")
    
    @classmethod
    def setup_logging(cls):
        """设置日志配置"""
        if cls.SIMPLIFIED_LOGGING:
            # 简化日志格式，只显示关键信息
            logging.basicConfig(
                level=getattr(logging, cls.LEVEL, logging.INFO),
                format='%(asctime)s - %(message)s'
            )
            # 禁用第三方库的详细日志
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("mcp").setLevel(logging.WARNING)
            logging.getLogger("uvicorn").setLevel(logging.WARNING)
            logging.getLogger("starlette").setLevel(logging.WARNING)
        else:
            # 完整日志格式
            logging.basicConfig(
                level=getattr(logging, cls.LEVEL, logging.DEBUG),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )