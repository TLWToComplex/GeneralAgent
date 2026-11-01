import os
import logging
import yaml
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger("chatchat_server")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass


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
            Path.cwd() / self.config_file,  # 当前工作目录
            Path.cwd() / "src" / self.config_file,  # src目录（用于兼容）
            Path(__file__).parent.parent / self.config_file,  # 父目录（项目根目录）
            Path("/app") / self.config_file,  # Docker容器中的默认路径（最低优先级）
        ]
        custom_path = os.getenv("GA_CONFIG_FILE")
        if custom_path:
            possible_paths.insert(0, Path(custom_path).expanduser())
        custom_path = os.getenv("GA_CONFIG_FILE")
        if custom_path:
            possible_paths.insert(0, Path(custom_path).expanduser())
        
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
            key_path: 配置键路径，如 'server.host'
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
    PORT = _config_loader.get("server.port", 8030, "PORT")
    RELOAD = _config_loader.get("server.reload", False, "UVICORN_RELOAD")
    PUBLIC_HOST = _config_loader.get("server.public_host", "localhost", "SERVER_PUBLIC_HOST")
    PUBLIC_PORT = _config_loader.get("server.public_port", 8038, "SERVER_PUBLIC_PORT")


class DatabaseConfig:
    """数据库配置"""
    URL = _config_loader.get("database.url", "mysql+pymysql://ga_user@127.0.0.1:3306/ai_service", "DATABASE_URL")
    TRACK_MODIFICATIONS = _config_loader.get("database.track_modifications", False, "SQLALCHEMY_TRACK_MODIFICATIONS")



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
            logging.getLogger("urllib3.connection").setLevel(logging.ERROR)
            logging.getLogger("starlette").setLevel(logging.WARNING)
        else:
            # 完整日志格式
            logging.basicConfig(
                level=getattr(logging, cls.LEVEL, logging.DEBUG),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )


class SSOConfig:
    """SSO配置"""
    URL = _config_loader.get("sso.url", "LOCAL_NO_AUTHZ", "SSO_URL")

class KBChatConfig:
    """知识库聊天服务配置"""
    BASE_URL = _config_loader.get("kb_chat.base_url", "http://172.16.235.50:7861", "KB_CHAT_BASE_URL")


class TravelPlannerConfig:
    """Travel Planner配置"""
    
    class LLMConfig:
        """LLM配置"""
        API_BASE_URL = _config_loader.get("travel_planner.llm.api_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1", "LLM_API_BASE_URL")
        API_KEY = _config_loader.get("travel_planner.llm.api_key", "", "LLM_API_KEY")
        MODEL_NAME = _config_loader.get("travel_planner.llm.model_name", "qwen3-next-80b-a3b-instruct", "LLM_MODEL_NAME")
    
    class CheckpointConfig:
        """LangGraph Checkpoint配置"""
        PATH_LOCAL = _config_loader.get("travel_planner.checkpoint.path_local", "/code/travel.db", "LANGGRAPH_IN_MEMORY_CHECKPOINT_PATH_LOCAL")
    
    @classmethod
    def get_service_configs(cls) -> Dict[str, Any]:
        """获取MCP服务配置"""
        return _config_loader.get("travel_planner.service_configs", {})


