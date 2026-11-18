"""Resolves the active organization for a request and checks the caller's access to it.

Every tenant-scoped route lives under /api/v1/orgs/{org_slug}/... and depends on
`require(<permission>)`. Callers who are not active members get 404, so the API never
confirms that another organization exists.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden, NotFound
from app.modules.auth.deps import AuthContext, get_auth
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.rbac.catalogue import ASSIGNED_WORKSPACES, CLIENT, PERMISSIONS
from app.modules.rbac.models import Role
from app.modules.rbac.service import role_permission_codes
from app.modules.users.models import User

ORG_NOT_FOUND = "Organization not found."


@dataclass
class OrgContext:
    org: Organization
    member: OrganizationMember
    role: Role
    user: User
    permissions: set[str] = field(default_factory=set)
    # For roles limited to assigned workspaces: the workspaces they may see, and the clients of
    # those workspaces. None = no restriction (the role sees every workspace).
    workspace_ids: set[uuid.UUID] | None = None
    client_ids: set[uuid.UUID] | None = None
    # Other organizations' workspaces this organization may work in, through an active access
    # grant: workspace id → "manage" or "view".
    linked: dict[uuid.UUID, str] = field(default_factory=dict)

    @property
    def is_client_user(self) -> bool:
        """An outside client-portal user: sees no internal notes or team details."""
        return self.role.system_key == CLIENT

    @property
    def is_restricted(self) -> bool:
        return self.workspace_ids is not None

    @property
    def is_owner(self) -> bool:
        return self.role.system_key == "owner"

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def get_org_context(
    org_slug: str = Path(max_length=64),
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
) -> OrgContext:
    row = db.execute(
        select(Organization, OrganizationMember, Role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(
            Organization.slug == org_slug.lower(),
            OrganizationMember.user_id == auth.user.id,
            OrganizationMember.status == "active",
        )
    ).first()
    if row is None:
        raise NotFound(ORG_NOT_FOUND)
    org, member, role = row
    if org.status != "active":
        raise Forbidden("This organization is suspended.", code="org_suspended")
    # Imported here: these modules import this one.
    from app.modules.grants.models import WorkspaceGrant
    from app.modules.workspaces.models import Workspace, WorkspaceAssignment

    linked = dict(db.execute(
        select(WorkspaceGrant.workspace_id, WorkspaceGrant.access).where(
            WorkspaceGrant.agency_organization_id == org.id, WorkspaceGrant.status == "active")
    ).all())
    workspace_ids = client_ids = None
    if role.workspace_scope == ASSIGNED_WORKSPACES:
        rows = db.execute(
            select(Workspace.id, Workspace.client_id)
            .join(WorkspaceAssignment, WorkspaceAssignment.workspace_id == Workspace.id)
            .where(WorkspaceAssignment.member_id == member.id,
                   (Workspace.organization_id == org.id) | Workspace.id.in_(linked))
        ).all()
        workspace_ids = {ws_id for ws_id, _ in rows}
        client_ids = {client_id for _, client_id in rows if client_id}
    return OrgContext(org=org, member=member, role=role, user=auth.user,
                      permissions=role_permission_codes(db, role.id),
                      workspace_ids=workspace_ids, client_ids=client_ids, linked=linked)


def require(permission: str) -> Callable[..., OrgContext]:
    """Dependency factory: the active org context, or 403 if the role lacks `permission`."""
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission {permission!r}")  # caught at import time

    def _dependency(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if not ctx.can(permission):
            raise Forbidden(details={"required_permission": permission})
        return ctx

    _dependency.required_permission = permission  # type: ignore[attr-defined]
    return _dependency
