"""
AI平台模型控制器模块。
处理AI平台和模型管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_platform_model_accessor import ai_platform_model_accessor
from src.accessors.ai_user_accessor import AIUser
from src.utils.async_route import async_route

logger = logging.getLogger(__name__)


class AIPlatformModelController:
    """
    处理AI平台和模型相关HTTP请求的控制器类。
    提供AI平台和模型的CRUD操作。
    """
    
    @staticmethod
    async def create_platform_with_models(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        创建平台并同时创建关联的模型
        
        期望输入包含平台详情和关联模型的JSON数据。
        
        返回:
            包含创建的平台和模型数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for create_platform_with_models")
            return jsonify({'error': '请求体必须为JSON格式'}), 400
        
        request_data = request.json
        
        # 验证必填字段
        if 'name' not in request_data:
            logger.warning("Missing required field: name")
            return jsonify({'error': '平台名称为必填字段'}), 400
        
        if 'models' not in request_data or not isinstance(request_data['models'], list):
            logger.warning("Missing or invalid models field")
            return jsonify({'error': 'Models必须是有效的数组'}), 400
        
        # 提取平台数据和模型数据
        platform_data = request_data
        models_data = request_data['models']
        
        # 调用访问器创建平台和模型
        success, result = ai_platform_model_accessor.create_platform_with_models(
            platform_data, models_data, create_by=current_user
        )
        
        if success:
            logger.info(f"Platform with models created successfully: {platform_data['name']}")
            
            # 构建响应数据，按照请求体格式返回
            platform_info = result['platform']
            
            # 构建返回的平台数据
            response_data = {
                'uuid': platform_info['uuid'], # 增加 uuid 返回
                'name': platform_info['name'],
                'type': platform_info['additional_info'].get('type'),
                'noApiKeyRequired': platform_info['no_api_key_required'] == 0,
                'connection': {
                    'apiBaseUrl': platform_info['api_url']
                },
                'credentials': {
                    'apiKey': platform_info['api_key']
                },
                'providerIcon': platform_info['additional_info'].get('providerIcon'),
                'avatar': platform_info['additional_info'].get('avatar'),
                'backgroundColor': platform_info['additional_info'].get('backgroundColor'),
                'models': []
            }
            
            # 组织模型数据为请求体格式
            model_groups = {}
            for model in result['models']:
                group_id = model['additional_info'].get('group_id')
                group_name = model['additional_info'].get('group_name')
                
                if group_id not in model_groups:
                    model_groups[group_id] = {
                        'id': group_id,
                        'name': group_name,
                        'models': []
                    }
                
                model_info = {
                    'id': model['model_id'],
                    'name': model['model_name'],
                    'iconText': model['additional_info'].get('iconText'),
                    'types': model['additional_info'].get('types', []),
                    'contextSize': model.get('context_size')
                }
                model_groups[group_id]['models'].append(model_info)
            
            response_data['models'] = list(model_groups.values())
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': response_data
            }), 200
        else:
            logger.error(f"Failed to create platform with models: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400
    
    @staticmethod
    async def get_platform_with_models(current_user: str = 'admin', allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """
        获取平台及其关联的模型详情（所有人可见）
        
        查询参数:
            - uuid: 平台UUID
        
        返回:
            包含平台和模型详情或错误信息的JSON响应
        """
        platform_uuid = request.args.get('uuid', type=str)
        
        if not platform_uuid:
            logger.warning("Platform UUID is required")
            return jsonify({
                'code': 1,
                'message': '平台UUID为必填参数'
            }), 400

        # 调用访问器获取平台和模型信息
        success, result = ai_platform_model_accessor.get_platform_with_models(platform_uuid)
        
        if success:
            platform_info = result['platform']
            
            # 构建响应数据
            response_data = {
                'name': platform_info['name'],
                'type': platform_info['additional_info'].get('type'),
                'noApiKeyRequired': platform_info['no_api_key_required'] == 0,
                'connection': {
                    'apiBaseUrl': platform_info['api_url']
                },
                'credentials': {
                    'apiKey': platform_info['api_key']
                },
                'providerIcon': platform_info['additional_info'].get('providerIcon'),
                'avatar': platform_info['additional_info'].get('avatar'),
                'backgroundColor': platform_info['additional_info'].get('backgroundColor'),
                'models': result['models']
            }
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': response_data
            }), 200
        else:
            logger.error(f"Failed to get platform with models: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 404
    
    @staticmethod
    async def list_platforms(current_user: str = 'admin', allowed_entity_ids: list = None) -> Tuple[Dict, int]:
        """
        获取平台列表，根据用户的platform_sort字段进行排序
        
        查询参数:
            - skip: 跳过记录数 (默认: 0)
            - take: 返回记录数 (默认: 100)
        
        返回:
            包含平台列表的JSON响应
        """
        try:
            skip = request.args.get('skip', default=0, type=int)
            take = request.args.get('take', default=100, type=int)
            
            # 验证分页参数
            if skip < 0 or take <= 0 or take > 1000:
                return jsonify({
                    'code': 1,
                    'message': '分页参数无效'
                }), 400
            
            # 获取用户信息，获取platform_sort排序偏好
            platform_sort_order = []
            success, user = AIUser.get_user(username=current_user)
            if success and user and 'platform_sort' in user and user['platform_sort']:
                # 确保platform_sort是有效的列表
                if isinstance(user['platform_sort'], list):
                    platform_sort_order = user['platform_sort']
                    logger.debug(f"[DEBUG] User {current_user} platform sort order: {platform_sort_order}")

            from flask import g as request_g
            perm_list = getattr(request_g, 'allowed_entity_ids', None) or allowed_entity_ids
            # 获取平台列表，传入create_by参数和权限列表
            success, result = ai_platform_model_accessor.list_platforms(skip, take, create_by=current_user, allowed_entity_ids=perm_list)
            
            if success:
                # 构建符合要求格式的响应数据
                formatted_platforms = []
                for platform in result['items']:
                    # 获取平台关联的模型信息
                    success, platform_with_models = ai_platform_model_accessor.get_platform_with_models(platform.get('uuid'))
                    
                    # 正确使用get_platform_with_models返回的已分组模型数据
                    models = []
                    if success and isinstance(platform_with_models, dict) and 'models' in platform_with_models:
                        models = platform_with_models['models']
                    
                    # 在accessor的list_platforms方法中，additional_info已经被平铺到platform字典中
                    # 直接从platform中获取这些信息
                    
                    # 构建平台数据
                    platform_data = {
                        'id': platform.get('uuid'),  # 使用uuid作为id
                        'name': platform.get('name'),
                        'type': platform.get('type', 'OpenAI'),  # 直接从平铺后的platform获取
                        'noApiKeyRequired': platform.get('no_api_key_required', 1) == 0,  # 数据库中1表示需要API密钥
                        'connection': {
                            'apiBaseUrl': platform.get('api_url')
                        },
                        'credentials': {
                            'apiKey': platform.get('api_key', '')  # 包含完整API密钥
                        },
                        'providerIcon': platform.get('providerIcon', ''),  # 直接从平铺后的platform获取
                        'backgroundColor': platform.get('backgroundColor', ''),  # 直接从平铺后的platform获取
                        'models': models,  # 使用从get_platform_with_models获取的已分组模型
                        # 格式化时间为ISO格式
                        'createdAt': platform.get('create_time'),
                        'updatedAt': platform.get('update_time')
                    }
                    
                    formatted_platforms.append(platform_data)
                
                # 根据用户的platform_sort进行排序
                if platform_sort_order:
                    # 创建一个映射：平台ID -> 索引位置
                    sort_index_map = {platform_id: i for i, platform_id in enumerate(platform_sort_order)}
                    
                    # 定义排序函数：优先按照sort_index_map中的顺序，未在排序列表中的平台排在最后
                    def sort_by_user_preference(platform):
                        # 返回元组，第一个元素是排序优先级，第二个元素是平台名称（用于相同优先级时保持稳定性）
                        return (sort_index_map.get(platform['id'], float('inf')), platform.get('name', ''))
                    
                    # 应用排序
                    formatted_platforms.sort(key=sort_by_user_preference)
                    logger.debug(f"[DEBUG] Platforms sorted according to user preference")
                
                # 直接返回平台列表数组
                return jsonify({
                    'code': 0,
                    'data': formatted_platforms,
                    'message': 'success'
                }), 200
            else:
                logger.error(f"Failed to list platforms: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500
        except Exception as e:
            logger.error(f"Error in list_platforms: {str(e)}")
            return jsonify({
                'code': 1,
                'message': str(e)
            }), 500
    
    @staticmethod
    async def update_platform(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        更新平台信息和关联的模型（仅 admin 和创建者可操作）
        
        请求体:
            - uuid: 平台UUID (必需)
            - 其他需要更新的平台详情
            - models: 模型组数组 (可选)
        
        返回:
            包含更新后的平台和模型数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for update_platform")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400
        
        request_data = request.json
        
        # 从请求体或URL参数获取平台UUID
        platform_uuid = request_data.pop('uuid', None)
        if not platform_uuid:
            platform_uuid = request.args.get('uuid', type=str)
            if not platform_uuid:
                logger.warning("Platform UUID is required for update")
                return jsonify({
                    'code': 1,
                    'message': '平台UUID为必填参数'
                }), 400
        
        # 权限检查：只有 admin 和创建者可以更新
        success, platform_info = ai_platform_model_accessor.get_platform_with_models(platform_uuid)
        if not success:
            return jsonify({
                'code': 1,
                'message': '平台不存在'
            }), 404
        
        create_by = platform_info['platform'].get('create_by')
        if current_user.lower() != 'admin' and create_by != current_user:
            return jsonify({
                'code': 403,
                'message': '无权限修改此平台，只有创建者或管理员可以修改'
            }), 403
        
        # 调用访问器更新平台和模型
        success, result = ai_platform_model_accessor.update_platform_with_models(
            platform_uuid, request_data, update_by=current_user
        )
        
        if success:
            logger.info(f"Platform with models updated successfully: {platform_uuid}")
            
            # 获取平台信息
            platform_info = result['platform']
            
            # 构建返回的平台数据
            response_data = {
                'name': platform_info.get('name'),
                'type': platform_info.get('type'),
                'noApiKeyRequired': platform_info.get('no_api_key_required') == 0,
                'connection': {
                    'apiBaseUrl': platform_info.get('api_url')
                },
                'credentials': {
                    'apiKey': platform_info.get('api_key')
                },
                'providerIcon': platform_info.get('providerIcon'),
                'avatar': platform_info.get('avatar'),
                'backgroundColor': platform_info.get('backgroundColor'),
                'models': []
            }
            
            # 组织模型数据为请求体格式
            model_groups = {}
            for model in result['models']:
                group_id = model.get('additional_info', {}).get('group_id')
                group_name = model.get('additional_info', {}).get('group_name')
                
                if group_id not in model_groups:
                    model_groups[group_id] = {
                        'id': group_id,
                        'name': group_name,
                        'models': []
                    }
                
                model_info = {
                    'id': model.get('model_id'),
                    'name': model.get('model_name'),
                    'iconText': model.get('additional_info', {}).get('iconText'),
                    'types': model.get('additional_info', {}).get('types', [])
                }
                model_groups[group_id]['models'].append(model_info)
            
            response_data['models'] = list(model_groups.values())
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': response_data
            }), 200
        else:
            logger.error(f"Failed to update platform with models {platform_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400
    
    @staticmethod
    async def delete_platform(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        删除平台（会级联删除关联的模型，仅 admin 和创建者可操作）
        
        请求体或查询参数:
            - uuid: 平台UUID (必需)
        
        返回:
            包含成功消息或错误信息的JSON响应
        """
        # 优先从请求体获取uuid
        if request.is_json:
            request_data = request.json
            platform_uuid = request_data.get('uuid')
        else:
            platform_uuid = None
            
        # 如果请求体中没有，从查询参数获取
        if not platform_uuid:
            platform_uuid = request.args.get('uuid', type=str)
        
        if not platform_uuid:
            logger.warning("Platform UUID is required for deletion")
            return jsonify({
                    'code': 1,
                    'message': '平台UUID为必填参数'
                }), 400
        
        # 权限检查：只有 admin 和创建者可以删除
        success, platform_info = ai_platform_model_accessor.get_platform_with_models(platform_uuid)
        if not success:
            return jsonify({
                'code': 1,
                'message': '平台不存在'
            }), 404
        
        create_by = platform_info['platform'].get('create_by')
        if current_user.lower() != 'admin' and create_by != current_user:
            return jsonify({
                'code': 403,
                'message': '无权限删除此平台，只有创建者或管理员可以删除'
            }), 403
        
        # 调用访问器删除平台
        success, result = ai_platform_model_accessor.delete_platform(platform_uuid)
        
        if success:
            logger.info(f"Platform deleted successfully: {platform_uuid}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {'message': '平台及其相关模型已成功删除'}
            }), 200
        else:
            logger.error(f"Failed to delete platform {platform_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400
    
    @staticmethod
    async def get_model_by_model_name(model_name: str) -> Tuple[Dict, int]:
        """
        通过模型名称查询单个模型信息

        查询参数:
            - model_name: 模型名称 (必需)

        返回:
            包含模型信息或错误信息的JSON响应
        """

        if not model_name:
            logger.warning("model_name is required")
            return jsonify({
                'code': 1,
                'message': '模型名称为必填参数'
            }), 400

        # 调用访问器查询模型
        success, result = ai_platform_model_accessor.get_model_by_model_name(model_name)
        return result if success else {}

    @staticmethod
    async def reorder_platforms(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        保存用户的平台排序偏好
        
        请求体：
            - uuids: 平台UUID数组，按用户期望的显示顺序排列
        
        返回：
            成功或失败的响应
        """
        # 验证请求体格式
        if not request.is_json:
            logger.warning("Received non-JSON request for reorder_platforms")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400
        
        request_data = request.json
        
        # 验证uuids字段
        if 'uuids' not in request_data or not isinstance(request_data['uuids'], list):
            logger.warning("Missing or invalid uuids field")
            return jsonify({
                'code': 1,
                'message': 'uuids必须是有效的数组'
            }), 400
        
        uuids = request_data['uuids']
        
        try:
            # 获取当前用户信息
            success, user = AIUser.get_user(username=current_user)
            if not success:
                logger.error(f"Failed to get user {current_user}: {user}")
                return jsonify({
                    'code': 1,
                    'message': '获取用户信息失败'
                }), 500
            
            # 直接更新platform_sort字段
            success, result = AIUser.update_user(user['id'], {'platform_sort': uuids})
            
            if not success:
                logger.error(f"Failed to update platform sort for user {current_user}: {result}")
                return jsonify({
                    'code': 1,
                    'message': '保存平台排序偏好失败'
                }), 500
            
            # 返回成功响应
            return jsonify({
                'code': 0,
                'message': '成功'
            }), 200
        except Exception as e:
            logger.error(f"Unexpected error in reorder_platforms: {str(e)}")
            return jsonify({
                'code': 1,
                'message': '服务器内部错误'
            }), 500


