"""
AI智能体访问器模块。
管理AI智能体记录的数据库操作。
"""
import uuid
from datetime import datetime
from sqlalchemy.inspection import inspect
from src.utils.database import db
import logging
logger = logging.getLogger(__name__)

class AIAgent(db.Model):
    __tablename__ = 'ai_agent'
    
    id = db.Column(db.String(64), primary_key=True, nullable=False, comment='唯一标识ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    config = db.Column(db.JSON, nullable=False, comment='智能体配置')
    additional_info = db.Column(db.JSON, nullable=False, comment='扩展字段')
    agent_type = db.Column(db.String(20), nullable=False, default='ai_agent', comment='智能体类型: ai_agent 或 deepagent')
    visibility = db.Column(db.String(10), nullable=False, default='private', comment='可见性: private 或 public')
    skills = db.Column(db.JSON, nullable=False, default=list, comment='技能列表')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')

    @classmethod
    def add_agent(cls, agent_data: dict):
        try:
            # 复制原始数据以避免修改传入的字典
            data_copy = agent_data.copy()
            
            # 生成UUID
            if 'uuid' not in data_copy:
                data_copy['uuid'] = str(uuid.uuid4())
            # 如果提供了id字段，将其设置为uuid（因为数据库的id是自增的）
            elif 'id' in data_copy:
                # 保留原始id值到additional_info中
                if 'additional_info' not in data_copy or not isinstance(data_copy['additional_info'], dict):
                    data_copy['additional_info'] = {}
                data_copy['additional_info']['original_id'] = data_copy['id']
            
            # 设置时间戳
            current_time = datetime.now()
            data_copy.setdefault('create_time', current_time)
            data_copy.setdefault('update_time', current_time)
            
            # 确保update_by不为空，如果create_by存在，则使用create_by的值
            if 'create_by' in data_copy:
                data_copy.setdefault('update_by', data_copy['create_by'])
            elif 'update_by' not in data_copy:
                # 如果都不存在，设置一个默认值
                data_copy['update_by'] = 'admin'
            
            # 设置新字段的默认值
            data_copy['agent_type'] = data_copy.get('agent_type', 'ai_agent')
            data_copy['visibility'] = data_copy.get('visibility', 'private')
            data_copy['skills'] = data_copy.get('skills', [])
            
            # 动态获取数据库字段
            db_fields = [c.key for c in inspect(cls).mapper.column_attrs]
            
            # 如果前端没传 id，则自动生成一个字符串 ID
            if 'id' not in data_copy or not data_copy['id']:
                data_copy['id'] = f"agent-{int(datetime.now().timestamp() * 1000)}"
            
            # 确保additional_info是字典
            if 'additional_info' not in data_copy or not isinstance(data_copy['additional_info'], dict):
                data_copy['additional_info'] = {}
            
            # 确保config是字典
            if not isinstance(data_copy.get('config'), dict):
                return False, "config必须是字典类型"
            
            # 如果 config 中包含 skills，提取到顶层以确保数据库 skills 列正确存储
            if 'config' in data_copy and isinstance(data_copy['config'], dict) and 'skills' in data_copy['config']:
                data_copy['skills'] = data_copy['config']['skills']
            
            # 确保skills是列表
            if not isinstance(data_copy.get('skills'), list):
                return False, "skills必须是列表类型"
            
            # 处理非数据库字段，将其移动到additional_info
            non_db_fields = []
            for key in list(data_copy.keys()):
                if key not in db_fields:
                    non_db_fields.append(key)
            
            # 将所有非数据库字段放入additional_info
            for key in non_db_fields:
                data_copy['additional_info'][key] = data_copy.pop(key)
            
            # 创建新的智能体
            new_agent = cls(**data_copy)
            db.session.add(new_agent)
            db.session.commit()
            return True, new_agent.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding agent: {str(e)}")
            return False, str(e)

    @classmethod
    def list_agents(cls, create_by: str = None, allowed_entity_ids: list = None, skip: int = None, take: int = None):
        try:
            from sqlalchemy import or_, and_
            
            if create_by == 'admin':
                # Admin 可以看到所有智能体
                query = cls.query
            else:
                conditions = [
                    cls.create_by == create_by  # 1. 自己创建的（无论 visibility）
                ]
                
                # 2. 权限组授权且为 public 的智能体
                if allowed_entity_ids:
                    conditions.append(
                        and_(
                            cls.uuid.in_(allowed_entity_ids),
                            cls.visibility == 'public'
                        )
                    )
                
                query = cls.query.filter(or_(*conditions))
            
            # 排序并返回所有数据
            agents = query.order_by(cls.id).all()
            
            # 直接返回数据列表，不再包含total和嵌套的data结构
            return True, [agent.to_dict() for agent in agents]
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            return False, str(e)

    @classmethod
    def get_agent(cls, agent_id: str = None, uuid: str = None, create_by: str = None):
        try:
            query = cls.query
            if agent_id:
                query = query.filter_by(id=agent_id)
            elif uuid:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供agent_id或uuid参数'
            
            # 如果提供了create_by参数，只查询该用户创建的智能体
            if create_by:
                query = query.filter_by(create_by=create_by)
            
            agent = query.first()
            if agent:
                return True, agent.to_dict()
            else:
                return False, '智能体不存在'
        except Exception as e:
            logger.error(f"Error getting agent: {str(e)}")
            return False, str(e)

    @classmethod
    def update_agent(cls, agent_id: str = None, uuid: str = None, update_data: dict = None):
        try:
            # 参数验证
            if not update_data or not isinstance(update_data, dict):
                return False, "更新数据必须是非空字典"
                
            query = cls.query
            if agent_id:
                query = query.filter_by(id=agent_id)
            elif uuid:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供agent_id或uuid参数'
            
            agent = query.first()
            if agent:
                # 复制更新数据以避免修改传入的字典
                data_copy = update_data.copy()
                
                # 忽略不可更新的字段
                data_copy.pop('id', None)
                data_copy.pop('uuid', None)
                data_copy.pop('create_time', None)
                data_copy.pop('create_by', None)
                
                # 更新时间戳
                data_copy['update_time'] = datetime.now()
                
                # 确保update_by不为空，如果不存在，设置为'admin'
                if 'update_by' not in data_copy:
                    data_copy['update_by'] = 'admin'
                
                # 动态获取数据库字段
                try:
                    db_fields = [c.key for c in inspect(cls).mapper.column_attrs]
                except Exception as e:
                    logger.error(f"Error getting database fields: {str(e)}")
                    # 备用方案：使用已知的数据库字段列表
                    db_fields = ['id', 'uuid', 'config', 'additional_info', 'agent_type', 'visibility', 'skills',
                                'create_time', 'update_time', 'create_by', 'update_by']
                
                # 验证config字段
                if 'config' in data_copy:
                    if not isinstance(data_copy['config'], dict):
                        return False, "config必须是字典类型"
                    
                    # 如果 config 中包含 skills，提取到顶层以确保数据库 skills 列同步更新
                    if 'skills' in data_copy['config']:
                        data_copy['skills'] = data_copy['config']['skills']
                
                # 验证skills字段
                if 'skills' in data_copy:
                    if not isinstance(data_copy['skills'], list):
                        return False, "skills必须是列表类型"
                
                # 获取原始的additional_info，确保它是字典类型
                original_additional_info = agent.additional_info if isinstance(agent.additional_info, dict) else {}
                
                # 创建新的additional_info字典用于更新
                updated_additional_info = original_additional_info.copy()
                
                # 处理additional_info字段的特殊情况
                if 'additional_info' in data_copy:
                    if isinstance(data_copy['additional_info'], dict):
                        updated_additional_info.update(data_copy['additional_info'])
                    else:
                        return False, "additional_info必须是字典类型"
                    # 从更新数据中移除additional_info
                    del data_copy['additional_info']
                
                # 将所有非数据库字段添加到additional_info
                non_db_fields_processed = []
                for key in list(data_copy.keys()):
                    if key not in db_fields:
                        updated_additional_info[key] = data_copy.pop(key)
                        non_db_fields_processed.append(key)
                
                # 日志记录处理的非数据库字段
                if non_db_fields_processed:
                    logger.info(f"Processed non-db fields for agent update: {non_db_fields_processed}")
                
                # 更新数据库字段
                for key, value in data_copy.items():
                    setattr(agent, key, value)
                
                # 显式设置additional_info以确保SQLAlchemy检测到变更
                logger.debug(f"Setting updated additional_info: {updated_additional_info}")
                agent.additional_info = updated_additional_info
                
                db.session.commit()
                
                # 返回更新后的完整数据
                updated_data = agent.to_dict()
                logger.info(f"Agent updated successfully: {agent.uuid if agent.uuid else agent.id}")
                return True, updated_data
            else:
                return False, '智能体不存在'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating agent: {str(e)}")
            return False, f"内部错误: {str(e)}"


    @classmethod
    def delete_agent(cls, agent_id: str = None, uuid: str = None):
        try:
            query = cls.query
            if agent_id:
                query = query.filter_by(id=agent_id)
            elif uuid:
                query = query.filter_by(uuid=uuid)
            else:
                return False, '必须提供agent_id或uuid参数'
            
            agent = query.first()
            if agent:
                db.session.delete(agent)
                db.session.commit()
                return True, '智能体删除成功'
            else:
                return False, '智能体不存在'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting agent: {str(e)}")
            return False, str(e)

    def to_dict(self):
        """将模型实例转换为字典，正确处理JSON字段。"""
        result = {}
        for c in inspect(self).mapper.column_attrs:
            key = c.key
            value = getattr(self, c.key)
            # 确保返回正确的Python字典类型
            result[key] = value
        return result

# 创建全局实例
ai_agent_accessor = AIAgent()