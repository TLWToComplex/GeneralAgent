"""配置加载层。

保留老项目 ``src/config.py`` 的「YAML 文件 + 环境变量、环境变量优先」语义与同名键，
使 V2 的配置可以直接沿用老项目的 config.yaml / 环境变量。

加载顺序（后者优先级更高）：

1. ``config/config.yaml``（或 ``CONFIG_FILE`` 指定的文件）
2. 环境变量（含仓库根目录 / 当前工作目录的 ``.env``）
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

#: 仓库根目录（GA-backend-v2/）
REPO_ROOT = Path(__file__).resolve().parents[1]

#: 本地账号登录模式：老项目用该常量表示「不做远程 SSO 校验，只解析本地 JWT」
LOCAL_NO_AUTHZ = "LOCAL_NO_AUTHZ"


def _load_dotenv() -> None:
    """在读取配置前加载 .env（若安装了 python-dotenv）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - 未安装时退化为纯环境变量
        return
    for candidate in (REPO_ROOT / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            logger.debug("已加载环境变量文件: %s", candidate)


_load_dotenv()


class ConfigLoader:
    """YAML + 环境变量配置加载器。"""

    def __init__(self, config_file: str = "config.yaml") -> None:
        self.config_file = config_file
        self.config_data: dict[str, Any] = {}
        self.config_path: Optional[Path] = None
        self._load_config()

    def _candidate_paths(self) -> list[Path]:
        env_path = os.getenv("CONFIG_FILE")
        candidates = [Path(env_path)] if env_path else []
        candidates += [
            REPO_ROOT / "config" / self.config_file,
            REPO_ROOT / self.config_file,
            Path.cwd() / self.config_file,
            Path("/config") / self.config_file,
        ]
        return candidates

    def _load_config(self) -> None:
        for path in self._candidate_paths():
            if not path.is_file():
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.config_data = yaml.safe_load(f) or {}
                self.config_path = path
                logger.info("已加载配置文件: %s", path)
                return
            except Exception as exc:  # pragma: no cover - 配置损坏时退化到环境变量
                logger.warning("加载配置文件失败: %s，将使用环境变量", exc)
        logger.info("未找到配置文件，将使用环境变量与内置默认值")

    def get(self, key_path: str, default: Any = None, env_key: Optional[str] = None) -> Any:
        """按 ``a.b.c`` 键路径读取配置，环境变量优先于 YAML，并按 default 类型转换。"""
        if env_key and os.getenv(env_key):
            raw = os.getenv(env_key)
            if isinstance(default, bool):
                return raw.strip().lower() in ("true", "1", "yes", "on")
            if isinstance(default, int) and not isinstance(default, bool):
                try:
                    return int(raw)
                except ValueError:
                    pass
            elif isinstance(default, float):
                try:
                    return float(raw)
                except ValueError:
                    pass
            return raw

        value: Any = self.config_data
        for key in key_path.split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return default if value is None else value


#: 全局配置加载器实例
config_loader = ConfigLoader()


class ServerConfig:
    """服务器配置"""

    HOST = config_loader.get("server.host", "0.0.0.0", "HOST")
    PORT = config_loader.get("server.port", 8038, "PORT")
    RELOAD = config_loader.get("server.reload", False, "UVICORN_RELOAD")


class DatabaseConfig:
    """数据库配置"""

    URL = config_loader.get(
        "database.url",
        "mysql+pymysql://root:123456@localhost:3306/ai_service?charset=utf8mb4",
        "DATABASE_URL",
    )


class LogConfig:
    """日志配置"""

    LEVEL = str(config_loader.get("logging.level", "INFO", "LOG_LEVEL")).upper()
    SIMPLIFIED = config_loader.get("logging.simplified", True, "SIMPLIFIED_LOGGING")
    _configured = False

    @classmethod
    def setup_logging(cls, force: bool = False) -> None:
        """初始化日志。重复调用（例如测试中多次建 app）默认不重复配置。"""
        if cls._configured and not force:
            return
        level = getattr(logging, cls.LEVEL, logging.INFO)
        fmt = "%(asctime)s - %(message)s" if cls.SIMPLIFIED else (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logging.basicConfig(level=level, format=fmt, force=True)
        for noisy in ("httpx", "httpcore", "uvicorn.access", "urllib3.connection"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        cls._configured = True


class JWTConfig:
    """JWT 配置"""

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRES_SECONDS = config_loader.get(
        "jwt.access_token_expires_seconds", 3600, "JWT_ACCESS_TOKEN_EXPIRES_SECONDS"
    )

    _SECRET_KEY = config_loader.get("jwt.secret_key", "", "JWT_SECRET_KEY") or ""
    #: True 表示没有显式配置密钥，进程启动时生成一次性随机密钥（重启后旧 token 失效）
    IS_EPHEMERAL_SECRET = not _SECRET_KEY
    SECRET_KEY = _SECRET_KEY or secrets.token_urlsafe(32)


class SSOConfig:
    """SSO 配置。

    V2 只迁移了本地账号登录，因此 :data:`LOCAL_NO_AUTHZ` 之外的值会让受保护接口
    返回 501，而不是静默放过请求（避免误配置造成鉴权降级）。
    """

    URL = config_loader.get("sso.url", LOCAL_NO_AUTHZ, "SSO_URL")


class CorsConfig:
    """跨域配置"""

    ALLOW_ORIGINS = config_loader.get("cors.allow_origins", ["*"], "CORS_ALLOW_ORIGINS")
    ALLOW_CREDENTIALS = config_loader.get("cors.allow_credentials", False, "CORS_ALLOW_CREDENTIALS")


class CaptchaConfig:
    """图形验证码配置"""

    TTL_SECONDS = config_loader.get("captcha.ttl_seconds", 300, "CAPTCHA_TTL_SECONDS")
    MAX_SIZE = config_loader.get("captcha.max_size", 1000, "CAPTCHA_MAX_SIZE")
    LENGTH = config_loader.get("captcha.length", 4)
    WIDTH = config_loader.get("captcha.width", 140)
    HEIGHT = config_loader.get("captcha.height", 40)


class AuthConfig:
    """账号安全策略配置（默认值与老项目硬编码值一致）"""

    MAX_LOGIN_FAILURES = config_loader.get("auth.max_login_failures", 5, "AUTH_MAX_LOGIN_FAILURES")
    LOCK_MINUTES = config_loader.get("auth.lock_minutes", 5, "AUTH_LOCK_MINUTES")
    INACTIVE_LOCK_DAYS = config_loader.get("auth.inactive_lock_days", 30, "AUTH_INACTIVE_LOCK_DAYS")
    PASSWORD_EXPIRE_DAYS = config_loader.get(
        "auth.password_expire_days", 90, "AUTH_PASSWORD_EXPIRE_DAYS"
    )
    ADMIN_PASSWORD_EXPIRE_DAYS = config_loader.get(
        "auth.admin_password_expire_days", 60, "AUTH_ADMIN_PASSWORD_EXPIRE_DAYS"
    )
    PASSWORD_HISTORY_KEEP = config_loader.get(
        "auth.password_history_keep", 5, "AUTH_PASSWORD_HISTORY_KEEP"
    )
    ADMIN_USERNAME = "admin"


class DshConfig:
    """dsh 实例映射配置（含供前置代理调用的内部查询接口）。

    ``INTERNAL_SECRET`` 为空表示**不启用**内部接口（返回 503），而不是默认放开 ——
    该接口会下发 dsh 容器的回环地址、端口与令牌文件名，属于内网凭据级信息，
    必须显式配置密钥后才对外提供。
    """

    #: 前置代理调用内部接口时携带的共享密钥（请求头 ``X-Internal-Token``）
    INTERNAL_SECRET = config_loader.get("dsh.internal_secret", "", "DSH_INTERNAL_SECRET") or ""


class DefaultAdminConfig:
    """默认管理员账号配置"""

    ENABLED = config_loader.get("default_admin.enabled", True, "DEFAULT_ADMIN_ENABLED")
    USERNAME = config_loader.get("default_admin.username", "admin")
    PASSWORD = config_loader.get("default_admin.password", "Aa123456")
    REALNAME = config_loader.get("default_admin.realname", "管理员")
    EMAIL = config_loader.get("default_admin.email", "admin@qq.com")