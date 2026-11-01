"""账号状态纯规则测试（不依赖数据库与 HTTP）。"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.config import AuthConfig
from app.services.auth_service import AuthService


class AccountLockRulesTest(unittest.TestCase):
    def test_not_locked_without_marker(self) -> None:
        info: dict = {}
        locked, message = AuthService.check_account_locked(info)
        self.assertFalse(locked)
        self.assertEqual(message, "")

    def test_locked_until_in_future(self) -> None:
        locked_until = datetime.now() + timedelta(minutes=3)
        info = {"locked_until": locked_until.isoformat()}
        locked, message = AuthService.check_account_locked(info)
        self.assertTrue(locked)
        self.assertRegex(message, r"^账号已锁定，请\d+分钟后重试$")

    def test_expired_lock_is_cleared_in_memory(self) -> None:
        info = {
            "locked_until": (datetime.now() - timedelta(minutes=1)).isoformat(),
            "login_failed_count": 5,
        }
        locked, message = AuthService.check_account_locked(info)
        self.assertFalse(locked)
        self.assertEqual(message, "")
        self.assertNotIn("locked_until", info)
        self.assertNotIn("login_failed_count", info)

    def test_invalid_locked_until_is_tolerated(self) -> None:
        info = {"locked_until": "not-a-timestamp", "login_failed_count": 2}
        locked, _ = AuthService.check_account_locked(info)
        self.assertFalse(locked)
        self.assertNotIn("locked_until", info)


class LoginFailureRulesTest(unittest.TestCase):
    def test_counts_down_and_reports_remaining(self) -> None:
        info: dict = {}
        for index in range(1, AuthConfig.MAX_LOGIN_FAILURES):
            message, status = AuthService.record_login_failure(info)
            self.assertEqual(status, 401)
            self.assertEqual(info["login_failed_count"], index)
            self.assertEqual(
                message, f"密码错误，还剩{AuthConfig.MAX_LOGIN_FAILURES - index}次机会"
            )

    def test_max_failures_locks_account(self) -> None:
        info: dict = {}
        for _ in range(AuthConfig.MAX_LOGIN_FAILURES - 1):
            AuthService.record_login_failure(info)

        message, status = AuthService.record_login_failure(info)
        self.assertEqual(status, 401)
        self.assertEqual(message, "连续5次密码错误，账号已锁定5分钟")
        self.assertIn("locked_until", info)

        locked_until = datetime.fromisoformat(info["locked_until"])
        expected = datetime.now() + timedelta(minutes=AuthConfig.LOCK_MINUTES)
        self.assertLess(abs((locked_until - expected).total_seconds()), 5)

    def test_clear_login_failure(self) -> None:
        info = {"login_failed_count": 3, "locked_until": datetime.now().isoformat()}
        AuthService.clear_login_failure(info)
        self.assertEqual(info, {})


class InactiveAccountRulesTest(unittest.TestCase):
    def test_admin_is_exempt(self) -> None:
        info = {"last_login_time": (datetime.now() - timedelta(days=365)).isoformat()}
        locked, message = AuthService.check_inactive_account(info, "admin")
        self.assertFalse(locked)
        self.assertEqual(message, "")
        self.assertNotIn("inactive_locked", info)

    def test_inactive_marker_keeps_account_locked(self) -> None:
        info = {"inactive_locked": "1"}
        locked, message = AuthService.check_inactive_account(info, "zhangsan")
        self.assertTrue(locked)
        self.assertEqual(message, "账号因超过30天未登录已被锁定，请联系管理员解锁")

    def test_locks_after_configured_days(self) -> None:
        info = {"last_login_time": (datetime.now() - timedelta(days=31)).isoformat()}
        locked, message = AuthService.check_inactive_account(info, "zhangsan")
        self.assertTrue(locked)
        self.assertEqual(message, "账号已超过30天未登录，已被自动锁定，请联系管理员解锁")
        self.assertEqual(info["inactive_locked"], "1")

    def test_exactly_configured_days_locks(self) -> None:
        info = {"last_login_time": (datetime.now() - timedelta(days=30)).isoformat()}
        locked, _ = AuthService.check_inactive_account(info, "zhangsan")
        self.assertTrue(locked, "达到 30 天即锁定（老项目口径 >= 30）")

    def test_within_window_not_locked(self) -> None:
        info = {"last_login_time": (datetime.now() - timedelta(days=29)).isoformat()}
        locked, _ = AuthService.check_inactive_account(info, "zhangsan")
        self.assertFalse(locked)
        self.assertNotIn("inactive_locked", info)

    def test_invalid_last_login_time_is_tolerated(self) -> None:
        info = {"last_login_time": "bad-timestamp"}
        locked, _ = AuthService.check_inactive_account(info, "zhangsan")
        self.assertFalse(locked)

    def test_no_last_login_time_is_tolerated(self) -> None:
        locked, _ = AuthService.check_inactive_account({}, "zhangsan")
        self.assertFalse(locked)


class PasswordExpiryRulesTest(unittest.TestCase):
    def test_never_changed_is_not_expired(self) -> None:
        self.assertFalse(AuthService.check_password_expired({}, "zhangsan"))

    def test_user_threshold_is_90_days(self) -> None:
        expired = {"last_password_change": (datetime.now() - timedelta(days=90)).isoformat()}
        fresh = {"last_password_change": (datetime.now() - timedelta(days=89)).isoformat()}
        self.assertTrue(AuthService.check_password_expired(expired, "zhangsan"))
        self.assertFalse(AuthService.check_password_expired(fresh, "zhangsan"))

    def test_admin_threshold_is_60_days(self) -> None:
        expired = {"last_password_change": (datetime.now() - timedelta(days=60)).isoformat()}
        fresh = {"last_password_change": (datetime.now() - timedelta(days=59)).isoformat()}
        self.assertTrue(AuthService.check_password_expired(expired, "admin"))
        self.assertFalse(AuthService.check_password_expired(fresh, "admin"))

    def test_invalid_timestamp_is_tolerated(self) -> None:
        self.assertFalse(
            AuthService.check_password_expired({"last_password_change": "bad"}, "zhangsan")
        )