"""密码历史仓储（对应老项目 ``AIPasswordHistoryAccessor``）。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_history import AIPasswordHistory

logger = logging.getLogger(__name__)


class PasswordHistoryRepository:
    """ai_password_history 表数据访问。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_record(self, user_uuid: str, password_hash: str) -> bool:
        """追加一条密码历史记录。"""
        try:
            record = AIPasswordHistory(
                user_uuid=user_uuid, password_hash=password_hash, create_time=datetime.now()
            )
            self.session.add(record)
            self.session.commit()
            logger.info("已记录密码历史，用户: %s", user_uuid)
            return True
        except Exception as exc:
            self.session.rollback()
            logger.error("记录密码历史失败: %s", exc)
            return False

    def get_recent_hashes(self, user_uuid: str, n: int = 5) -> list[str]:
        """获取最近 n 条密码哈希（按时间倒序）。"""
        try:
            stmt = (
                select(AIPasswordHistory)
                .where(AIPasswordHistory.user_uuid == user_uuid)
                .order_by(AIPasswordHistory.create_time.desc(), AIPasswordHistory.id.desc())
                .limit(n)
            )
            return [record.password_hash for record in self.session.execute(stmt).scalars().all()]
        except Exception as exc:
            logger.error("获取密码历史失败: %s", exc)
            return []

    def cleanup_old_records(self, user_uuid: str, keep: int = 5) -> bool:
        """只保留最近 keep 条历史记录。"""
        try:
            stmt = (
                select(AIPasswordHistory)
                .where(AIPasswordHistory.user_uuid == user_uuid)
                .order_by(AIPasswordHistory.create_time.desc(), AIPasswordHistory.id.desc())
            )
            records = list(self.session.execute(stmt).scalars().all())
            if len(records) <= keep:
                return True
            for record in records[keep:]:
                self.session.delete(record)
            self.session.commit()
            logger.info("已清理用户 %s 的 %s 条旧密码历史记录", user_uuid, len(records) - keep)
            return True
        except Exception as exc:
            self.session.rollback()
            logger.error("清理密码历史失败: %s", exc)
            return False

    def check_plaintext_password(self, user_uuid: str, plain_password: str, n: int = 5) -> bool:
        """判断明文密码是否命中近 n 次历史密码。"""
        from app.core.security import verify_password_hash

        for stored_hash in self.get_recent_hashes(user_uuid, n=n):
            if verify_password_hash(stored_hash, plain_password):
                return True
        return False

    def count_records(self, user_uuid: str) -> Optional[int]:
        """统计历史记录条数（测试/运维排查用）。"""
        try:
            stmt = select(AIPasswordHistory).where(AIPasswordHistory.user_uuid == user_uuid)
            return len(list(self.session.execute(stmt).scalars().all()))
        except Exception as exc:
            logger.error("统计密码历史失败: %s", exc)
            return None