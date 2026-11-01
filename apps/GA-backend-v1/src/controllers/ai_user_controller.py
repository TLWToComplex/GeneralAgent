"""
AI用户控制器模块。
处理AI用户管理操作的HTTP请求。
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from werkzeug.security import generate_password_hash

from src.accessors.ai_user_accessor import AIUser
from src.accessors.ai_password_history_accessor import ai_password_history_accessor
from src.services.ai_user_service import AIUserService
from src.utils.password_validator import PasswordValidator


logger = logging.getLogger(__name__)

class AIUserController:
    """
    处理AI用户相关HTTP请求的控制器类。
    提供AI用户的CRUD操作。
    """
    
    @staticmethod
    async def add_user() -> Tuple[Dict, int]:
        """
        添加新的AI用户。
        
        期望输入的JSON数据包含：
            - username (str): 用户名 (必需)
            - password (str): 密码 (必需)
            - email (str, 可选): 电子邮箱
            - realname (str, 可选): 真实姓名
            - contact (str, 可选): 联系方式（如电话号码）
            - address (str, 可选): 家庭住址
            - additional_info (dict, 可选): 附加信息
            - create_by (str, 可选): 创建者
            - update_by (str, 可选): 更新者
        
        返回：
            包含创建的用户数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for add_user")
            return jsonify({'error': '请求体必须为JSON格式'}), 400
        
        user_data = request.json
        
        # 验证必填字段
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in user_data:
                logger.warning(f"Missing required field: {field}")
                return jsonify({'code': 400, 'message': f'{field}为必填字段'}), 400
        
        # 密码禁用规则校验
        password_validation = PasswordValidator.validate_password(
            user_data['password'],
            username=user_data['username']
        )
        if not password_validation['valid']:
            logger.warning(f"Password validation failed for user {user_data['username']}: {password_validation['message']}")
            return jsonify({'code': 400, 'message': password_validation['message']}), 400
        
        # 调用访问器添加用户
        success, result = AIUser.add_user(user_data)

        if success:
            logger.info(f"User added successfully: {user_data['username']}")

            # 首次创建时，将初始密码 hash 写入 password_history 表
            try:
                user_uuid = result.get('uuid')
                if user_uuid:
                    initial_password_hash = generate_password_hash(user_data['password'])
                    ai_password_history_accessor.add_record(user_uuid, initial_password_hash)
                    logger.info(f"Initial password history recorded for user {user_uuid}")
            except Exception as hist_err:
                logger.error(f"Failed to record initial password history: {str(hist_err)}")

            return jsonify({'code': 200, 'message': '用户添加成功', 'data': result}), 200
        else:
            logger.error(f"Failed to add user: {result}")
            return jsonify({'code': 400, 'message': result}), 400
    
    @staticmethod
    async def list_users() -> Tuple[Dict, int]:
        """
        分页列出AI用户。
        
        查询参数：
            - skip (int): 跳过记录数 (默认: 0)
            - take (int): 返回记录数 (默认: 100)
        
        返回：
            包含用户列表的JSON响应
        """
        try:
            skip = request.args.get('skip', default=0, type=int)
            take = request.args.get('take', default=100, type=int)
            
            # 验证分页参数
            if skip < 0 or take <= 0 or take > 1000:
                return jsonify({'error': '分页参数无效'}), 400
            
            success, result = AIUser.list_users(skip, take)
            
            if success:
                # 平铺每个用户的 additional_info 字段
                if 'items' in result and isinstance(result['items'], list):
                    result['items'] = [AIUserService.flatten_additional_info(user) for user in result['items']]
                return result, 200
            else:
                logger.error(f"Failed to list users: {result}")
                return {'error': '获取用户列表失败', 'message': result}, 500
        except Exception as e:
            logger.error(f"Error in list_users: {str(e)}")
            return {'error': '服务器内部错误'}, 500
    
    
    @staticmethod
    async def list_users_with_groups(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        获取用户列表及其所属的用户组信息（仅 admin 可访问）
        
        查询参数：
            - skip (int): 跳过记录数 (默认: 0)
            - take (int): 返回记录数 (默认: 300)
        
        返回：
            包含用户列表及用户组信息的JSON响应
        """
        try:
            
            skip = request.args.get('skip', default=0, type=int)
            take = request.args.get('take', default=4000, type=int)

            # 验证分页参数
            if skip < 0 or take <= 0:
                return jsonify({'code': 400, 'message': '分页参数无效'}), 400
            
            # 调用 Service 层处理业务逻辑
            success, result = AIUserService.list_users_with_groups(skip, take)
            
            if success:
                # 平铺每个用户的 additional_info 字段
                if 'items' in result and isinstance(result['items'], list):
                    result['items'] = [AIUserService.flatten_additional_info(user) for user in result['items']]
                
                logger.info(f"Admin {current_user} retrieved users with groups: total={result['total']}")
                return jsonify({'code': 0, 'message': 'success', 'data': result}), 200
            else:
                logger.error(f"Failed to list users with groups: {result}")
                return jsonify({'code': 500, 'message': '获取用户列表失败', 'error': result}), 500
        except Exception as e:
            logger.error(f"Error in list_users_with_groups: {str(e)}")
            return jsonify({'code': 500, 'message': '服务器内部错误'}), 500
    
    @staticmethod
    async def sync_user_groups(current_user: str = 'admin') -> Tuple[Dict, int]:
        """
        批量同步用户与用户组的关联关系（仅 admin 可访问）
        
        请求体格式：
        {
            "user_group_map": {
                "user_uuid_1": ["group_uuid_a", "group_uuid_b"],
                "user_uuid_2": ["group_uuid_c"]
            }
        }
        
        对于每个用户，会：
        1. 保留已存在的关联
        2. 新增需要关联的用户组
        3. 删除取消关联的用户组
        
        返回：
            包含同步结果的JSON响应
        """
        try:
            # # 权限检查：只有 admin 可以访问
            # if current_user != 'admin':
            #     logger.warning(f"Non-admin user {current_user} attempted to access sync_user_groups")
            #     return jsonify({'code': 403, 'message': '权限不足，仅管理员可访问'}), 403
            
            if not request.is_json:
                return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400
            
            request_data = request.json
            
            # 验证必填字段
            if 'user_group_map' not in request_data:
                return jsonify({'code': 400, 'message': 'user_group_map为必填字段'}), 400
            
            user_group_map = request_data['user_group_map']
            
            # 验证格式
            if not isinstance(user_group_map, dict):
                return jsonify({'code': 400, 'message': 'user_group_map必须为字典对象'}), 400
            
            # 调用 Service 层处理业务逻辑
            success, result = AIUserService.sync_user_groups_for_users(user_group_map, current_user)
            
            if success:
                has_failures = 'failures' in result
                status_code = 207 if has_failures else 200
                message = '部分用户组关联操作失败' if has_failures else '用户组关联同步成功'
                
                logger.info(f"{current_user} synced user groups: added={result.get('total_added')}, deleted={result.get('total_deleted')}")
                return jsonify({
                    'code': 2 if has_failures else 0,
                    'message': message,
                    'data': result
                }), status_code
            else:
                logger.error(f"Failed to sync user groups: {result}")
                return jsonify({'code': 500, 'message': '同步用户组关联失败', 'error': result}), 500
        except Exception as e:
            logger.error(f"Error in sync_user_groups: {str(e)}")
            return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

    @staticmethod
    async def get_user() -> Tuple[Dict, int]:
        """
        根据ID、UUID或用户名获取特定的AI用户。
        
        查询参数：
            - id (int): 用户ID
            - uuid (str): 用户UUID
            - username (str): 用户名
        
        返回：
            包含用户详情或错误信息的JSON响应
        """
        user_id = request.args.get('id', type=int)
        uuid = request.args.get('uuid', type=str)
        username = request.args.get('username', type=str)
        
        # 确保提供了至少一个标识符
        if not any([user_id, uuid, username]):
            return jsonify({'code': 400, 'message': '必须提供id、uuid或username中的至少一项'}), 400
        
        success, result = AIUserService.get_user_with_groups(user_id, uuid, username)
        
        if success:
            # 平铺 additional_info 字段
            result = AIUserService.flatten_additional_info(result)
            return jsonify({'code': 200, 'message': '获取用户成功', 'data': result}), 200
        else:
            logger.warning(f"User not found: id={user_id}, uuid={uuid}, username={username}")
            return jsonify({'code': 404, 'message': result}), 404
    
    @staticmethod
    async def update_user() -> Tuple[Dict, int]:
        """
        更新现有的AI用户。
        
        期望输入的JSON数据包含：
            - uuid (str): 用户UUID (必需)
            - 其他需要更新的字段 (可选)：
                - username (str): 用户名
                - password (str): 密码
                - email (str): 电子邮箱
                - realname (str): 真实姓名
                - contact (str): 联系方式（如电话号码）
                - address (str): 家庭住址
                - additional_info (dict): 附加信息
                - update_by (str): 更新者
        
        返回：
            包含更新后的用户数据或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for update_user")
            return jsonify({'code': 400, 'message': '请求体必须为JSON格式'}), 400
        
        update_data = request.json
        
        if not update_data:
            return jsonify({'code': 400, 'message': '更新数据不能为空'}), 400
        
        # 优先从请求体中获取uuid
        user_uuid = update_data.pop('uuid', None)
        
        # 如果请求体中没有uuid，尝试从URL参数获取作为兼容
        if not user_uuid:
            user_uuid = request.args.get('uuid', type=str)
            if not user_uuid:
                return jsonify({'code': 400, 'message': '用户UUID为必填字段'}), 400
        
        # 先通过uuid查询用户以获取其id
        user_success, user_result = AIUser.get_user(uuid=user_uuid)
        if not user_success:
            logger.error(f"Failed to find user by uuid {user_uuid}: {user_result}")
            return jsonify({'code': 404, 'message': '用户不存在'}), 404
        
        user_id = user_result['id']

        if 'password' in update_data and not (update_data['password'] and update_data['password'].strip()):
            update_data.pop('password')

        # 使用获取到的id调用update_user方法更新其他字段（不含密码）
        success, result = AIUser.update_user(user_id=user_id, update_data=update_data)
        
        if success:
            # 平铺 additional_info 字段
            result = AIUserService.flatten_additional_info(result)
            logger.info(f"User updated successfully: uuid={user_uuid}, id={user_id}")
            return jsonify({'code': 200, 'message': '用户更新成功', 'data': result}), 200
        else:
            logger.error(f"Failed to update user {user_uuid}: {result}")
            if 'not found' in result.lower():
                return jsonify({'code': 404, 'message': result}), 404
            else:
                return jsonify({'code': 400, 'message': result}), 400
    
    @staticmethod
    async def delete_user() -> Tuple[Dict, int]:
        """
        删除AI用户（软删除）。
        
        请求体：
            - uuid (str): 用户UUID (必需) 或通过查询参数提供
        
        返回：
            包含成功消息或错误信息的JSON响应
        """
        # 支持从请求体中获取UUID
        request_data = request.json or {}
        user_uuid = request_data.get('uuid')

        if not user_uuid:
            return jsonify({'code': 400, 'message': '必须提供用户UUID'}), 400
        
        # 调用 Service 层删除用户及其关联记录
        from src.services.ai_user_service import AIUserService
        success, result = AIUserService.delete_user_with_relations(user_uuid)
        
        if success:
            logger.info(f"User deleted successfully: id={user_uuid}")
            return jsonify({'code': 200, 'message': '用户删除成功'}), 200
        else:
            logger.error(f"Failed to delete user {user_uuid}: {result}")
            if 'not found' in result.lower():
                return jsonify({'code': 404, 'message': result}), 404
            else:
                return jsonify({'code': 400, 'message': result}), 400
    
    @staticmethod
    async def query_users() -> Tuple[Dict, int]:
        """
        带过滤条件和分页的AI用户查询。
        
        查询参数：
            - username (str): 用户名过滤 (部分匹配)
            - realname (str): 真实姓名过滤 (部分匹配)
            - contact (str): 联系方式过滤 (部分匹配)
            - skip (int): 跳过记录数 (默认: 0)
            - take (int): 返回记录数 (默认: 100)
        
        返回：
            包含匹配用户列表的JSON响应
        """
        try:
            username = request.args.get('username', type=str)
            realname = request.args.get('realname', type=str)
            contact = request.args.get('contact', type=str)
            skip = request.args.get('skip', default=0, type=int)
            take = request.args.get('take', default=100, type=int)
            
            # 验证分页参数
            if skip < 0 or take <= 0 or take > 1000:
                return jsonify({'error': '分页参数无效'}), 400
            
            success, result = AIUser.query_users(username=username, realname=realname, contact=contact, skip=skip, take=take)
            if success:
                # 平铺每个用户的 additional_info 字段
                if 'items' in result and isinstance(result['items'], list):
                    result['items'] = [AIUserService.flatten_additional_info(user) for user in result['items']]
                return result, 200
            else:
                logger.error(f"Failed to query users: {result}")
                return {'error': '查询用户失败', 'message': result}, 500
        except Exception as e:
            logger.error(f"Error in query_users: {str(e)}")
            return {'error': '服务器内部错误'}, 500
