"""Resolves the active organization for a request and checks the caller's access to it.

Every tenant-scoped route lives under /api/v1/orgs/{org_slug}/... and depends on
`require(<permission>)`. Callers who are not active members get 404, so the API never
confirms that another organization exists.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden, NotFound
from app.modules.auth.deps import AuthContext, get_auth
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.rbac.catalogue import PERMISSIONS
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
    return OrgContext(org=org, member=member, role=role, user=auth.user,
                      permissions=role_permission_codes(db, role.id))


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
