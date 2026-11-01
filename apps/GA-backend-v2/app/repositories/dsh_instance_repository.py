"""dsh 实例映射仓储（ai_dsh_instance 表数据访问）。

只暴露「按用户定位实例」这一条读路径（前置代理查询接口所需），以及写入方法供
管理侧与本地联调工具使用。当前 V2 还没有映射管理接口，登记/修改走 ``sql/`` 下的
运维语句，因此这里不提供删除能力。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dsh_instance import STATUS_ENABLED, AIDshInstance

logger = logging.getLogger(__name__)


class DshInstanceRepository:
    """ai_dsh_instance 表数据访问。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ 查询
    def get_by_user_uuid(self, user_uuid: str) -> Optional[AIDshInstance]:
        """按用户 UUID 查映射（不做状态过滤，调用方需要区分「未登记」与「已停用」）。"""
        stmt = select(AIDshInstance).where(AIDshInstance.user_uuid == user_uuid)
        return self.session.execute(stmt).scalars().first()

    def get_by_username(self, username: str) -> Optional[AIDshInstance]:
        """按用户名查映射（不做状态过滤，理由同上）。

        Note:
            ``ai_user.username`` 与 ``ai_dsh_instance.username`` 在生产库上都是
            ``utf8mb4_0900_ai_ci``（不区分大小写），因此这里按用户名等值查询在
            MySQL 上可命中不同大小写的写法，与登录接口的匹配口径一致；
            SQLite（本地测试）区分大小写，故测试只覆盖同大小写的场景。
        """
        stmt = select(AIDshInstance).where(AIDshInstance.username == username)
        return self.session.execute(stmt).scalars().first()

    def list_all(self) -> list[AIDshInstance]:
        """列出全部映射（运维巡检用）。"""
        return list(self.session.execute(select(AIDshInstance).order_by(AIDshInstance.id)).scalars())

    # ------------------------------------------------------------------ 写入
    def create(
        self,
        *,
        user_uuid: str,
        username: str,
        container_name: str,
        proxy_user: str,
        port: int,
        host: str = "127.0.0.1",
        token_file: Optional[str] = None,
        status: int = STATUS_ENABLED,
        remark: Optional[str] = None,
        operator: str = "system",
    ) -> AIDshInstance:
        """登记一条映射。

        Raises:
            ValueError: 必填字段缺失或端口越界（唯一性冲突由数据库索引兜底）。
        """
        for field, value in (
            ("user_uuid", user_uuid),
            ("username", username),
            ("container_name", container_name),
            ("proxy_user", proxy_user),
        ):
            if not value:
                raise ValueError(f"{field}不能为空")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(f"端口非法: {port}")

        now = datetime.now()
        instance = AIDshInstance(
            user_uuid=user_uuid,
            username=username,
            container_name=container_name,
            proxy_user=proxy_user,
            host=host,
            port=port,
            token_file=token_file,
            status=status,
            remark=remark,
            create_time=now,
            create_by=operator,
            update_time=now,
            update_by=operator,
        )
        self.session.add(instance)
        self.session.commit()
        return instance

    def set_status(self, username: str, status: int, *, operator: str = "system") -> bool:
        """启用/停用一个用户的映射，返回是否命中记录。"""
        instance = self.get_by_username(username)
        if instance is None:
            return False
        instance.status = status
        instance.update_time = datetime.now()
        instance.update_by = operator
        self.session.commit()
        return True