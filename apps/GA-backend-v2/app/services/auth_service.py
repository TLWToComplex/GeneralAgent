"""认证业务逻辑服务。

从老项目 ``src/services/auth_service.py`` 迁移，业务规则与错误提示语逐条对齐：

* 验证码一次性使用（无论校验是否通过都作废）；
* 连续 :data:`AuthConfig.MAX_LOGIN_FAILURES` 次密码错误锁定账号
  :data:`AuthConfig.LOCK_MINUTES` 分钟；
* 超过 :data:`AuthConfig.INACTIVE_LOCK_DAYS` 天未登录自动锁定（admin 豁免），
  需管理员通过 ``/aiUser/unlockAccount`` 解锁；
* 密码超过 :data:`AuthConfig.PASSWORD_EXPIRE_DAYS` 天未更新时**仅提醒不阻断**登录
  （admin 为 :data:`AuthConfig.ADMIN_PASSWORD_EXPIRE_DAYS` 天）。

与老项目的差异（有意收敛，见 README「与老项目的差异」）：

* 老项目 Service 返回 ``(success, result)`` 元组，由 Controller 组装 HTTP 响应；
  V2 改为直接抛 :class:`ApiError`（携带原状态码与错误文案），HTTP 组装集中在一处；
* 密码写库失败时老项目把数据库异常原文回给前端（400），V2 统一为 500「服务器内部错误」。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import AuthConfig
from app.core.captcha_cache import CaptchaCacheManager
from app.core.errors import ApiError
from app.core.password_policy import PasswordValidator
from app.core.security import create_access_token, hash_password
from app.models.user import AIUser
from app.repositories.password_history_repository import PasswordHistoryRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """用户认证业务逻辑。"""

    def __init__(self, session: Session, captcha_cache: Optional[CaptchaCacheManager] = None) -> None:
        self.session = session
        self.captcha_cache = captcha_cache
        self.users = UserRepository(session)
        self.password_history = PasswordHistoryRepository(session)

    # ============================================================ 纯规则函数
    @staticmethod
    def check_account_locked(additional_info: dict) -> Tuple[bool, str]:
        """检查「密码错误锁定」状态。

        只修改内存中的 ``additional_info``，落库由调用方在行锁保护下统一提交，
        以免并发登录时丢失其它字段。
        """
        locked_until_str = additional_info.get("locked_until")
        if not locked_until_str:
            return False, ""
        try:
            locked_until = datetime.fromisoformat(locked_until_str)
        except (TypeError, ValueError):
            logger.warning("解析 locked_until 失败: %s", locked_until_str)
            additional_info.pop("locked_until", None)
            additional_info.pop("login_failed_count", None)
            return False, ""

        now = datetime.now()
        if now < locked_until:
            remaining = int((locked_until - now).total_seconds() / 60)
            return True, f"账号已锁定，请{remaining}分钟后重试"

        # 锁定已过期：清除锁定状态与失败记录（仅内存）
        additional_info.pop("locked_until", None)
        additional_info.pop("login_failed_count", None)
        return False, ""

    @staticmethod
    def check_inactive_account(additional_info: dict, username: str) -> Tuple[bool, str]:
        """检查「超过 N 天未登录」的自动锁定状态。

        ``inactive_locked`` 标记一旦存在即保持锁定，只能由管理员解锁。
        """
        if username == AuthConfig.ADMIN_USERNAME:
            return False, ""

        if "inactive_locked" in additional_info:
            return True, f"账号因超过{AuthConfig.INACTIVE_LOCK_DAYS}天未登录已被锁定，请联系管理员解锁"

        last_login_str = additional_info.get("last_login_time")
        if last_login_str:
            try:
                last_login = datetime.fromisoformat(last_login_str)
                days_inactive = (datetime.now() - last_login).days
                if days_inactive >= AuthConfig.INACTIVE_LOCK_DAYS:
                    additional_info["inactive_locked"] = "1"
                    logger.warning("账号因超过%s天未登录被锁定，最后登录时间: %s",
                                   AuthConfig.INACTIVE_LOCK_DAYS, last_login_str)
                    return True, f"账号已超过{AuthConfig.INACTIVE_LOCK_DAYS}天未登录，已被自动锁定，请联系管理员解锁"
            except (TypeError, ValueError):
                logger.warning("解析 last_login_time 失败: %s", last_login_str)
        return False, ""

    @staticmethod
    def record_login_failure(additional_info: dict) -> Tuple[str, int]:
        """累计一次密码错误，返回 ``(错误提示, HTTP状态码)``。"""
        failed_count = additional_info.get("login_failed_count", 0) + 1
        additional_info["login_failed_count"] = failed_count

        if failed_count >= AuthConfig.MAX_LOGIN_FAILURES:
            locked_until = datetime.now() + timedelta(minutes=AuthConfig.LOCK_MINUTES)
            additional_info["locked_until"] = locked_until.isoformat()
            return (
                f"连续{AuthConfig.MAX_LOGIN_FAILURES}次密码错误，"
                f"账号已锁定{AuthConfig.LOCK_MINUTES}分钟",
                401,
            )
        remaining = AuthConfig.MAX_LOGIN_FAILURES - failed_count
        return f"密码错误，还剩{remaining}次机会", 401

    @staticmethod
    def clear_login_failure(additional_info: dict) -> None:
        """登录成功后清除失败计数与锁定标记（仅内存）。"""
        additional_info.pop("login_failed_count", None)
        additional_info.pop("locked_until", None)

    @staticmethod
    def check_password_expired(additional_info: dict, username: str) -> bool:
        """密码是否已超期（超期只提醒，不阻断登录）。"""
        last_change_str = additional_info.get("last_password_change")
        if not last_change_str:
            return False
        try:
            days_since_change = (datetime.now() - datetime.fromisoformat(last_change_str)).days
        except (TypeError, ValueError):
            logger.warning("解析 last_password_change 失败: %s", last_change_str)
            return False

        if days_since_change >= AuthConfig.PASSWORD_EXPIRE_DAYS:
            return True
        if username == AuthConfig.ADMIN_USERNAME and days_since_change >= AuthConfig.ADMIN_PASSWORD_EXPIRE_DAYS:
            return True
        return False

    # ============================================================ 对外能力
    def _validate_captcha(self, captcha_id: str, captcha_code: str) -> None:
        """校验验证码；无论成功失败都作废（一次性）。"""
        if self.captcha_cache is None:  # pragma: no cover - 仅登录流程会用到验证码
            raise ApiError("验证码校验不可用", 500)
        stored_code = self.captcha_cache.get(captcha_id)
        self.captcha_cache.delete(captcha_id)

        if not stored_code:
            raise ApiError("验证码已过期，请重新获取", 401)
        if stored_code.upper() != (captcha_code or "").upper():
            raise ApiError("验证码错误", 401)

    def _resolve_login_user(self, username_or_email: str) -> Tuple[AIUser, str]:
        """定位登录用户，返回 ``(用户对象, 用户名)``（邮箱登录时返回真实用户名）。"""
        user = self.users.find_by_login(username_or_email, for_update=True)
        if user is None:
            raise ApiError("用户名或邮箱无效", 401)
        username = user.username if "@" in username_or_email else username_or_email
        return user, username

    @staticmethod
    def build_user_details(user: AIUser) -> dict:
        """组装登录返回的用户信息：去掉密码、平铺 additional_info、补 needUpdateMsg。"""
        details = user.to_dict()
        details.pop("password", None)
        additional = details.pop("additional_info", None)
        if isinstance(additional, dict):
            details.update(additional)
        details["needUpdateMsg"] = False if details.get("realname") else True
        return details

    def login(self, username_or_email: str, password: str, captcha_id: str, captcha_code: str) -> dict:
        """登录认证。

        Returns:
            dict: ``{"user_details", "username", "is_email", "token", "password_expired_warning"}``

        Raises:
            ApiError: 验证码失效/错误(401)、账号密码无效(401)、账号被锁定(403)、写库失败(500)
        """
        self._validate_captcha(captcha_id, captcha_code)

        user, username = self._resolve_login_user(username_or_email)

        # 先复制一份 additional_info，改动集中在内存中，最后在行锁保护下一次性写回
        additional_info = dict(user.additional_info or {})

        is_locked, lock_message = self.check_account_locked(additional_info)
        if is_locked:
            logger.warning("账号处于密码错误锁定状态: %s", username_or_email)
            raise ApiError(lock_message, 403)

        is_inactive, inactive_message = self.check_inactive_account(additional_info, username)
        if is_inactive:
            # 把 inactive_locked 标记持久化，否则下次登录无法判定为不活跃锁定
            if not self.users.save_additional_info(user, additional_info):
                logger.error("保存 inactive_locked 标记失败: %s", username)
            logger.warning("账号处于未登录锁定状态: %s", username_or_email)
            raise ApiError(inactive_message, 403)

        if not self.users.verify_password(username, password):
            failure_message, status_code = self.record_login_failure(additional_info)
            if not self.users.save_additional_info(user, additional_info):
                raise ApiError("系统错误，请稍后重试", 500)
            logger.warning("密码校验失败: %s", username_or_email)
            raise ApiError(failure_message, status_code)

        # 登录成功：清理失败记录与不活跃锁定标记，刷新最后登录时间
        self.clear_login_failure(additional_info)
        additional_info.pop("inactive_locked", None)
        additional_info["last_login_time"] = datetime.now().isoformat()

        password_expired = self.check_password_expired(additional_info, username)

        if not self.users.save_additional_info(user, additional_info):
            logger.error("更新 additional_info 失败: %s", username)
            raise ApiError("系统错误，请稍后重试", 500)

        user_details = self.build_user_details(user)
        is_email = "@" in username_or_email
        token = create_access_token(username=username, user_id=user_details.get("id"))

        logger.info("用户登录成功: %s（通过 %s）", username, "邮箱" if is_email else "用户名")
        return {
            "user_details": user_details,
            "username": username,
            "is_email": is_email,
            "token": token,
            "password_expired_warning": password_expired,
        }

    def change_password(self, user_uuid: str, old_password: str, new_password: str, current_user: str) -> dict:
        """修改密码（校验旧密码、密码强度、近 N 次历史密码）。"""
        user = self.users.get_by_uuid(user_uuid)
        if user is None:
            logger.error("按 uuid 未找到用户: %s", user_uuid)
            raise ApiError("用户不存在", 404)

        username = user.username
        if not self.users.verify_password(username, old_password):
            logger.warning("旧密码不正确: %s (uuid: %s)", username, user_uuid)
            raise ApiError("旧密码不正确", 401)

        recent_hashes = self.password_history.get_recent_hashes(
            user.uuid, n=AuthConfig.PASSWORD_HISTORY_KEEP
        )
        validation = PasswordValidator.validate_password(
            new_password, username, password_history_hashes=recent_hashes
        )
        if not validation["valid"]:
            logger.warning("密码强度校验失败: %s -> %s", username, validation["message"])
            raise ApiError(validation["message"], 400)

        try:
            user.password = hash_password(new_password)
            user.update_by = current_user
            user.update_time = datetime.now()
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            logger.error("更新密码失败 (uuid: %s): %s", user_uuid, exc)
            raise ApiError("服务器内部错误", 500) from exc

        logger.info("密码更新成功: %s (uuid: %s)", username, user_uuid)

        # 密码历史与变更时间属于附加记录，失败不影响主流程（与老项目一致）
        try:
            self.password_history.add_record(user.uuid, hash_password(new_password))
            self.password_history.cleanup_old_records(
                user.uuid, keep=AuthConfig.PASSWORD_HISTORY_KEEP
            )
        except Exception as exc:
            logger.error("记录密码历史失败 (uuid: %s): %s", user_uuid, exc)

        try:
            additional_info = dict(user.additional_info or {})
            additional_info["last_password_change"] = datetime.now().isoformat()
            if not self.users.save_additional_info(user, additional_info):
                logger.error("更新 last_password_change 失败 (uuid: %s)", user_uuid)
        except Exception as exc:
            logger.error("更新 last_password_change 异常 (uuid: %s): %s", user_uuid, exc)

        return {"status": "success", "message": "密码更新成功"}

    def unlock_account(self, user_uuid: str, current_user: str) -> dict:
        """管理员解锁因超过 N 天未登录而被锁定的账号。"""
        user = self.users.get_by_uuid(user_uuid)
        if user is None:
            logger.warning("解锁失败，用户不存在: %s", user_uuid)
            raise ApiError("用户不存在", 404)

        additional_info = dict(user.additional_info or {})
        if "inactive_locked" not in additional_info:
            logger.info("用户 %s (uuid: %s) 未被锁定，无需解锁", user.username, user_uuid)
            return {"status": "success", "message": "该账号未被锁定，无需解锁"}

        additional_info.pop("inactive_locked", None)
        additional_info["last_login_time"] = datetime.now().isoformat()

        if not self.users.save_additional_info(user, additional_info):
            logger.error("解锁失败，数据库更新错误 (uuid: %s)", user_uuid)
            raise ApiError("系统错误，请稍后重试", 500)

        logger.info("管理员 %s 已解锁用户 %s (uuid: %s)", current_user, user.username, user_uuid)
        return {"status": "success", "message": "账号已解锁，用户可以正常登录"}