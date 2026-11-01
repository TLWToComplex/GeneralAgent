"""
AI实体权限控制器模块。
提供实体、权限和用户组之间关联关系的查询接口。
"""
from flask import request, jsonify
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class AIEntityPermissionController:
    """
    AI实体权限控制器类。
    提供实体与用户组关联关系的查询接口。
    """

    @staticmethod
    async def get_entity_assigned_groups(current_user: str = None) -> Tuple[Dict, int]:
        """
        获取实体分配的用户组列表
        
        参数:
            entity_id: 实体UUID（必需）
            entity_type: 实体类型（必需）
                - 0: MCP Server
                - 1: Platform
                - 2: Prompt
                - 3: Agent
                - 4: KB Chat
                - 5: Skill
                
        返回:
            包含用户组列表的JSON响应
        """
        from src.accessors.ai_entity_permission_accessor import ai_entity_permission_accessor
        from src.utils.entity_type import EntityType
        
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
        
        # 获取请求参数
        entity_id = request.args.get('entity_id', type=str)
        entity_type = request.args.get('entity_type', type=int)
        
        # 验证参数
        if not entity_id:
            return jsonify({'error': '必须提供实体ID (entity_id)'}), 400
        
        if entity_type is None:
            return jsonify({'error': '必须提供实体类型 (entity_type)'}), 400
        
        # 验证实体类型是否有效
        if not EntityType.is_valid(entity_type):
            return jsonify({
                'error': f'无效的实体类型，有效值为: {EntityType.get_all_types()}'
            }), 400
        
        try:
            # 调用 accessor 查询用户组列表
            assigned_groups = ai_entity_permission_accessor.get_entity_assigned_groups(
                entity_id=entity_id,
                entity_type=entity_type
            )
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'entity_id': entity_id,
                    'entity_type': entity_type,
                    'assigned_groups': assigned_groups
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to get assigned groups for entity {entity_id} (type={entity_type}): {str(e)}")
            return jsonify({
                'code': 1,
                'message': f'查询失败: {str(e)}'
            }), 500


# 创建全局控制器实例
ai_entity_permission_controller = AIEntityPermissionController()
