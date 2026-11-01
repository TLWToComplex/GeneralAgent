"""
AI权限访问器模块。
管理AI权限的数据库操作。
"""
import uuid
from datetime import datetime
from src.utils.database import db
from typing import Dict, Any, Tuple, List, Union

class AIPermission(db.Model):
    __tablename__ = 'ai_permissions'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(50), unique=True, nullable=False)
    group_id = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50))
    permission = db.Column(db.Integer, nullable=False)
    additional_info = db.Column(db.JSON)
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    create_by = db.Column(db.String(50), nullable=False)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    update_by = db.Column(db.String(50), nullable=False)

    @classmethod
    def add_permission(cls, permission_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            # 生成UUID如果不存在
            if 'uuid' not in permission_data:
                permission_data['uuid'] = str(uuid.uuid4())
            
            # 设置创建和更新时间
            if 'create_time' not in permission_data:
                permission_data['create_time'] = datetime.now()
            if 'update_time' not in permission_data:
                permission_data['update_time'] = datetime.now()
            
            new_permission = cls(**permission_data)
            db.session.add(new_permission)
            db.session.commit()
            return True, cls._to_dict(new_permission)
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def list_permissions(cls, skip: int = 0, take: int = 100, filters: dict = None) -> Tuple[bool, Union[Dict, str]]:
        try:
            query = cls.query
            
            # 应用过滤条件
            if filters:
                # 处理group_id过滤
                if 'group_id' in filters:
                    query = query.filter_by(group_id=filters['group_id'])
                # 处理entity_id和entity_type过滤
                if 'entity_id' in filters and 'entity_type' in filters:
                    query = query.filter_by(entity_id=filters['entity_id'], entity_type=filters['entity_type'])
                elif 'entity_id' in filters:
                    query = query.filter_by(entity_id=filters['entity_id'])
                elif 'entity_type' in filters:
                    query = query.filter_by(entity_type=filters['entity_type'])
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            permissions = query.order_by(cls.id).offset(skip).limit(take).all()
            
            return True, {
                'items': [cls._to_dict(permission) for permission in permissions] if permissions else [],
                'total': total,
                'skip': skip,
                'take': take
            }
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_permission(cls, permission_id: int = None, uuid: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            query = cls.query
            if permission_id is not None:
                query = query.filter_by(id=permission_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            permission = query.first()
            if permission:
                return True, cls._to_dict(permission)
            else:
                return False, '权限不存在'
        except Exception as e:
            return False, str(e)

    @classmethod
    def update_permission(cls, permission_id: int = None, uuid: str = None, update_data: dict = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            query = cls.query
            if permission_id is not None:
                query = query.filter_by(id=permission_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            permission = query.first()
            if permission:
                # 移除不能更新的字段
                update_data.pop('id', None)
                update_data.pop('uuid', None)
                update_data.pop('create_time', None)
                update_data.pop('create_by', None)
                
                # 设置更新时间
                update_data['update_time'] = datetime.now()
                
                for key, value in update_data.items():
                    setattr(permission, key, value)
                
                db.session.commit()
                return True, cls._to_dict(permission)
            else:
                return False, '权限不存在'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_permission(cls, permission_id: int = None, uuid: str = None) -> Tuple[bool, str]:
        try:
            query = cls.query
            if permission_id is not None:
                query = query.filter_by(id=permission_id)
            elif uuid is not None:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供id或uuid'
            
            permission = query.first()
            if permission:
                db.session.delete(permission)
                db.session.commit()
                return True, '权限删除成功'
            else:
                return False, '权限不存在'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_permissions_by_group(cls, group_id: str) -> Tuple[bool, str]:
        try:
            deleted = cls.query.filter_by(group_id=group_id).delete()
            db.session.commit()
            return True, f'成功删除{deleted}条权限记录'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def _to_dict(permission) -> Dict[str, Any]:
        """将模型实例转换为字典。"""
        return {
            'id': permission.id,
            'uuid': permission.uuid,
            'group_id': permission.group_id,
            'entity_id': permission.entity_id,
            'entity_type': permission.entity_type,
            'name': permission.name,
            'permission': permission.permission,
            'additional_info': permission.additional_info,
            'create_time': permission.create_time,
            'create_by': permission.create_by,
            'update_time': permission.update_time,
            'update_by': permission.update_by
        }