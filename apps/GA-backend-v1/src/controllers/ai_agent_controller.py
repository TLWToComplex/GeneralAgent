"""
AI智能体控制器模块。
处理AI智能体管理的API端点。
"""
from flask import request, jsonify
from typing import Dict, List, Union, Tuple, Any
from src.accessors.ai_agent_accessor import AIAgent
from src.core.memory.memory_seeder import delete_agent_memory
from src.utils.name_converter import convert_dict_keys_to_camel_case
import logging

# 获取logger
logger = logging.getLogger(__name__)

class AIAgentController:

    @staticmethod
    async def add_agent(current_user: str = None) -> Tuple[Dict, int]:
        """添加新的AI智能体"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        data = request.json
        
        # 验证config字段必须是字典类型
        if not isinstance(data['config'], dict):
            return jsonify({'error': 'config必须是字典类型'}), 400
        
        # 添加创建人信息
        data['create_by'] = current_user
        
        result, agent_or_error = AIAgent.add_agent(data)
        if result:
            # 平铺additional_info字段并转换命名格式
            agent_data = AIAgentController._flatten_additional_info(agent_or_error)
            return jsonify(agent_data), 201
        else:
            return jsonify({'error': agent_or_error}), 400

    @staticmethod
    async def list_agents(current_user: str = None) -> Tuple[Dict, int]:
        """获取AI智能体列表（一次性返回所有数据）"""
        from flask import g as request_g
        
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
        
        # 直接从 g 对象获取权限列表，这是由 permission_check 装饰器注入的
        perm_list = getattr(request_g, 'allowed_entity_ids', None)
            
        # 调用accessor方法获取所有智能体，传入权限列表
        result, agents_or_error = AIAgent.list_agents(create_by=current_user, allowed_entity_ids=perm_list)
        if result:
            # 为列表中的每个智能体平铺additional_info字段并转换命名格式
            processed_agents = []
            for agent in agents_or_error:
                processed_agent = AIAgentController._flatten_additional_info(agent)
                processed_agents.append(processed_agent)
            
            # 直接返回处理后的智能体列表，不包含分页信息
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': processed_agents
            }), 200
        else:
            return jsonify({'error': agents_or_error}), 500

    @staticmethod
    async def get_agent(current_user: str = None, allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """根据ID或UUID获取AI智能体信息"""
        from flask import g as request_g
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        agent_id = request.args.get('id', type=str)
        uuid = request.args.get('uuid', type=str)
        
        if not agent_id and not uuid:
            return jsonify({'error': '必须提供id或uuid参数'}), 400
        
        # 优先从 g 对象获取权限列表，确保与装饰器同步
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
        
        # 只有在没有权限过滤（即查询列表或Admin操作）或者用户是创建者时才传入 create_by
        create_by_filter = current_user
        if perm_list and uuid in perm_list:
            # 用户在允许访问的列表中，不限制创建者
            create_by_filter = None
        
        result, agent_or_error = AIAgent.get_agent(agent_id=agent_id, uuid=uuid, create_by=create_by_filter)
        if result:
            # 平铺additional_info字段并转换命名格式
            agent_data = AIAgentController._flatten_additional_info(agent_or_error)
            return jsonify(agent_data), 200
        else:
            return jsonify({'error': '智能体未找到或无访问权限'}), 404

    @staticmethod
    async def update_agent(current_user: str = None) -> Tuple[Dict, int]:
        """更新AI智能体信息"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        # 获取请求数据
        update_data = request.json
        
        # 验证请求数据
        if not update_data or not isinstance(update_data, dict):
            return jsonify({'error': '更新数据必须是非空JSON对象'}), 400
        
        # 优先从请求体中获取uuid
        uuid = update_data.pop('uuid', None)
        agent_id = request.args.get('id', type=str)
        
        # 如果请求体中没有uuid，尝试从URL参数获取作为兼容
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        
        # 验证标识符
        if not agent_id and not uuid:
            return jsonify({'error': '必须提供id或uuid'}), 400
        
        # 设置更新人信息
        update_data['update_by'] = current_user
        
        # 记录请求中additional_info的内容，用于调试
        if 'additional_info' in update_data:
            logger.info(f"Received additional_info in update request: {update_data['additional_info']}")
        
        # 执行更新操作
        result, agent_or_message = AIAgent.update_agent(agent_id=agent_id, uuid=uuid, update_data=update_data)
        if result:
            # 平铺additional_info字段并转换命名格式
            agent_data = AIAgentController._flatten_additional_info(agent_or_message)
            # 返回标准化的响应格式
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': agent_data
            }), 200
        else:
            # 根据错误信息类型返回不同的状态码
            if 'not found' in agent_or_message.lower():
                return jsonify({'error': agent_or_message}), 404
            elif 'must be' in agent_or_message.lower() or 'required' in agent_or_message.lower():
                return jsonify({'error': agent_or_message}), 400
            else:
                return jsonify({'error': agent_or_message}), 500

    @staticmethod
    async def delete_agent(current_user: str = None) -> Tuple[Dict, int]:
        """删除AI智能体"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        # 支持从请求体中获取UUID
        request_data = request.json or {}
        uuid = request_data.get('uuid')
        agent_id = request.args.get('id', type=str)
        
        # 如果请求体中没有uuid，尝试从URL参数获取作为兼容
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        
        if not agent_id and not uuid:
            return jsonify({'error': '必须提供id或uuid'}), 400
        
        # 先检查智能体是否存在
        get_result, agent_or_error = AIAgent.get_agent(agent_id=agent_id, uuid=uuid)
        if not get_result:
            return jsonify({'error': '智能体未找到或无访问权限'}), 404
        
        # 检查用户是否是创建者
        if agent_or_error.get('create_by') != current_user:
            # 不是创建者，权限检查由permission_check装饰器处理
            # permission_check装饰器会自动处理权限验证，未通过会直接返回错误
            pass
        
        result, message = AIAgent.delete_agent(agent_id=agent_id, uuid=uuid)
        if result:
            # 同步清理该 agent 的全部记忆目录（best-effort，失败不影响删除结果）
            try:
                agent_uuid_for_memory = uuid or agent_or_error.get('uuid')
                if agent_uuid_for_memory:
                    delete_agent_memory(agent_uuid_for_memory)
            except Exception as mem_err:
                logger.warning(f"清理 agent 记忆目录失败: {mem_err}")
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'error': message}), 404
    
    @staticmethod
    def _flatten_additional_info(agent_data: Dict) -> Dict:
        """平铺agent_data中的additional_info字段，并将下划线命名转换为驼峰命名
        
        如果agent_data中存在additional_info字段且为字典类型，
        则将其中的所有键值对添加到agent_data的顶层，然后移除additional_info字段。
        同时将所有键名从下划线命名转换为驼峰命名（如agent_id -> agentId）。
        
        Args:
            agent_data: 智能体数据字典
            
        Returns:
            处理后的智能体数据字典
        """
        # 创建一个副本以避免修改原始数据
        result = agent_data.copy()
        
        # 确保处理所有可能的情况
        if 'additional_info' in result:
            # 处理None值或非字典类型
            if result['additional_info'] is None:
                del result['additional_info']
            elif isinstance(result['additional_info'], dict):
                # 将additional_info中的键值对添加到顶层
                for key, value in result['additional_info'].items():
                    result[key] = value
                # 移除原始的additional_info字段
                del result['additional_info']
        
        # 从utils导入的函数转换所有键名为驼峰命名
        return convert_dict_keys_to_camel_case(result)