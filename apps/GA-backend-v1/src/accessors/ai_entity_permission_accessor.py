"""
AI实体权限访问器模块。
处理实体、权限和用户组之间的关联查询。
"""
import logging
from typing import List, Dict
from src.utils.database import db

logger = logging.getLogger(__name__)


class AIEntityPermissionAccessor:
    """
    AI实体权限访问器类。
    提供实体、权限和用户组之间关联关系的查询操作。
    """

    def __init__(self):
        """初始化访问器并设置数据库实例。"""
        self.db = db

    def get_entity_assigned_groups(self, entity_id: str, entity_type: int) -> List[Dict[str, str]]:
        """
        获取实体分配的用户组列表
        
        通过JOIN查询权限表和用户组表，获取指定实体被授权访问的所有用户组。
        
        参数:
            entity_id: 实体UUID
            entity_type: 实体类型（0：mcp_server, 1：platform, 2：prompt, 3：agent, 4：kb_chat, 5：skill）
            
        返回:
            用户组列表，每个元素包含 group_id 和 group_name
        """
        try:
            from src.accessors.ai_permissions_accessor import AIPermission
            from src.accessors.ai_user_group_accessor import AIUserGroup
            from sqlalchemy import and_
            
            # 通过JOIN一次性查询权限和用户组信息
            permissions_with_groups = self.db.session.query(
                AIPermission.group_id,
                AIUserGroup.name.label('group_name')
            ).join(
                AIUserGroup, AIPermission.group_id == AIUserGroup.uuid
            ).filter(
                and_(
                    AIPermission.entity_id == entity_id,
                    AIPermission.entity_type == entity_type
                )
            ).all()
            
            # 构建用户组列表
            return [
                {'group_id': perm.group_id, 'group_name': perm.group_name}
                for perm in permissions_with_groups
            ]
        except Exception as e:
            logger.error(f"Failed to get assigned groups for entity {entity_id} (type={entity_type}): {str(e)}")
            return []


# 创建全局访问器实例
ai_entity_permission_accessor = AIEntityPermissionAccessor()
