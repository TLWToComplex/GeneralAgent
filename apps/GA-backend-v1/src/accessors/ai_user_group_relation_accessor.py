"""
AI 用户组关联表数据访问层
处理用户组关联表的CRUD操作
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy import and_, desc, func
from src.utils.database import db
from sqlalchemy import Column, String, Integer, DateTime, JSON, BigInteger

logger = logging.getLogger(__name__)


class AIUserGroupRelation(db.Model):
    """
    用户组关联表模型类
    对应数据库中的ai_user_group_relation表
    """
    __tablename__ = 'ai_user_group_relation'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = Column(String(50), nullable=False, unique=True, comment='唯一ID')
    user_id = Column(String(50), nullable=False, comment='用户ID（关联ai_user.uuid）')
    group_id = Column(String(50), nullable=False, comment='群组ID（关联ai_user_group.uuid）')
    additional_info = Column(JSON, nullable=True, comment='扩展字段')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    create_by = Column(String(50), nullable=False, comment='创建人')
    update_time = Column(DateTime, nullable=False, comment='更新时间')
    update_by = Column(String(50), nullable=False, comment='更新人')


class AIUserGroupRelationAccessor:
    """
    用户组关联表数据访问类
    提供用户组关联表的CRUD操作
    """

    def __init__(self):
        pass

    def create_user_group_relation(self, data: Dict, create_by: str = 'admin') -> Tuple[bool, Any]:
        """
        创建用户组关联
        
        Args:
            data: 包含关联信息的字典，必须包含user_id和group_id
            create_by: 创建人
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回创建的关联信息，失败返回错误信息)
        """
        try:
            # 验证必填字段
            if 'user_id' not in data or 'group_id' not in data:
                return False, 'user_id和group_id为必填字段'
            
            # 检查关联是否已存在
            existing = AIUserGroupRelation.query.filter(
                and_(
                    AIUserGroupRelation.user_id == data['user_id'],
                    AIUserGroupRelation.group_id == data['group_id']
                )
            ).first()
            
            if existing:
                return False, '该用户与用户组的关联已存在'

            # 创建新关联
            relation_uuid = str(uuid.uuid4())
            now = datetime.now()
            
            relation = AIUserGroupRelation(
                uuid=relation_uuid,
                user_id=data['user_id'],
                group_id=data['group_id'],
                additional_info=data.get('additional_info'),
                create_time=now,
                create_by=create_by,
                update_time=now,
                update_by=create_by
            )
            
            db.session.add(relation)
            db.session.commit()
            
            logger.info(f"Created user group relation: user_id={data['user_id']}, group_id={data['group_id']}")
            
            return True, {
                'uuid': relation_uuid,
                'user_id': data['user_id'],
                'group_id': data['group_id']
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create user group relation: {str(e)}")
            return False, f'创建关联失败: {str(e)}'

    def get_user_group_relation(self, relation_uuid: str) -> Tuple[bool, Any]:
        """
        获取用户组关联详情
        
        Args:
            relation_uuid: 关联的UUID
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回关联详情，失败返回错误信息)
        """
        try:
            relation = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.uuid == relation_uuid
            ).first()
            
            if not relation:
                return False, '关联不存在'
            
            return True, {
                'id': relation.id,
                'uuid': relation.uuid,
                'user_id': relation.user_id,
                'group_id': relation.group_id,
                'additional_info': relation.additional_info,
                'create_time': relation.create_time.strftime('%Y-%m-%d %H:%M:%S') if relation.create_time else None,
                'create_by': relation.create_by,
                'update_time': relation.update_time.strftime('%Y-%m-%d %H:%M:%S') if relation.update_time else None,
                'update_by': relation.update_by
            }
            
        except Exception as e:
            logger.error(f"Failed to get user group relation: {str(e)}")
            return False, f'获取关联失败: {str(e)}'

    def list_user_group_relations(self, skip: int = 0, take: int = 100, 
                                filters: Optional[Dict] = None) -> Tuple[bool, Any]:
        """
        获取用户组关联列表
        
        Args:
            skip: 跳过记录数
            take: 返回记录数
            filters: 过滤条件，可选包含user_id、group_id等
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回关联列表及分页信息，失败返回错误信息)
        """
        try:
            query = AIUserGroupRelation.query
            
            # 应用过滤条件
            if filters:
                if 'user_id' in filters:
                    query = query.filter(AIUserGroupRelation.user_id == filters['user_id'])
                if 'group_id' in filters:
                    query = query.filter(AIUserGroupRelation.group_id == filters['group_id'])
            
            # 获取总数
            total = query.count()
            
            # 应用分页并获取数据
            relations = query.order_by(desc(AIUserGroupRelation.create_time))\
                             .offset(skip).limit(take).all()
            
            items = []
            for relation in relations:
                items.append({
                    'id': relation.id,
                    'uuid': relation.uuid,
                    'user_id': relation.user_id,
                    'group_id': relation.group_id,
                    'additional_info': relation.additional_info,
                    'create_time': relation.create_time.strftime('%Y-%m-%d %H:%M:%S') if relation.create_time else None,
                    'create_by': relation.create_by,
                    'update_time': relation.update_time.strftime('%Y-%m-%d %H:%M:%S') if relation.update_time else None,
                    'update_by': relation.update_by
                })
            
            return True, {
                'items': items,
                'total': total,
                'skip': skip,
                'take': take
            }
            
        except Exception as e:
            logger.error(f"Failed to list user group relations: {str(e)}")
            return False, f'获取关联列表失败: {str(e)}'

    def update_user_group_relation(self, relation_uuid: str, data: Dict, 
                                 update_by: str = 'admin') -> Tuple[bool, Any]:
        """
        更新用户组关联
        
        Args:
            relation_uuid: 关联的UUID
            data: 要更新的数据
            update_by: 更新人
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回更新后的关联信息，失败返回错误信息)
        """
        try:
            relation = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.uuid == relation_uuid
            ).first()
            
            if not relation:
                return False, '关联不存在'
            
            # 不允许更新user_id和group_id，因为它们是唯一约束的一部分
            if 'user_id' in data or 'group_id' in data:
                return False, '不允许更新user_id和group_id字段'
            
            # 更新可修改字段
            if 'additional_info' in data:
                relation.additional_info = data['additional_info']
            
            relation.update_time = datetime.now()
            relation.update_by = update_by
            
            db.session.commit()
            
            logger.info(f"Updated user group relation: {relation_uuid}")
            
            # 返回更新后的信息
            return True, {
                'id': relation.id,
                'uuid': relation.uuid,
                'user_id': relation.user_id,
                'group_id': relation.group_id,
                'additional_info': relation.additional_info,
                'create_time': relation.create_time.strftime('%Y-%m-%d %H:%M:%S') if relation.create_time else None,
                'create_by': relation.create_by,
                'update_time': relation.update_time.strftime('%Y-%m-%d %H:%M:%S') if relation.update_time else None,
                'update_by': relation.update_by
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update user group relation: {str(e)}")
            return False, f'更新关联失败: {str(e)}'

    def delete_user_group_relation(self, relation_uuid: str, delete_by: str = 'admin') -> Tuple[bool, Any]:
        """
        删除用户组关联
        
        Args:
            relation_uuid: 关联的UUID
            delete_by: 删除人
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回成功消息，失败返回错误信息)
        """
        try:
            relation = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.uuid == relation_uuid
            ).first()
            
            if not relation:
                return False, '关联不存在'
            
            db.session.delete(relation)
            db.session.commit()
            
            logger.info(f"Deleted user group relation: {relation_uuid} by {delete_by}")
            
            return True, '删除成功'
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete user group relation: {str(e)}")
            return False, f'删除关联失败: {str(e)}'

    def delete_user_group_relations_by_user(self, user_id: str, delete_by: str = 'admin') -> Tuple[bool, Any]:
        """
        根据用户ID删除所有关联
        
        Args:
            user_id: 用户ID
            delete_by: 删除人
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回成功消息，失败返回错误信息)
        """
        try:
            # 查找并删除所有关联
            relations = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.user_id == user_id
            ).all()
            
            if not relations:
                return True, '没有找到关联记录'
            
            for relation in relations:
                db.session.delete(relation)
            
            db.session.commit()
            
            logger.info(f"Deleted {len(relations)} user group relations for user: {user_id} by {delete_by}")
            
            return True, f'成功删除{len(relations)}条关联记录'
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete user group relations by user: {str(e)}")
            return False, f'删除关联失败: {str(e)}'

    def delete_user_group_relations_by_group(self, group_id: str, delete_by: str = 'admin') -> Tuple[bool, Any]:
        """
        根据用户组ID删除所有关联
        
        Args:
            group_id: 用户组ID
            delete_by: 删除人
        
        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回成功消息，失败返回错误信息)
        """
        try:
            # 查找并删除所有关联
            relations = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.group_id == group_id
            ).all()
            
            if not relations:
                return True, '没有找到关联记录'
            
            for relation in relations:
                db.session.delete(relation)
            
            db.session.commit()
            
            logger.info(f"Deleted {len(relations)} user group relations for group: {group_id} by {delete_by}")
            
            return True, f'成功删除{len(relations)}条关联记录'
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete user group relations by group: {str(e)}")
            return False, f'删除关联失败: {str(e)}'

    def get_user_groups_by_user_id(self, user_id: str) -> Tuple[bool, Any]:
        """
        根据用户ID获取该用户所属的所有用户组ID

        Args:
            user_id: 用户ID

        Returns:
            Tuple[bool, Any]: (是否成功, 成功返回用户组列表，失败返回错误信息)
        """
        try:
            relations = AIUserGroupRelation.query.filter(
                AIUserGroupRelation.user_id == user_id
            ).all()

            group_ids = [relation.group_id for relation in relations]

            return True, group_ids

        except Exception as e:
            logger.error(f"Failed to get user groups by user: {str(e)}")
            return False, []


# 创建访问器实例
ai_user_group_relation_accessor = AIUserGroupRelationAccessor()