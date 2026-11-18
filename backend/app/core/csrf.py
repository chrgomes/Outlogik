"""Double-submit CSRF protection.

A random token is set in a readable (non-HTTP-only) cookie. Every state-changing request to
the API must echo it in a header. A cross-site attacker can make the browser send the cookie,
but cannot read it to put it in the header.
"""

import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import error_body

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
# Website forms never use the session cookie, so CSRF doesn't apply. They're protected instead
# by an Origin check, spam checks and rate limits (app.modules.leads.router).
EXEMPT_PREFIX = "/api/v1/public/"


def set_csrf_cookie(response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.csrf_cookie_name, token, httponly=False, secure=s.cookie_secure, samesite="lax",
        domain=s.cookie_domain, path="/",
    )


def install_csrf(app: FastAPI) -> None:
    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        s = get_settings()
        cookie = request.cookies.get(s.csrf_cookie_name)
        path = request.url.path
        if (request.method not in SAFE_METHODS and path.startswith("/api/")
                and not path.startswith(EXEMPT_PREFIX)):
            header = request.headers.get(s.csrf_header_name)
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                response = JSONResponse(
                    error_body("csrf_failed", "Missing or invalid CSRF token. Reload and retry."),
                    status_code=403,
                )
                if not cookie:
                    set_csrf_cookie(response, secrets.token_urlsafe(32))
                return response
        response = await call_next(request)
        if not cookie:
            set_csrf_cookie(response, secrets.token_urlsafe(32))
        return response
