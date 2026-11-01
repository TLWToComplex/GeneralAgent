"""
权限检查装饰器模块。
提供用于API端点的通用权限验证装饰器。
"""
import logging
import json
from typing import Dict, Any, Tuple, Union, Callable, List, Optional
from functools import wraps
from flask import jsonify, request, g
from src.utils.database import db
from src.accessors.ai_permissions_accessor import AIPermission
from src.accessors.ai_user_group_relation_accessor import AIUserGroupRelation
from src.accessors.ai_user_accessor import AIUser
from src.utils.entity_type import EntityType
from src.accessors.ai_mcp_server_accessor import AIMCPServer
from src.accessors.ai_platform_model_accessor import AIPlatform
from src.accessors.ai_prompt_accessor import AIPrompt
from src.accessors.ai_agent_accessor import AIAgent
from src.accessors.ai_platform_model_accessor import AIModel
from src.accessors.ai_kb_chat_accessor import AIKBChat
from src.accessors.ai_skill_accessor import AISkill

logger = logging.getLogger(__name__)

# 实体类型与模型类的映射字典
ENTITY_TYPE_MODEL_MAP = {
    EntityType.MCP_SERVER: AIMCPServer,
    EntityType.PLATFORM: AIPlatform,
    EntityType.PROMPT: AIPrompt,
    EntityType.AGENT: AIAgent,
    EntityType.KB_CHAT: AIKBChat,
    EntityType.SKILL: AISkill
}

