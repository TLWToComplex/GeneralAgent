"""
AI平台模型访问器模块。
管理AI平台和模型记录的数据库操作。
"""
import uuid
from datetime import datetime
from sqlalchemy import inspect
from src.utils.database import db
import logging

logger = logging.getLogger(__name__)


class AIPlatform(db.Model):
    """AI平台模型"""
    __tablename__ = 'ai_platform'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    name = db.Column(db.String(50), unique=True, nullable=False, comment='模型平台名称')
    api_key = db.Column(db.String(500), nullable=False, comment='模型平台密钥')
    no_api_key_required = db.Column(db.Integer, nullable=False, comment='是否需要平台密钥（0：否 1：是）')
    api_url = db.Column(db.String(500), nullable=False, comment='模型平台地址')
    # 注意：visibility 字段当前未使用，平台权限控制改为：所有人可见，仅 admin 和创建者可修改/删除
    visibility = db.Column(db.String(10), nullable=False, default='private', comment='可见性: private 或 public（已废弃，保留用于向后兼容）')
    additional_info = db.Column(db.JSON, nullable=False, default=dict, comment='扩展字段')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')
    
    def to_dict(self):
        """将模型对象转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'api_key': self.api_key,
            'no_api_key_required': self.no_api_key_required,
            'api_url': self.api_url,
            'additional_info': self.additional_info,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by
        }


class AIModel(db.Model):
    """AI模型模型"""
    __tablename__ = 'ai_models'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    model_id = db.Column(db.String(100), nullable=False, comment='模型标识')
    platform_id = db.Column(db.String(50), nullable=False, comment='模型服务编号（关联ai_platform.uuid）')
    model_name = db.Column(db.String(50), nullable=False, comment='模型名称')
    model_type = db.Column(db.Integer, nullable=False, comment='模型类型')
    context_size = db.Column(db.Integer, nullable=True, default=None, comment='上下文大小（token数量）')
    additional_info = db.Column(db.JSON, nullable=False, default=dict, comment='扩展字段')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')
    
    def to_dict(self):
        """将模型对象转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'model_id': self.model_id,
            'platform_id': self.platform_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'context_size': self.context_size,
            'additional_info': self.additional_info,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by
        }


