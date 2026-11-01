"""本地免 MySQL 试跑 + 联调数据预置。

    # 1) 起服务（SQLite 建库，自动建表）
    python tools/dev_sqlite_server.py --seed --port 8038

    # 2) 另开一个终端跑真实 HTTP 冒烟
    python tools/smoke_login.py --base-url http://127.0.0.1:8038

``--seed`` 会做三件**仅限本地联调**的事：

* 预置 50 个验证码（id ``demo-captcha-0..49``，答案统一 ``ABCD``），
  否则外部脚本无法得知随机验证码，无法完成登录；
* 创建一个演示普通账号 ``demo / Demo!12345``（登录功能本身不含注册接口，
  这里直接走仓储层建号，仅用于验证非管理员分支）；
* 为演示账号登记一条 dsh 实例映射（``127.0.0.1:8083``，代理用户键 ``demo``），
  供前置代理调用 ``GET /internal/dsh/route`` 联调。

另外本脚本会强制设置一个**开发用**内部接口密钥（``DSH_INTERNAL_SECRET`` 未配置时
取 ``dev-internal-secret``），否则 ``GET /internal/dsh/route`` 按设计返回 503。

生产环境请用 MySQL + ``sql/001_init_auth.sql`` + ``sql/003_init_dsh_instance.sql`` +
``run.py``，不要使用本脚本。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn  # noqa: E402

from app.config import DshConfig  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.dsh_instance import STATUS_ENABLED  # noqa: E402
from app.repositories.dsh_instance_repository import DshInstanceRepository  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402

#: 联调用固定验证码
DEV_CAPTCHA_CODE = "ABCD"
DEV_CAPTCHA_ID_PREFIX = "demo-captcha"
DEV_CAPTCHA_COUNT = 50
#: 联调用演示账号
DEV_USERNAME = "demo"
DEV_PASSWORD = "Kp!3RzT7Vm"
#: 联调用 dsh 实例映射（与 dsh-new.sh 拉起容器时的参数保持一致）
DEV_DSH_CONTAINER = "dsh-web-demo"
DEV_DSH_PROXY_USER = "demo"
DEV_DSH_PORT = 8083
#: 联调用内部接口密钥（未显式配置时使用）
DEV_INTERNAL_SECRET = "dev-internal-secret"


def _resolve_db_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _seed(app) -> None:
    """预置联调数据：固定验证码 + 演示账号 + dsh 实例映射。"""
    for index in range(DEV_CAPTCHA_COUNT):
        app.state.captcha_cache.set(
            f"{DEV_CAPTCHA_ID_PREFIX}-{index}", DEV_CAPTCHA_CODE, ttl=24 * 3600
        )

    session = app.state.session_factory()
    try:
        repository = UserRepository(session)
        user = repository.get_by_username(DEV_USERNAME)
        if user is None:
            user = repository.create_user(
                {
                    "username": DEV_USERNAME,
                    "password": DEV_PASSWORD,
                    "realname": "演示用户",
                    "email": "demo@example.com",
                    "additional_info": {},
                    "platform_sort": [],
                    "preferences": {},
                    "create_by": "dev-tool",
                }
            )
            print(f"[seed] 已创建演示账号: {DEV_USERNAME} / {DEV_PASSWORD}")
        else:
            print(f"[seed] 演示账号已存在: {DEV_USERNAME}")

        # dsh 实例映射：供前置代理调 GET /internal/dsh/route 联调。
        # 注意这里只登记映射，并不真的拉起 dsh 容器 —— 代理转发到 127.0.0.1:8083 时
        # 若本机没有 dsh 在监听，会得到代理的 502「后端服务暂时不可用」，属预期现象。
        dsh_repository = DshInstanceRepository(session)
        if dsh_repository.get_by_user_uuid(user.uuid) is None:
            dsh_repository.create(
                user_uuid=user.uuid,
                username=user.username,
                container_name=DEV_DSH_CONTAINER,
                proxy_user=DEV_DSH_PROXY_USER,
                port=DEV_DSH_PORT,
                status=STATUS_ENABLED,
                remark="dev_sqlite_server --seed 预置",
                operator="dev-tool",
            )
            print(
                f"[seed] 已登记 dsh 实例映射: {user.username} -> "
                f"http://127.0.0.1:{DEV_DSH_PORT}/ （容器 {DEV_DSH_CONTAINER}，"
                f"代理用户键 {DEV_DSH_PROXY_USER}）"
            )
        else:
            print(f"[seed] dsh 实例映射已存在: {user.username}")
    finally:
        session.close()

    print(
        f"[seed] 已预置 {DEV_CAPTCHA_COUNT} 个联调验证码: "
        f"{DEV_CAPTCHA_ID_PREFIX}-0..{DEV_CAPTCHA_COUNT - 1} / 答案 {DEV_CAPTCHA_CODE}"
    )


def _ensure_dev_internal_secret() -> None:
    """确保本地联调时内部映射接口可用。

    ``DshConfig.INTERNAL_SECRET`` 是在 ``app.config`` 导入时定型的类属性，因此这里
    直接改类属性（而不是设环境变量）—— 仅限本地联调，生产走配置文件/环境变量。
    """
    if DshConfig.INTERNAL_SECRET:
        print("[dev] 内部接口密钥取自配置（DSH_INTERNAL_SECRET / dsh.internal_secret）")
        return
    DshConfig.INTERNAL_SECRET = DEV_INTERNAL_SECRET
    print(
        f"[dev] 未配置内部接口密钥，已使用联调默认值 {DEV_INTERNAL_SECRET}；"
        f"调用示例: curl -H 'X-Internal-Token: {DEV_INTERNAL_SECRET}' "
        f"'http://127.0.0.1:8038/internal/dsh/route?username={DEV_USERNAME}'"
    )


def build_app():
    """uvicorn factory 入口（支持 --reload）。"""
    db_path = _resolve_db_path(os.getenv("DEV_SQLITE_DB", "data/dev.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_dev_internal_secret()
    app = create_app(database_url=_database_url(db_path), create_tables=True)
    if os.getenv("DEV_SQLITE_SEED") == "1":
        _seed(app)
    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="用 SQLite 本地起服务（仅开发联调）")
    parser.add_argument("--db", default="data/dev.db", help="SQLite 文件路径（相对仓库根）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认仅本机")
    parser.add_argument("--port", type=int, default=8038, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开启热重载")
    parser.add_argument(
        "--seed",
        action="store_true",
        help=(
            f"预置联调验证码、演示账号 {DEV_USERNAME}/{DEV_PASSWORD}，"
            f"以及 dsh 实例映射（127.0.0.1:{DEV_DSH_PORT}）"
        ),
    )
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DEV_SQLITE_DB"] = str(db_path)
    os.environ["DEV_SQLITE_SEED"] = "1" if args.seed else "0"

    # 先构建一次，把 SQLite 库表与种子数据真正落地（reload 子进程会重建连接）
    app = build_app()
    print(f"SQLite 数据库: {db_path}")
    print(f"服务地址: http://{args.host}:{args.port}   接口文档: /docs")
    if args.seed:
        print("注意：--seed 仅用于本地联调，生产环境请勿使用")

    uvicorn.run(
        "tools.dev_sqlite_server:build_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())