class DeepAgentConfig:
    """DeepAgent配置"""

    class SkillsConfig:
        """Skills配置"""
        PATH = _config_loader.get("deepagent.skills.path", "skills_repo", "DEEPAGENT_SKILLS_PATH")
        # 技能在沙盒容器内的绝对路径
        SANDBOX_PATH = _config_loader.get("deepagent.skills.sandbox_path", "/workspace/skills_repo", "DEEPAGENT_SKILLS_SANDBOX_PATH")
        # 宿主机上的技能仓库绝对路径（Docker启动时，沙盒容器直接挂载此路径）
        HOST_PATH = _config_loader.get("deepagent.skills.host_path", "", "HOST_SKILLS_PATH")

    class ExecutionConfig:
        """执行环境配置"""
        # 运行模式: 'local' 或 'docker'
        MODE = _config_loader.get("deepagent.execution.mode", "local", "DEEPAGENT_EXECUTION_MODE")
        # Docker镜像名称
        DOCKER_IMAGE = _config_loader.get("deepagent.execution.docker_image", "skill-agent:latest", "DEEPAGENT_DOCKER_IMAGE")
        # Docker容器名称 (用于重用容器)
        DOCKER_CONTAINER_NAME = _config_loader.get("deepagent.execution.docker_container_name", "skill-agent-sandbox", "DEEPAGENT_DOCKER_CONTAINER_NAME")
        # 是否自动挂载技能目录
        MOUNT_SKILLS = _config_loader.get("deepagent.execution.mount_skills", True, "DEEPAGENT_MOUNT_SKILLS")
        # 工作目录 (容器内)
        WORK_DIR = _config_loader.get("deepagent.execution.work_dir", "/workspace", "DEEPAGENT_WORK_DIR")
        # 临时文件目录
        TEMP_DIR = _config_loader.get("deepagent.execution.temp_dir", "temp", "DEEPAGENT_TEMP_DIR")
        # 依赖供给模式：
        #   'preinstalled'（默认）——镜像已预装全部依赖、离线禁装；提示词第6条列举已装包（读 sandbox-*.txt）
        #   'mirror'——沙箱接入内网镜像源；提示词第6条不列举、改为允许按需安装，
        #             并在容器启动时注入 pip/npm 内网源（见 pip_mirror_url / npm_mirror_url）
        PACKAGE_MODE = _config_loader.get("deepagent.execution.package_mode", "preinstalled", "DEEPAGENT_PACKAGE_MODE")
        # 内网 pip 镜像源地址（仅 package_mode='mirror' 时生效，注入沙箱容器 PIP_INDEX_URL/PIP_TRUSTED_HOST）
        PIP_MIRROR_URL = _config_loader.get("deepagent.execution.pip_mirror_url", "", "DEEPAGENT_PIP_MIRROR_URL")
        # 内网 npm 镜像源地址（仅 package_mode='mirror' 时生效，注入沙箱容器 npm_config_registry）
        # 注意：apt 内网源无法用环境变量在运行时切换，需在构建镜像时用 --build-arg APT_MIRROR=<内网> 指定
        NPM_MIRROR_URL = _config_loader.get("deepagent.execution.npm_mirror_url", "", "DEEPAGENT_NPM_MIRROR_URL")

    class CheckpointConfig:
        """Checkpoint配置"""
        PATH_LOCAL = _config_loader.get("deepagent.checkpoint.path_local", "/code/deepagent.db", "DEEPAGENT_CHECKPOINT_PATH_LOCAL")

    class LLMConfig:
        """LLM配置"""
        # 模型上下文大小使用比例（max_input_tokens = model_context_size * 1024 * ratio）
        MODEL_CONTEXT_SIZE_RATIO = _config_loader.get(
            "deepagent.llm.model_context_size_ratio", 0.6, "DEEPAGENT_LLM_MODEL_CONTEXT_SIZE_RATIO"
        )

    class MemoryConfig:
        """记忆配置 - DeepAgent per-user 记忆系统"""
        # 宿主机记忆根目录（仅作为沙盒子容器 -v 挂载的源路径，由宿主机 Docker daemon 解释）
        HOST_PATH = _config_loader.get("deepagent.memory.host_path", "D:/agent_memory", "DEEPAGENT_MEMORY_HOST_PATH")
        # 主服务容器内的记忆目录路径（用于种子写入与 /aiMemory/* 管理接口读写）
        CONTAINER_PATH = _config_loader.get("deepagent.memory.container_path", "/code/agent_memory", "DEEPAGENT_MEMORY_CONTAINER_PATH")
        # 容器内记忆挂载路径
        SANDBOX_PATH = _config_loader.get("deepagent.memory.sandbox_path", "/workspace/agent_memory", "DEEPAGENT_MEMORY_SANDBOX_PATH")
        # 记忆文件列表（顺序决定 system prompt 中的注入顺序）
        FILES = _config_loader.get(
            "deepagent.memory.files",
            ["AGENTS.md", "preferences.md", "knowledge.md"],
            "DEEPAGENT_MEMORY_FILES"
        )


