"""
管理员权限校验装饰器模块。
提供用于API端点的管理员身份验证装饰器，确保只有 admin 用户可访问。
"""
import logging
from typing import Callable
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """
    管理员权限校验装饰器。
    校验当前登录用户是否为 admin，仅 admin 可访问被装饰的接口。

    必须在已注入 current_user 的上下文中使用（即配合 @jwt_required 使用）。

    Usage:
        @app.route('/some/admin/endpoint', methods=['POST'])
        @jwt_required(sso_url, permission_codes)
        @admin_required
        @async_route
        async def my_endpoint(current_user: str = 'admin') -> Response:
            ...
    """
    @wraps(func)
    async def decorated_function(*args, **kwargs):
        current_user = kwargs.get('current_user', '')
        if not current_user or current_user.lower() != 'admin':
            logger.warning(
                f"Non-admin user '{current_user}' attempted to access "
                f"admin-only endpoint: {func.__name__}"
            )
            return jsonify({'code': 403, 'message': '权限不足，仅管理员可访问'}), 403

        return await func(*args, **kwargs)

    return decorated_function
