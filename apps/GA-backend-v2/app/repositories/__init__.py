"""数据访问层（对应老项目的 accessors）。

仓储只负责 SQL，事务提交点由 Service 层显式控制，避免「隐式提交」把
登录失败计数、锁定标记等半成品状态提前落库。
"""
from app.repositories.password_history_repository import PasswordHistoryRepository
from app.repositories.user_repository import UserRepository

__all__ = ["UserRepository", "PasswordHistoryRepository"]