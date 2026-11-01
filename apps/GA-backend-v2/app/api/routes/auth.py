"""认证相关接口。

路径、请求体字段名、响应体结构与 HTTP 状态码均与老项目保持一致：

============== ==================================== ==========================
接口            请求                                 说明
============== ==================================== ==========================
GET  /captcha         -                               图形验证码（无需认证）
POST /aiUser/login    username/password/captchaId/captchaCode  本地账号登录
POST /aiUser/changePassword  uuid/old_password/new_password    需登录
POST /aiUser/unlockAccount   uuid                              需 admin
============== ==================================== ==========================
"""
from __future__ import annotations

import logging
import uuid as uuid_lib

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import (
    get_captcha_cache,
    get_captcha_generator,
    get_session,
    require_admin,
    require_current_user,
)
from app.config import AuthConfig, CaptchaConfig
from app.core.captcha import CaptchaGenerator
from app.core.captcha_cache import CaptchaCacheManager
from app.core.errors import ApiError
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["认证"])


class LoginRequest(BaseModel):
    """登录请求体（字段名与老项目一致）。"""

    username: str = Field(description="用户名或邮箱")
    password: str = Field(description="明文密码")
    captchaId: str = Field(description="验证码ID")
    captchaCode: str = Field(description="验证码答案")


class ChangePasswordRequest(BaseModel):
    """修改密码请求体。"""

    uuid: str = Field(description="用户UUID")
    old_password: str = Field(description="旧密码")
    new_password: str = Field(description="新密码")


class UnlockAccountRequest(BaseModel):
    """解锁账号请求体。"""

    uuid: str = Field(description="用户UUID")


@router.get("/captcha", summary="获取图形验证码（无需认证）")
def generate_captcha(
    captcha_cache: CaptchaCacheManager = Depends(get_captcha_cache),
    captcha_generator: CaptchaGenerator = Depends(get_captcha_generator),
) -> dict:
    """生成验证码并写入缓存（默认 5 分钟有效）。"""
    try:
        code, image_base64 = captcha_generator.generate()
    except Exception as exc:
        logger.error("验证码生成失败: %s", exc)
        raise ApiError("验证码生成失败", 500) from exc

    captcha_id = str(uuid_lib.uuid4())
    captcha_cache.set(captcha_id, code, ttl=CaptchaConfig.TTL_SECONDS)
    logger.info("验证码已生成: id=%s", captcha_id)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "captchaId": captcha_id,
            "captchaImage": f"data:image/png;base64,{image_base64}",
        },
    }


@router.post("/aiUser/login", summary="用户登录（支持用户名或邮箱）")
def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    captcha_cache: CaptchaCacheManager = Depends(get_captcha_cache),
) -> dict:
    """本地账号登录：验证码 → 账号锁定 → 未登录锁定 → 密码校验 → 签发 JWT。"""
    service = AuthService(session, captcha_cache)
    result = service.login(
        payload.username, payload.password, payload.captchaId, payload.captchaCode
    )

    if result["password_expired_warning"]:
        logger.info(
            "用户 %s 密码超过%s天未更新（仅提醒，不阻断登录）",
            result["username"],
            AuthConfig.PASSWORD_EXPIRE_DAYS
            if result["username"] != AuthConfig.ADMIN_USERNAME
            else AuthConfig.ADMIN_PASSWORD_EXPIRE_DAYS,
        )

    return {
        "status": "success",
        "message": "登录成功",
        "user": result["user_details"],
        "token": result["token"],
        "passwordExpiredWarning": result["password_expired_warning"],
    }


@router.post("/aiUser/changePassword", summary="修改密码（需登录）")
def change_password(
    payload: ChangePasswordRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(require_current_user),
) -> dict:
    """修改指定用户密码；需要携带登录返回的 Bearer 令牌。"""
    service = AuthService(session)
    return service.change_password(
        payload.uuid, payload.old_password, payload.new_password, current_user
    )


@router.post("/aiUser/unlockAccount", summary="解锁超期未登录账号（需 admin）")
def unlock_account(
    payload: UnlockAccountRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(require_admin),
) -> dict:
    """管理员解锁因超过配置天数未登录而被自动锁定的账号。"""
    service = AuthService(session)
    return service.unlock_account(payload.uuid, current_user)