class ScreenshotConfig:
    """截图服务配置"""
    SAVE_DIR = _config_loader.get("screenshot.save_dir", "./data/screenshots", "SCREENSHOT_SAVE_DIR")
    DEFAULT_WIDTH = _config_loader.get("screenshot.default_width", 1280, "SCREENSHOT_DEFAULT_WIDTH")
    DEFAULT_HEIGHT = _config_loader.get("screenshot.default_height", 720, "SCREENSHOT_DEFAULT_HEIGHT")
    DEFAULT_TIMEOUT = _config_loader.get("screenshot.default_timeout", 30000, "SCREENSHOT_DEFAULT_TIMEOUT")


class LangfuseConfig:
    """Langfuse追踪配置"""
    ENABLED = _config_loader.get("langfuse.enabled", True, "LANGFUSE_ENABLED")
    HOST = _config_loader.get("langfuse.host", "http://localhost:13000", "LANGFUSE_HOST")
    PUBLIC_KEY = _config_loader.get("langfuse.public_key", "", "LANGFUSE_PUBLIC_KEY")
    SECRET_KEY = _config_loader.get("langfuse.secret_key", "", "LANGFUSE_SECRET_KEY")
    PROJECT = _config_loader.get("langfuse.project", "SkillAgent", "LANGFUSE_PROJECT")

    @classmethod
    def configure_langfuse(cls):
        """配置Langfuse追踪"""
        if cls.ENABLED:
            import os
            os.environ["LANGFUSE_ENABLED"] = "true"
            os.environ["LANGFUSE_HOST"] = cls.HOST
            os.environ["LANGFUSE_PUBLIC_KEY"] = cls.PUBLIC_KEY
            os.environ["LANGFUSE_SECRET_KEY"] = cls.SECRET_KEY
            os.environ.setdefault("OTEL_SERVICE_NAME", "ai-service-backend")
            # 禁用 Langfuse SDK 媒体上传，避免 base64 图片触发连接到不可达服务端
            os.environ["LANGFUSE_MEDIA_UPLOAD_ENABLED"] = "false"
            logger.info(f"Langfuse tracing enabled for project: {cls.PROJECT}")
        else:
            import os
            os.environ["LANGFUSE_ENABLED"] = "false"
            logger.info("Langfuse tracing disabled")


class ChatRecordConfig:
    """对话记录配置"""
    RETENTION_DAYS = _config_loader.get("chat_record.retention_days", 90, "CHAT_RECORD_RETENTION_DAYS")
    CLEANUP_HOUR = _config_loader.get("chat_record.cleanup_hour", 3, "CHAT_RECORD_CLEANUP_HOUR")

    class FileConfig:
        HOST_PATH = _config_loader.get("chat_record.file.host_path", "D:/chat_record_files", "CHAT_RECORD_FILE_HOST_PATH")
        CONTAINER_PATH = _config_loader.get("chat_record.file.container_path", "/code/chat_record_files", "CHAT_RECORD_FILE_CONTAINER_PATH")
        SANDBOX_PATH = _config_loader.get("chat_record.file.sandbox_path", "/workspace", "CHAT_RECORD_FILE_SANDBOX_PATH")


class DefaultAdminConfig:
    """默认管理员账号配置"""
    USERNAME = _config_loader.get("default_admin.username", "admin")
    PASSWORD = _config_loader.get("default_admin.password", "Aa123456")
    REALNAME = _config_loader.get("default_admin.realname", "管理员")
    EMAIL = _config_loader.get("default_admin.email", "admin@qq.com")
