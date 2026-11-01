"""
AI 用户组控制器模块。
处理AI用户组管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_user_group_accessor import ai_user_group_accessor
from src.services.ai_user_service import AIUserService
from src.utils.async_route import async_route

logger = logging.getLogger(__name__)


class AIUserGroupController:
    """
    处理AI用户组相关HTTP请求的控制器类。
    提供AI用户组的CRUD操作。
    """

    @staticmethod
    def create_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        创建用户组的内部方法
        
        期望输入包含用户组详情的JSON数据。
        
        返回:
            包含创建的用户组数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for create_user_group")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json

        # 验证必填字段
        if 'name' not in request_data:
            logger.warning("Missing required field: name")
            return jsonify({
                'code': 1,
                'message': '用户组名称为必填字段'
            }), 400

        # 调用访问器创建用户组
        success, result = ai_user_group_accessor.create_user_group(
            request_data, create_by=current_user
        )

        if success:
            logger.info(f"User group created successfully: {request_data['name']}")

            # 获取创建的完整用户组信息
            success, group_info = ai_user_group_accessor.get_user_group(result['uuid'])
            if success:
                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': group_info
                }), 200
            else:
                return jsonify({
                    'code': 1,
                    'message': '创建成功但获取详情失败'
                }), 500
        else:
            logger.error(f"Failed to create user group: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400
    
    # 以下是路由中使用的方法名，作为上面方法的别名
    @staticmethod
    async def add_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """创建用户组（路由方法）"""
        # 虽然accessor方法是同步的，但为了支持异步路由，这里使用异步方法包装
        return AIUserGroupController.create_user_group(current_user)
    
    
    @staticmethod
    async def get_user_group_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取用户组详情（异步路由方法）"""
        return AIUserGroupController.get_user_group(current_user)
    
    @staticmethod
    async def list_user_groups_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取用户组列表（异步路由方法）"""
        return AIUserGroupController.list_user_groups(current_user)
    
    @staticmethod
    async def update_user_group_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """更新用户组（异步路由方法）"""
        return AIUserGroupController.update_user_group(current_user)
    
    @staticmethod
    async def delete_user_group_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        """删除用户组（异步路由方法）"""
        return AIUserGroupController.delete_user_group(current_user)

    @staticmethod
    def get_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取用户组详情的内部方法
        
        查询参数:
            - uuid: 用户组UUID
        
        返回:
            包含用户组详情或错误信息的JSON响应
        """
        group_uuid = request.args.get('uuid', type=str)

        if not group_uuid:
            logger.warning("User group UUID is required")
            return jsonify({
                'code': 1,
                'message': '用户组UUID为必填参数'
            }), 400

        # 调用访问器获取用户组信息，传递当前用户参数以过滤create_by字段
        success, result = ai_user_group_accessor.get_user_group(group_uuid, create_by=current_user)

        if success:
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': result
            }), 200
        else:
            logger.error(f"Failed to get user group: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 404

    @staticmethod
    def list_user_groups(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取用户组列表的内部方法
        
        查询参数:
            - skip: 跳过记录数 (默认: 0)
            - take: 返回记录数 (默认: 100)
        
        返回:
            包含用户组列表的JSON响应
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

            # 获取用户组列表，传递当前用户参数以过滤create_by字段
            success, result = ai_user_group_accessor.list_user_groups(skip, take, create_by=current_user)

            if success:
                return jsonify({
                    'code': 0,
                    'message': 'success',
                    'data': result['items'],
                    'total': result['total'],
                    'skip': result['skip'],
                    'take': result['take']
                }), 200
            else:
                logger.error(f"Failed to list user groups: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500
        except Exception as e:
            logger.error(f"Error in list_user_groups: {str(e)}")
            return jsonify({
                'code': 1,
                'message': str(e)
            }), 500

    @staticmethod
    def update_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        更新用户组的内部方法
        
        请求体:
            - uuid: 用户组UUID (必需)
            - 其他需要更新的字段
        
        返回:
            包含更新后的用户组数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for update_user_group")
            return jsonify({
                'code': 1,
                'message': '请求体必须为JSON格式'
            }), 400

        request_data = request.json

        # 从请求体或URL参数获取用户组UUID
        group_uuid = request_data.pop('uuid', None)
        if not group_uuid:
            group_uuid = request.args.get('uuid', type=str)
            if not group_uuid:
                logger.warning("User group UUID is required for update")
                return jsonify({
                    'code': 1,
                    'message': '用户组UUID为必填参数'
                }), 400

        # 调用访问器更新用户组
        success, result = ai_user_group_accessor.update_user_group(
            group_uuid, request_data, update_by=current_user
        )

        if success:
            logger.info(f"User group updated successfully: {group_uuid}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': result
            }), 200
        else:
            logger.error(f"Failed to update user group {group_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400

    @staticmethod
    def delete_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        删除用户组的内部方法
        
        请求体或查询参数:
            - uuid: 用户组UUID (必需)
        
        返回:
            包含成功消息或错误信息的JSON响应
        """
        # 优先从请求体获取uuid
        if request.is_json:
            request_data = request.json
            group_uuid = request_data.get('uuid')
        else:
            group_uuid = None

        # 如果请求体中没有，从查询参数获取
        if not group_uuid:
            group_uuid = request.args.get('uuid', type=str)

        if not group_uuid:
            logger.warning("User group UUID is required for deletion")
            return jsonify({
                'code': 1,
                'message': '用户组UUID为必填参数'
            }), 400

        success, result = AIUserService.delete_group_with_relations(group_uuid)

        if success:
            logger.info(f"User group deleted successfully: {group_uuid}")
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {'message': result}
            }), 200
        else:
            logger.error(f"Failed to delete user group {group_uuid}: {result}")
            return jsonify({
                'code': 1,
                'message': result
            }), 400

    @staticmethod
    def set_default_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """设置默认用户组，请求体传 uuid"""
        if not request.is_json:
            return jsonify({'code': 1, 'message': '请求体必须为JSON格式'}), 400

        group_uuid = request.json.get('uuid')
        if not group_uuid:
            return jsonify({'code': 1, 'message': '用户组UUID为必填参数'}), 400

        success, result = ai_user_group_accessor.set_default_user_group(group_uuid, update_by=current_user)
        if success:
            return jsonify({'code': 0, 'message': 'success', 'data': result}), 200
        return jsonify({'code': 1, 'message': result}), 400

    @staticmethod
    async def set_default_user_group_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        return AIUserGroupController.set_default_user_group(current_user)

    @staticmethod
    def get_default_user_group(current_user: str = 'admin') -> Tuple[Dict, int]:
        """获取当前默认用户组"""
        success, result = ai_user_group_accessor.get_default_user_group()
        if success:
            return jsonify({'code': 0, 'message': 'success', 'data': result}), 200
        return jsonify({'code': 1, 'message': result}), 404

    @staticmethod
    async def get_default_user_group_async(current_user: str = 'admin') -> Tuple[Dict, int]:
        return AIUserGroupController.get_default_user_group(current_user)