def permission_check(entity_type: int = None):
    """
    通用权限检查装饰器
    
    功能：
    1. 检查当前用户所属的用户组是否有对应实体的权限
    2. 对于查询接口，在响应中添加有权限的实体ID列表
    3. 对于修改/删除接口，验证用户是否有操作权限
    
    Args:
        entity_type: 实体类型（0：mcp 1：platform 2：prompt 3：agent 4：kbchat）
    
    Returns:
        装饰后的函数
    """
    def decorator(func):
        @wraps(func)
        async def decorated_function(*args, **kwargs):
            try:
                # 获取当前用户
                current_user = kwargs.get('current_user', 'admin')
                if not current_user:
                    return jsonify({'code': 401, 'message': '用户未认证'}), 401
                
                # 查询用户信息，获取用户UUID
                user = AIUser.query.filter_by(username=current_user).first()
                if not user:
                    return jsonify({'code': 401, 'message': '用户不存在'}), 401
                user_uuid = user.uuid
                
                # 查询用户所属的用户组
                user_groups = AIUserGroupRelation.query.filter_by(user_id=user_uuid).all()
                user_group_ids = [relation.group_id for relation in user_groups]
                
                # 查询用户的权限信息
                permissions = []
                is_admin = current_user.lower() == 'admin'
                
                # Admin 用户拥有所有权限，直接查询该实体类型下的所有授权记录
                if is_admin:
                    query = AIPermission.query
                    if entity_type is not None:
                        # Admin 也需要知道哪些实体被分配了权限，以便在树状图中展示
                        permissions_str = query.filter_by(entity_type=str(entity_type)).all()
                        permissions_int = query.filter_by(entity_type=entity_type).all()
                        permissions = permissions_str + [p for p in permissions_int if p not in permissions_str]
                elif user_group_ids:
                    # 普通用户根据所在组查询权限
                    query = AIPermission.query.filter(AIPermission.group_id.in_(user_group_ids))
                    if entity_type is not None:
                        permissions_str = query.filter_by(entity_type=str(entity_type)).all()
                        permissions_int = query.filter_by(entity_type=entity_type).all()
                        permissions = permissions_str + [p for p in permissions_int if p not in permissions_str]
                    else:
                        permissions = query.all()
                
                # 添加日志以便调试
                logger.debug(f"用户权限查询结果: {len(permissions)} 条记录")
                for perm in permissions:
                    logger.debug(f"权限详情: entity_type={perm.entity_type}, entity_id={perm.entity_id}, permission={perm.permission}")
                
                # 构建权限映射
                # 格式: {entity_type: {entity_id: permission_level}}
                user_permissions = {}
                allowed_entity_ids = []
                
                # 转换entity_type为字符串用于比较
                entity_type_str = str(entity_type) if entity_type is not None else None
                
                for perm in permissions:
                    # 统一将entity_type转换为字符串格式存储
                    perm_entity_type = str(perm.entity_type)
                    
                    if perm_entity_type not in user_permissions:
                        user_permissions[perm_entity_type] = {}
                    user_permissions[perm_entity_type][perm.entity_id] = perm.permission
                    
                        # 只有当permission>0时，才将实体ID添加到allowed_entity_ids列表中
                    if entity_type is not None and (perm_entity_type == entity_type_str or str(perm.entity_type) == str(entity_type)) and perm.permission > 0:
                        allowed_entity_ids.append(perm.entity_id)
                
                # 添加日志以便调试
                logger.debug(f"用户权限查询结果: {len(permissions)} 条记录")
                g.user_permissions = user_permissions
                g.allowed_entity_ids = allowed_entity_ids
                g.current_user_uuid = user_uuid
                
                # 根据请求方法和权限级别进行精细化权限控制
                entity_type_str = str(entity_type) if entity_type is not None else None
                
                # 对于GET请求，需要至少有只读权限（permission >= 1）或者满足 visibility 规则
                if request.method == 'GET':
                    kwargs['allowed_entity_ids'] = allowed_entity_ids
                    
                    # 如果是针对特定实体的GET请求，验证该实体的权限
                    entity_id = request.args.get('uuid') or request.args.get('id')
                    if entity_id and entity_type_str:
                        # 检查用户是否对该实体有至少只读权限
                        permission_level = 0
                        if entity_type_str in user_permissions and entity_id in user_permissions[entity_type_str]:
                            permission_level = user_permissions[entity_type_str][entity_id]
                        
                        # 权限为 0 时，只有创建者或 admin 有权限
                        if permission_level <= 0:
                            is_creator = False
                            try:
                                model_class = ENTITY_TYPE_MODEL_MAP.get(entity_type)
                                if model_class:
                                    # 统一使用 uuid 查询实体
                                    target = model_class.query.filter_by(uuid=entity_id).first()
                                    if target and target.create_by == current_user:
                                        is_creator = True
                            except Exception as e:
                                logger.error(f"检查实体创建者时出错: {str(e)}")
                                                    
                            # 如果不是管理员且不是创建者，则拒绝访问
                            if current_user.lower() != 'admin' and not is_creator:
                                return jsonify({'code': 403, 'message': '无权限访问此实体'}), 403
                
                # 对于POST/PUT/DELETE请求，需要至少有读写权限（permission >= 2）
                elif request.method in ['POST', 'PUT', 'DELETE'] and entity_type is not None:
                    # 获取请求中的实体ID
                    entity_id = None
                    if request.is_json:
                        request_data = request.json
                        entity_id = request_data.get('uuid') or request_data.get('id')
                    
                    # 如果是删除请求，可能在查询参数中
                    if not entity_id:
                        entity_id = request.args.get('uuid') or request.args.get('id')
                    
                    # 如果有实体ID，检查权限
                    if entity_id and entity_type_str:
                         # 检查当前用户是否是实体的创建者
                         is_creator = False
                         try:
                             model_class = ENTITY_TYPE_MODEL_MAP.get(entity_type)
                             if model_class:
                                 # 统一使用 uuid 查询实体
                                 target = model_class.query.filter_by(uuid=entity_id).first()
                                 if target and target.create_by == current_user:
                                     is_creator = True
                         except Exception as e:
                             logger.error(f"检查实体创建者时出错: {str(e)}")
                        
                         # 检查用户是否对该实体有至少读写权限
                         permission_level = 0
                         if entity_type_str in user_permissions and entity_id in user_permissions[entity_type_str]:
                             permission_level = user_permissions[entity_type_str][entity_id]
                         
                         # 权限小于2表示只有只读权限或无权限，拒绝修改操作
                         # 但如果是创建者或管理员，则允许修改
                         if permission_level < 2 and not is_creator:
                             # 检查是否是管理员
                             if current_user.lower() != 'admin':
                                 return jsonify({'code': 403, 'message': '无权限修改此实体'}), 403
                
                # 调用原始函数
                response = await func(*args, **kwargs)
                
                # 为所有请求类型添加有权限的实体列表和实体详情
                if entity_type is not None:
                    try:
                        # 添加调试日志
                        logger.debug(f"处理响应: method={request.method}, entity_type={entity_type}")
                        # 处理tuple类型响应（包含状态码）
                        if isinstance(response, tuple) and len(response) == 2:
                            json_response, status_code = response
                            try:
                                json_data = json_response.get_json()
                                if isinstance(json_data, dict):
                                    # 添加实体详情
                                    update_response_with_entity_details(json_data, entity_type, allowed_entity_ids, user_permissions)
                                    return jsonify(json_data), status_code
                            except Exception:
                                return response
                        else:
                            # 处理普通响应
                            if isinstance(response, dict):
                                json_data = response
                            else:
                                try:
                                    json_data = response.get_json()
                                except Exception:
                                    return response

                            if json_data:
                                # 添加实体详情
                                update_response_with_entity_details(json_data, entity_type, allowed_entity_ids, user_permissions)
                                return jsonify(json_data)
                    except Exception as e:
                        logger.error(f"处理响应时出错: {str(e)}")
                        return response
                
                return response
                
            except Exception as e:
                logger.error(f"权限检查失败: {str(e)}")
                # 权限检查失败不应阻止请求，返回原始函数的结果
                return await func(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def get_user_permissions():
    """
    获取当前用户的权限信息
    可以在controller中调用此函数获取权限信息
    
    Returns:
        Dict: 用户权限映射
    """
    return getattr(g, 'user_permissions', {})


def get_allowed_entity_ids():
    """
    获取当前用户有权限的实体ID列表
    
    Returns:
        List: 有权限的实体ID列表
    """
    return getattr(g, 'allowed_entity_ids', [])


def get_current_user_uuid():
    """
    获取当前用户的UUID
    
    Returns:
        str: 用户UUID
    """
    return getattr(g, 'current_user_uuid', None)


def update_response_with_entity_details(json_data: dict, entity_type: int, allowed_entity_ids: List[str], user_permissions: dict) -> None:
    """
    更新响应数据，将实体详情合并到响应体的data中并去重
    
    Args:
        json_data: 要更新的JSON数据字典
        entity_type: 实体类型
        allowed_entity_ids: 允许访问的实体ID列表
        user_permissions: 用户权限映射
    """
    # 对于 KB Chat 列表接口，跳过自动合并逻辑，避免重复数据
    # 因为 KB Chat 代理接口已经处理了数据过滤和合并
    if entity_type == EntityType.KB_CHAT:
        logger.debug(f"KB Chat 实体类型，跳过自动合并逻辑")
        return
    
    # 查询实体详细信息，添加异常处理
    try:
        entity_details = get_entity_details(entity_type, allowed_entity_ids)
        
        # 将实体详情合并到响应体的data中，并去重
        if 'data' in json_data:
            # 检查data是否为列表
            if isinstance(json_data['data'], list):
                # 创建一个集合用于去重，根据实体的id或uuid
                existing_entity_ids = set()
                merged_data = []
                
                # 首先添加响应中的现有数据，并记录已存在的实体ID
                for item in json_data['data']:
                    # 使用uuid或id作为唯一标识
                    entity_id = item.get('uuid') or item.get('id')
                    if entity_id:
                        existing_entity_ids.add(entity_id)
                    merged_data.append(item)
                
                # 然后添加entity_details中不存在的实体
                for detail in entity_details:
                    # 使用uuid或id作为唯一标识
                    entity_id = detail.get('uuid') or detail.get('id')
                    if entity_id and entity_id not in existing_entity_ids:
                        existing_entity_ids.add(entity_id)
                        merged_data.append(detail)
                    elif not entity_id:
                        # 如果没有唯一标识，直接添加
                        merged_data.append(detail)
                
                # 更新data字段
                json_data['data'] = merged_data
            else:
                # 如果data不是列表，检查是否为单个实体对象
                # 并创建包含该对象和所有权限实体的新列表
                if isinstance(json_data['data'], dict):
                    existing_entity = json_data['data']
                    existing_entity_id = existing_entity.get('uuid') or existing_entity.get('id')
                    
                    # 创建新列表，包含现有实体和过滤后的权限实体
                    merged_data = [existing_entity]
                    
                    # 添加不在现有实体中的权限实体
                    for detail in entity_details:
                        detail_id = detail.get('uuid') or detail.get('id')
                        if detail_id and detail_id != existing_entity_id:
                            merged_data.append(detail)
                        elif not detail_id:
                            # 如果没有唯一标识，直接添加
                            merged_data.append(detail)
                    
                    # 更新data字段
                    json_data['data'] = merged_data
    except Exception as e:
        logger.error(f"获取实体详情失败: {str(e)}")
        logger.error(f"失败上下文: entity_type={entity_type}, entity_ids={allowed_entity_ids}")
        # 即使获取失败，也设置空列表而不是抛出异常，确保请求能够正常完成
        json_data['allowed_data'] = []


from src.utils.name_converter import convert_dict_keys_to_camel_case

def get_entity_details(entity_type: int, entity_ids: List[str]) -> List[Dict[str, Any]]:
    """
    根据实体类型和ID列表查询实体的详细信息，并保持与对应controller返回的数据结构一致
    
    Args:
        entity_type: 实体类型 (0: mcp, 1: platform, 2: prompt, 3: agent, 4: kbchat, 5: skill)
        entity_ids: 实体ID列表
    
    Returns:
        List[Dict]: 实体详细信息列表，格式与对应controller的list方法一致
    """
    entity_details = []
    
    try:
        # 添加调试日志
        logger.debug(f"get_entity_details调用: entity_type={entity_type}, entity_ids={entity_ids}")
        
        if not entity_ids:
            logger.debug("entity_ids为空，返回空列表")
            return entity_details
        
        # 根据实体类型查询对应的表
        if entity_type == EntityType.MCP_SERVER:  # mcp 
            servers = AIMCPServer.query.filter(AIMCPServer.uuid.in_(entity_ids)).all()
            for server in servers:
                # 构建与AIMCPServer.to_dict()一致的数据结构
                server_dict = {
                    'id': server.id,
                    'uuid': server.uuid,
                    'name': server.name,
                    'description': server.description,
                    'type': server.type,
                    'url': server.url,
                    'timeout': server.timeout,
                    'create_time': server.create_time.isoformat() if server.create_time else None,
                    'create_by': server.create_by,
                    'update_time': server.update_time.isoformat() if server.update_time else None,
                    'update_by': server.update_by,
                    'headers': [],
                    'tools': []
                }
                
                # 处理headers字段
                if server.headers:
                    try:
                        server_dict['headers'] = json.loads(server.headers)
                    except json.JSONDecodeError:
                        server_dict['headers'] = []
                
                # 处理additional_info中的tools字段
                if server.additional_info:
                    try:
                        additional_info = json.loads(server.additional_info)
                        server_dict['tools'] = additional_info.get('tools', [])
                    except json.JSONDecodeError:
                        server_dict['tools'] = []
                
                entity_details.append(server_dict)
        
        elif entity_type == EntityType.PLATFORM:  # platform
            platforms = AIPlatform.query.filter(AIPlatform.uuid.in_(entity_ids)).all()
            for platform in platforms:
                # 处理additional_info字段
                additional_info = {}
                if hasattr(platform, 'additional_info') and platform.additional_info:
                    try:
                        # 如果additional_info是字符串，尝试解析为JSON
                        if isinstance(platform.additional_info, str):
                            additional_info = json.loads(platform.additional_info)
                        elif isinstance(platform.additional_info, dict):
                            additional_info = platform.additional_info
                    except (json.JSONDecodeError, TypeError):
                        additional_info = {}
                
                # 获取平台关联的模型信息
                try:
                    from src.accessors.ai_platform_model_accessor import ai_platform_model_accessor
                    success, platform_with_models = ai_platform_model_accessor.get_platform_with_models(platform.uuid)
                    models = []
                    if success and isinstance(platform_with_models, dict) and 'models' in platform_with_models:
                        models = platform_with_models['models']
                except Exception as e:
                    logger.error(f"获取平台模型信息失败: {str(e)}")
                    models = []
                
                # 构建与controller保持一致的平台数据结构
                platform_dict = {
                    'id': platform.uuid,  # 使用uuid作为id
                    'name': platform.name,
                    'type': additional_info.get('type', 'OpenAI'),
                    'noApiKeyRequired': getattr(platform, 'no_api_key_required', 1) == 0,  # 数据库中1表示需要API密钥
                    'connection': {
                        'apiBaseUrl': getattr(platform, 'api_url', '')
                    },
                    'credentials': {
                        'apiKey': getattr(platform, 'api_key', '')
                    },
                    'providerIcon': additional_info.get('providerIcon', ''),
                    'backgroundColor': additional_info.get('backgroundColor', ''),
                    'models': models,
                    'createdAt': platform.create_time.isoformat() if platform.create_time else None,
                    'updatedAt': platform.update_time.isoformat() if platform.update_time else None
                }
                entity_details.append(platform_dict)
        
        elif entity_type == EntityType.PROMPT:  # prompt
            prompts = AIPrompt.query.filter(AIPrompt.uuid.in_(entity_ids)).all()
            for prompt in prompts:
                prompt_dict = {
                    'uuid': prompt.uuid,
                    'text': prompt.content,  # 注意字段名与controller保持一致
                    'type': prompt.type,
                    'platform_id': prompt.platform_id,
                    'create_time': prompt.create_time.isoformat() if prompt.create_time else None
                }
                
                # 平铺additional_info字段并转换命名格式
                if hasattr(prompt, 'additional_info') and prompt.additional_info:
                    try:
                        additional_info = json.loads(prompt.additional_info)
                        if isinstance(additional_info, dict):
                            prompt_dict.update(additional_info)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # 转换为驼峰命名
                entity_details.append(convert_dict_keys_to_camel_case(prompt_dict))
        
        elif entity_type == EntityType.AGENT:  # agent
            agents = AIAgent.query.filter(AIAgent.uuid.in_(entity_ids)).all()
            for agent in agents:
                # 从config和additional_info中提取信息
                config_data = {} if not agent.config else agent.config
                additional_info = {} if not agent.additional_info else agent.additional_info
                
                # 确保additional_info是字典
                if isinstance(additional_info, str):
                    try:
                        additional_info = json.loads(additional_info)
                        if not isinstance(additional_info, dict):
                            additional_info = {}
                    except json.JSONDecodeError:
                        additional_info = {}
                
                # 构建agent字典，使用模型实际存在的字段
                agent_dict = {
                    'uuid': agent.uuid,
                    'config': config_data,
                    'create_time': agent.create_time.isoformat() if agent.create_time else None,
                    'create_by': agent.create_by,
                    'update_time': agent.update_time.isoformat() if agent.update_time else None,
                    'update_by': agent.update_by
                }
                
                # 从config和additional_info中提取常用字段
                agent_dict['name'] = config_data.get('name') or additional_info.get('name', '')
                agent_dict['description'] = config_data.get('description') or additional_info.get('description', '')
                agent_dict['platform_id'] = config_data.get('platform_id') or additional_info.get('platform_id')
                
                # 平铺additional_info字段
                for key, value in additional_info.items():
                    if key not in agent_dict:
                        agent_dict[key] = value
                
                # 转换为驼峰命名
                entity_details.append(convert_dict_keys_to_camel_case(agent_dict))
        
        elif entity_type == EntityType.KB_CHAT:  # kbchat
            kb_chats = AIKBChat.query.filter(AIKBChat.uuid.in_(entity_ids)).all()
            for kb_chat in kb_chats:
                kb_dict = kb_chat.to_dict()
                # 转换为驼峰命名
                entity_details.append(convert_dict_keys_to_camel_case(kb_dict))
        
        elif entity_type == EntityType.SKILL:  # skill
            skills = AISkill.query.filter(AISkill.uuid.in_(entity_ids)).all()
            for skill in skills:
                skill_dict = AISkill._to_dict(skill)
                # 转换为驼峰命名
                entity_details.append(convert_dict_keys_to_camel_case(skill_dict))
        
        else:
            logger.debug(f"未知的实体类型: {entity_type}")
    
    except Exception as e:
        logger.error(f"获取实体详情失败: {str(e)}")
        logger.error(f"失败上下文: entity_type={entity_type}, entity_ids={entity_ids}")
    
    # 记录返回结果
    logger.debug(f"get_entity_details返回: {len(entity_details)} 条记录")
    return entity_details