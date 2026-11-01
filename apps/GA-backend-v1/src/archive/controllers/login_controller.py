"""
Login controller module.
Handles user authentication and login functionality for the admin interface.
"""
import logging
from typing import Dict, Tuple
from flask import request, jsonify
from flask_jwt_extended import create_access_token
from accessors.admin_accounts_accessor import AdminAccount

from requests import post, exceptions, get

# 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     handlers=[
#         logging.StreamHandler()
#     ]
# )
logger = logging.getLogger('login')

class LoginController:
    @staticmethod
    def login() -> Tuple[Dict, int]:
        if not request.is_json:
            logger.warning("接收到非JSON请求")
            return jsonify({"msg": "Missing JSON in request"}), 400

        username = request.json.get('username', None)
        password = request.json.get('password', None)

        if not username or not password:
            logger.warning(f"登录请求缺少必要参数: username={bool(username)}, password={bool(password)}")
            return jsonify({"msg": "Missing username or password"}), 400

        logger.info(f"尝试验证用户: {username}")
        user = AdminAccount.authenticate(username, password)
        if user:
            access_token = create_access_token(identity=username)
            logger.info(f"用户 {username} 验证成功")
            return jsonify(access_token=access_token), 200
        else:
            logger.warning(f"用户 {username} 验证失败")
            return jsonify({"msg": "Bad username or password"}), 401

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
        return jsonify({'message': 'Permission denied'}), 403

