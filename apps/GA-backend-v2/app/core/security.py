"""密码哈希与 JWT 签发/解析。

密码哈希沿用老项目的 Werkzeug ``generate_password_hash`` / ``check_password_hash``，
因此 V2 可以直接校验既有 ``ai_user.password`` 数据，无需迁移密码。

JWT 约定（与老项目 flask-jwt-extended 的 LOCAL_NO_AUTHZ 解析逻辑兼容）：

* 顶层 ``username``：鉴权时优先读取；
* ``identity``：``{"username", "user_id", "timestamp"}`，对应老项目 create_access_token 的 identity；
* 不使用 ``sub`` 存放字典——PyJWT 2.10 起要求 ``sub`` 必须是字符串。
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import JWTConfig

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """生成密码哈希。"""
    return generate_password_hash(password)


def verify_password_hash(password_hash: Optional[str], password: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    if not password_hash:
        return False
    try:
        return check_password_hash(password_hash, password)
    except Exception as exc:  # 历史数据里可能存在非法哈希
        logger.error("密码校验异常: %s", exc)
        return False


def create_access_token(username: str, user_id: Any = None) -> str:
    """签发访问令牌。"""
    now = int(time.time())
    payload = {
        "username": username,
        "identity": {
            "username": username,
            "user_id": user_id,
            "timestamp": time.time(),
        },
        "iat": now,
        "exp": now + int(JWTConfig.ACCESS_TOKEN_EXPIRES_SECONDS),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析并校验访问令牌，签名或有效期不合法时抛 ``jwt.PyJWTError``。

    老项目 LOCAL_NO_AUTHZ 分支不校验签名（任意 Bearer 值都能拿到用户名），
    V2 做了一次收敛：签名必须合法。接口返回的提示语保持 401。
    """
    return jwt.decode(token, JWTConfig.SECRET_KEY, algorithms=[JWTConfig.ALGORITHM])


def extract_username(payload: dict) -> Optional[str]:
    """从令牌载荷中提取用户名，兼容老项目支持的多种字段形态。"""
    username = payload.get("username")
    if username:
        return username if isinstance(username, str) else None

    identity = payload.get("identity")
    if isinstance(identity, dict):
        for key in ("username", "user"):
            value = identity.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):  # 老项目 identity 里可能再嵌一层
                nested = value.get("username")
                if isinstance(nested, str) and nested:
                    return nested
    elif isinstance(identity, str) and identity:
        return identity

    sub = payload.get("sub")
    if isinstance(sub, str) and sub:
        return sub

    user = payload.get("user")
    if isinstance(user, str) and user:
        return user
    return None