import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Client(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "clients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    # active | archived
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    notes: Mapped[str | None] = mapped_column(Text)


class ClientUser(UUIDPrimaryKey, Timestamps, Base):
    """Replaced by workspace_assignments (migration 0010). Kept, unused and read-only, until a
    later migration removes it (docs/HYBRID_SAAS_PLAN.md §2)."""

    __tablename__ = "client_users"
    __table_args__ = (UniqueConstraint("client_id", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
