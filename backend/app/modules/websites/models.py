import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Website(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "websites"
    # One record per normalised URL per organization.
    __table_args__ = (
        UniqueConstraint("organization_id", "url", name="uq_websites_organization_id_url"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    # Kept in step with the workspace (set for client workspaces, null for the own workspace)
    # until every reader uses workspace_id; see docs/HYBRID_SAAS_PLAN.md §2.
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2048))
    domain: Mapped[str] = mapped_column(String(253), index=True)
    # active | paused | archived
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
