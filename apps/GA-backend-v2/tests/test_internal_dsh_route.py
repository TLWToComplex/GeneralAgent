"""内部映射查询接口（GET /internal/dsh/route）测试。

这个接口是前置代理唯一的映射来源，失效模式会直接表现为「用户进不去工作台」，
因此错误分支（未启用 / 未授权 / 参数错 / 用户不存在 / 未登记 / 已停用）逐个覆盖。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import DshConfig
from app.models.dsh_instance import STATUS_DISABLED
from app.repositories.user_repository import UserRepository
from tests.support import USER_PASSWORD, ApiTestCase

#: 测试用内部共享密钥
INTERNAL_SECRET = "internal-test-secret"
#: 内部接口请求头名（与 app/api/routes/internal_dsh.py 保持一致）
TOKEN_HEADER = "X-Internal-Token"

ROUTE = "/internal/dsh/route"


class InternalDshRouteTest(ApiTestCase):
    """默认在「已配置密钥」的前提下运行；未配置密钥的场景单独覆盖。"""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user("zhangsan", USER_PASSWORD, realname="张三")
        self.secret_patch = patch.object(DshConfig, "INTERNAL_SECRET", INTERNAL_SECRET)
        self.secret_patch.start()
        self.addCleanup(self.secret_patch.stop)

    # ------------------------------------------------------------ 辅助
    def call(self, *, headers: bool = True, **params):
        """调用内部接口；headers=False 模拟代理漏带密钥。"""
        request_headers = {TOKEN_HEADER: INTERNAL_SECRET} if headers else {}
        return self.client.get(ROUTE, params=params, headers=request_headers)

    def soft_delete(self, user_uuid: str) -> None:
        """把用户标记为软删除（登录口径下等同"用户不存在"）。"""
        session = self.new_session()
        try:
            user = UserRepository(session).get_by_uuid(user_uuid)
            self.assertIsNotNone(user)
            user.is_del = 1
            session.commit()
        finally:
            session.close()

    # ------------------------------------------------------------ 开关与鉴权
    def test_disabled_when_secret_not_configured(self) -> None:
        """未配置密钥时接口整体不启用 —— 宁可显式失败也不默认放开。"""
        with patch.object(DshConfig, "INTERNAL_SECRET", ""):
            response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 503, response.text)
        body = response.json()
        self.assertEqual(body["code"], 503)
        self.assertIn("未启用", body["message"])

    def test_missing_token_rejected(self) -> None:
        response = self.call(headers=False, username="zhangsan")
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"code": 401, "message": "内部接口令牌缺失"})

    def test_wrong_token_rejected(self) -> None:
        response = self.client.get(
            ROUTE, params={"username": "zhangsan"}, headers={TOKEN_HEADER: "wrong"}
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"code": 401, "message": "内部接口令牌无效"})

    def test_empty_token_rejected(self) -> None:
        """空值不能当成"未携带"之外的例外：一律 401，不能落到查库分支。"""
        response = self.client.get(
            ROUTE, params={"username": "zhangsan"}, headers={TOKEN_HEADER: ""}
        )
        self.assertEqual(response.status_code, 401, response.text)

    # ------------------------------------------------------------ 参数
    def test_requires_exactly_one_identifier(self) -> None:
        response = self.call()
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(
            response.json(), {"code": 400, "message": "username与uuid必须且只能提供一个"}
        )

    def test_rejects_both_identifiers(self) -> None:
        response = self.call(username="zhangsan", uuid=self.user["uuid"])
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(
            response.json(), {"code": 400, "message": "username与uuid必须且只能提供一个"}
        )

    # ------------------------------------------------------------ 正常查询
    def test_lookup_by_username(self) -> None:
        self.create_dsh_instance("zhangsan", port=8083)
        response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assertEqual(
            body["data"],
            {
                "username": "zhangsan",
                "uuid": self.user["uuid"],
                "containerName": "dsh-web-zhangsan",
                "proxyUser": "zhangsan",
                "host": "127.0.0.1",
                "port": 8083,
                "target": "http://127.0.0.1:8083/",
                "tokenFile": None,
                "status": 1,
            },
        )

    def test_lookup_by_uuid(self) -> None:
        self.create_dsh_instance("zhangsan", port=8090)
        response = self.call(uuid=self.user["uuid"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["target"], "http://127.0.0.1:8090/")

    def test_container_and_proxy_user_may_differ_from_username(self) -> None:
        """容器名 / 令牌文件名与用户名不必相同（dsh-new.sh 允许显式指定 ProxyUser）。"""
        self.create_dsh_instance(
            "zhangsan",
            port=8084,
            container_name="dsh-web-a",
            proxy_user="a",
            token_file="/srv/dsh/tokens.d/a",
        )
        response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["containerName"], "dsh-web-a")
        self.assertEqual(data["proxyUser"], "a")
        self.assertEqual(data["tokenFile"], "/srv/dsh/tokens.d/a")
        self.assertEqual(data["target"], "http://127.0.0.1:8084/")

    def test_custom_host_reflected_in_target(self) -> None:
        """host 不是回环时同样成立（例如代理与 dsh 不在同一台机器）。"""
        self.create_dsh_instance("zhangsan", port=8085, host="10.0.0.9")
        response = self.call(username="zhangsan")
        self.assertEqual(response.json()["data"]["target"], "http://10.0.0.9:8085/")

    def test_username_padded_with_spaces_is_trimmed(self) -> None:
        self.create_dsh_instance("zhangsan")
        response = self.call(username="  zhangsan  ")
        self.assertEqual(response.status_code, 200, response.text)

    # ------------------------------------------------------------ 错误分支
    def test_unknown_user_returns_404(self) -> None:
        response = self.call(username="nobody")
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"code": 404, "message": "用户不存在或已删除"})

    def test_soft_deleted_user_returns_404(self) -> None:
        self.create_dsh_instance("zhangsan")
        self.soft_delete(self.user["uuid"])
        response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"code": 404, "message": "用户不存在或已删除"})

    def test_user_without_mapping_returns_404(self) -> None:
        response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"code": 404, "message": "该用户未登记 dsh 实例"})

    def test_disabled_mapping_returns_403(self) -> None:
        self.create_dsh_instance("zhangsan", status=STATUS_DISABLED)
        response = self.call(username="zhangsan")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json(), {"code": 403, "message": "该用户的 dsh 实例已停用"})

    def test_disabled_mapping_does_not_leak_target(self) -> None:
        """停用态不能顺带把容器地址下发出去。"""
        self.create_dsh_instance("zhangsan", port=8087, status=STATUS_DISABLED)
        response = self.call(username="zhangsan")
        self.assertNotIn("8087", response.text)

    # ------------------------------------------------------------ 用户名不一致的脏数据
    def test_mapping_username_out_of_sync_still_works(self) -> None:
        """映射表里的 username 是冗余字段，以账号表为准，不因此报错。"""
        self.create_dsh_instance("zhangsan", port=8088, proxy_user="z-old")
        session = self.new_session()
        try:
            from app.repositories.dsh_instance_repository import DshInstanceRepository

            instance = DshInstanceRepository(session).get_by_username("zhangsan")
            instance.username = "zhangsan-old"
            session.commit()
        finally:
            session.close()

        response = self.call(uuid=self.user["uuid"])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["username"], "zhangsan")


class InternalDshRouteHostNotFoundTest(ApiTestCase):
    """用户表为空 / 未建映射表时的行为（防止细节差异导致 500）。"""

    def setUp(self) -> None:
        super().setUp()
        self.secret_patch = patch.object(DshConfig, "INTERNAL_SECRET", INTERNAL_SECRET)
        self.secret_patch.start()
        self.addCleanup(self.secret_patch.stop)

    def test_unknown_uuid_returns_404(self) -> None:
        response = self.client.get(
            ROUTE, params={"uuid": "no-such-uuid"}, headers={TOKEN_HEADER: INTERNAL_SECRET}
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"code": 404, "message": "用户不存在或已删除"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()