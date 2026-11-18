"""Custom roles. System roles (Owner, Admin, Team Member, Client) are read-only."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, Conflict
from app.core.pagination import PageParams, paginate
from app.modules.audit.service import record
from app.modules.organizations.models import Invitation, OrganizationMember
from app.modules.rbac.catalogue import PERMISSIONS
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import RoleOut
from app.modules.rbac.service import permission_codes_by_role, set_role_permissions
from app.tenancy.context import OrgContext
from app.tenancy.scoped import get_scoped


def _validate_codes(codes: list[str]) -> set[str]:
    unknown = sorted(set(codes) - set(PERMISSIONS))
    if unknown:
        raise AppError("Unknown permissions.", code="validation_error", status_code=422,
                       details=[{"field": "permissions", "message": f"Unknown: {c}"}
                                for c in unknown])
    return set(codes)


def _out(role: Role, perms: set[str], count: int) -> RoleOut:
    return RoleOut(id=role.id, name=role.name, description=role.description,
                   is_system=role.is_system, system_key=role.system_key,
                   workspace_scope=role.workspace_scope, permissions=sorted(perms),
                   member_count=count, created_at=role.created_at)


def _counts(db: Session, role_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = db.execute(select(OrganizationMember.role_id, func.count())
                      .where(OrganizationMember.role_id.in_(role_ids))
                      .group_by(OrganizationMember.role_id))
    return dict(rows.all())


def to_out(db: Session, role: Role) -> RoleOut:
    return _out(role, permission_codes_by_role(db, [role.id])[role.id],
                _counts(db, [role.id]).get(role.id, 0))


def list_roles(db: Session, ctx: OrgContext, params: PageParams) -> tuple[list[RoleOut], int]:
    stmt = (select(Role).where(Role.organization_id == ctx.org.id)
            .order_by(Role.is_system.desc(), Role.created_at, Role.name))
    rows, total = paginate(db, stmt, params)
    roles = [r for (r,) in rows]
    ids = [r.id for r in roles]
    perms, counts = permission_codes_by_role(db, ids), _counts(db, ids)
    return [_out(r, perms[r.id], counts.get(r.id, 0)) for r in roles], total


def _ensure_name_free(db: Session, ctx: OrgContext, name: str,
                      exclude: uuid.UUID | None = None) -> None:
    stmt = select(Role.id).where(Role.organization_id == ctx.org.id,
                                 func.lower(Role.name) == name.lower())
    if exclude:
        stmt = stmt.where(Role.id != exclude)
    if db.scalar(stmt):
        raise Conflict("A role with this name already exists.", code="role_name_taken")


def _load_custom(db: Session, ctx: OrgContext, role_id: uuid.UUID) -> Role:
    role = get_scoped(db, Role, role_id, ctx, label="Role", for_update=True)
    if role.is_system:
        raise Conflict("Built-in roles can't be changed. Create a custom role instead.",
                       code="system_role")
    return role


def create_role(db: Session, ctx: OrgContext, *, name: str, description: str | None,
                permissions: list[str], ip: str | None,
                workspace_scope: str = "all") -> RoleOut:
    codes = _validate_codes(permissions)
    _ensure_name_free(db, ctx, name)
    role = Role(organization_id=ctx.org.id, name=name, description=description or None,
                workspace_scope=workspace_scope)
    db.add(role)
    db.flush()
    set_role_permissions(db, role, codes)
    record(db, "role.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="role", target_id=role.id,
           meta={"name": name, "permissions": sorted(codes), "workspace_scope": workspace_scope},
           ip=ip)
    db.commit()
    return to_out(db, role)


def update_role(db: Session, ctx: OrgContext, role_id: uuid.UUID, *, name: str | None,
                description: str | None, permissions: list[str] | None,
                ip: str | None, workspace_scope: str | None = None) -> RoleOut:
    role = _load_custom(db, ctx, role_id)
    changes: dict = {}
    if workspace_scope is not None and workspace_scope != role.workspace_scope:
        # Members' assignments are kept: switching back to "assigned" restores them.
        changes["workspace_scope"] = {"from": role.workspace_scope, "to": workspace_scope}
        role.workspace_scope = workspace_scope
    if name is not None and name != role.name:
        _ensure_name_free(db, ctx, name, exclude=role.id)
        changes["name"] = {"from": role.name, "to": name}
        role.name = name
    if description is not None and (description or None) != role.description:
        role.description = description or None
        changes["description"] = True
    if permissions is not None:
        new = _validate_codes(permissions)
        old = permission_codes_by_role(db, [role.id])[role.id]
        if new != old:
            set_role_permissions(db, role, new)
            changes["permissions"] = {"added": sorted(new - old), "removed": sorted(old - new)}
    if changes:
        record(db, "role.update", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="role", target_id=role.id, meta={"role": role.name, **changes},
               ip=ip)
    db.commit()
    return to_out(db, role)


def delete_role(db: Session, ctx: OrgContext, role_id: uuid.UUID, ip: str | None) -> None:
    role = _load_custom(db, ctx, role_id)
    members = _counts(db, [role.id]).get(role.id, 0)
    invites = db.scalar(select(func.count()).select_from(Invitation).where(
        Invitation.role_id == role.id, Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None))) or 0
    if members or invites:
        raise Conflict("This role is still in use. Move its members and cancel its open "
                       "invitations first.", code="role_in_use",
                       details={"members": members, "open_invitations": invites})
    record(db, "role.delete", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="role", target_id=role.id, meta={"name": role.name}, ip=ip)
    db.delete(role)
    db.commit()
