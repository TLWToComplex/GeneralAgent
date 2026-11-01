"""FastAPI 应用装配入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  导入以把 ORM 模型注册进 Base.metadata
from app import __version__
from app.api.routes import auth as auth_routes
from app.api.routes import internal_dsh as internal_dsh_routes
from app.config import (
    CaptchaConfig,
    CorsConfig,
    DatabaseConfig,
    JWTConfig,
    LogConfig,
)
from app.core.captcha import CaptchaGenerator
from app.core.captcha_cache import CaptchaCacheManager
from app.core.errors import register_exception_handlers
from app.db import Base, build_engine, build_session_factory
from app.services.bootstrap import ensure_default_admin

logger = logging.getLogger(__name__)

DESCRIPTION = """\
GeneralAgent V2 身份认证与实例路由服务。

当前版本包含两块能力：

1. 从老项目迁移的**用户登录**：图形验证码、本地账号登录（JWT）、修改密码
   （密码强度 + 近5次历史密码校验）、超期未登录账号解锁；
2. **dsh 实例映射查询**（`GET /internal/dsh/route`）：供前置代理按登录用户查出
   该用户应被反代到的 dsh 容器，替代代理侧硬编码的用户路由。
"""


@asynccontextmanager
async def lifespan(application: FastAPI):
    """启动/关闭钩子。"""
    if getattr(application.state, "ensure_default_admin_on_startup", True):
        if not ensure_default_admin(application.state.session_factory):
            # 初始化失败不阻断启动（数据库抖动时服务仍应可就绪），但必须显式告警：
            # 库里没有 admin 账号时登录功能实际不可用。
            logger.warning("默认管理员账号未就绪，请检查数据库连接或 default_admin 配置")
    yield
    application.state.engine.dispose()
    logger.info("数据库连接已释放")


def create_app(
    *,
    database_url: str | None = None,
    create_tables: bool = False,
    ensure_admin_on_startup: bool = True,
) -> FastAPI:
    """构建 FastAPI 应用。

    Args:
        database_url: 覆盖配置中的数据库 URL（测试用）
        create_tables: 是否用 ORM 元数据自动建表（仅本地/测试；生产用 sql/ 下 DDL）
        ensure_admin_on_startup: 启动时是否确保默认管理员存在
    """
    LogConfig.setup_logging()
    if JWTConfig.IS_EPHEMERAL_SECRET:
        logger.warning(
            "未配置 JWT_SECRET_KEY，已生成一次性随机密钥：服务重启后已签发的 token 会全部失效，"
            "生产环境请通过环境变量显式配置"
        )

    engine = build_engine(database_url or DatabaseConfig.URL)
    session_factory = build_session_factory(engine)

    application = FastAPI(
        title="GeneralAgent V2 · 身份认证与实例路由服务",
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )

    # 进程级共享资源挂在 app.state 上，由依赖注入下发，便于测试替换
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.captcha_cache = CaptchaCacheManager(
        default_ttl=CaptchaConfig.TTL_SECONDS, max_size=CaptchaConfig.MAX_SIZE
    )
    application.state.captcha_generator = CaptchaGenerator(
        length=CaptchaConfig.LENGTH, width=CaptchaConfig.WIDTH, height=CaptchaConfig.HEIGHT
    )
    application.state.ensure_default_admin_on_startup = ensure_admin_on_startup

    if create_tables:
        Base.metadata.create_all(engine)

    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CorsConfig.ALLOW_ORIGINS,
        allow_credentials=CorsConfig.ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth_routes.router)
    application.include_router(internal_dsh_routes.router)

    @application.get("/", tags=["系统"], summary="服务信息")
    def root_info() -> dict:
        return {
            "status": "running",
            "service": "GA-backend-v2",
            "version": __version__,
            "scope": "用户登录 + dsh 实例映射查询（供前置代理）",
            "endpoints": [
                "GET  /captcha",
                "POST /aiUser/login",
                "POST /aiUser/changePassword",
                "POST /aiUser/unlockAccount",
                "GET  /internal/dsh/route",
            ],
            "docs": "/docs",
        }

    @application.get("/health", tags=["系统"], summary="健康检查")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return application


app = create_app()