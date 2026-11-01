"""
AI知识库访问器模块。
管理AI知识库的数据库操作。
"""
import uuid
import logging
from datetime import datetime
from src.utils.database import db
from src.utils.entity_type import EntityType

from typing import Dict, Any, Tuple, List, Union

logger = logging.getLogger(__name__)


class AIKBChat(db.Model):
    """AI知识库数据模型类"""
    __tablename__ = 'ai_kb_chat'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    name = db.Column(db.String(50), unique=True, nullable=False, comment='知识库名称')
    visibility = db.Column(db.String(10), nullable=False, default='private', comment='可见性: private 或 public')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')
    
    def to_dict(self) -> Dict[str, Any]:
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'visibility': self.visibility,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by
        }
    
    @classmethod
    def add_kb_chat(cls, kb_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        创建知识库记录
        
        参数:
            kb_data: 包含 name, create_by 等字段的字典
            
        返回:
            (成功状态, 结果)
        """
        try:
            # 生成UUID
            if 'uuid' not in kb_data:
                kb_data['uuid'] = str(uuid.uuid4())
            
            # 设置默认值
            kb_data.setdefault('visibility', 'private')
            current_time = datetime.now()
            kb_data.setdefault('create_time', current_time)
            kb_data.setdefault('update_time', current_time)
            kb_data.setdefault('update_by', kb_data.get('create_by', 'admin'))
            
            new_kb = cls(**kb_data)
            db.session.add(new_kb)
            db.session.commit()
            return True, new_kb.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding kb_chat: {str(e)}")
            return False, str(e)
    
    @classmethod
    def list_kb_chats(cls, create_by: str = None, allowed_entity_ids: list = None, permission_code: str = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """查询知识库列表"""
        try:
            from sqlalchemy import or_, and_

            if create_by == 'admin':
                # Admin 根据 permission_code 过滤
                if permission_code:
                    query = cls.query.filter(cls.visibility == permission_code)
                else:
                    # 默认返回所有
                    query = cls.query
            else:
                # 根据 permission_code 决定查询逻辑
                if permission_code == 'public':
                    # 返回权限组授权的 public 智能体
                    if allowed_entity_ids:
                        query = cls.query.filter(
                            and_(
                                cls.uuid.in_(allowed_entity_ids),
                                cls.visibility == 'public'
                            )
                        )
                    else:
                        # 没有权限组授权，返回空结果
                        query = cls.query.filter(cls.id == -1)
                elif permission_code == 'private':
                    # 返回自己创建的智能体（无论 visibility）
                    query = cls.query.filter(cls.create_by == create_by)
                else:
                    # 默认行为：同时返回 private 和授权的 public
                    conditions = []
                    
                    # 1. 自己创建的 private 智能体
                    conditions.append(
                        and_(
                            cls.create_by == create_by,
                            cls.visibility == 'private'
                        )
                    )
                    
                    # 2. 权限组授权的 public 智能体
                    if allowed_entity_ids:
                        conditions.append(
                            and_(
                                cls.uuid.in_(allowed_entity_ids),
                                cls.visibility == 'public'
                            )
                        )

                    query = cls.query.filter(or_(*conditions))

            kb_chats = query.order_by(cls.id).all()
            return True, [kb.to_dict() for kb in kb_chats] if kb_chats else []
        except Exception as e:
            logger.error(f"Error listing kb_chats: {str(e)}")
            return False, str(e)
    
    @classmethod
    def get_kb_chat(cls, name: str = None, uuid: str = None, create_by: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """获取单个知识库详情"""
        try:
            query = cls.query
            if name:
                query = query.filter_by(name=name)
            elif uuid:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供name或uuid参数'
            
            kb_chat = query.first()
            if kb_chat:
                return True, kb_chat.to_dict()
            else:
                return False, '知识库不存在或无访问权限'
        except Exception as e:
            logger.error(f"Error getting kb_chat: {str(e)}")
            return False, str(e)
    
    @classmethod
    def delete_kb_chat(cls, name: str = None, create_by: str = None) -> Tuple[bool, str]:
        """删除知识库记录"""
        try:
            query = cls.query.filter_by(name=name)
            
            kb_chat = query.first()
            if kb_chat:
                db.session.delete(kb_chat)
                db.session.commit()
                return True, '知识库删除成功'
            else:
                return False, '知识库不存在或无删除权限'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting kb_chat: {str(e)}")
            return False, str(e)
    
    @classmethod
    def update_kb_chat(cls, name: str = None, update_data: dict = None, current_user: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        更新知识库信息
        
        参数:
            name: 知识库名称
            update_data: 更新数据
            current_user: 当前用户
        """
        try:
            if not update_data or not isinstance(update_data, dict):
                return False, "更新数据必须是非空字典"
            
            query = cls.query.filter_by(name=name)
            kb_chat = query.first()
            
            if not kb_chat:
                return False, '知识库不存在'
            
            # 只有创建者或admin可以修改
            if current_user and kb_chat.create_by != current_user and current_user.lower() != 'admin':
                return False, '无权修改该知识库'
            
            # 如果尝试修改 visibility，只有 admin 可以
            if 'visibility' in update_data and current_user.lower() != 'admin':
                return False, '只有管理员可以修改可见性'
            
            # 处理 name 字段的特殊情况（重命名）
            new_name = update_data.pop('name', None)
            if new_name and new_name != kb_chat.name:
                # 检查新名称是否已被使用
                existing = cls.query.filter_by(name=new_name).first()
                if existing:
                    return False, f'知识库名称 "{new_name}" 已存在'
            
            # 不允许更新的其他字段
            update_data.pop('id', None)
            update_data.pop('uuid', None)
            update_data.pop('create_time', None)
            update_data.pop('create_by', None)
            
            # 更新时间戳
            update_data['update_time'] = datetime.now()
            update_data['update_by'] = current_user or 'admin'
            
            # 更新字段
            for key, value in update_data.items():
                setattr(kb_chat, key, value)
            
            # 如果有新名称，更新 name
            if new_name:
                kb_chat.name = new_name
            
            db.session.commit()
            return True, kb_chat.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating kb_chat: {str(e)}")
            return False, str(e)


# 创建全局实例
ai_kb_chat_accessor = AIKBChat()
