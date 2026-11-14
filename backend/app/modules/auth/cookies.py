from fastapi import Response

from app.core.config import get_settings


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie_name, token, httponly=True, secure=s.cookie_secure, samesite="lax",
        domain=s.cookie_domain, path="/", max_age=s.session_absolute_lifetime_hours * 3600,
    )


def clear_session_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.session_cookie_name, path="/", domain=s.cookie_domain,
                           secure=s.cookie_secure, httponly=True, samesite="lax")
