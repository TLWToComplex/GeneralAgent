"""
AI提示词访问器模块。
管理AI提示词的数据库操作。
"""
import uuid
from datetime import datetime
from src.utils.database import db
from typing import Dict, Any, Tuple, List, Union

class AIPrompt(db.Model):
    __tablename__ = 'ai_prompt'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(50), unique=True, nullable=False)
    text = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.String(10), nullable=False, default='private', comment='可见性: private 或 public')
    additional_info = db.Column(db.JSON)
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    create_by = db.Column(db.String(50), nullable=False)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    update_by = db.Column(db.String(50), nullable=False)

    @classmethod
    def add_prompt(cls, prompt_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            # 生成UUID如果不存在
            if 'uuid' not in prompt_data:
                prompt_data['uuid'] = str(uuid.uuid4())
            
            # 设置创建和更新时间
            if 'create_time' not in prompt_data:
                prompt_data['create_time'] = datetime.now()
            if 'update_time' not in prompt_data:
                prompt_data['update_time'] = datetime.now()
            
            new_prompt = cls(**prompt_data)
            db.session.add(new_prompt)
            db.session.commit()
            return True, cls._to_dict(new_prompt)
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def list_prompts(cls, skip: int = 0, take: int = 100, create_by: str = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        try:
            query = cls.query
            # 如果提供了create_by参数，只查询该用户创建的提示词
            if create_by:
                query = query.filter_by(create_by=create_by)
            prompts = query.order_by(cls.id).offset(skip).limit(take).all()
            return True, [cls._to_dict(prompt) for prompt in prompts] if prompts else []
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def list_prompts_by_user(cls, user_id: str, allowed_entity_ids: list = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """根据用户ID查询提示词记录，并包含有权限访问的记录"""
        try:
            from sqlalchemy import or_
            # 基础查询：自己创建的提示词（无论 visibility 状态）
            query = cls.query.filter_by(create_by=user_id)
            
            # 如果有授权的实体ID列表，则通过 OR 条件合并查询
            # 注意：这里我们只允许访问 visibility='public' 或者自己创建的 private 提示词
            if allowed_entity_ids:
                authorized_query = cls.query.filter(
                    cls.uuid.in_(allowed_entity_ids),
                    cls.visibility == 'public'
                )
                query = query.union(authorized_query)
            
            prompts = query.all()
            return True, [cls._to_dict(prompt) for prompt in prompts] if prompts else []
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_prompt(cls, prompt_id: int = None, uuid: str = None, create_by: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            query = cls.query
            if prompt_id is not None:
                query = query.filter_by(id=prompt_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            # 如果提供了create_by参数，只查询该用户创建的提示词
            if create_by:
                query = query.filter_by(create_by=create_by)
            
            prompt = query.first()
            if prompt:
                return True, cls._to_dict(prompt)
            else:
                return False, '提示词不存在'
        except Exception as e:
            return False, str(e)

    @classmethod
    def update_prompt(cls, prompt_id: int = None, uuid: str = None, update_data: dict = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            query = cls.query
            if prompt_id is not None:
                query = query.filter_by(id=prompt_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            prompt = query.first()
            if prompt:
                # 移除不能更新的字段
                update_data.pop('id', None)
                update_data.pop('uuid', None)
                update_data.pop('create_time', None)
                update_data.pop('create_by', None)
                
                # 设置更新时间
                update_data['update_time'] = datetime.now()
                
                for key, value in update_data.items():
                    setattr(prompt, key, value)
                
                db.session.commit()
                return True, cls._to_dict(prompt)
            else:
                return False, '提示词不存在'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_prompt(cls, prompt_id: int = None, uuid: str = None) -> Tuple[bool, str]:
        try:
            query = cls.query
            if prompt_id is not None:
                query = query.filter_by(id=prompt_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            prompt = query.first()
            if prompt:
                db.session.delete(prompt)
                db.session.commit()
                return True, '提示词删除成功'
            else:
                return False, '提示词不存在'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def _to_dict(prompt) -> Dict[str, Any]:
        """将模型实例转换为字典。"""
        return {
            'id': prompt.id,
            'uuid': prompt.uuid,
            'text': prompt.text,
            'visibility': prompt.visibility,
            'additional_info': prompt.additional_info,
            'create_time': prompt.create_time,
            'create_by': prompt.create_by,
            'update_time': prompt.update_time,
            'update_by': prompt.update_by
        }