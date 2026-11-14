"""Consistent error responses: {"error": {"code", "message", "details"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None,
                 status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFound(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, message: str = "Not found.", **kw: Any):
        super().__init__(message, **kw)


class Unauthorized(AppError):
    status_code = 401
    code = "not_authenticated"

    def __init__(self, message: str = "Authentication required.", **kw: Any):
        super().__init__(message, **kw)


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"

    def __init__(self, message: str = "You do not have permission to do this.", **kw: Any):
        super().__init__(message, **kw)


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class TooManyRequests(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str = "Too many attempts. Please try again later.", **kw: Any):
        super().__init__(message, **kw)


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


_HTTP_CODES = {400: "bad_request", 401: "not_authenticated", 403: "forbidden", 404: "not_found",
               405: "method_not_allowed", 409: "conflict", 429: "rate_limited"}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"Retry-After": str(exc.details["retry_after"])} if (
            isinstance(exc, TooManyRequests) and isinstance(exc.details, dict)
        ) else None
        return JSONResponse(error_body(exc.code, exc.message, exc.details),
                            status_code=exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(error_body(code, message), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(error_body("validation_error", "Some fields are invalid.", details),
                            status_code=422)
