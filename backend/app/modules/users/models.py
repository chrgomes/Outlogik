from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey

# Outlogik staff roles (not organization roles). Super Admins have every staff permission.
# Outlogik staff (not organization roles): website admin, and the platform (Super Admin area).
PLATFORM_ROLES = ("content_editor", "site_admin", "platform_admin", "support_admin",
                  "billing_admin")


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "platform_role IS NULL OR platform_role IN ('content_editor', 'site_admin', "
            "'platform_admin', 'support_admin', 'billing_admin')",
            name="platform_role_valid",
        ),
    )

    # Stored lower-cased; uniqueness is therefore case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Access to the Outlogik admin area (website content, leads, settings). Granted by CLI.
    platform_role: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Why staff suspended the account (shown in the Super Admin area)
    suspended_reason: Mapped[str | None] = mapped_column(String(500))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Reserved for optional MFA (TOTP) in a later phase.
    mfa_secret: Mapped[str | None] = mapped_column(String(255))
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
