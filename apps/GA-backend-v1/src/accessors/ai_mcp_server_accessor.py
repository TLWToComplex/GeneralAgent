"""
AI MCP服务访问器模块。
使用SQLAlchemy ORM处理AI MCP服务的数据库操作。
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple
from src.utils.database import db

logger = logging.getLogger(__name__)


class AIMCPServer(db.Model):
    """
    MCP服务数据模型类
    对应数据库表: ai_mcp_server
    """
    __tablename__ = 'ai_mcp_server'
    
    id = db.Column(db.String(50), primary_key=True, comment='服务ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一标识')
    name = db.Column(db.String(100), nullable=False, comment='服务名称')
    description = db.Column(db.Text, nullable=True, comment='服务描述')
    type = db.Column(db.String(50), nullable=False, comment='服务类型')
    url = db.Column(db.String(500), nullable=False, comment='服务地址')
    headers = db.Column(db.Text, nullable=True, comment='请求头配置(JSON)')
    timeout = db.Column(db.Integer, nullable=False, default=30, comment='超时时间(秒)')
    visibility = db.Column(db.String(10), nullable=False, default='private', comment='可见性: private 或 public')
    additional_info = db.Column(db.Text, nullable=True, comment='附加信息(JSON)')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型对象转换为字典
        
        返回:
            包含服务信息的字典
        """
        server_dict = {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'transport': self.type,
            'url': self.url,
            'timeout': self.timeout,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by,
            'visibility': self.visibility
        }
        
        # 处理headers字段，将 [{'key': '...', 'value': '...'}] 转换为 {'key': 'value'}
        if self.headers:
            try:
                headers_list = json.loads(self.headers)
                # 如果是数组格式，转换为字典格式
                if isinstance(headers_list, list):
                    server_dict['headers'] = {item['key']: item['value'] for item in headers_list if 'key' in item and 'value' in item}
                else:
                    # 如果已经是字典格式，直接使用
                    server_dict['headers'] = headers_list
            except (json.JSONDecodeError, KeyError, TypeError):
                server_dict['headers'] = {}
        else:
            server_dict['headers'] = {}
        
        # 处理additional_info中的tools字段
        if self.additional_info:
            try:
                additional_info = json.loads(self.additional_info)
                server_dict['tools'] = additional_info.get('tools', [])
            except json.JSONDecodeError:
                server_dict['tools'] = []
        else:
            server_dict['tools'] = []
        
        return server_dict


