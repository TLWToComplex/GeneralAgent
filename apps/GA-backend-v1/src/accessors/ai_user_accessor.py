"""
AI用户访问器模块。
管理AI用户记录的数据库操作。
"""
import uuid
from datetime import datetime
from sqlalchemy import cast, String
from sqlalchemy.inspection import inspect
from werkzeug.security import generate_password_hash, check_password_hash
from src.utils.database import db
import logging
logger = logging.getLogger(__name__)

class AIUser(db.Model):
    __tablename__ = 'ai_user'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    email = db.Column(db.String(255), nullable=True, comment='邮箱')
    realname = db.Column(db.String(50), nullable=True, comment='真实姓名')
    contact = db.Column(db.String(255), nullable=True, comment='联系方式')
    address = db.Column(db.String(500), nullable=True, comment='家庭住址')
    password = db.Column(db.String(255), nullable=False, comment='密码')
    additional_info = db.Column(db.JSON, nullable=False, comment='扩展字段')
    platform_sort = db.Column(db.JSON, nullable=False, comment='模型平台排序')
    preferences = db.Column(db.JSON, nullable=False, comment='用户偏好')
    create_time = db.Column(db.DateTime, nullable=True, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=True, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=True, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=True, comment='更新人')
    is_del = db.Column(db.Integer, nullable=False, default=0, comment='是否删除（0：未删除 1：已删除）')
    
    def to_dict(self):
        """将模型对象转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'username': self.username,
            'email': self.email,
            'realname': self.realname,
            'contact': self.contact,
            'address': self.address,
            'additional_info': self.additional_info,
            'platform_sort': self.platform_sort,
            'preferences': self.preferences,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by,
            'is_del': self.is_del
        }
    
    @classmethod
    def add_user(cls, user_data: dict):
        try:
            # 生成UUID
            if 'uuid' not in user_data:
                user_data['uuid'] = str(uuid.uuid4())
            
            # 设置时间戳
            current_time = datetime.now()
            user_data.setdefault('create_time', current_time)
            user_data.setdefault('update_time', current_time)
            
            # 确保additional_info是字典
            if 'additional_info' not in user_data:
                user_data['additional_info'] = {}
            elif user_data['additional_info'] is not None and not isinstance(user_data['additional_info'], dict):
                return False, "additional_info必须是字典类型"

            # 记录初始密码变更时间戳
            user_data['additional_info']['last_password_change'] = current_time.isoformat()
            
            # 设置默认删除状态
            user_data.setdefault('is_del', 0)
            
            # 验证必填字段
            required_fields = ['username', 'password']
            for field in required_fields:
                if field not in user_data:
                    return False, f"{field}为必填字段"
            
            # 检查用户名是否已存在（包括已删除的用户）
            existing_user = cls.query.filter_by(username=user_data['username']).first()
            if existing_user:
                if existing_user.is_del == 0:
                    return False, f"用户名 {user_data['username']} 已存在"
                else:
                    # 如果用户已被软删除，先硬删除该用户
                    from src.accessors.ai_user_group_relation_accessor import ai_user_group_relation_accessor
                    ai_user_group_relation_accessor.delete_user_group_relations_by_user(
                        user_id=existing_user.uuid,
                        delete_by='system'
                    )
                    db.session.delete(existing_user)
                    db.session.commit()
                    logger.info(f"Deleted old record and relations for username: {user_data['username']}")
            
            # 加密密码
            user_data['password'] = generate_password_hash(user_data['password'])
            
            new_user = cls(**user_data)
            db.session.add(new_user)
            db.session.commit()
            return True, new_user.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding user: {str(e)}")
            return False, str(e)
    
    @classmethod
    def list_users(cls, skip: int = 0, take: int = 100):
        try:
            # 只查询未删除的用户
            users = cls.query.filter_by(is_del=0).order_by(cls.id).offset(skip).limit(take).all()
            return True, [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return False, str(e)
    
    @classmethod
    def get_user(cls, user_id: int = None, uuid: str = None, username: str = None):
        try:
            query = cls.query.filter_by(is_del=0)
                
            if user_id:
                query = query.filter_by(id=user_id)
            elif uuid:
                query = query.filter_by(uuid=uuid)
            elif username:
                query = query.filter_by(username=username)
            else:
                return False, '必须提供user_id、uuid、username或email'
            
            user = query.first()
            if user:
                return True, user.to_dict()
            else:
                return False, '用户不存在'
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return False, str(e)
    
    @classmethod
    def update_user(cls, user_id: int, update_data: dict):
        try:
            # 不允许直接更新uuid
            update_data.pop('uuid', None)
            
            # 获取用户
            user = cls.query.filter_by(id=user_id, is_del=0).first()
            if not user:
                return False, '用户不存在'
            
            # 如果要更新用户名，检查是否已存在
            if 'username' in update_data and update_data['username'] != user.username:
                existing_user = cls.query.filter_by(username=update_data['username']).first()
                if existing_user:
                    if existing_user.is_del == 0:
                        return False, f"用户名 {update_data['username']} 已存在"
                    else:
                        # 如果用户已被删除，可以考虑允许重新使用用户名，或者返回错误
                        # 这里选择返回错误，要求使用不同的用户名
                        return False, f"用户名 {update_data['username']} 已被使用过，请选择其他用户名"
            
            # 更新additional_info字段
            if 'additional_info' in update_data:
                if update_data['additional_info'] is not None and not isinstance(update_data['additional_info'], dict):
                    return False, "additional_info必须是字典类型"
            
            # 加密密码（如果提供了新密码）
            if 'password' in update_data:
                update_data['password'] = generate_password_hash(update_data['password'])
            
            # 更新其他字段
            for key, value in update_data.items():
                setattr(user, key, value)
            
            # 更新时间戳
            user.update_time = datetime.now()
            
            db.session.commit()
            return True, user.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            return False, str(e)
    
    @classmethod
    def delete_user(cls, user_uuid: str):
        try:
            # 使用软删除
            user = cls.query.filter_by(uuid=user_uuid, is_del=0).first()
            if user:
                user.is_del = 1
                user.update_time = datetime.now()
                db.session.commit()
                return True, {'message': '用户删除成功'}
            else:
                return False, '用户不存在'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            return False, str(e)
    
    @classmethod
    def query_users(cls, username: str = None, realname: str = None, contact: str = None, create_by: str = None, skip: int = 0, take: int = 100):
        try:
            query = cls.query.filter_by(is_del=0)
            
            if create_by:
                query = query.filter_by(create_by=create_by)
                
            if username:
                query = query.filter(cls.username.like(f'%{username}%'))
            
            if realname:
                query = query.filter(cls.realname.like(f'%{realname}%'))
            
            if contact:
                query = query.filter(cls.contact.like(f'%{contact}%'))
            
            users = query.order_by(cls.id).offset(skip).limit(take).all()
            return True, [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error querying users: {str(e)}")
            return False, str(e)
    
    @classmethod
    def verify_password(cls, username: str, password: str) -> bool:
        """
        验证用户密码
        
        Args:
            username (str): 用户名
            password (str): 明文密码
            
        Returns:
            bool: 密码是否正确
        """
        try:
            user = cls.query.filter_by(username=username, is_del=0).first()
            if user:
                return check_password_hash(user.password, password)
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    @classmethod
    def update_user_additional_info(cls, user, additional_info: dict) -> bool:
        """
        更新用户附加信息（独立事务，自带提交和回滚）
        
        :param user: 用户对象
        :param additional_info: 新的附加信息字典
        :return: 是否成功
        """
        try:
            from sqlalchemy.orm.attributes import flag_modified
            user.additional_info = additional_info
            flag_modified(user, 'additional_info')
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user additional_info: {str(e)}")
            return False

    @classmethod
    def update_user_additional_info_in_transaction(cls, user, additional_info: dict) -> bool:
        """
        在已有事务/行锁上下文中更新用户附加信息并提交。
        适用于调用方已通过 SELECT ... FOR UPDATE 锁定行的场景，
        由该方法统一完成赋值、标记脏字段和提交。
        
        :param user: 用户对象（已在行锁保护下）
        :param additional_info: 新的附加信息字典
        :return: 是否成功
        """
        try:
            from sqlalchemy.orm.attributes import flag_modified
            user.additional_info = additional_info
            flag_modified(user, 'additional_info')
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user additional_info in transaction: {str(e)}")
            return False