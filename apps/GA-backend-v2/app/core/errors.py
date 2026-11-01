"""统一异常与响应契约。

老项目的错误响应是 ``{"error": <message>}``（HTTP 状态码随业务语义），
``admin_required`` 例外地返回 ``{"code": 403, "message": "..."}``。
V2 用 :class:`ApiError` 承载这两种形态，并在异常处理器里原样输出，
保证前端不需要改动解析逻辑。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """业务异常：``payload`` 默认为 ``{"error": message}``。"""

    def __init__(self, message: str, status_code: int = 400, payload: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload if payload is not None else {"error": message}


def _validation_message(exc: RequestValidationError) -> str:
    """把 pydantic 校验错误翻译成老项目风格的提示语。"""
    errors = exc.errors()
    if not errors:
        return "请求体必须为JSON格式"

    first = errors[0]
    error_type = first.get("type", "")
    loc = [part for part in first.get("loc", ()) if part != "body"]

    # 非 JSON 请求体 / 请求体不是 JSON 对象 / 缺少请求体：
    # 老项目统一返回「请求体必须为JSON格式」
    if error_type in ("json_invalid", "model_attributes_type") or not loc:
        return "请求体必须为JSON格式"

    field = loc[-1]
    if error_type == "missing":
        return f"{field}为必填字段"
    return f"{field}格式不正确"


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("业务异常(%s): %s", exc.status_code, exc.message)
        else:
            logger.info("业务异常(%s): %s", exc.status_code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.payload)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        message = _validation_message(exc)
        logger.info("请求参数校验失败: %s", message)
        return JSONResponse(status_code=400, content={"error": message})

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("未预期的服务器异常: %s", exc)
        return JSONResponse(status_code=500, content={"error": "服务器内部错误"})