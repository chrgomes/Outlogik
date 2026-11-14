from fastapi import Request


def client_ip(request: Request) -> str | None:
    # Behind a reverse proxy, configure uvicorn --proxy-headers / --forwarded-allow-ips
    # so request.client reflects the real client address.
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:500] if ua else None
