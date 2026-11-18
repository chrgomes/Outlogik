import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class WorkspaceGrant(UUIDPrimaryKey, Timestamps, Base):
    """A business lets an agency work in its own workspace, without copying any data.

    Lifecycle: pending (emailed to someone at the agency) → active (accepted into an agency
    organization) → revoked (by either side). Expired pending grants simply stop working.
    """

    __tablename__ = "workspace_grants"
    __table_args__ = (
        CheckConstraint("access IN ('manage', 'view')", name="access_valid"),
        CheckConstraint("status IN ('pending', 'active', 'revoked')", name="status_valid"),
        CheckConstraint("(status = 'active') = (agency_organization_id IS NOT NULL "
                        "AND accepted_at IS NOT NULL AND revoked_at IS NULL)",
                        name="active_is_accepted"),
        Index("uq_workspace_grants_one_active_per_agency", "workspace_id",
              "agency_organization_id", unique=True, postgresql_where=text("status = 'active'")),
    )

    # The business that owns the workspace
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    # Set when accepted
    agency_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # manage: the agency's own roles apply. view: read-only.
    access: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    # Who at the agency it was sent to; only that account can accept it.
    email: Mapped[str] = mapped_column(String(320))
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
