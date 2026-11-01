"""密码历史记录 ORM 模型。

对应老项目 ``src/accessors/ai_password_history_accessor.py`` 中的 ``AIPasswordHistory``。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.user import BigIntPK


class AIPasswordHistory(Base):
    """密码历史记录表（ai_password_history）。"""

    __tablename__ = "ai_password_history"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="自增ID")
    user_uuid: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="用户UUID")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希值")
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="创建时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_uuid": self.user_uuid,
            "password_hash": self.password_hash,
            "create_time": self.create_time.isoformat() if self.create_time else None,
        }