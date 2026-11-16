"""Security headers on every API response.

The API only returns JSON, so it can be strict: no framing, no MIME sniffing, no referrer,
and nothing cached (responses are per-user). Headers for the Angular app itself (CSP)
are set by the web server that serves it (frontend/docker/app/nginx.conf).
"""

from fastapi import FastAPI, Request

API_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
    # HTTPS only from now on (browsers ignore this over plain HTTP, e.g. local development).
    "Strict-Transport-Security": "max-age=31536000",
}
# The interactive API docs page loads its own script and styles, so it can't use the strict CSP.
DOCS_PATHS = {"/api/docs", "/api/docs/oauth2-redirect"}


def install_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in API_HEADERS.items():
            if name == "Content-Security-Policy" and request.url.path in DOCS_PATHS:
                continue
            response.headers.setdefault(name, value)
        return response
