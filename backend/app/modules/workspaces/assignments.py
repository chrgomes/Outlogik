"""Which workspaces a member sees, for roles limited to assigned workspaces."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden
from app.modules.audit.service import record
from app.modules.organizations.models import OrganizationMember
from app.modules.rbac.catalogue import ALL_WORKSPACES, CLIENT
from app.modules.rbac.models import Role
from app.modules.rbac.service import ensure_can_grant
from app.modules.users.models import User
from app.modules.workspaces import service as workspaces
from app.modules.workspaces.models import Workspace, WorkspaceAssignment
from app.modules.workspaces.schemas import WorkspaceRef
from app.tenancy.context import OrgContext
from app.tenancy.scoped import get_scoped


def _member(db: Session, ctx: OrgContext, member_id: uuid.UUID, *, for_update: bool = False):
    member = get_scoped(db, OrganizationMember, member_id, ctx, label="Member",
                        for_update=for_update)
    return member, db.get(Role, member.role_id)


def list_member_workspaces(db: Session, ctx: OrgContext,
                           member_id: uuid.UUID) -> list[WorkspaceRef]:
    """The member's assigned workspaces that the caller can also see."""
    member, _ = _member(db, ctx, member_id)
    rows = db.scalars(
        select(Workspace)
        .join(WorkspaceAssignment, WorkspaceAssignment.workspace_id == Workspace.id)
        .where(WorkspaceAssignment.member_id == member.id, workspaces.visibility(ctx))
        .order_by(func.lower(Workspace.name))
    )
    return [WorkspaceRef(id=w.id, kind=w.kind, name=w.name) for w in rows]


def set_member_workspaces(db: Session, ctx: OrgContext, member_id: uuid.UUID,
                          workspace_ids: list[uuid.UUID], ip: str | None) -> list[WorkspaceRef]:
    member, role = _member(db, ctx, member_id, for_update=True)
    if member.user_id == ctx.user.id:
        raise Forbidden("You can't change your own workspaces.", code="cannot_modify_self")
    if role.workspace_scope == ALL_WORKSPACES:
        raise Conflict(f"{role.name} sees every workspace already. Only roles limited to "
                       "assigned workspaces need them chosen.", code="role_sees_all")
    ensure_can_grant(db, ctx.permissions, ctx.is_owner, role, ctx.role.workspace_scope)

    wanted = {i: workspaces.get_workspace(db, ctx, i) for i in set(workspace_ids)}
    if role.system_key == CLIENT and any(ws.kind != "client" for ws in wanted.values()):
        raise Conflict("Client Viewers can only be given client workspaces.",
                       code="client_workspaces_only")

    current = workspaces.assigned_workspace_ids(db, member.id)
    # Workspaces the caller can't see are left as they are.
    visible_now = {ws_id for ws_id in current
                   if ctx.workspace_ids is None or ws_id in ctx.workspace_ids}
    added = [wanted[i] for i in wanted if i not in current]
    removed = [db.get(Workspace, i) for i in visible_now - set(wanted)]
    for ws in added:
        workspaces.assign(db, member, ws)
    for ws in removed:
        workspaces.unassign(db, member.id, ws.id)
    if added or removed:
        user = db.get(User, member.user_id)
        record(db, "member.workspaces_update", actor_user_id=ctx.user.id,
               organization_id=ctx.org.id, target_type="member", target_id=member.id,
               meta={"user_email": user.email, "added": sorted(w.name for w in added),
                     "removed": sorted(w.name for w in removed)}, ip=ip)
    db.commit()
    return list_member_workspaces(db, ctx, member.id)
