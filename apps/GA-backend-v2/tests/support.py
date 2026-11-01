"""测试基础设施：内存 SQLite + 默认管理员 + 常用操作封装。

运行方式（本机已验证）：

    cd GA-backend-v2
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from typing import Optional

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.dsh_instance import STATUS_ENABLED
from app.models.user import AIUser
from app.repositories.dsh_instance_repository import DshInstanceRepository
from app.repositories.user_repository import UserRepository

#: 默认管理员账号（config/config.yaml 的 default_admin）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Aa123456"

#: 测试用普通用户密码（满足密码强度策略，但创建用户时并不强制校验）
USER_PASSWORD = "Kp!3RzT7Vm"


class ApiTestCase(unittest.TestCase):
    """接口测试基类：每个用例一个独立的内存库与应用实例。"""

    def setUp(self) -> None:
        self.app = create_app(
            database_url="sqlite+pysqlite:///:memory:",
            create_tables=True,
            ensure_admin_on_startup=True,
        )
        self.client = TestClient(self.app)
        self.client.__enter__()  # 触发 lifespan（初始化默认管理员）
        self.addCleanup(self._shutdown)

    def _shutdown(self) -> None:
        self.client.__exit__(None, None, None)

    # ------------------------------------------------------------ 数据库辅助
    def new_session(self):
        return self.app.state.session_factory()

    def create_user(
        self,
        username: str,
        password: str = USER_PASSWORD,
        *,
        email: Optional[str] = None,
        realname: Optional[str] = None,
        additional_info: Optional[dict] = None,
    ) -> dict:
        """创建用户并返回其字典表示。"""
        session = self.new_session()
        try:
            user = UserRepository(session).create_user(
                {
                    "username": username,
                    "password": password,
                    "email": email,
                    "realname": realname,
                    "additional_info": additional_info or {},
                    "platform_sort": [],
                    "preferences": {},
                    "create_by": "test",
                }
            )
            return user.to_dict()
        finally:
            session.close()

    def create_dsh_instance(
        self,
        username: str,
        *,
        port: int = 8083,
        container_name: Optional[str] = None,
        proxy_user: Optional[str] = None,
        host: str = "127.0.0.1",
        token_file: Optional[str] = None,
        status: int = STATUS_ENABLED,
        remark: Optional[str] = None,
    ) -> dict:
        """为用户登记一条 dsh 实例映射并返回其字典表示。

        默认容器名 / 代理用户键都取用户名（与 ``dsh-new.sh <Name> <Port> <ProxyUser>``
        的常见用法一致），默认端口 8083。
        """
        session = self.new_session()
        try:
            repository = UserRepository(session)
            user = repository.get_by_username(username)
            self.assertIsNotNone(user, f"用户 {username} 不存在，无法登记映射")
            instance = DshInstanceRepository(session).create(
                user_uuid=user.uuid,
                username=user.username,
                container_name=container_name or f"dsh-web-{username}",
                proxy_user=proxy_user or username,
                host=host,
                port=port,
                token_file=token_file,
                status=status,
                remark=remark,
                operator="test",
            )
            return instance.to_dict()
        finally:
            session.close()

    def get_additional_info(self, user_uuid: str) -> dict:
        """读取用户 additional_info（断言锁定标记、失败计数用）。"""
        session = self.new_session()
        try:
            user = UserRepository(session).get_by_uuid(user_uuid)
            return dict(user.additional_info or {}) if user else {}
        finally:
            session.close()

    def get_row(self, user_uuid: str) -> dict:
        """读取整行用户数据（断言 update_time / update_by 等审计字段用）。"""
        session = self.new_session()
        try:
            user = UserRepository(session).get_by_uuid(user_uuid)
            return user.to_dict() if user else {}
        finally:
            session.close()

    def patch_additional_info(self, user_uuid: str, patch: dict) -> None:
        """覆盖用户 additional_info 的部分字段（构造历史时间点用）。"""
        session = self.new_session()
        try:
            repository = UserRepository(session)
            user = repository.get_by_uuid(user_uuid)
            info = dict(user.additional_info or {})
            info.update(patch)
            self.assertTrue(repository.save_additional_info(user, info))
        finally:
            session.close()

    def user_by_username(self, username: str) -> AIUser | None:
        session = self.new_session()
        try:
            return UserRepository(session).get_by_username(username)
        finally:
            session.close()

    # ------------------------------------------------------------ 接口辅助
    def fetch_captcha(self) -> tuple[str, str]:
        """取一个验证码，返回 ``(captchaId, 答案)``（答案从服务端缓存读出）。"""
        response = self.client.get("/captcha")
        self.assertEqual(response.status_code, 200, response.text)
        captcha_id = response.json()["data"]["captchaId"]
        code = self.app.state.captcha_cache.get(captcha_id)
        self.assertTrue(code, "验证码未写入缓存")
        return captcha_id, code

    def login(
        self,
        username: str,
        password: str,
        *,
        captcha_code: Optional[str] = None,
        captcha_id: Optional[str] = None,
    ):
        """走完整登录链路（默认自动获取可用验证码）。"""
        if captcha_id is None:
            captcha_id, real_code = self.fetch_captcha()
            captcha_code = real_code if captcha_code is None else captcha_code
        return self.client.post(
            "/aiUser/login",
            json={
                "username": username,
                "password": password,
                "captchaId": captcha_id,
                "captchaCode": captcha_code,
            },
        )

    def login_and_token(self, username: str, password: str) -> str:
        response = self.login(username, password)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["token"]

    def auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------ 时间辅助
    @staticmethod
    def days_ago(days: int) -> str:
        return (datetime.now() - timedelta(days=days)).isoformat()

    @staticmethod
    def assert_error(test: unittest.TestCase, response, status_code: int, message: str) -> None:
        test.assertEqual(response.status_code, status_code, response.text)
        test.assertEqual(response.json(), {"error": message}, response.text)