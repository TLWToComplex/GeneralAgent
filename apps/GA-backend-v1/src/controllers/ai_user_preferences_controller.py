"""
AI用户偏好设置控制器模块。
处理用户偏好设置管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from src.accessors.ai_user_accessor import AIUser
from src.utils.async_route import async_route

logger = logging.getLogger(__name__)

class AIUserPreferencesController:
    """
    处理AI用户偏好设置相关HTTP请求的控制器类。
    提供用户偏好设置的CRUD操作。
    """
    
    @staticmethod
    async def get_user_preferences(current_user: str) -> Tuple[Dict, int]:
        """
        根据当前用户获取用户偏好设置。
        
        参数：
            - current_user (str): 当前登录的用户名
            
        返回：
            包含用户偏好设置或错误信息的JSON响应
        """
        try:
            logger.info(f"Getting preferences for user: {current_user}")
            
            # Query users by username only
            # First try to get user by username directly
            success, user_data = AIUser.get_user(username=current_user)
            
            # If not found, try querying with username containing current_user
            if not success:
                success, users = AIUser.query_users(username=current_user, take=1)
                if success and users:
                    user_data = users[0]
                
            if not success or not user_data:
                logger.warning(f"User not found for username: {current_user}")
                return jsonify({'code': 404, 'message': '用户不存在'}), 404
            
            if success:
                # Prepare response data
                response_data = {
                    'userId': user_data['uuid'],
                    'preferences': user_data['preferences'],
                    'createBy': user_data['create_by'],
                    'createTime': user_data['create_time'],
                    'updateBy': user_data['update_by'],
                    'updateTime': user_data['update_time']
                }
                
                return jsonify({'code': 0, 'data': response_data, 'message': '成功'}), 200
            else:
                logger.warning(f"User not found")
                return jsonify({'code': 404, 'message': '用户不存在'}), 404
                
        except Exception as e:
            logger.error(f"Error in get_user_preferences: {str(e)}")
            return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    @staticmethod
    async def update_user_preferences(current_user: str) -> Tuple[Dict, int]:
        """
        更新用户偏好设置。
        
        参数：
            - current_user (str): 当前登录的用户名
            
        期望输入的JSON数据包含：
            - preferences (dict): 要更新的用户偏好设置
        
        返回：
            包含更新后的偏好设置或错误信息的JSON响应
        """
        try:
            logger.info(f"Updating preferences for user: {current_user}")
            
            if not request.is_json:
                logger.warning("Received non-JSON request for update_user_preferences")
                return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400
            
            request_data = request.json
            
            # Validate required fields
            if 'preferences' not in request_data or 'userId' not in request_data:
                logger.warning("Missing preferences in request body")
                return jsonify({'code': 400, 'message': 'preferences和userId为必填字段'}), 400
            
            # Validate preferences is a dictionary
            if not isinstance(request_data['preferences'], dict):
                logger.warning("preferences必须是一个字典")
                return jsonify({'code': 400, 'message': 'preferences必须是一个字典'}), 400
            
            preferences_data = request_data['preferences']
            
            # Find user by username
            # First try to get user by username directly since that's more reliable
            success, user_data = AIUser.get_user(uuid=request_data['userId'])
            
            # If not found, try querying with username containing current_user
            if not success:
                success, users = AIUser.query_users(username=current_user, take=1)
                if not success or not users:
                    logger.warning(f"User not found for username: {current_user}")
                    return jsonify({'code': 404, 'message': '用户不存在'}), 404
                user_data = users[0]
            
            # Prepare update data
            update_data = {
                'preferences': preferences_data,
                'update_by': current_user  # Use current_user as update_by
            }
            
            # Update user
            update_success, updated_user = AIUser.update_user(
                user_id=user_data['id'],
                update_data=update_data
            )
            
            if update_success:
                # Prepare response data
                response_data = {
                    'userId': updated_user['uuid'],
                    'preferences': updated_user['preferences'],
                    'createBy': updated_user['create_by'],
                    'createTime': updated_user['create_time'],
                    'updateBy': updated_user['update_by'],
                    'updateTime': updated_user['update_time']
                }
                
                logger.info(f"User preferences updated successfully: uuid={updated_user['uuid']}")
                return jsonify({'code': 0, 'data': response_data, 'message': '成功'}), 200
            else:
                logger.error(f"Failed to update user preferences: {updated_user}")
                return jsonify({'code': 400, 'message': updated_user}), 400
                
        except Exception as e:
            logger.error(f"Error in update_user_preferences: {str(e)}")
            return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    @staticmethod
    async def add_user_preferences(current_user: str) -> Tuple[Dict, int]:
        """
        添加用户偏好设置（创建或更新）。
        
        参数：
            - current_user (str): 当前登录的用户名
            
        期望输入的JSON数据包含：
            - preferences (dict): 用户偏好设置
        
        返回：
            包含偏好设置数据或错误信息的JSON响应
        """
        logger.info(f"Adding preferences for user: {current_user}")
        
        # For this API, we can reuse the update_user_preferences method
        # since adding preferences is essentially updating them
        return await AIUserPreferencesController.update_user_preferences(current_user)
    