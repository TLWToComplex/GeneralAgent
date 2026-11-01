"""登录接口测试（POST /aiUser/login）——覆盖老项目 login 全部分支。"""
from __future__ import annotations

from tests.support import ADMIN_PASSWORD, ADMIN_USERNAME, USER_PASSWORD, ApiTestCase


class LoginApiTest(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user(
            "zhangsan", USER_PASSWORD, email="zhangsan@example.com", realname="张三"
        )

    # ------------------------------------------------------------ 正常流程
    def test_login_success_contract(self) -> None:
        response = self.login("zhangsan", USER_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["status"], "success")
        self.assertEqual(body["message"], "登录成功")
        self.assertTrue(body["token"])
        self.assertFalse(body["passwordExpiredWarning"])

        user = body["user"]
        self.assertEqual(user["username"], "zhangsan")
        self.assertEqual(user["uuid"], self.user["uuid"])
        self.assertEqual(user["realname"], "张三")
        self.assertEqual(user["email"], "zhangsan@example.com")
        self.assertNotIn("password", user, "响应不能包含密码字段")
        self.assertNotIn("additional_info", user, "additional_info 应被平铺到顶层")
        self.assertFalse(user["needUpdateMsg"], "已填写真实姓名时 needUpdateMsg 应为 False")

    def test_login_writes_last_login_time(self) -> None:
        self.login("zhangsan", USER_PASSWORD)
        info = self.get_additional_info(self.user["uuid"])
        self.assertIn("last_login_time", info)
        self.assertNotIn("login_failed_count", info)
        self.assertNotIn("locked_until", info)

    def test_login_does_not_touch_row_timestamps(self) -> None:
        """登录只写 additional_info，不刷新 ai_user 的 update_time / update_by。

        老项目登录走 ``update_user_additional_info_in_transaction``（只赋值 JSON 字段 + commit），
        ``update_time`` 仅由 ``update_user``（注册/管理/解锁/改密）刷新。这条断言是为了防止
        后续有人"顺手"在登录时刷新更新时间，从而偏离老项目行为。
        """
        before = self.get_row(self.user["uuid"])
        self.assertIsNotNone(before["update_time"], "创建用户时应写入 update_time，否则本断言无意义")
        self.login("zhangsan", USER_PASSWORD)
        after = self.get_row(self.user["uuid"])

        self.assertEqual(after["update_time"], before["update_time"])
        self.assertIsNone(after["update_by"])
        self.assertEqual(
            after["additional_info"].get("last_login_time") is not None,
            True,
            "additional_info 仍然要被写回",
        )

    def test_login_with_email(self) -> None:
        """邮箱登录：返回的 username 为真实用户名。"""
        response = self.login("zhangsan@example.com", USER_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["username"], "zhangsan")

    def test_need_update_msg_true_without_realname(self) -> None:
        self.create_user("lisi", USER_PASSWORD)
        response = self.login("lisi", USER_PASSWORD)
        self.assertTrue(response.json()["user"]["needUpdateMsg"])

    def test_username_is_case_sensitive_and_exact(self) -> None:
        response = self.login("ZhangSan", USER_PASSWORD)
        self.assert_error(self, response, 401, "用户名或邮箱无效")

    # ------------------------------------------------------------ 验证码分支
    def test_wrong_captcha_code(self) -> None:
        response = self.login("zhangsan", USER_PASSWORD, captcha_code="ZZZZ")
        self.assert_error(self, response, 401, "验证码错误")

    def test_captcha_is_single_use(self) -> None:
        """验证码校验后立即作废：即便密码正确也不能复用同一个 captchaId。"""
        captcha_id, code = self.fetch_captcha()
        wrong = self.login("zhangsan", USER_PASSWORD, captcha_id=captcha_id, captcha_code="ZZZZ")
        self.assert_error(self, wrong, 401, "验证码错误")

        replay = self.login("zhangsan", USER_PASSWORD, captcha_id=captcha_id, captcha_code=code)
        self.assert_error(self, replay, 401, "验证码已过期，请重新获取")

    def test_expired_captcha(self) -> None:
        self.app.state.captcha_cache.set("expired-id", "ABCD", ttl=-1)
        response = self.login(
            "zhangsan", USER_PASSWORD, captcha_id="expired-id", captcha_code="ABCD"
        )
        self.assert_error(self, response, 401, "验证码已过期，请重新获取")

    def test_captcha_check_precedes_password_check(self) -> None:
        """验证码错误时不消耗密码错误次数（老项目顺序：验证码在前）。"""
        self.login("zhangsan", "wrong-password", captcha_code="ZZZZ")
        info = self.get_additional_info(self.user["uuid"])
        self.assertNotIn("login_failed_count", info)

    # ------------------------------------------------------------ 请求体校验
    def test_missing_fields(self) -> None:
        for field in ("username", "password", "captchaId", "captchaCode"):
            with self.subTest(field=field):
                payload = {
                    "username": "zhangsan",
                    "password": USER_PASSWORD,
                    "captchaId": "x",
                    "captchaCode": "ABCD",
                }
                payload.pop(field)
                response = self.client.post("/aiUser/login", json=payload)
                self.assert_error(self, response, 400, f"{field}为必填字段")

    def test_non_json_body(self) -> None:
        response = self.client.post(
            "/aiUser/login", content="username=zhangsan", headers={"Content-Type": "text/plain"}
        )
        self.assert_error(self, response, 400, "请求体必须为JSON格式")

    def test_body_without_content_type(self) -> None:
        response = self.client.post("/aiUser/login", content="not-json")
        self.assert_error(self, response, 400, "请求体必须为JSON格式")

    # ------------------------------------------------------------ 账号与密码
    def test_unknown_username(self) -> None:
        response = self.login("nobody", USER_PASSWORD)
        self.assert_error(self, response, 401, "用户名或邮箱无效")

    def test_unknown_email(self) -> None:
        response = self.login("nobody@example.com", USER_PASSWORD)
        self.assert_error(self, response, 401, "用户名或邮箱无效")

    def test_wrong_password_remaining_attempts(self) -> None:
        for remaining in (4, 3, 2, 1):
            response = self.login("zhangsan", "WrongPass!1")
            self.assert_error(self, response, 401, f"密码错误，还剩{remaining}次机会")
            self.assertEqual(
                self.get_additional_info(self.user["uuid"])["login_failed_count"], 5 - remaining
            )

    def test_fifth_failure_locks_account(self) -> None:
        for _ in range(4):
            self.login("zhangsan", "WrongPass!1")

        fifth = self.login("zhangsan", "WrongPass!1")
        self.assert_error(self, fifth, 401, "连续5次密码错误，账号已锁定5分钟")

        info = self.get_additional_info(self.user["uuid"])
        self.assertEqual(info["login_failed_count"], 5)
        self.assertIn("locked_until", info)

        # 锁定期间即使密码正确也拒绝，并返回剩余分钟数提示
        locked = self.login("zhangsan", USER_PASSWORD)
        self.assertEqual(locked.status_code, 403, locked.text)
        self.assertRegex(locked.json()["error"], r"^账号已锁定，请\d+分钟后重试$")

    def test_successful_login_resets_failure_counter(self) -> None:
        self.login("zhangsan", "WrongPass!1")
        self.login("zhangsan", "WrongPass!1")
        self.assertEqual(self.get_additional_info(self.user["uuid"])["login_failed_count"], 2)

        self.assertEqual(self.login("zhangsan", USER_PASSWORD).status_code, 200)
        self.assertNotIn("login_failed_count", self.get_additional_info(self.user["uuid"]))

        # 计数器已清零：再错一次仍是「还剩4次」
        again = self.login("zhangsan", "WrongPass!1")
        self.assert_error(self, again, 401, "密码错误，还剩4次机会")

    def test_expired_lock_is_released(self) -> None:
        """locked_until 已过期：清除锁定标记，密码正确即可登录。"""
        self.patch_additional_info(
            self.user["uuid"],
            {"locked_until": self.days_ago(1), "login_failed_count": 5},
        )
        response = self.login("zhangsan", USER_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        info = self.get_additional_info(self.user["uuid"])
        self.assertNotIn("locked_until", info)
        self.assertNotIn("login_failed_count", info)

    # ------------------------------------------------------------ 30 天未登录锁定
    def test_inactive_account_is_locked_after_30_days(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_login_time": self.days_ago(31)})

        response = self.login("zhangsan", USER_PASSWORD)
        self.assert_error(
            self, response, 403, "账号已超过30天未登录，已被自动锁定，请联系管理员解锁"
        )
        self.assertEqual(
            self.get_additional_info(self.user["uuid"]).get("inactive_locked"), "1",
            "inactive_locked 标记必须落库",
        )

        # 标记存在后：走另一条提示语，且不会因为再次登录而解除
        again = self.login("zhangsan", USER_PASSWORD)
        self.assert_error(
            self, again, 403, "账号因超过30天未登录已被锁定，请联系管理员解锁"
        )

    def test_account_within_30_days_is_not_locked(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_login_time": self.days_ago(29)})
        self.assertEqual(self.login("zhangsan", USER_PASSWORD).status_code, 200)

    def test_admin_is_exempt_from_inactive_lock(self) -> None:
        admin = self.user_by_username(ADMIN_USERNAME)
        self.patch_additional_info(admin.uuid, {"last_login_time": self.days_ago(400)})
        response = self.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("inactive_locked", self.get_additional_info(admin.uuid))

    def test_inactive_lock_precedes_password_check(self) -> None:
        """未登录锁定先于密码校验：密码错误也不会累加失败次数。"""
        self.patch_additional_info(self.user["uuid"], {"last_login_time": self.days_ago(40)})
        response = self.login("zhangsan", "WrongPass!1")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertNotIn("login_failed_count", self.get_additional_info(self.user["uuid"]))

    # ------------------------------------------------------------ 密码超期提醒
    def test_password_expired_warning_for_user(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_password_change": self.days_ago(91)})
        body = self.login("zhangsan", USER_PASSWORD).json()
        self.assertTrue(body["passwordExpiredWarning"], "超过 90 天应给出提醒")

    def test_password_not_expired_within_90_days(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_password_change": self.days_ago(89)})
        body = self.login("zhangsan", USER_PASSWORD).json()
        self.assertFalse(body["passwordExpiredWarning"])

    def test_admin_password_expires_after_60_days(self) -> None:
        admin_uuid = self.user_by_username(ADMIN_USERNAME).uuid
        self.patch_additional_info(admin_uuid, {"last_password_change": self.days_ago(61)})
        body = self.login(ADMIN_USERNAME, ADMIN_PASSWORD).json()
        self.assertTrue(body["passwordExpiredWarning"], "admin 阈值是 60 天")

    def test_admin_password_not_expired_at_59_days(self) -> None:
        admin_uuid = self.user_by_username(ADMIN_USERNAME).uuid
        self.patch_additional_info(admin_uuid, {"last_password_change": self.days_ago(59)})
        body = self.login(ADMIN_USERNAME, ADMIN_PASSWORD).json()
        self.assertFalse(body["passwordExpiredWarning"])

    def test_expired_password_only_warns_and_still_logs_in(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_password_change": self.days_ago(200)})
        response = self.login("zhangsan", USER_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)

    # ------------------------------------------------------------ 默认管理员
    def test_default_admin_can_login(self) -> None:
        response = self.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["username"], ADMIN_USERNAME)

    # ------------------------------------------------------------ 软删除用户
    def test_soft_deleted_user_cannot_login(self) -> None:
        session = self.new_session()
        try:
            from app.models.user import AIUser

            user = session.query(AIUser).filter_by(username="zhangsan").one()
            user.is_del = 1
            session.commit()
        finally:
            session.close()

        response = self.login("zhangsan", USER_PASSWORD)
        self.assert_error(self, response, 401, "用户名或邮箱无效")