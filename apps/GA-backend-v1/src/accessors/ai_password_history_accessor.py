"""
密码历史记录访问器模块。

记录每个用户的密码变更历史，用于实现"禁止复用近5次历史密码"的规则。
"""
from datetime import datetime
from werkzeug.security import check_password_hash
from src.utils.database import db
import logging

logger = logging.getLogger(__name__)


class AIPasswordHistory(db.Model):
    """密码历史记录表"""
    __tablename__ = 'ai_password_history'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    user_uuid = db.Column(db.String(50), nullable=False, comment='用户UUID')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码哈希值')
    create_time = db.Column(db.DateTime, nullable=True, comment='创建时间')

    def to_dict(self):
        """将模型对象转换为字典"""
        return {
            'id': self.id,
            'user_uuid': self.user_uuid,
            'password_hash': self.password_hash,
            'create_time': self.create_time.isoformat() if self.create_time else None,
        }


class AIPasswordHistoryAccessor:
    """密码历史记录访问器"""

    def add_record(self, user_uuid: str, password_hash: str) -> bool:
        """
        添加一条密码历史记录。

        Args:
            user_uuid: 用户UUID
            password_hash: 加密后的密码哈希值

        Returns:
            bool: 是否成功
        """
        try:
            record = AIPasswordHistory(
                user_uuid=user_uuid,
                password_hash=password_hash,
                create_time=datetime.now()
            )
            db.session.add(record)
            db.session.commit()
            logger.info(f"已记录密码历史，用户: {user_uuid}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"记录密码历史失败: {str(e)}")
            return False

    def get_recent_hashes(self, user_uuid: str, n: int = 5) -> list:
        """
        获取用户最近的 n 条密码哈希值（按时间倒序）。

        Args:
            user_uuid: 用户UUID
            n: 需要获取的最近记录数，默认5条

        Returns:
            list: 密码哈希值列表，按时间从新到旧排列
        """
        try:
            records = (
                AIPasswordHistory.query
                .filter_by(user_uuid=user_uuid)
                .order_by(AIPasswordHistory.create_time.desc())
                .limit(n)
                .all()
            )
            return [r.password_hash for r in records]
        except Exception as e:
            logger.error(f"获取密码历史失败: {str(e)}")
            return []

    def cleanup_old_records(self, user_uuid: str, keep: int = 5) -> bool:
        """
        清理用户超出保留数量的旧密码历史记录，只保留最近的 keep 条。

        Args:
            user_uuid: 用户UUID
            keep: 保留的最新记录数，默认5条

        Returns:
            bool: 是否成功
        """
        try:
            # 查询所有记录，按时间升序排列
            records = (
                AIPasswordHistory.query
                .filter_by(user_uuid=user_uuid)
                .order_by(AIPasswordHistory.create_time.desc())
                .all()
            )

            if len(records) <= keep:
                return True

            # 需要删除的旧记录（超出 keep 的部分）
            records_to_delete = records[keep:]
            for record in records_to_delete:
                db.session.delete(record)

            db.session.commit()
            logger.info(f"已清理用户 {user_uuid} 的 {len(records_to_delete)} 条旧密码历史记录")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"清理密码历史失败: {str(e)}")
            return False

    def check_history(self, user_uuid: str, new_password_hash: str) -> bool:
        """
        检查新密码哈希是否在用户的近5次历史密码中。

        Args:
            user_uuid: 用户UUID
            new_password_hash: 新密码的哈希值

        Returns:
            bool: True表示与历史密码重复，False表示未重复
        """
        recent_hashes = self.get_recent_hashes(user_uuid, n=5)
        return new_password_hash in recent_hashes

    def check_plaintext_password(self, user_uuid: str, plain_password: str) -> bool:
        """
        检查明文密码是否在用户的近5次历史密码中。
        使用 werkzeug 的 check_password_hash 逐个比对（支持加盐哈希）。

        Args:
            user_uuid: 用户UUID
            plain_password: 明文密码

        Returns:
            bool: True表示与历史密码重复（不可用），False表示未重复（可用）
        """
        recent_hashes = self.get_recent_hashes(user_uuid, n=5)
        for stored_hash in recent_hashes:
            if check_password_hash(stored_hash, plain_password):
                logger.info(f"新密码与用户 {user_uuid} 的历史密码重复")
                return True
        return False


# 全局单例
ai_password_history_accessor = AIPasswordHistoryAccessor()
