"""用户 ↔ dsh 实例映射 ORM 模型。

字段、注释与 ``sql/003_init_dsh_instance.sql`` 一致（``tests/test_schema_parity.py``
会逐列比对 DDL 与 ORM，改这里必须同步改 DDL）。

这张表是「登录用户该被反代到哪个 dsh 容器」的唯一权威来源，替代前置代理里硬编码的
用户路由常量。与部署脚本的对应关系见 DDL 头部注释。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.user import BigIntPK

#: 状态：启用（proxy 正常转发）
STATUS_ENABLED = 1
#: 状态：停用（proxy 拒绝转发并给出明确提示；端口与容器可能仍被占用）
STATUS_DISABLED = 0


class AIDshInstance(Base):
    """用户与 dsh 实例映射表（ai_dsh_instance）。"""

    __tablename__ = "ai_dsh_instance"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True, comment="自增ID")
    user_uuid: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户UUID（对应 ai_user.uuid）"
    )
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="用户名（冗余存放，供代理按用户名直接查询）"
    )
    container_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="dsh 容器名（dsh-new.sh 的 Name 参数）"
    )
    proxy_user: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="代理用户键（dsh-new.sh 的 ProxyUser 参数，决定 tokens.d 下的令牌文件名）",
    )
    host: Mapped[str] = mapped_column(
        String(64), nullable=False, default="127.0.0.1", comment="dsh 监听地址（容器 host 网络，默认仅本机）"
    )
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="dsh 监听端口（dsh-new.sh 的 Port 参数）")
    token_file: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="启动令牌文件路径，可为空；为空时由 proxy 按 TOKENS_DIR/proxy_user 推导",
    )
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=STATUS_ENABLED, comment="状态（1：启用 0：停用）"
    )
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="备注")
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="创建时间")
    create_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="创建人")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="更新时间")
    update_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="更新人")

    @property
    def enabled(self) -> bool:
        """是否处于启用状态。"""
        return self.status == STATUS_ENABLED

    @property
    def target(self) -> str:
        """反代目标地址（与 proxy 的 ``http-proxy`` target 语义一致，带结尾斜杠）。"""
        return f"http://{self.host}:{self.port}/"

    def to_dict(self) -> dict:
        """转换为字典（下发给代理的字段名用 camelCase，见 internal_dsh 路由）。"""
        return {
            "user_uuid": self.user_uuid,
            "username": self.username,
            "container_name": self.container_name,
            "proxy_user": self.proxy_user,
            "host": self.host,
            "port": self.port,
            "token_file": self.token_file,
            "status": self.status,
            "remark": self.remark,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return (
            f"<AIDshInstance username={self.username!r} "
            f"target={self.target!r} status={self.status}>"
        )