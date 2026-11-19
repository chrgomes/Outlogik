import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, UUIDPrimaryKey


class WorkspaceReview(UUIDPrimaryKey, Base):
    """When someone in an organization last marked a workspace as reviewed (the agency
    dashboard's "Reviewed Nov 17"). Belongs to the reviewing organization, so an agency's
    reviews of a business's shared workspace stay the agency's."""

    __tablename__ = "workspace_reviews"
    __table_args__ = (UniqueConstraint("organization_id", "workspace_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
