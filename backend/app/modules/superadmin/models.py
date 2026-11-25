import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class SignupCode(UUIDPrimaryKey, Timestamps, Base):
    """An invitation code for signing up during the beta (SIGNUP_MODE=code).

    Only a hash is stored; staff see the code once, when it's made. `hint` (its last four
    characters) helps tell codes apart in the list."""

    __tablename__ = "signup_codes"
    __table_args__ = (
        CheckConstraint("account_type IS NULL OR account_type IN ('business', 'agency')",
                        name="account_type_valid"),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name="max_uses_positive"),
    )

    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    hint: Mapped[str] = mapped_column(String(8))
    label: Mapped[str] = mapped_column(String(200))  # who it's for, e.g. "Beta wave 1"
    account_type: Mapped[str | None] = mapped_column(String(20))  # None: either
    max_uses: Mapped[int | None] = mapped_column(Integer)  # None: unlimited
    uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
