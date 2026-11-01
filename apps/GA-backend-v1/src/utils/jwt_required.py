"""
JWT认证装饰器模块。
提供用于API端点保护的自定义JWT认证装饰器。
"""
import time
from typing import Dict, Any, Tuple, Union, Callable
from functools import wraps
from flask import jsonify, request, make_response
from requests import post, exceptions


def jwt_required(sso_url: str, permission_codes: list) -> Callable:
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs) -> Tuple[Union[Dict, Any], int]:
            # 本地不进行授权
            if sso_url == 'LOCAL_NO_AUTHZ':
                # 从Authorization Header中获取 JWT 令牌
                auth_header = request.headers.get('Authorization')
                token = None
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header[len('Bearer '):]
                
                # 如果没有token，则返回操作失败
                if not token:
                    return make_response(jsonify({'message': 'Bearer令牌缺失', 'code': 401}), 401)
                
                # 尝试从token中解析username
                username = ''  # 默认用户名作为回退
                if token:
                    try:
                        # 首先检查是否是标准JWT格式 (header.payload.signature)
                        if len(token.split('.')) == 3:
                            # 处理标准JWT格式，特别是由create_access_token生成的token
                            import base64
                            import json
                            # 解码payload部分
                            payload = token.split('.')[1]
                            # 补充padding
                            payload += '=' * ((4 - len(payload) % 4) % 4)
                            try:
                                # 解码base64
                                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                                # 解析JSON
                                payload_data = json.loads(decoded)
                                
                                # 检查常见的JWT payload结构
                                # 1. 直接在payload根级别查找username
                                if 'username' in payload_data:
                                    username = payload_data['username']
                                # 2. 查找identity字段（Flask-JWT-Extended常用方式）
                                elif 'identity' in payload_data:
                                    # identity可能是字典
                                    if isinstance(payload_data['identity'], dict):
                                        if 'username' in payload_data['identity']:
                                            username = payload_data['identity']['username']
                                        elif 'user' in payload_data['identity']:
                                            username = payload_data['identity']['user']
                                    # 也可能是字符串
                                    else:
                                        username = str(payload_data['identity'])
                                # 3. 查找sub字段（标准JWT claim）
                                elif 'sub' in payload_data:
                                    username = payload_data['sub']
                                # 4. 查找user字段
                                elif 'user' in payload_data:
                                    username = payload_data['user']
                                print(f"JWT payload解析结果: {payload_data}")
                            except Exception as e:
                                print(f"JWT解码错误: {e}")
                                # 解码失败则尝试其他格式
                        # 尝试简单分隔格式
                        elif '|' in token:
                            # 假设格式为 username|timestamp
                            username = token.split('|')[0]
                        # 如果token不是标准格式，直接使用token作为username
                        else:
                            username = token
                    except Exception as e:
                        # 解析失败时记录错误但继续使用默认值
                        print(f"解析token获取username错误: {e}")
                # 确保username是字符串而不是字典
                # 如果username是字典，提取其中的username字段
                if isinstance(username, dict):
                    username = username.get('username', '')
                    print('从字典中提取的username:', username)
                # 添加解析出的用户到kwargs中
                kwargs['current_user'] = username
                return func(*args, **kwargs)

            # 从Authorization Header中获取 JWT 令牌
            auth_header = request.headers.get('Authorization')
            token = None
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[len('Bearer '):]
            else:
                token = request.headers.get('X-ACCESS-TOKEN')

            if not token:
                return make_response(jsonify({'message': 'Bearer令牌或X-ACCESS-TOKEN缺失或无效'}), 401)

            if not token:
                return jsonify({'message': '令牌或时间戳缺失'}), 401

            # 构造请求数据
            data = {'token': token, 'timeStamp': str(int(time.time()) * 1000)}

            # 调用单点登录系统的 API 来验证令牌和时间戳
            response = None
            try:
                response = post(
                    sso_url, 
                    headers={
                        'X-Access-Token': token, 
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }, 
                    data=data, 
                    timeout=30
                )
            except exceptions.RequestException as e:
                return jsonify({'message': f'请求异常: {str(e)}'}), 503

            if response.status_code != 200:
                return jsonify({'message': '令牌验证失败'}), 401

            # 解析返回的数据
            user_info = response.json()
            print(user_info)

            if user_info.get('success', False) != True:
                return jsonify({'message': '令牌验证失败'}), 401

            # 检查权限码
            permissions = user_info.get('result', {}).get('userQxVOS', [])
            for permission in permissions:
                permission_list = permission.get('wjbdyhqxVOList', [])
                for permission_item in permission_list:
                    permission_code = permission_item.get('qxnm')
                    if permission_code in permission_codes:
                        # 如果一切正常，则调用原始视图函数
                        return func(*args, **kwargs)

            # 如果没有找到相应的权限码，则返回错误
            return jsonify({'message': '权限被拒绝'}), 403

        return decorated_function

    return decorator

