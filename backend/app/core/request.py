import secrets

from fastapi import Request

from app.core.config import get_settings

SITE_PROXY_KEY_HEADER = "x-site-proxy-key"
SITE_CLIENT_IP_HEADER = "x-site-client-ip"


def client_ip(request: Request) -> str | None:
    """The visitor's IP address, for rate limits and audit entries.

    1. Requests forwarded by the website's server carry the visitor's IP, trusted only with the
       shared SITE_PROXY_SECRET (anyone could send the header without it).
    2. Behind the hosting platform, the header it sets (CLIENT_IP_HEADER).
    3. Otherwise the direct connection (development, tests).
    """
    s = get_settings()
    if s.site_proxy_secret:
        key = request.headers.get(SITE_PROXY_KEY_HEADER, "")
        forwarded = request.headers.get(SITE_CLIENT_IP_HEADER)
        if forwarded and secrets.compare_digest(key.encode(), s.site_proxy_secret.encode()):
            return forwarded.strip()[:64]
    if s.client_ip_header:
        value = request.headers.get(s.client_ip_header)
        if value:
            return value.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:500] if ua else None
