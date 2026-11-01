"""用户表 ORM 模型。

字段、注释与 ``sql/001_init_auth.sql`` 一致，对应老项目
``src/accessors/ai_user_accessor.py`` 中的 ``AIUser``。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

#: BigInteger 主键在 SQLite 下不会自增，用 Integer 变体保持本地测试可用
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class AIUser(Base):
    """用户管理表（ai_user）。"""

    __tablename__ = "ai_user"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="自增ID")
    uuid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="唯一ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="邮箱")
    realname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="真实姓名")
    contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="联系方式")
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="家庭住址")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    additional_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="扩展字段")
    platform_sort: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True, comment="模型平台排序")
    preferences: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True, comment="用户偏好")
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="创建时间")
    create_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="创建人")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="更新时间")
    update_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="更新人")
    is_del: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="是否删除（0：未删除 1：已删除）")

    def to_dict(self) -> dict:
        """转换为字典（与老项目一致：不包含 password 字段）。"""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "username": self.username,
            "email": self.email,
            "realname": self.realname,
            "contact": self.contact,
            "address": self.address,
            "additional_info": self.additional_info,
            "platform_sort": self.platform_sort,
            "preferences": self.preferences,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "create_by": self.create_by,
            "update_time": self.update_time.isoformat() if self.update_time else None,
            "update_by": self.update_by,
            "is_del": self.is_del,
        }

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<AIUser id={self.id} username={self.username!r}>"