class AIPlatformModelAccessor:
    """AI平台模型访问器，提供统一的接口来操作AI平台和模型数据"""
    
    @staticmethod
    def create_platform_with_models(platform_data, models_data, create_by='admin'):
        """创建平台并同时创建关联的模型"""
        try:
            # 开始事务
            with db.session.begin():
                # 准备平台数据
                current_time = datetime.now()
                
                # 从请求体中提取平台核心字段
                platform_core = {
                    'uuid': str(uuid.uuid4()),
                    'name': platform_data.get('name'),
                    'api_key': platform_data.get('credentials', {}).get('apiKey', ''),
                    'no_api_key_required': 0 if platform_data.get('noApiKeyRequired', False) else 1,
                    'api_url': platform_data.get('connection', {}).get('apiBaseUrl', ''),
                    'create_time': current_time,
                    'create_by': create_by,
                    'update_time': current_time,
                    'update_by': create_by
                }
                
                # 准备additional_info字段，存储请求体中不在核心字段的数据
                additional_info = {
                    'type': platform_data.get('type'),
                    'providerIcon': platform_data.get('providerIcon'),
                    'backgroundColor': platform_data.get('backgroundColor')
                }
                
                # 添加avatar信息
                if platform_data.get('avatar'):
                    additional_info['avatar'] = platform_data.get('avatar')
                
                platform_core['additional_info'] = additional_info
                
                # 创建平台
                new_platform = AIPlatform(**platform_core)
                db.session.add(new_platform)
                db.session.flush()  # 获取平台ID但不提交事务
                
                # 处理模型数据
                created_models = []
                for model_group in models_data:
                    group_id = model_group.get('id')
                    group_name = model_group.get('name')
                    
                    for model in model_group.get('models', []):
                        # 准备模型数据
                        model_type_map = {
                            'chat': 1,
                            'vision': 2,
                            'embedding': 3
                        }
                        
                        # 确定模型类型（取第一个类型或默认值）
                        model_types = model.get('types', [])
                        model_type = model_type_map.get(model_types[0] if model_types else 'chat', 1)
                        
                        # 准备模型additional_info
                        model_additional = {
                            'iconText': model.get('iconText'),
                            'types': model_types,
                            'group_id': group_id,
                            'group_name': group_name
                        }
                        
                        model_data = {
                            'uuid': str(uuid.uuid4()),
                            'model_id': model.get('id'),
                            'platform_id': new_platform.uuid,
                            'model_name': model.get('name'),
                            'model_type': model_type,
                            'context_size': model.get('contextSize') or model.get('context_size'),
                            'additional_info': model_additional,
                            'create_time': current_time,
                            'create_by': create_by,
                            'update_time': current_time,
                            'update_by': create_by
                        }
                        
                        new_model = AIModel(**model_data)
                        db.session.add(new_model)
                        created_models.append(new_model.to_dict())
                
            return True, {
                'platform': new_platform.to_dict(),
                'models': created_models
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating platform with models: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def get_platform_with_models(platform_uuid):
        """获取平台及其关联的模型"""
        try:
            # 获取平台信息
            platform = AIPlatform.query.filter_by(uuid=platform_uuid).first()
            if not platform:
                return False, "平台不存在"
            
            platform_dict = platform.to_dict()
            
            # 获取关联的模型
            models = AIModel.query.filter_by(platform_id=platform_uuid).all()
            models_dict = [model.to_dict() for model in models]
            
            # 将模型按组组织
            model_groups = {}
            for model in models_dict:
                group_id = model['additional_info'].get('group_id')
                group_name = model['additional_info'].get('group_name')
                
                if group_id not in model_groups:
                    model_groups[group_id] = {
                        'id': group_id,
                        'name': group_name,
                        'models': []
                    }
                
                # 移除模型中的group信息，只保留必要的模型信息
                model_info = {
                    'id': model['model_id'],
                    'name': model['model_name'],
                    'iconText': model['additional_info'].get('iconText'),
                    'types': model['additional_info'].get('types', []),
                    'contextSize': model.get('context_size')
                }
                model_groups[group_id]['models'].append(model_info)
            
            # 转换为列表格式
            models = list(model_groups.values())
            
            return True, {
                'platform': platform_dict,
                'models': models
            }
            
        except Exception as e:
            logger.error(f"Error getting platform with models: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_model_by_model_name(model_name: str):
        """通过模型名称查询单个模型（取第一条匹配记录）

        参数:
            model_name: 模型名称

        返回:
            (是否成功, 模型字典或错误消息)
        """
        try:
            if not model_name:
                return False, "model_name 不能为空"

            model = AIModel.query.filter_by(model_name=model_name).first()
            if not model:
                return False, f"模型 {model_name} 不存在"

            return True, model.to_dict()

        except Exception as e:
            logger.error(f"Error getting model by model_name: {str(e)}")
            return False, str(e)

    @staticmethod
    def list_platforms(skip=0, take=100, create_by=None, allowed_entity_ids: list = None):
        """获取平台列表（所有人可见，无权限过滤）"""
        try:
            # 查询所有平台，不进行任何权限过滤
            query = AIPlatform.query
            
            platforms = query.order_by(AIPlatform.id).offset(skip).limit(take).all()
            platforms_dict = [platform.to_dict() for platform in platforms]
            
            # 平铺additional_info
            for platform in platforms_dict:
                additional_info = platform.pop('additional_info', {})
                if isinstance(additional_info, dict):
                    platform.update(additional_info)
            
            # 计算总数
            total = AIPlatform.query.count()
            
            return True, {
                'items': platforms_dict,
                'total': total,
                'skip': skip,
                'take': take
            }
            
        except Exception as e:
            logger.error(f"Error listing platforms: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def update_platform_with_models(platform_uuid, update_data, update_by='admin'):
        """更新平台信息和关联的模型"""
        try:
            # 获取平台
            platform = AIPlatform.query.filter_by(uuid=platform_uuid).first()
            if not platform:
                return False, "平台不存在"
            
            current_time = datetime.now()
            
            # 更新平台核心字段
            if 'name' in update_data:
                platform.name = update_data['name']
            if 'credentials' in update_data and 'apiKey' in update_data['credentials']:
                platform.api_key = update_data['credentials']['apiKey']
            if 'noApiKeyRequired' in update_data:
                platform.no_api_key_required = 0 if update_data['noApiKeyRequired'] else 1
            if 'connection' in update_data and 'apiBaseUrl' in update_data['connection']:
                platform.api_url = update_data['connection']['apiBaseUrl']
            
            # 更新additional_info
            additional_info = platform.additional_info or {}
            fields_to_update = ['type', 'providerIcon', 'backgroundColor', 'avatar']
            for field in fields_to_update:
                if field in update_data:
                    additional_info[field] = update_data[field]
            platform.additional_info = additional_info
            
            # 更新时间和操作人
            platform.update_time = current_time
            platform.update_by = update_by
            
            # 处理模型更新
            updated_models = []
            if 'models' in update_data and isinstance(update_data['models'], list):
                # 获取现有模型
                existing_models = {model.uuid: model for model in AIModel.query.filter_by(platform_id=platform_uuid).all()}
                
                # 创建模型类型映射
                model_type_map = {
                    'chat': 1,
                    'vision': 2,
                    'embedding': 3
                }
                
                # 处理新的模型数据
                for model_group in update_data['models']:
                    group_id = model_group.get('id')
                    group_name = model_group.get('name')
                    
                    for model in model_group.get('models', []):
                        # 确定模型类型（取第一个类型或默认值）
                        model_types = model.get('types', [])
                        model_type = model_type_map.get(model_types[0] if model_types else 'chat', 1)
                        
                        # 准备模型additional_info
                        model_additional = {
                            'iconText': model.get('iconText'),
                            'types': model_types,
                            'group_id': group_id,
                            'group_name': group_name
                        }
                        
                        # 查找现有模型（通过model_id）
                        existing_model = next(
                            (m for m in existing_models.values() if m.model_id == model.get('id')),
                            None
                        )
                        
                        if existing_model:
                            # 更新现有模型
                            existing_model.model_name = model.get('name')
                            existing_model.model_type = model_type
                            existing_model.context_size = model.get('contextSize') or model.get('context_size')
                            existing_model.additional_info = model_additional
                            existing_model.update_time = current_time
                            existing_model.update_by = update_by
                            updated_models.append(existing_model.to_dict())
                            del existing_models[existing_model.uuid]  # 从现有模型字典中移除
                        else:
                            # 创建新模型
                            new_model = AIModel(
                                uuid=str(uuid.uuid4()),
                                model_id=model.get('id'),
                                platform_id=platform_uuid,
                                model_name=model.get('name'),
                                model_type=model_type,
                                context_size=model.get('contextSize') or model.get('context_size'),
                                additional_info=model_additional,
                                create_time=current_time,
                                create_by=update_by,
                                update_time=current_time,
                                update_by=update_by
                            )
                            db.session.add(new_model)
                            updated_models.append(new_model.to_dict())
                
                # 删除不再存在的模型（在所有模型组处理完成后）
                for model_uuid in existing_models:
                    db.session.delete(existing_models[model_uuid])
            
            # 提交事务
            db.session.commit()
            
            # 获取更新后的平台信息
            platform_dict = platform.to_dict()
            
            # 平铺additional_info返回
            additional_info = platform_dict.pop('additional_info', {})
            if isinstance(additional_info, dict):
                platform_dict.update(additional_info)
            
            return True, {
                'platform': platform_dict,
                'models': updated_models
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating platform with models: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def update_platform(platform_uuid, update_data, update_by='admin'):
        """更新平台信息（仅平台，不包括模型）"""
        try:
            platform = AIPlatform.query.filter_by(uuid=platform_uuid).first()
            if not platform:
                return False, "平台不存在"
            
            current_time = datetime.now()
            
            # 更新核心字段
            if 'name' in update_data:
                platform.name = update_data['name']
            if 'credentials' in update_data and 'apiKey' in update_data['credentials']:
                platform.api_key = update_data['credentials']['apiKey']
            if 'noApiKeyRequired' in update_data:
                platform.no_api_key_required = 0 if update_data['noApiKeyRequired'] else 1
            if 'connection' in update_data and 'apiBaseUrl' in update_data['connection']:
                platform.api_url = update_data['connection']['apiBaseUrl']
            
            # 更新additional_info
            additional_info = platform.additional_info or {}
            fields_to_update = ['type', 'providerIcon', 'backgroundColor', 'avatar']
            for field in fields_to_update:
                if field in update_data:
                    additional_info[field] = update_data[field]
            platform.additional_info = additional_info
            
            # 更新时间和操作人
            platform.update_time = current_time
            platform.update_by = update_by
            
            db.session.commit()
            
            # 平铺additional_info返回
            platform_dict = platform.to_dict()
            additional_info = platform_dict.pop('additional_info', {})
            if isinstance(additional_info, dict):
                platform_dict.update(additional_info)
            
            return True, platform_dict
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating platform: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def delete_platform(platform_uuid: str):
        """
        删除平台及关联模型
        注意：由于外键约束，需要先删除所有关联模型，再删除平台
        
        参数:
            platform_uuid: 平台UUID
        
        返回:
            (是否成功, 结果信息或错误消息)
        """
        try:
            # 先检查平台是否存在
            platform = db.session.query(AIPlatform).filter_by(uuid=platform_uuid).first()
            if not platform:
                return False, f"平台 {platform_uuid} 不存在"
            
            # 先删除所有关联的模型
            db.session.query(AIModel).filter_by(platform_id=platform_uuid).delete()
            
            # 然后删除平台
            db.session.delete(platform)
            
            db.session.commit()
            return True, {"message": "平台和相关模型删除成功"}
        except Exception as e:
            logger.error(f"删除平台时出错: {str(e)}")
            db.session.rollback()
            return False, f"删除平台失败: {str(e)}"


# 创建全局实例
ai_platform_model_accessor = AIPlatformModelAccessor()