"""启动初始化：默认管理员账号。

老项目在 ``src/core/bootstrap.py`` 里做 ``ensure_default_admin`` / ``ensure_default_group``；
用户组能力不在本次迁移范围内，因此 V2 只保留管理员账号初始化，
保证全新部署的库上「登录」功能开箱可用。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.config import DefaultAdminConfig
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def ensure_default_admin(session_factory: sessionmaker[Session]) -> bool:
    """确保默认管理员账号存在（幂等）。"""
    if not DefaultAdminConfig.ENABLED:
        logger.info("默认管理员账号初始化已关闭（default_admin.enabled=false）")
        return True

    session = session_factory()
    try:
        repository = UserRepository(session)
        existing = repository.get_by_username(DefaultAdminConfig.USERNAME)
        if existing is not None:
            logger.info("默认管理员账号已存在: %s", DefaultAdminConfig.USERNAME)
            return True

        repository.create_user(
            {
                "username": DefaultAdminConfig.USERNAME,
                "password": DefaultAdminConfig.PASSWORD,
                "realname": DefaultAdminConfig.REALNAME,
                "email": DefaultAdminConfig.EMAIL,
                "additional_info": {},
                "platform_sort": [],
                "preferences": {},
                "create_by": "system",
            }
        )
        logger.info("默认管理员账号创建成功: %s", DefaultAdminConfig.USERNAME)
        return True
    except Exception as exc:
        session.rollback()
        logger.error("初始化默认管理员账号失败: %s", exc)
        return False
    finally:
        session.close()