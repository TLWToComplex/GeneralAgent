"""内部接口：给前置代理（apps/proxy）查「用户 → dsh 实例」映射。

为什么做成独立接口而不是让代理直连数据库：

* 映射表结构、用户有效性判定口径（``is_del``）只由后端维护一处，代理不掌握库凭据；
* 404（未登记）/ 403（已停用）/ 404（用户不存在）三种语义分开表达，代理能给出不同提示；
* 后续加缓存、审计、限流、保活都在这里一处收口。

安全姿态：

* 会下发 dsh 容器的回环地址、端口与启动令牌文件名 —— 拿到即可触碰别人的容器，
  因此只应暴露给同机 / 内网的代理；
* 走共享密钥 ``X-Internal-Token`` + 常量时间比较；
* **未配置密钥时接口整体不启用（503）**，宁可显式失败也不默认放开（与 SSO 分支的
  501 处理同一思路）；
* 校验顺序是「密钥 → 用户有效性 → 映射存在 → 映射启用」，任何一步失败都只给
  粗粒度提示，不泄漏"某用户名是否存在且登记了实例"的组合信息。

响应契约统一为 ``{"code", "message", "data"}``（与 ``GET /captcha`` 一致）：

============================ ==================================================
GET /internal/dsh/route?username=<用户名>
GET /internal/dsh/route?uuid=<用户UUID>   两者必须且只能提供一个
---------------------------- --------------------------------------------------
200                          ``data`` 见 :func:`_serialize`
400                          参数缺失或同时提供
401                          内部接口令牌缺失 / 无效
403                          该用户的 dsh 实例已停用
404                          用户不存在或已删除 / 该用户未登记 dsh 实例
503                          未配置 ``dsh.internal_secret``，内部接口未启用
============================ ==================================================

其中 ``tokenFile`` 可为 ``null`` —— 表示由代理按「它自己的 ``TOKENS_DIR`` /
``proxyUser``」推导令牌文件路径（就是代理现在的行为），后端不假设代理的部署目录。
"""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.config import DshConfig
from app.core.errors import ApiError
from app.models.dsh_instance import AIDshInstance
from app.repositories.dsh_instance_repository import DshInstanceRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["内部接口"])

#: 前置代理携带共享密钥的请求头
INTERNAL_TOKEN_HEADER = "X-Internal-Token"


def _internal_error(message: str, status_code: int) -> ApiError:
    """内部接口错误体：与成功体同为 ``{code, message}``，便于代理统一解析。"""
    return ApiError(message, status_code, payload={"code": status_code, "message": message})


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias=INTERNAL_TOKEN_HEADER),
) -> None:
    """校验内部接口共享密钥（常量时间比较，避免时序侧信道）。"""
    expected = DshConfig.INTERNAL_SECRET
    if not expected:
        raise _internal_error(
            "内部接口未启用：请在 config/config.yaml 的 dsh.internal_secret "
            "或环境变量 DSH_INTERNAL_SECRET 配置共享密钥",
            503,
        )
    if not x_internal_token:
        raise _internal_error("内部接口令牌缺失", 401)
    if not hmac.compare_digest(x_internal_token, expected):
        raise _internal_error("内部接口令牌无效", 401)


def _serialize(username: str, user_uuid: str, instance: AIDshInstance) -> dict:
    """组装下发给代理的映射数据（camelCase，与登录响应的字段风格一致）。"""
    return {
        "username": username,
        "uuid": user_uuid,
        "containerName": instance.container_name,
        "proxyUser": instance.proxy_user,
        "host": instance.host,
        "port": instance.port,
        "target": instance.target,
        "tokenFile": instance.token_file,
        "status": instance.status,
    }


@router.get(
    "/dsh/route",
    summary="查询用户对应的 dsh 实例（供前置代理调用，需共享密钥）",
    dependencies=[Depends(require_internal_token)],
)
def get_dsh_route(
    request: Request,
    session: Session = Depends(get_session),
    username: str | None = Query(default=None, description="用户名"),
    uuid: str | None = Query(default=None, description="用户UUID，与 username 二选一"),
) -> dict:
    """按用户名或 UUID 返回该用户应被反代到的 dsh 实例。"""
    username = (username or "").strip()
    uuid = (uuid or "").strip()
    if bool(username) == bool(uuid):
        # 两个都给或两个都不给：不做「用户名优先」之类的兜底，避免调用方误解语义
        raise ApiError(
            "username与uuid必须且只能提供一个",
            400,
            payload={"code": 400, "message": "username与uuid必须且只能提供一个"},
        )

    user_repository = UserRepository(session)
    user = user_repository.get_by_username(username) if username else user_repository.get_by_uuid(uuid)
    if user is None:
        # 已软删除的用户与"不存在"同答复：软删除即视为无此用户（与登录口径一致）
        logger.info("内部查询：用户不存在或已删除（请求方 %s）", _client_ip(request))
        raise _internal_error("用户不存在或已删除", 404)

    repository = DshInstanceRepository(session)
    instance = repository.get_by_user_uuid(user.uuid)
    if instance is None:
        logger.info("内部查询：用户 %s 未登记 dsh 实例（请求方 %s）", user.username, _client_ip(request))
        raise _internal_error("该用户未登记 dsh 实例", 404)
    if not instance.enabled:
        logger.info("内部查询：用户 %s 的 dsh 实例已停用（请求方 %s）", user.username, _client_ip(request))
        raise _internal_error("该用户的 dsh 实例已停用", 403)

    # 映射表里的 username 是冗余字段，可能与 ai_user 的当前值不一致（改名后未同步）：
    # 以账号表的权威值为准回调一次，顺带暴露这种脏数据便于排查。
    if instance.username != user.username:
        logger.warning(
            "映射表用户名与账号表不一致（映射表=%s，账号表=%s），本次以账号表为准",
            instance.username,
            user.username,
        )

    logger.info("内部查询：%s -> %s（请求方 %s）", user.username, instance.target, _client_ip(request))
    return {"code": 200, "message": "success", "data": _serialize(user.username, user.uuid, instance)}


def _client_ip(request: Request) -> str:
    """取调用方 IP（仅用于日志，反代场景下取 X-Forwarded-For 首段）。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"