class AIMCPServerAccessor:
    """
    AI MCP服务数据库操作访问器类。
    提供使用SQLAlchemy ORM的AI MCP服务CRUD操作。
    """

    def __init__(self):
        """
        初始化访问器并设置数据库实例。
        """
        self.db = db

    def create_mcp_server(self, server_data: Dict[str, Any], create_by: str = 'admin') -> Tuple[bool, Dict[str, Any]]:
        """
        创建MCP服务
        
        参数:
            server_data: MCP服务数据
            create_by: 创建人
            
        返回:
            成功状态和结果
        """
        try:
            # 生成UUID和ID
            server_uuid = str(uuid.uuid4())
            server_id = f"mcp_{int(datetime.now().timestamp() * 1000)}_{server_uuid[:8]}"
            
            # 处理headers字段，将 {'key': 'value'} 转换为 [{'key': '...', 'value': '...'}] 存储
            headers = server_data.get('headers', {})
            if headers and isinstance(headers, dict):
                # 字典格式转换为数组格式
                headers_list = [{'key': k, 'value': v} for k, v in headers.items()]
                headers_json = json.dumps(headers_list)
            elif headers and isinstance(headers, list):
                # 已经是数组格式，直接存储
                headers_json = json.dumps(headers)
            else:
                headers_json = None
            
            # 动态获取所有数据库字段，而不是硬编码
            db_fields = [column.name for column in AIMCPServer.__table__.columns]
            
            # 初始化additional_info
            additional_info = {}
            
            # 将所有非数据库字段放入additional_info
            for key, value in server_data.items():
                if key not in db_fields:
                    additional_info[key] = value
            
            # 如果没有额外信息，至少保留一个空对象
            additional_info_json = json.dumps(additional_info)
            
            # 创建模型实例
            mcp_server = AIMCPServer(
                id=server_id,
                uuid=server_uuid,
                name=server_data.get('name'),
                description=server_data.get('description'),
                type=server_data.get('type'),
                url=server_data.get('url'),
                headers=headers_json,
                timeout=server_data.get('timeout', 30),
                additional_info=additional_info_json,
                create_time=datetime.now(),
                create_by=create_by,
                update_time=datetime.now(),
                update_by=create_by,
                visibility=server_data.get('visibility', 'private'),
            )
            
            # 添加到数据库
            self.db.session.add(mcp_server)
            self.db.session.commit()
            
            # 返回创建的服务信息
            return True, {'id': server_id, 'uuid': server_uuid}
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to create MCP server: {str(e)}")
            return False, f"创建失败: {str(e)}"

    def get_mcp_server(self, server_uuid: str, create_by: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        获取MCP服务详情
        
        参数:
            server_uuid: MCP服务UUID
            create_by: 可选，按创建人过滤
            
        返回:
            成功状态和服务信息
        """
        try:
            # 构建查询
            query = AIMCPServer.query.filter_by(uuid=server_uuid)
            
            # 如果提供了create_by参数，则添加过滤条件
            if create_by:
                query = query.filter_by(create_by=create_by)

            # 查询服务
            mcp_server = query.first()
            
            if not mcp_server:
                return False, "MCP服务不存在"
            
            # 转换为字典返回
            return True, mcp_server.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get MCP server: {str(e)}")
            return False, f"查询失败: {str(e)}"

    def list_mcp_servers(self, skip: int = 0, take: int = 100, create_by: str = None, allowed_entity_ids: list = None) -> Tuple[bool, Dict[str, Any]]:
        """
        获取MCP服务列表
        
        参数:
            skip: 跳过记录数
            take: 返回记录数
            create_by: 可选，按创建人过滤
            allowed_entity_ids: 可选，有权限访问的实体ID列表
            
        返回:
            成功状态和服务列表
        """
        try:
            # 基础查询：自己创建的服务（无论 visibility 状态）
            query = AIMCPServer.query.filter_by(create_by=create_by)
            
            # 如果有授权的实体ID列表，则通过 OR 条件合并查询
            # 注意：这里我们只允许访问 visibility='public' 或者自己创建的 private 服务
            if allowed_entity_ids:
                authorized_query = AIMCPServer.query.filter(
                    AIMCPServer.uuid.in_(allowed_entity_ids),
                    AIMCPServer.visibility == 'public'
                )
                query = query.union(authorized_query)
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            mcp_servers = query.order_by(AIMCPServer.create_time.desc()).limit(take).offset(skip).all()
            
            # 转换为字典列表
            servers = [server.to_dict() for server in mcp_servers]
            
            return True, {
                'items': servers,
                'total': total,
                'skip': skip,
                'take': take
            }
            
        except Exception as e:
            logger.error(f"Failed to list MCP servers: {str(e)}")
            return False, f"查询列表失败: {str(e)}"

    def update_mcp_server(self, server_uuid: str, update_data: Dict[str, Any], update_by: str = 'admin') -> Tuple[bool, Dict[str, Any]]:
        """
        更新MCP服务
        
        参数:
            server_uuid: MCP服务UUID
            update_data: 更新数据
            update_by: 更新人
            
        返回:
            成功状态和结果
        """
        try:
            # 查询服务
            mcp_server = AIMCPServer.query.filter_by(uuid=server_uuid).first()
            
            if not mcp_server:
                return False, "MCP服务不存在"
            
            # 更新字段
            if 'name' in update_data:
                mcp_server.name = update_data['name']
            
            if 'description' in update_data:
                mcp_server.description = update_data['description']
            
            if 'type' in update_data:
                mcp_server.type = update_data['type']
            
            if 'url' in update_data:
                mcp_server.url = update_data['url']
            
            if 'timeout' in update_data:
                mcp_server.timeout = update_data['timeout']
            
            if 'headers' in update_data:
                mcp_server.headers = json.dumps(update_data['headers']) if update_data['headers'] else None

            if 'visibility' in update_data:
                mcp_server.visibility = update_data['visibility']
            
            # 动态获取所有数据库字段，而不是硬编码
            db_fields = [column.name for column in AIMCPServer.__table__.columns]
            
            # 检查是否有非数据库字段需要更新
            has_additional_fields = False
            for key in update_data.keys():
                if key not in db_fields:
                    has_additional_fields = True
                    break
            
            if has_additional_fields:
                # 获取现有additional_info
                additional_info = {}
                if mcp_server.additional_info:
                    try:
                        additional_info = json.loads(mcp_server.additional_info)
                    except json.JSONDecodeError:
                        pass
                
                # 更新所有非数据库字段
                for key, value in update_data.items():
                    if key not in db_fields:
                        additional_info[key] = value
                mcp_server.additional_info = json.dumps(additional_info)
            
            # 更新时间和更新人
            mcp_server.update_time = datetime.now()
            mcp_server.update_by = update_by
            
            # 提交更改
            self.db.session.commit()
            
            # 返回更新后的服务信息
            return True, mcp_server.to_dict()
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to update MCP server: {str(e)}")
            return False, f"更新失败: {str(e)}"

    def delete_mcp_server(self, server_uuid: str, delete_by: str = 'admin') -> Tuple[bool, str]:
        """
        删除MCP服务
        
        参数:
            server_uuid: MCP服务UUID
            delete_by: 删除人
            
        返回:
            成功状态和结果消息
        """
        try:
            # 查询服务
            mcp_server = AIMCPServer.query.filter_by(uuid=server_uuid).first()
            
            if not mcp_server:
                return False, "MCP服务不存在"
            
            # 检查是否有AI智能体引用了该MCP服务器
            # 导入AIAgent模型
            from .ai_agent_accessor import AIAgent
            
            # 查询所有智能体，检查其config字段中是否引用了当前MCP服务器
            agents = self.db.session.query(AIAgent).all()
            referencing_agents = []
            
            for agent in agents:
                # 检查config字段中的mcp.enabledServerIdentifiers
                if isinstance(agent.config, dict):
                    # 检查是否有mcp.enabledServerIdentifiers字段
                    mcp_config = agent.config.get('mcp', {})
                    if isinstance(mcp_config, dict):
                        enabled_servers = mcp_config.get('enabledServerIdentifiers', [])
                        if isinstance(enabled_servers, list) and mcp_server.id in enabled_servers:
                            # 尝试从additional_info中获取name，如果不存在则使用uuid
                            agent_name = agent.uuid  # 默认使用uuid
                            if isinstance(agent.additional_info, dict):
                                agent_name = agent.additional_info.get('name', agent.uuid)
                            referencing_agents.append(agent_name)
            
            # 如果有智能体引用了该MCP服务器，返回错误信息
            if referencing_agents:
                return False, f"无法删除该MCP服务器，以下智能体正在引用它: {', '.join(referencing_agents)}"
            
            # 执行删除
            self.db.session.delete(mcp_server)
            self.db.session.commit()
            
            # 记录删除人信息到日志
            if delete_by:
                logger.info(f"MCP server {server_uuid} deleted by {delete_by}")
            
            return True, "删除成功"
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Failed to delete MCP server: {str(e)}")
            return False, f"删除失败: {str(e)}"


# 创建访问器实例
ai_mcp_server_accessor = AIMCPServerAccessor()