"""修改密码接口测试（POST /aiUser/changePassword）。"""
from __future__ import annotations

from app.repositories.password_history_repository import PasswordHistoryRepository
from tests.support import USER_PASSWORD, ApiTestCase

NEW_PASSWORD = "Kp!9ZzQ2Wn"


class ChangePasswordApiTest(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user("zhangsan", USER_PASSWORD, realname="张三")
        self.token = self.login_and_token("zhangsan", USER_PASSWORD)

    def change(self, *, uuid=None, old=USER_PASSWORD, new=NEW_PASSWORD, token=None):
        return self.client.post(
            "/aiUser/changePassword",
            json={
                "uuid": uuid or self.user["uuid"],
                "old_password": old,
                "new_password": new,
            },
            headers=self.auth_headers(self.token if token is None else token),
        )

    def history_count(self) -> int:
        session = self.new_session()
        try:
            return PasswordHistoryRepository(session).count_records(self.user["uuid"])
        finally:
            session.close()

    # ------------------------------------------------------------ 正常流程
    def test_change_password_success(self) -> None:
        response = self.change()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"status": "success", "message": "密码更新成功"})

        # 新密码可登录，旧密码失效
        self.assertEqual(self.login("zhangsan", NEW_PASSWORD).status_code, 200)
        old = self.login("zhangsan", USER_PASSWORD)
        self.assert_error(self, old, 401, "密码错误，还剩4次机会")

    def test_password_history_recorded(self) -> None:
        self.assertEqual(self.history_count(), 0)
        self.change()
        self.assertEqual(self.history_count(), 1, "改密后应写入一条历史密码")

    def test_last_password_change_refreshed(self) -> None:
        self.patch_additional_info(self.user["uuid"], {"last_password_change": self.days_ago(120)})
        self.change()
        self.assertIn("last_password_change", self.get_additional_info(self.user["uuid"]))

        # 超期提醒随之消失
        body = self.login("zhangsan", NEW_PASSWORD).json()
        self.assertFalse(body["passwordExpiredWarning"])

    def test_cannot_reuse_recent_password(self) -> None:
        """改密两次后，再用回第一次的新密码应被拒绝（近 5 次历史密码）。"""
        second = "Kp!2YyW8Qr"
        self.assertEqual(self.change(new=NEW_PASSWORD).status_code, 200)
        self.assertEqual(self.change(old=NEW_PASSWORD, new=second).status_code, 200)

        again = self.change(old=second, new=NEW_PASSWORD)
        self.assert_error(self, again, 400, "密码不能与近5次历史密码相同")

    def test_initial_password_is_not_in_history(self) -> None:
        """老项目口径：创建用户时不写历史，因此初始密码可以再改回来一次。"""
        self.assertEqual(self.change(new=NEW_PASSWORD).status_code, 200)
        self.assertEqual(self.change(old=NEW_PASSWORD, new=USER_PASSWORD).status_code, 200)

    def test_history_keeps_only_five_records(self) -> None:
        """连续改密 6 次，历史表只保留最近 5 条。"""
        passwords = [
            "Kp!3RzT7Vm", "Kp!4RzT7Vm", "Kp!5RzT7Vm",
            "Kp!6RzT7Vm", "Kp!7RzT7Vm", "Kp!8RzT7Vm",
        ]
        current = USER_PASSWORD
        for candidate in passwords:
            response = self.change(old=current, new=candidate)
            self.assertEqual(response.status_code, 200, response.text)
            current = candidate
        self.assertEqual(self.history_count(), 5)

    # ------------------------------------------------------------ 失败分支
    def test_wrong_old_password(self) -> None:
        response = self.change(old="WrongPass!1")
        self.assert_error(self, response, 401, "旧密码不正确")

    def test_unknown_uuid(self) -> None:
        response = self.change(uuid="00000000-0000-0000-0000-000000000000")
        self.assert_error(self, response, 404, "用户不存在")

    def test_weak_new_passwords(self) -> None:
        cases = {
            "Kp!3RzT7V": "密码长度不能少于10位",
            "kp!3rzt7vm": "密码必须包含至少一个大写字母",
            "KP!3RZT7VM": "密码必须包含至少一个小写字母",
            "Kp!xRzTvVm": "密码必须包含至少一个数字",
            "Kp13RzT7Vm": "密码必须包含至少一个特殊符号（如 !@# 等）",
            "Kp!3Zhangsan1": "密码不能包含用户名",
        }
        for password, message in cases.items():
            with self.subTest(password=password):
                response = self.change(new=password)
                self.assert_error(self, response, 400, message)

    def test_password_unchanged_after_validation_failure(self) -> None:
        self.change(new="short")
        self.assertEqual(self.login("zhangsan", USER_PASSWORD).status_code, 200)

    def test_missing_fields(self) -> None:
        for field in ("uuid", "old_password", "new_password"):
            with self.subTest(field=field):
                payload = {
                    "uuid": self.user["uuid"],
                    "old_password": USER_PASSWORD,
                    "new_password": NEW_PASSWORD,
                }
                payload.pop(field)
                response = self.client.post(
                    "/aiUser/changePassword",
                    json=payload,
                    headers=self.auth_headers(self.token),
                )
                self.assert_error(self, response, 400, f"{field}为必填字段")

    # ------------------------------------------------------------ 鉴权
    def test_requires_token(self) -> None:
        response = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"message": "Bearer令牌缺失", "code": 401})

    def test_rejects_invalid_token(self) -> None:
        response = self.change(token="this-is-not-a-jwt")
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"message": "Bearer令牌无效", "code": 401})

    def test_non_admin_can_change_own_password(self) -> None:
        """改密不限制 admin（与老项目一致）。"""
        self.assertEqual(self.change().status_code, 200)

    def test_login_token_grants_access_to_protected_endpoint(self) -> None:
        token = self.login_and_token("zhangsan", USER_PASSWORD)
        response = self.change(old=USER_PASSWORD, new="Kp!2YyW8Qr", token=token)
        self.assertEqual(response.status_code, 200, response.text)