import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey

WORKSPACE_KINDS = ("own", "client")


class Workspace(UUIDPrimaryKey, Timestamps, Base):
    """Where an organization's marketing data lives.

    - "own": the organization's own marketing. Every organization has exactly one.
    - "client": one per agency client, linked by client_id.
    """

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("kind IN ('own', 'client')", name="kind_valid"),
        CheckConstraint("(kind = 'client') = (client_id IS NOT NULL)", name="client_matches_kind"),
        Index("uq_workspaces_one_own_per_organization", "organization_id", unique=True,
              postgresql_where=text("kind = 'own'")),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), unique=True
    )


class WorkspaceAssignment(UUIDPrimaryKey, Timestamps, Base):
    """Which workspaces a member sees, for members whose role is limited to assigned
    workspaces (Account Manager, Client Viewer, or a custom role with that scope)."""

    __tablename__ = "workspace_assignments"
    __table_args__ = (UniqueConstraint("member_id", "workspace_id"),)

    # The member's organization (the workspace may belong to another one, through an access
    # grant).
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_members.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
