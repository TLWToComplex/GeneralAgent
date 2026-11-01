"""
AI提示词控制器模块。
处理AI提示词管理的API端点。
"""
from flask import request, jsonify
from typing import Dict, List, Union, Tuple, Any
from src.accessors.ai_prompt_accessor import AIPrompt
from src.utils.name_converter import convert_dict_keys_to_camel_case

class AIPromptController:

    @staticmethod
    async def add_prompt(current_user: str = None) -> Tuple[Dict, int]:
        """添加AI提示词，根据请求体数据插入"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        data = request.json
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400
        
        # 自动注入创建人和更新人信息
        data['create_by'] = current_user
        data['update_by'] = current_user
        
        # 验证必填字段（text）
        if 'text' not in data or not data['text']:
            return jsonify({'error': 'text为必填字段'}), 400
        
        # 直接创建新的提示词
        result, prompt_or_error = AIPrompt.add_prompt(data)
        if result:
            prompt_data = AIPromptController._flatten_additional_info(prompt_or_error)
            return jsonify(prompt_data), 201
        else:
            return jsonify({'error': prompt_or_error}), 400

    @staticmethod
    async def list_prompts(current_user: str = None, allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """获取AI提示词列表，只返回text值"""
        from flask import g as request_g
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
        
        # 优先从 g 对象获取权限列表
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
        
        # 使用list_prompts_by_user获取当前用户的提示词
        result, prompts_or_error = AIPrompt.list_prompts_by_user(current_user, perm_list)
        if result:
            # 只提取每个提示词的text字段
            text_list = [prompt.get('text', '') for prompt in prompts_or_error]
            return jsonify(text_list), 200
        else:
            return jsonify({'error': prompts_or_error}), 500

    @staticmethod
    async def get_prompt(current_user: str = None, allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """根据ID或UUID获取AI提示词信息，只返回text值"""
        from flask import g as request_g
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        prompt_id = request.args.get('id', type=int)
        uuid = request.args.get('uuid', type=str)
        
        if not prompt_id and not uuid:
            return jsonify({'error': '必须提供id或uuid参数'}), 400
        
        # 优先从 g 对象获取权限列表
        perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
        
        # 只有在没有权限过滤（即查询列表或Admin操作）或者用户是创建者时才传入 create_by
        create_by_filter = current_user
        if perm_list and uuid in perm_list:
            # 用户在允许访问的列表中，不限制创建者
            create_by_filter = None
        
        result, prompt_or_error = AIPrompt.get_prompt(prompt_id=prompt_id, uuid=uuid, create_by=create_by_filter)
        if result:
            # 只返回text字段的值
            text_value = prompt_or_error.get('text', '')
            return jsonify(text_value), 200
        else:
            return jsonify({'error': '提示词不存在或无权访问'}), 404

    @staticmethod
    async def update_prompt(current_user: str = None) -> Tuple[Dict, int]:
        """更新AI提示词信息"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        update_data = request.json
        
        if not update_data:
            return jsonify({'error': '更新数据不能为空'}), 400
        
        # 优先从请求体中获取uuid
        uuid = update_data.pop('uuid', None)
        prompt_id = request.args.get('id', type=int)
        
        # 如果请求体中没有uuid，尝试从URL参数获取作为兼容
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        
        if not prompt_id and not uuid:
            return jsonify({'error': '必须提供id或uuid参数'}), 400
        
        # 先检查提示词是否存在且属于当前用户
        get_result, prompt_or_error = AIPrompt.get_prompt(prompt_id=prompt_id, uuid=uuid, create_by=current_user)
        if not get_result:
            return jsonify({'error': '提示词不存在或无权访问'}), 404
        
        # 设置更新人信息
        update_data['update_by'] = current_user
        
        result, prompt_or_message = AIPrompt.update_prompt(prompt_id=prompt_id, uuid=uuid, update_data=update_data)
        if result:
            # 平铺additional_info字段并转换命名格式
            prompt_data = AIPromptController._flatten_additional_info(prompt_or_message)
            return jsonify(prompt_data), 200
        else:
            return jsonify({'error': prompt_or_message}), 400

    @staticmethod
    async def delete_prompt(current_user: str = None) -> Tuple[Dict, int]:
        """删除AI提示词（通过UUID查询）"""
        # 检查当前用户是否存在
        if not current_user:
            return jsonify({'error': '用户未认证'}), 401
            
        # 支持从请求体中获取UUID
        request_data = request.json or {}
        uuid = request_data.get('uuid')
        
        # 如果请求体中没有uuid，尝试从URL参数获取
        if not uuid:
            uuid = request.args.get('uuid', type=str)
        
        if not uuid:
            return jsonify({'error': '删除操作需要提供UUID'}), 400
        
        # 先检查提示词是否存在且属于当前用户
        get_result, prompt_or_error = AIPrompt.get_prompt(uuid=uuid, create_by=current_user)
        if not get_result:
            return jsonify({'error': '提示词不存在或无权访问'}), 404
        
        # 只通过UUID删除
        result, message = AIPrompt.delete_prompt(uuid=uuid)
        if result:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'error': message}), 404
    
    @staticmethod
    def _flatten_additional_info(prompt_data: Dict) -> Dict:
        """平铺prompt_data中的additional_info字段，并将下划线命名转换为驼峰命名
        
        如果prompt_data中存在additional_info字段且为字典类型，
        则将其中的所有键值对添加到prompt_data的顶层，然后移除additional_info字段。
        同时将所有键名从下划线命名转换为驼峰命名（如create_time -> createTime）。
        
        参数:
            prompt_data: 提示词数据字典
            
        返回:
            处理后的提示词数据字典
        """
        # 创建一个副本以避免修改原始数据
        result = prompt_data.copy()
        
        # 检查是否存在additional_info字段且为字典类型
        if 'additional_info' in result and isinstance(result['additional_info'], dict):
            # 将additional_info中的键值对添加到顶层
            result.update(result['additional_info'])
            # 移除原始的additional_info字段
            del result['additional_info']
        
        # 从utils导入的函数转换所有键名为驼峰命名
        return convert_dict_keys_to_camel_case(result)