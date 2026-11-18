import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Permission(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(300))


class Role(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("workspace_scope IN ('all', 'assigned')", name="workspace_scope_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(300))
    # System roles (Owner, Admin, Team Member, Client) are created with every organization.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Stable identifier for system roles (see rbac/catalogue.py DEFAULT_ROLES).
    system_key: Mapped[str | None] = mapped_column(String(30))
    # "all": every workspace in the organization. "assigned": only the workspaces each member
    # is assigned to (workspace_assignments).
    workspace_scope: Mapped[str] = mapped_column(String(20), default="all", server_default="all")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
