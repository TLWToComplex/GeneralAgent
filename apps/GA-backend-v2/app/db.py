"""数据库引擎 / 会话管理。

与老项目 ``flask_sqlalchemy`` 全局 ``db`` 不同，V2 把 Engine 与 Session 工厂挂在
``app.state`` 上，由 FastAPI 依赖注入下发 Session，便于测试替换数据库。
"""
from __future__ import annotations

from typing import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def build_engine(database_url: str) -> Engine:
    """按数据库 URL 构建 Engine。

    SQLite 仅用于本地开发/测试：内存库需要 StaticPool 才能在连接之间共享数据。
    """
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """构建 Session 工厂。

    ``expire_on_commit=False`` 让接口在 commit 之后仍可安全读取对象属性
    （登录流程需要在写回 additional_info 后继续组装响应）。
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI 依赖：每请求一个 Session。"""
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()