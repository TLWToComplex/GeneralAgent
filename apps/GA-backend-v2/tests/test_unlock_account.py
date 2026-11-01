"""解锁接口测试（POST /aiUser/unlockAccount）。"""
from __future__ import annotations

from tests.support import ADMIN_PASSWORD, ADMIN_USERNAME, USER_PASSWORD, ApiTestCase


class UnlockAccountApiTest(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user("zhangsan", USER_PASSWORD, realname="张三")
        self.admin_token = self.login_and_token(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.user_token = self.login_and_token("zhangsan", USER_PASSWORD)

    def unlock(self, *, uuid=None, token=None):
        return self.client.post(
            "/aiUser/unlockAccount",
            json={"uuid": uuid or self.user["uuid"]},
            headers=self.auth_headers(self.admin_token if token is None else token),
        )

    def lock_user_by_inactivity(self) -> None:
        """把用户构造成「超过 30 天未登录」并触发一次登录，使其被自动锁定。"""
        self.patch_additional_info(self.user["uuid"], {"last_login_time": self.days_ago(31)})
        response = self.login("zhangsan", USER_PASSWORD)
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.get_additional_info(self.user["uuid"])["inactive_locked"], "1")

    # ------------------------------------------------------------ 正常流程
    def test_unlock_locked_account(self) -> None:
        self.lock_user_by_inactivity()

        response = self.unlock()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(), {"status": "success", "message": "账号已解锁，用户可以正常登录"}
        )

        info = self.get_additional_info(self.user["uuid"])
        self.assertNotIn("inactive_locked", info, "解锁后应移除锁定标记")
        self.assertIn("last_login_time", info, "解锁时应刷新最后登录时间")

        self.assertEqual(self.login("zhangsan", USER_PASSWORD).status_code, 200)

    def test_unlock_account_that_is_not_locked(self) -> None:
        response = self.unlock()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(), {"status": "success", "message": "该账号未被锁定，无需解锁"}
        )

    def test_password_failure_lock_is_not_cleared_by_unlock(self) -> None:
        """unlockAccount 只解「30天未登录」锁定，不动密码错误锁定。"""
        for _ in range(5):
            self.login("zhangsan", "WrongPass!1")
        self.assertIn("locked_until", self.get_additional_info(self.user["uuid"]))

        response = self.unlock()
        self.assertEqual(
            response.json()["message"], "该账号未被锁定，无需解锁", response.text
        )
        self.assertIn("locked_until", self.get_additional_info(self.user["uuid"]))

    # ------------------------------------------------------------ 失败分支
    def test_unknown_uuid(self) -> None:
        response = self.unlock(uuid="00000000-0000-0000-0000-000000000000")
        self.assert_error(self, response, 404, "用户不存在")

    def test_requires_admin(self) -> None:
        """普通用户调用返回老项目 admin_required 的原响应体。"""
        response = self.unlock(token=self.user_token)
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json(), {"code": 403, "message": "权限不足，仅管理员可访问"})

    def test_requires_token(self) -> None:
        response = self.client.post("/aiUser/unlockAccount", json={"uuid": self.user["uuid"]})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"message": "Bearer令牌缺失", "code": 401})

    def test_missing_uuid(self) -> None:
        response = self.client.post(
            "/aiUser/unlockAccount", json={}, headers=self.auth_headers(self.admin_token)
        )
        self.assert_error(self, response, 400, "uuid为必填字段")