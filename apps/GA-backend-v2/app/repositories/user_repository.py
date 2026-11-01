"""用户仓储（对应老项目 ``AIUser`` accessor 的读/写方法）。"""
from __future__ import annotations

import logging
import uuid as uuid_lib
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password_hash
from app.models.user import AIUser

logger = logging.getLogger(__name__)


class UserRepository:
    """ai_user 表数据访问。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ 查询
    def _supports_row_lock(self) -> bool:
        """SQLite 不支持 SELECT ... FOR UPDATE，本地测试时自动降级。"""
        try:
            return self.session.get_bind().dialect.name != "sqlite"
        except Exception:  # pragma: no cover - 绑定异常时按不支持处理
            return False

    def find_by_login(self, username_or_email: str, for_update: bool = False) -> Optional[AIUser]:
        """按用户名或邮箱（含 ``@`` 视为邮箱）查询未删除用户。

        Args:
            username_or_email: 用户名或邮箱
            for_update: 是否加行锁，用于防止并发登录竞态
        """
        stmt = select(AIUser).where(AIUser.is_del == 0)
        if "@" in username_or_email:
            stmt = stmt.where(AIUser.email == username_or_email)
        else:
            stmt = stmt.where(AIUser.username == username_or_email)
        if for_update and self._supports_row_lock():
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalars().first()

    def get_by_uuid(self, user_uuid: str) -> Optional[AIUser]:
        stmt = select(AIUser).where(AIUser.uuid == user_uuid, AIUser.is_del == 0)
        return self.session.execute(stmt).scalars().first()

    def get_by_username(self, username: str) -> Optional[AIUser]:
        stmt = select(AIUser).where(AIUser.username == username, AIUser.is_del == 0)
        return self.session.execute(stmt).scalars().first()

    def verify_password(self, username: str, password: str) -> bool:
        """按用户名校验明文密码。"""
        user = self.get_by_username(username)
        if user is None:
            return False
        return verify_password_hash(user.password, password)

    # ------------------------------------------------------------------ 写入
    def save_additional_info(self, user: AIUser, additional_info: dict) -> bool:
        """写回 ``additional_info`` 并提交。

        传入的字典必须是**新的**字典对象（Service 层读取时会 ``dict(...)`` 复制），
        否则 SQLAlchemy 不会把 JSON 字段标记为脏数据。已实测（SQLAlchemy 2.0.44 /
        SQLite）：原地修改原字典、或原地修改后再把同一个对象赋值回去，提交后都不会
        落库；只有赋值一个内容不同的新字典才会生成 UPDATE。
        """
        try:
            user.additional_info = additional_info
            self.session.commit()
            return True
        except Exception as exc:
            self.session.rollback()
            logger.error("更新用户 additional_info 失败: %s", exc)
            return False

    def create_user(self, user_data: dict) -> AIUser:
        """创建用户（登录功能的配套能力：默认管理员初始化使用）。

        Raises:
            ValueError: 必填字段缺失、additional_info 类型非法或用户名已存在。

        Note:
            老项目在「用户名属于软删除记录」时会先删关联用户组再硬删除重建；
            用户组能力不在本次迁移范围内，V2 统一按「用户名已存在」处理。
        """
        data = dict(user_data)
        for field in ("username", "password"):
            if not data.get(field):
                raise ValueError(f"{field}为必填字段")

        additional_info = data.get("additional_info") or {}
        if not isinstance(additional_info, dict):
            raise ValueError("additional_info必须是字典类型")

        existing = self.session.execute(
            select(AIUser).where(AIUser.username == data["username"])
        ).scalars().first()
        if existing is not None:
            raise ValueError(f"用户名 {data['username']} 已存在")

        now = datetime.now()
        data.setdefault("uuid", str(uuid_lib.uuid4()))
        data.setdefault("create_time", now)
        data.setdefault("update_time", now)
        data.setdefault("is_del", 0)
        data.setdefault("platform_sort", [])
        data.setdefault("preferences", {})
        additional_info["last_password_change"] = now.isoformat()
        data["additional_info"] = additional_info
        data["password"] = hash_password(data["password"])

        user = AIUser(**data)
        self.session.add(user)
        self.session.commit()
        return user