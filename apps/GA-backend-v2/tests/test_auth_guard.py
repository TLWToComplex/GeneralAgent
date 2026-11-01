"""鉴权依赖与应用装配测试。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import LOCAL_NO_AUTHZ, DshConfig, SSOConfig
from app.core.security import create_access_token, decode_access_token, extract_username
from tests.support import ADMIN_PASSWORD, ADMIN_USERNAME, USER_PASSWORD, ApiTestCase


class TokenTest(unittest.TestCase):
    def test_token_contains_expected_claims(self) -> None:
        token = create_access_token(username="zhangsan", user_id=7)
        payload = decode_access_token(token)
        self.assertEqual(payload["username"], "zhangsan")
        self.assertEqual(payload["identity"]["username"], "zhangsan")
        self.assertEqual(payload["identity"]["user_id"], 7)
        self.assertNotIn("sub", payload, "PyJWT 2.10 起 sub 必须是字符串，因此不写入 sub")
        self.assertIn("exp", payload)
        self.assertIn("jti", payload)

    def test_extract_username_fallbacks(self) -> None:
        self.assertEqual(extract_username({"username": "a"}), "a")
        self.assertEqual(extract_username({"identity": {"username": "b"}}), "b")
        self.assertEqual(extract_username({"identity": {"user": "c"}}), "c")
        self.assertEqual(extract_username({"identity": "d"}), "d")
        self.assertEqual(extract_username({"sub": "e"}), "e")
        self.assertEqual(extract_username({"user": "f"}), "f")
        self.assertIsNone(extract_username({"other": "x"}))


class AuthDependencyTest(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user("zhangsan", USER_PASSWORD)
        self.token = self.login_and_token("zhangsan", USER_PASSWORD)

    def test_valid_token_accepted(self) -> None:
        response = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": "Kp!9ZzQ2Wn"},
            headers=self.auth_headers(self.token),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_expired_token_rejected(self) -> None:
        with patch("app.core.security.JWTConfig.ACCESS_TOKEN_EXPIRES_SECONDS", -1):
            expired = create_access_token(username="zhangsan")
        response = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": "Kp!9ZzQ2Wn"},
            headers=self.auth_headers(expired),
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"message": "Bearer令牌无效", "code": 401})

    def test_token_signed_with_other_secret_rejected(self) -> None:
        import jwt

        forged = jwt.encode({"username": "zhangsan"}, "another-secret", algorithm="HS256")
        response = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": "Kp!9ZzQ2Wn"},
            headers=self.auth_headers(forged),
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_non_bearer_scheme_rejected(self) -> None:
        response = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": "Kp!9ZzQ2Wn"},
            headers={"Authorization": f"Basic {self.token}"},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_remote_sso_config_fails_loudly(self) -> None:
        """配置了远程 SSO 时显式 501，绝不静默降级为本地解析。"""
        with patch.object(SSOConfig, "URL", "http://sso.example.com/api/validate"):
            response = self.client.post(
                "/aiUser/changePassword",
                json={"uuid": self.user["uuid"], "old_password": USER_PASSWORD, "new_password": "Kp!9ZzQ2Wn"},
                headers=self.auth_headers(self.token),
            )
        self.assertEqual(response.status_code, 501, response.text)
        self.assertIn("远程 SSO", response.json()["error"])

    def test_default_config_is_local_mode(self) -> None:
        self.assertEqual(SSOConfig.URL, LOCAL_NO_AUTHZ)


class AppWiringTest(ApiTestCase):
    def test_root_info(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["service"], "GA-backend-v2")
        self.assertIn("POST /aiUser/login", body["endpoints"])

    def test_health(self) -> None:
        self.assertEqual(self.client.get("/health").json()["status"], "ok")

    def test_openapi_exposes_migrated_endpoints(self) -> None:
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertEqual(
            sorted(paths),
            [
                "/",
                "/aiUser/changePassword",
                "/aiUser/login",
                "/aiUser/unlockAccount",
                "/captcha",
                "/health",
                "/internal/dsh/route",
            ],
            "除系统信息与健康检查外，只应暴露登录接口与供前置代理调用的内部映射接口",
        )
        self.assertEqual(sorted(paths["/aiUser/login"]), ["post"])
        self.assertEqual(sorted(paths["/captcha"]), ["get"])
        self.assertEqual(sorted(paths["/internal/dsh/route"]), ["get"])

    def test_root_info_lists_internal_route(self) -> None:
        """内部接口要出现在服务自述里，便于运维确认部署的是哪一版。"""
        body = self.client.get("/").json()
        self.assertIn("GET  /internal/dsh/route", body["endpoints"])

    def test_internal_route_requires_secret_by_default(self) -> None:
        """默认配置（未设 dsh.internal_secret）下，内部接口必须不可用。

        这条是装配层的兜底断言：接口存在但在默认配置下返回 503，
        避免「新加的接口忘了加鉴权开关」这类回归。
        显式把密钥清空再断言，避免本机 .env 里配了密钥导致用例结果随环境漂移。
        """
        with patch.object(DshConfig, "INTERNAL_SECRET", ""):
            response = self.client.get("/internal/dsh/route", params={"username": "admin"})
        self.assertEqual(response.status_code, 503, response.text)

    def test_unknown_route_returns_404(self) -> None:
        self.assertEqual(self.client.get("/aiAgent/list").status_code, 404)


class BootstrapTest(ApiTestCase):
    def test_default_admin_created_once(self) -> None:
        from app.services.bootstrap import ensure_default_admin

        session = self.new_session()
        try:
            from app.repositories.user_repository import UserRepository

            self.assertIsNotNone(UserRepository(session).get_by_username(ADMIN_USERNAME))
        finally:
            session.close()

        # 再跑一次初始化不应报错也不应重复创建
        self.assertTrue(ensure_default_admin(self.app.state.session_factory))
        self.assertTrue(ensure_default_admin(self.app.state.session_factory))
        self.assertEqual(self.login(ADMIN_USERNAME, ADMIN_PASSWORD).status_code, 200)

    def test_default_admin_password_is_hashed(self) -> None:
        session = self.new_session()
        try:
            from app.repositories.user_repository import UserRepository

            admin = UserRepository(session).get_by_username(ADMIN_USERNAME)
            self.assertNotEqual(admin.password, ADMIN_PASSWORD)
            self.assertTrue(admin.password.startswith("scrypt:") or admin.password.startswith("pbkdf2:"))
            self.assertEqual(admin.realname, "管理员")
            self.assertEqual(admin.email, "admin@qq.com")
            self.assertIn("last_password_change", admin.additional_info)
        finally:
            session.close()

    def test_legacy_werkzeug_hashes_still_verify(self) -> None:
        """复用老库数据的前提：历史 Werkzeug 哈希（pbkdf2 等）仍可校验通过。

        老项目 `ai_user.password` 里可能是 `pbkdf2:sha256:...`（老版本 Werkzeug 默认），
        这里直接写入这种格式的哈希并走真实 HTTP 登录，确认不需要重置密码即可迁移。
        """
        from werkzeug.security import generate_password_hash

        from app.repositories.user_repository import UserRepository

        legacy_hash = generate_password_hash(USER_PASSWORD, method="pbkdf2:sha256", salt_length=8)
        self.assertTrue(legacy_hash.startswith("pbkdf2:sha256:"))

        session = self.new_session()
        try:
            repository = UserRepository(session)
            user = repository.create_user(
                {"username": "legacy", "password": "placeholder-not-used", "realname": "老用户"}
            )
            user.password = legacy_hash  # 模拟历史数据
            session.commit()
            uuid = user.uuid
        finally:
            session.close()

        response = self.login("legacy", USER_PASSWORD)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["uuid"], uuid)

        # 旧哈希登录后不应被"顺手"重写
        session = self.new_session()
        try:
            self.assertEqual(UserRepository(session).get_by_username("legacy").password, legacy_hash)
        finally:
            session.close()

    def test_null_password_field_is_rejected_as_bad_request(self) -> None:
        """字段存在但为 null：V2 返回 400（老项目会走到服务层算作一次密码失败 → 401）。

        这是有意收敛：畸形请求不应被计入登录失败次数。详见 README「与老项目的差异」。
        """
        captcha_id, captcha_code = self.fetch_captcha()
        response = self.client.post(
            "/aiUser/login",
            json={
                "username": "admin",
                "password": None,
                "captchaId": captcha_id,
                "captchaCode": captcha_code,
            },
        )
        self.assert_error(self, response, 400, "password格式不正确")

        # 关键：这次畸形请求不能消耗失败次数
        info = self.get_additional_info(
            self.user_by_username(ADMIN_USERNAME).uuid
        )
        self.assertNotIn("login_failed_count", info)

    def test_admin_can_be_disabled(self) -> None:
        from app.main import create_app
        from app.repositories.user_repository import UserRepository

        app = create_app(
            database_url="sqlite+pysqlite:///:memory:",
            create_tables=True,
            ensure_admin_on_startup=False,
        )
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            session = app.state.session_factory()
            try:
                self.assertIsNone(UserRepository(session).get_by_username(ADMIN_USERNAME))
            finally:
                session.close()
            self.assertEqual(client.get("/health").status_code, 200)