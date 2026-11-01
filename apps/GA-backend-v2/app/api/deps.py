"""FastAPI 依赖注入：数据库会话、验证码资源、鉴权。

鉴权语义对齐老项目 ``src/utils/jwt_required.py`` 的 ``LOCAL_NO_AUTHZ`` 分支：
只从 ``Authorization: Bearer <token>`` 取令牌并解析出 ``current_user``。

差异（安全收敛）：老项目在本地模式下不校验签名（任意字符串都能成为用户名），
V2 要求签名合法；提示语仍为原 401 结构与文案。
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

from app.config import LOCAL_NO_AUTHZ, SSOConfig
from app.core.captcha import CaptchaGenerator
from app.core.captcha_cache import CaptchaCacheManager
from app.core.errors import ApiError
from app.core.security import decode_access_token, extract_username
from app.db import get_session

logger = logging.getLogger(__name__)

__all__ = [
    "get_session",
    "get_captcha_cache",
    "get_captcha_generator",
    "require_token_payload",
    "require_current_user",
    "require_admin",
]

bearer_scheme = HTTPBearer(auto_error=False)


def get_captcha_cache(request: Request) -> CaptchaCacheManager:
    """取当前应用进程的验证码缓存。"""
    return request.app.state.captcha_cache


def get_captcha_generator(request: Request) -> CaptchaGenerator:
    """取当前应用进程的验证码生成器。"""
    return request.app.state.captcha_generator


def _unauthorized(message: str) -> ApiError:
    """构造与老项目一致的 401 响应体：``{"message": ..., "code": 401}``。"""
    return ApiError(message, 401, payload={"message": message, "code": 401})


def require_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """解析并校验 Bearer 令牌，返回 JWT 载荷。"""
    if SSOConfig.URL and SSOConfig.URL != LOCAL_NO_AUTHZ:
        # 宁可显式失败，也不能在配置了远程 SSO 的情况下静默降级为本地解析
        raise ApiError(
            f"V2 尚未迁移远程 SSO 令牌校验（当前 sso.url={SSOConfig.URL}），"
            f"请配置为 {LOCAL_NO_AUTHZ}",
            501,
        )

    if credentials is None or not credentials.credentials:
        raise _unauthorized("Bearer令牌缺失")

    try:
        return decode_access_token(credentials.credentials)
    except PyJWTError as exc:
        logger.warning("令牌解析失败: %s", exc)
        raise _unauthorized("Bearer令牌无效") from exc


def require_current_user(payload: dict = Depends(require_token_payload)) -> str:
    """从令牌载荷中取出当前登录用户名。"""
    username = extract_username(payload)
    if not username:
        raise _unauthorized("Bearer令牌无效")
    return username


def require_admin(current_user: str = Depends(require_current_user)) -> str:
    """仅允许 admin 访问（对应老项目 ``src/utils/admin_required.py``）。"""
    if not current_user or current_user.lower() != "admin":
        logger.warning("非管理员用户 '%s' 尝试访问管理员接口", current_user)
        message = "权限不足，仅管理员可访问"
        raise ApiError(message, 403, payload={"code": 403, "message": message})
    return current_user