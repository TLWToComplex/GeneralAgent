"""
实体类型常量定义模块。
统一管理所有实体的类型标识，避免魔法数字。
"""


class EntityType:
    """
    实体类型常量类
    
    用于 ai_permissions 表中的 entity_type 字段
    """
    MCP_SERVER = 0      # MCP 服务
    PLATFORM = 1        # AI 平台
    PROMPT = 2          # Prompt 模板
    AGENT = 3           # AI Agent
    KB_CHAT = 4         # 知识库
    SKILL = 5           # 技能
    
    # 实体类型名称映射（用于日志和调试）
    NAMES = {
        0: 'mcp_server',
        1: 'platform',
        2: 'prompt',
        3: 'agent',
        4: 'kb_chat',
        5: 'skill'
    }
    
    # 反向映射：名称到类型
    TYPE_MAP = {v: k for k, v in NAMES.items()}
    
    @classmethod
    def get_name(cls, entity_type: int) -> str:
        """根据实体类型获取名称"""
        return cls.NAMES.get(entity_type, f'unknown_{entity_type}')
    
    @classmethod
    def get_type(cls, name: str) -> int:
        """根据名称获取实体类型"""
        return cls.TYPE_MAP.get(name.lower(), -1)
    
    @classmethod
    def is_valid(cls, entity_type: int) -> bool:
        """检查实体类型是否有效"""
        return entity_type in cls.NAMES
    
    @classmethod
    def get_all_types(cls) -> list:
        """获取所有有效的实体类型"""
        return list(cls.NAMES.keys())


# 便捷导入
MCP_SERVER = EntityType.MCP_SERVER
PLATFORM = EntityType.PLATFORM
PROMPT = EntityType.PROMPT
AGENT = EntityType.AGENT
KB_CHAT = EntityType.KB_CHAT
SKILL = EntityType.SKILL
