from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Outlogik"

    database_url: str = "postgresql+psycopg://outlogik:outlogik@localhost:5432/outlogik"
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:4200"

    # Cookies
    session_cookie_name: str = "outlogik_session"
    # Names match Angular's built-in XSRF support (HttpClient withXsrfConfiguration defaults).
    csrf_cookie_name: str = "XSRF-TOKEN"
    csrf_header_name: str = "X-XSRF-TOKEN"
    cookie_secure: bool = True
    cookie_domain: str | None = None

    # Sessions
    session_idle_timeout_minutes: int = 60 * 24  # 1 day without activity
    session_absolute_lifetime_hours: int = 24 * 14  # 14 days, regardless of activity
    session_touch_interval_seconds: int = 60

    # Tokens
    password_reset_token_minutes: int = 60
    email_verification_token_hours: int = 48
    invitation_token_days: int = 7

    signup_mode: Literal["open", "invite_only"] = "open"

    # Rate limits: (max attempts, window seconds)
    rate_limit_enabled: bool = True
    rate_limit_login: tuple[int, int] = (10, 300)
    rate_limit_register: tuple[int, int] = (5, 3600)
    rate_limit_password_reset: tuple[int, int] = (5, 3600)

    # Email
    email_backend: Literal["smtp", "console", "memory"] = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    email_from: str = "Outlogik <no-reply@outlogik.local>"


@lru_cache
def get_settings() -> Settings:
    return Settings()
