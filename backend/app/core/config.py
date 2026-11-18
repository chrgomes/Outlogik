from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Outlogik"

    database_url: str = "postgresql+psycopg://outlogik:outlogik@localhost:5432/outlogik"
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:4200"
    # The public website. Its forms may post to /api/v1/public/* only from this origin
    # (plus any extra origins listed, comma-separated, e.g. a staging site).
    site_url: str = "http://localhost:4300"
    public_form_extra_origins: str = ""

    # Real visitor IP addresses (for rate limits and audit entries).
    # - CLIENT_IP_HEADER: a header the hosting platform sets to the visitor's IP and that visitors
    #   can't forge, e.g. "do-connecting-ip" on DigitalOcean App Platform. Unset in development.
    # - SITE_PROXY_SECRET: shared with the website's server, which forwards form posts and vouches
    #   for the visitor's IP with it. Requests without the secret can't set that IP.
    client_ip_header: str | None = None
    site_proxy_secret: str | None = None

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

    # Outlogik is an agency: clients are invited to their portal, nobody signs up themselves.
    signup_mode: Literal["open", "invite_only"] = "invite_only"

    # Rate limits: (max attempts, window seconds)
    rate_limit_enabled: bool = True
    rate_limit_login: tuple[int, int] = (10, 300)
    # Sign-in: only failed attempts count; a successful sign-in clears the account's count.
    # 5 failures on one account, or 20 from one IP address, within 15 minutes lock sign-in
    # for the rest of the window.
    rate_limit_login_failures_email: tuple[int, int] = (5, 900)
    rate_limit_login_failures_ip: tuple[int, int] = (20, 900)
    rate_limit_register: tuple[int, int] = (5, 3600)
    rate_limit_password_reset: tuple[int, int] = (5, 3600)
    # Website forms: at most 5 per IP address per 10 minutes, and 3 per email address per hour.
    rate_limit_public_form_ip: tuple[int, int] = (5, 600)
    rate_limit_public_form_email: tuple[int, int] = (3, 3600)

    # Website forms: anything sent faster than this after the form appeared is treated as spam.
    form_min_seconds: float = 3.0
    # The same email sending the same form again within this window adds a note to the earlier
    # lead instead of creating a new one (and emails nobody again).
    duplicate_window_hours: int = 24
    # Invisible proof-of-work on website forms (app/modules/leads/challenge.py). Its key is
    # derived from FORM_CHALLENGE_SECRET, or else SITE_PROXY_SECRET. About max_number / 2
    # SHA-256 hashes per form for the visitor's browser.
    form_challenge_required: bool = True
    # The same check on the app's sign-in, forgot-password and accept-invitation forms.
    auth_challenge_required: bool = True
    form_challenge_secret: str | None = None
    form_challenge_max_number: int = 50_000
    form_challenge_minutes: int = 10
    # Flag form submissions whose email domain can't receive email (a DNS lookup, cached).
    email_domain_check: bool = True
    newsletter_confirm_token_hours: int = 72
    # Who is emailed about new consultation requests and contact messages (comma-separated).
    # Empty means no notifications: leads are still stored and shown in the admin area.
    lead_notification_emails: str = ""

    # Email
    email_backend: Literal["smtp", "console", "memory"] = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    email_from: str = "Outlogik <no-reply@outlogik.local>"


    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Hosting platforms give "postgresql://" or "postgres://" URLs; SQLAlchemy needs the
        driver named (psycopg 3)."""
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def public_form_origins(self) -> set[str]:
        extra = {o.strip().rstrip("/") for o in self.public_form_extra_origins.split(",")}
        return {self.site_url.rstrip("/")} | {o for o in extra if o}

    @property
    def lead_notification_recipients(self) -> list[str]:
        return [e.strip() for e in self.lead_notification_emails.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
