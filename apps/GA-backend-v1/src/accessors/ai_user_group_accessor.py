"""
AI 用户组访问器模块。
使用SQLAlchemy ORM处理AI用户组的数据库操作。
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Union
from src.utils.database import db

logger = logging.getLogger(__name__)


class AIUserGroup(db.Model):
    """
    用户组数据模型类
    对应数据库表: ai_user_group
    """
    __tablename__ = 'ai_user_group'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    name = db.Column(db.String(50), nullable=False, unique=True, comment='群组名称')
    additional_info = db.Column(db.JSON, nullable=True, comment='扩展字段')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型对象转换为字典
        
        返回:
            包含用户组信息的字典
        """
        group_dict = {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by
        }
        
        # 处理additional_info字段
        if self.additional_info:
            group_dict['additional_info'] = self.additional_info
        else:
            group_dict['additional_info'] = {}
        
        return group_dict


class AIUserGroupAccessor:
    """
    AI 用户组数据库操作访问器类。
    提供使用SQLAlchemy ORM的AI用户组CRUD操作。
    """

    def __init__(self):
        """
        初始化访问器并设置数据库实例。
        """
        self.db = db

    def create_user_group(self, group_data: Dict[str, Any], create_by: str = 'admin') -> Tuple[bool, Dict[str, Any]]:
        """
        创建用户组
        
        参数:
            group_data: 用户组数据
            create_by: 创建人
            
        返回:
            成功状态和结果
        """
        try:
            # 检查名称是否已存在
            existing_group = AIUserGroup.query.filter_by(name=group_data.get('name')).first()
            if existing_group:
                return False, "用户组名称已存在"
            
            # 生成UUID
            group_uuid = str(uuid.uuid4())
            
            # 提取additional_info
            additional_info = group_data.get('additional_info', {})
            
            # 创建模型实例
            user_group = AIUserGroup(
                uuid=group_uuid,
                name=group_data.get('name'),
                additional_info=additional_info,
                create_time=datetime.now(),
                create_by=create_by,
                update_time=datetime.now(),
                update_by=create_by
            )
            
            # 添加到数据库
            self.db.session.add(user_group)
            self.db.session.commit()
            
            # 返回创建的用户组信息
            return True, {'uuid': group_uuid}
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to create user group: {str(e)}")
            return False, f"创建失败: {str(e)}"

    def get_user_group(self, group_uuid: str, create_by: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        获取用户组详情
        
        参数:
            group_uuid: 用户组UUID
            create_by: 可选，按创建人过滤
            
        返回:
            成功状态和用户组信息
        """
        try:
            # 构建查询
            query = AIUserGroup.query.filter_by(uuid=group_uuid)
            
            # 如果提供了create_by参数，则添加过滤条件
            if create_by:
                query = query.filter_by(create_by=create_by)
            
            # 查询用户组
            user_group = query.first()
            
            if not user_group:
                return False, "用户组不存在"
            
            # 转换为字典返回
            return True, user_group.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get user group: {str(e)}")
            return False, f"查询失败: {str(e)}"

    def list_user_groups(self, skip: int = 0, take: int = 100, create_by: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        获取用户组列表
        
        参数:
            skip: 跳过记录数
            take: 返回记录数
            create_by: 可选，按创建人过滤
            
        返回:
            成功状态和用户组列表
        """
        try:
            # 构建查询
            query = AIUserGroup.query
            
            # # 如果提供了create_by参数，则添加过滤条件
            # if create_by:
            #     query = query.filter_by(create_by=create_by)
            #
            # 获取总数
            total = query.count()
            
            # 分页查询
            user_groups = query.offset(skip).limit(take).all()
            
            # 转换为字典列表
            items = [group.to_dict() for group in user_groups]
            
            return True, {
                'items': items,
                'total': total,
                'skip': skip,
                'take': take
            }
            
        except Exception as e:
            logger.error(f"Failed to list user groups: {str(e)}")
            return False, f"查询失败: {str(e)}"

    def update_user_group(self, group_uuid: str, update_data: Dict[str, Any], update_by: str = 'admin') -> Tuple[bool, Dict[str, Any]]:
        """
        更新用户组
        
        参数:
            group_uuid: 用户组UUID
            update_data: 更新数据
            update_by: 更新人
            
        返回:
            成功状态和更新后的用户组信息
        """
        try:
            # 查询用户组
            user_group = AIUserGroup.query.filter_by(uuid=group_uuid).first()
            
            if not user_group:
                return False, "用户组不存在"
            
            # 检查名称是否与其他用户组冲突
            if 'name' in update_data and update_data['name'] != user_group.name:
                existing_group = AIUserGroup.query.filter(AIUserGroup.name == update_data['name'], AIUserGroup.uuid != group_uuid).first()
                if existing_group:
                    return False, "用户组名称已存在"
            
            # 更新字段
            for key, value in update_data.items():
                if key == 'name':
                    user_group.name = value
                elif key == 'additional_info':
                    user_group.additional_info = value
            
            # 更新时间和更新人
            user_group.update_time = datetime.now()
            user_group.update_by = update_by
            
            # 提交更新
            self.db.session.commit()
            
            # 返回更新后的用户组信息
            return True, user_group.to_dict()
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to update user group: {str(e)}")
            return False, f"更新失败: {str(e)}"

    def delete_user_group(self, group_uuid: str, delete_by: str = 'admin') -> Tuple[bool, str]:
        """
        删除用户组
        
        参数:
            group_uuid: 用户组UUID
            delete_by: 删除人
            
        返回:
            成功状态和消息
        """
        try:
            # 查询用户组
            user_group = AIUserGroup.query.filter_by(uuid=group_uuid).first()
            
            if not user_group:
                return False, "用户组不存在"
            
            # 删除用户组
            self.db.session.delete(user_group)
            self.db.session.commit()
            
            return True, "用户组删除成功"

        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to delete user group: {str(e)}")
            return False, f"删除失败: {str(e)}"

    def set_default_user_group(self, group_uuid: str, update_by: str = 'admin') -> Tuple[bool, Any]:
        """
        设置默认用户组：将指定用户组标记为默认，其余清除默认标记
        """
        try:
            target = AIUserGroup.query.filter_by(uuid=group_uuid).first()
            if not target:
                return False, "用户组不存在"

            now = datetime.now()
            # 清除所有用户组的 is_default 标记
            for group in AIUserGroup.query.all():
                if group.additional_info and group.additional_info.get('is_default'):
                    group.additional_info = {**group.additional_info, 'is_default': False}
                    group.update_time = now
                    group.update_by = update_by

            # 设置目标用户组为默认
            target.additional_info = {**(target.additional_info or {}), 'is_default': True}
            target.update_time = now
            target.update_by = update_by

            self.db.session.commit()
            return True, target.to_dict()

        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to set default user group: {str(e)}")
            return False, f"设置失败: {str(e)}"

    def get_default_user_group(self) -> Tuple[bool, Any]:
        """
        获取当前默认用户组
        """
        try:
            groups = AIUserGroup.query.all()
            for group in groups:
                if group.additional_info and group.additional_info.get('is_default'):
                    return True, group.to_dict()
            return False, "未设置默认用户组"
        except Exception as e:
            logger.error(f"Failed to get default user group: {str(e)}")
            return False, f"查询失败: {str(e)}"


# 创建全局访问器实例
ai_user_group_accessor = AIUserGroupAccessor()