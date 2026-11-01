"""
配置管理模块
集中处理配置的读取和管理
"""
import logging
from src.accessors.ai_agent_accessor import AIAgent
from src.config import DeepAgentConfig, ServerConfig, ChatRecordConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    配置管理器
    提供统一的配置访问接口
    """
    
    @staticmethod
    def get_deepagent_config():
        """
        获取技能代理配置
        """
        return DeepAgentConfig
    

    
    @staticmethod
    def get_execution_config():
        """
        获取执行配置
        """
        return DeepAgentConfig.ExecutionConfig
    
    @staticmethod
    def get_docker_image():
        """
        获取 Docker 镜像名称
        """
        return DeepAgentConfig.ExecutionConfig.DOCKER_IMAGE
    
    @staticmethod
    def get_docker_container_name():
        """
        获取 Docker 容器名称
        """
        return DeepAgentConfig.ExecutionConfig.DOCKER_CONTAINER_NAME
    
    @staticmethod
    def get_work_dir():
        """
        获取工作目录
        """
        return DeepAgentConfig.ExecutionConfig.WORK_DIR
    
    @staticmethod
    def get_mount_skills():
        """
        获取是否挂载技能
        """
        return DeepAgentConfig.ExecutionConfig.MOUNT_SKILLS
    
    @staticmethod
    def get_public_port():
        """
        获取主服务对外公开端口（供浏览器或其他客户端使用）
        """
        return ServerConfig.PUBLIC_PORT

    @staticmethod
    def get_public_host():
        """
        获取主服务对外公开主机地址（供浏览器或其他客户端使用）
        """
        return ServerConfig.PUBLIC_HOST

    @staticmethod
    def get_sandbox_timeout():
        """
        获取沙盒超时时间
        """
        return 3600  # 默认1小时
    
    @staticmethod
    def get_sandbox_cleanup_interval():
        """
        获取沙盒清理间隔
        """
        return 300  # 默认5分钟

    @staticmethod
    def get_skills_path():
        """
        获取技能路径
        如果配置的路径不存在或不是目录，返回默认路径
        """
        import os
        config_path = DeepAgentConfig.SkillsConfig.PATH
        if os.path.isdir(config_path):
            return config_path
        else:
            default_path = "skills_repo"
            logger.warning(f"Skills path {config_path} is not a valid directory, using default path: {default_path}")
            return default_path
    
    @staticmethod
    def get_skills_sandbox_path():
        """
        获取技能在沙盒容器内的绝对路径
        """
        return DeepAgentConfig.SkillsConfig.SANDBOX_PATH
    
    @staticmethod
    def get_host_skills_path():
        """
        获取宿主机上的技能仓库绝对路径（Docker启动时使用）
        优先使用环境变量 HOST_SKILLS_PATH，其次使用配置文件中的值
        """
        import os
        env_path = os.environ.get('HOST_SKILLS_PATH', '').strip()
        if env_path:
            return env_path
        return DeepAgentConfig.SkillsConfig.HOST_PATH or ''
    
    @staticmethod
    def get_temp_dir():
        """
        获取临时文件目录
        """
        return DeepAgentConfig.ExecutionConfig.TEMP_DIR

    @staticmethod
    def get_package_mode():
        """
        获取沙箱依赖供给模式：'preinstalled'（镜像预装、离线禁装）或 'mirror'（内网镜像源、允许按需安装）
        """
        return DeepAgentConfig.ExecutionConfig.PACKAGE_MODE

    @staticmethod
    def get_pip_mirror_url():
        """
        获取内网 pip 镜像源地址（仅 package_mode='mirror' 时生效）
        """
        return DeepAgentConfig.ExecutionConfig.PIP_MIRROR_URL

    @staticmethod
    def get_npm_mirror_url():
        """
        获取内网 npm 镜像源地址（仅 package_mode='mirror' 时生效）
        """
        return DeepAgentConfig.ExecutionConfig.NPM_MIRROR_URL

    @staticmethod
    def get_memory_enabled(agent_uuid: str = None):
        """
        获取记忆系统开关
        """
        success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
        if not success or not agent_data:
            return False
        agent_config = agent_data.get('config') or {}
        memory_config = agent_config.get('memory') or {}
        return memory_config.get('enabled', False)

    @staticmethod
    def get_memory_host_path():
        """
        获取宿主机记忆根目录（用于沙盒子容器 -v 挂载的源路径，由宿主机 Docker daemon 解释）
        """
        import os
        env_path = os.environ.get('DEEPAGENT_MEMORY_HOST_PATH', '').strip()
        if env_path:
            return env_path
        return DeepAgentConfig.MemoryConfig.HOST_PATH

    @staticmethod
    def get_memory_container_path():
        """
        获取主服务容器内的记忆目录路径（用于种子写入与 /aiMemory/* 管理接口读写）
        """
        import os
        env_path = os.environ.get('DEEPAGENT_MEMORY_CONTAINER_PATH', '').strip()
        if env_path:
            return env_path
        return DeepAgentConfig.MemoryConfig.CONTAINER_PATH

    @staticmethod
    def get_memory_sandbox_path():
        """
        获取沙盒容器内的记忆挂载路径
        """
        return DeepAgentConfig.MemoryConfig.SANDBOX_PATH

    @staticmethod
    def get_memory_files():
        """
        获取记忆文件清单（顺序决定 system prompt 中的注入顺序）
        """
        files = DeepAgentConfig.MemoryConfig.FILES
        if not files:
            return ["AGENTS.md", "preferences.md", "knowledge.md"]
        return list(files)

    @staticmethod
    def get_sandbox_env(agent_uuid: str = None):
        """
        获取沙盒容器的环境变量配置
        """
        success, agent_data = AIAgent.get_agent(uuid=agent_uuid)
        if not success or not agent_data:
            return {}
        agent_config = agent_data.get('config') or {}
        env_vars = agent_config.get('env_vars') or {}
        return env_vars

    @staticmethod
    def get_file_host_path():
        """
        获取宿主机文件根目录（用于沙盒子容器 -v 挂载的源路径，由宿主机 Docker daemon 解释）
        """
        import os
        env_path = os.environ.get('CHAT_RECORD_FILE_HOST_PATH', '').strip()
        if env_path:
            return env_path
        return ChatRecordConfig.FileConfig.HOST_PATH

    @staticmethod
    def get_file_container_path():
        """
        获取主服务容器内的文件目录路径
        """
        import os
        env_path = os.environ.get('CHAT_RECORD_FILE_CONTAINER_PATH', '').strip()
        if env_path:
            return env_path
        return ChatRecordConfig.FileConfig.CONTAINER_PATH

    @staticmethod
    def get_file_sandbox_path():
        """
        获取沙盒容器内的文件挂载路径
        """
        return ChatRecordConfig.FileConfig.SANDBOX_PATH


# 全局配置管理器实例
config_manager = ConfigManager()
