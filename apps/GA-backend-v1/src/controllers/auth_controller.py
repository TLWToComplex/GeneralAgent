"""
认证控制器模块。
处理用户登录、密码修改、验证码、CAS认证等安全认证相关HTTP请求。
仅负责 HTTP 请求解析、调用 Service 层、构建响应。
"""
import logging
from typing import Dict, Tuple
from datetime import datetime
from flask import request, jsonify
from src.services.auth_service import AuthService
from src.accessors.ai_user_accessor import AIUser
from src.utils.captcha_utils import captcha_generator
from src.core.cache.captcha_cache import captcha_cache
from requests import get, post
from requests import exceptions

logger = logging.getLogger(__name__)


class AuthController:
    """
    处理用户认证相关HTTP请求的控制器类。
    职责限定：请求参数校验 → 调用 Service 层 → 构建 HTTP 响应。
    """

    @staticmethod
    async def generate_captcha() -> Tuple[Dict, int]:
        """
        生成验证码接口

        返回：
            包含验证码ID和验证码图片Base64编码的JSON响应
        """
        try:
            import uuid
            # 生成验证码
            code, image_base64 = captcha_generator.generate()

            # 生成唯一验证码ID
            captcha_id = str(uuid.uuid4())

            # 将验证码存入缓存，5分钟有效期
            captcha_cache.set(captcha_id, code, ttl=300)

            logger.info(f"Captcha generated: id={captcha_id}")

            return {
                'code': 200,
                'message': 'success',
                'data': {
                    'captchaId': captcha_id,
                    'captchaImage': f"data:image/png;base64,{image_base64}"
                }
            }, 200
        except Exception as e:
            logger.error(f"Error generating captcha: {str(e)}")
            return {'error': '验证码生成失败'}, 500

    @staticmethod
    async def login() -> Tuple[Dict, int]:
        """
        用户登录接口（支持用户名或邮箱登录）

        职责：请求解析 → 调用 AuthService.authenticate → 构建响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for login")
            return jsonify({'error': '请求体必须为JSON格式'}), 400

        login_data = request.json

        # 验证必填字段
        required_fields = ['username', 'password', 'captchaId', 'captchaCode']
        for field in required_fields:
            if field not in login_data:
                return jsonify({'error': f'{field}为必填字段'}), 400

        username_or_email = login_data['username']
        password = login_data['password']
        captcha_id = login_data['captchaId']
        captcha_code = login_data['captchaCode']

        # 调用服务层执行业务逻辑
        success, result = AuthService.authenticate(
            username_or_email, password, captcha_id, captcha_code
        )

        if success:
            # 构建登录成功响应
            response = {
                'status': 'success',
                'message': '登录成功',
                'user': result['user_details'],
                'token': result['token'],
                'passwordExpiredWarning': result.get('password_expired_warning', False)
            }

            # 超过90天未更新密码时添加提醒标记（仅提醒，不阻断登录）
            if result.get('password_expired_warning'):
                logger.info(
                    f"Password expired warning for user: "
                    f"{result['username']} (超过90天未更新)"
                )

            logger.info(
                f"User logged in successfully: {result['username']} "
                f"(via {'email' if result['is_email'] else 'username'})"
            )
            return response, 200
        else:
            return {'error': result['error']}, result.get('status_code', 401)

    @staticmethod
    async def unlock_account(current_user: str) -> Tuple[Dict, int]:
        """
        管理员解锁因超过30天未登录而被锁定的账号

        期望输入的JSON数据包含：
            - uuid (str): 用户UUID (必需)

        返回：
            包含成功消息或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for unlock_account")
            return jsonify({'error': '请求体必须为JSON格式'}), 400

        data = request.json

        # 验证必填字段
        if 'uuid' not in data:
            logger.warning("Missing required field for unlock_account: uuid")
            return jsonify({'error': 'uuid为必填字段'}), 400

        user_uuid = data['uuid']

        # 调用服务层执行业务逻辑
        success, result = AuthService.unlock_account(user_uuid, current_user)

        if success:
            return result, 200
        else:
            return {'error': result['error']}, result.get('status_code', 400)

    @staticmethod
    async def change_password(current_user: str) -> Tuple[Dict, int]:
        """
        修改用户密码接口

        期望输入的JSON数据包含：
            - uuid (str): 用户UUID (必需)
            - old_password (str): 旧密码 (必需)
            - new_password (str): 新密码 (必需)

        返回：
            包含成功消息或错误信息的JSON响应
        """
        if not request.is_json:
            logger.warning("Received non-JSON request for change_password")
            return jsonify({'error': '请求体必须为JSON格式'}), 400

        data = request.json

        # 验证必填字段
        required_fields = ['uuid', 'old_password', 'new_password']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field for change_password: {field}")
                return jsonify({'error': f'{field}为必填字段'}), 400

        user_uuid = data['uuid']
        old_password = data['old_password']
        new_password = data['new_password']

        # 调用服务层执行业务逻辑
        success, result = AuthService.change_password(
            user_uuid, old_password, new_password, current_user
        )

        if success:
            return result, 200
        else:
            return {'error': result['error']}, result.get('status_code', 400)

    @staticmethod
    def update_last_login_time(username: str) -> bool:
        """
        更新用户的最后登录时间为当前时间。
        用于用户在活跃使用系统时（如调用 aiUserPreferences/get 接口）刷新登录时间，
        防止因超过30天未登录而被自动锁定。

        Args:
            username: 用户名

        Returns:
            bool: 是否更新成功
        """
        try:
            success, user_data = AIUser.get_user(username=username)
            if not success:
                logger.warning(f"更新 last_login_time 失败，用户不存在: {username}")
                return False

            additional_info = user_data.get('additional_info', {}) or {}
            if not isinstance(additional_info, dict):
                additional_info = {}

            additional_info['last_login_time'] = datetime.now().isoformat()

            update_success, update_result = AIUser.update_user(
                user_id=user_data['id'],
                update_data={
                    'additional_info': additional_info,
                    'update_by': username
                }
            )

            if update_success:
                logger.debug(f"已更新用户 {username} 的 last_login_time")
            else:
                logger.warning(f"更新用户 {username} 的 last_login_time 失败: {update_result}")

            return update_success
        except Exception as e:
            logger.error(f"更新 last_login_time 异常 (user: {username}): {str(e)}")
            return False

    @staticmethod
    def validate_cas_login(sso_url, permission_codes) -> Tuple[Dict, int]:
        logger.info("-" * 50)
        logger.info("开始CAS验证登录流程")

        # 1. 验证登录
        api = request.json.get('api')
        ticket = request.json.get('ticket')
        service = request.json.get('service')
        timestamp = request.json.get('timestamp')

        logger.info(f"请求参数: api={api}, ticket={ticket[:4]}..., service={service}, timestamp={timestamp}")

        try:
            logger.info("发送CAS验证请求...")
            response = get(
                f"{api}",
                params={
                    'ticket': ticket,
                    'service': service,
                    '_t': timestamp
                },
                headers={
                    'Content-Type': 'application/json',
                },
                timeout=300  # 添加超时设置
            )

            # 检查响应状态码
            if response.status_code != 200:
                error_msg = f'CAS验证失败: 状态码 {response.status_code}'
                logger.error(f"{error_msg}, 响应内容: {response.text[:200]}")
                return jsonify({'message': error_msg}), response.status_code

            logger.info("CAS验证请求成功，解析响应...")
            response_data = response.json()

            # 检查响应成功标志
            if not response_data.get('success', False):
                error_msg = f"CAS验证失败: {response_data.get('message', '未知错误')}"
                logger.error(error_msg)
                return jsonify({'message': error_msg}), 401

            # 解析响应
            access_token = response_data.get('result', {}).get('token')

            # 检查access_token是否存在
            if not access_token:
                error_msg = 'CAS验证失败: 未获取到access_token'
                logger.error(error_msg)
                return jsonify({'message': error_msg}), 401

            logger.info(f"成功获取access_token: {access_token}")

        except exceptions.Timeout:
            error_msg = "CAS验证请求超时"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 504
        except exceptions.ConnectionError:
            error_msg = "CAS验证连接错误，无法连接到服务器"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 503
        except exceptions.RequestException as e:
            error_msg = f"CAS验证请求异常: {str(e)}"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 503
        except Exception as e:
            error_msg = f"CAS验证过程中发生未知错误: {str(e)}"
            logger.exception("CAS验证异常")
            return jsonify({'message': error_msg}), 500

        # 2. 验证权限
        logger.info("开始验证用户权限...")
        # 构造请求数据
        request_data = {'token': access_token, 'timeStamp': timestamp}

        # 调用单点登录系统的 API 来验证令牌和时间戳
        try:
            logger.info(f"发送权限验证请求到: {sso_url}")
            response = post(
                sso_url,
                headers={
                    'X-Access-Token': access_token,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data=request_data,  # 使用json参数发送JSON格式数据
                timeout=30
            )
        except exceptions.Timeout:
            error_msg = "权限验证请求超时"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 504
        except exceptions.ConnectionError:
            error_msg = "权限验证连接错误，无法连接到服务器"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 503
        except exceptions.RequestException as e:
            error_msg = f"权限验证请求异常: {str(e)}"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 503
        except Exception as e:
            error_msg = f"权限验证过程中发生未知错误: {str(e)}"
            logger.exception("权限验证异常")
            return jsonify({'message': error_msg}), 500

        if response.status_code != 200:
            error_msg = f'权限验证失败: 状态码 {response.status_code}'
            logger.error(f"{error_msg}, 响应内容: {response.text[:200]}")
            return jsonify({'message': error_msg}), response.status_code

        # 解析返回的数据
        try:
            user_info = response.json()
            logger.info(f"收到权限验证响应: success={user_info.get('success')}")
        except Exception as e:
            error_msg = f"解析权限验证响应失败: {str(e)}"
            logger.error(f"{error_msg}, 响应内容: {response.text[:200]}")
            return jsonify({'message': error_msg}), 500

        # token不正确，返回401
        if user_info.get('success', False) != True:
            error_msg = f"权限验证失败: {user_info.get('message', '未知错误')}"
            logger.error(error_msg)
            return jsonify({'message': error_msg}), 401

        # 获取用户信息
        logger.info("提取用户信息...")
        user_info = user_info.get('result', {})
        user_name = user_info.get('xm', '')
        user_account = user_info.get('userName', '')
        user_gender = user_info.get('xbmc', '')
        user_org_code = user_info.get('orgCode', '')
        user_org_text = user_info.get('orgCodeTxt', '')
        user_org_full_name = user_info.get('orgCodeFullName', '')
        user_position = user_info.get('position', '')
        user_level_code = user_info.get('yhjbnm', '')
        user_level = user_info.get('yhjb', '')

        logger.info(f"用户信息: name={user_name}, account={user_account}, org_code={user_org_code}")

        # 检查权限码
        logger.info(f"开始检查权限码，需要的权限: {permission_codes}")
        permissions = user_info.get('userQxVOS', [])
        found_permissions = []

        for permission in permissions:
            permission_list = permission.get('wjbdyhqxVOList', [])
            for permission_item in permission_list:
                permission_code = permission_item.get('qxnm')
                found_permissions.append(permission_code)
                if permission_code in permission_codes:
                    logger.info(f"找到所需权限: {permission_code}")
                    logger.info("CAS验证流程完成，验证成功")
                    # 如果一切正常，则返回（保持原有的JSON字段名）
                    return jsonify({
                        'access_token': access_token,
                        'user_xm': user_name,
                        'user_userName': user_account,
                        'user_xbmc': user_gender,
                        'user_orgCode': user_org_code,
                        'user_orgCodeTxt': user_org_text,
                        'user_orgCodeFullName': user_org_full_name,
                        'user_position': user_position,
                        'user_yhjbnm': user_level_code,
                        'user_yhjb': user_level}), 200

        # 没权限，则返回403
        logger.warning(f"用户无所需权限，拥有的权限: {found_permissions}")
        return jsonify({'message': '权限被拒绝'}), 403
