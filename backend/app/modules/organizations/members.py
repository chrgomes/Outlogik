"""Team members: list, change role/status, remove, leave."""

import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, NotFound
from app.core.pagination import PageParams, apply_sort, paginate
from app.modules.audit.service import record
from app.modules.clients.models import ClientUser
from app.modules.organizations.models import OrganizationMember
from app.modules.organizations.schemas import MemberOut, RoleRef
from app.modules.rbac.catalogue import CLIENT, OWNER
from app.modules.rbac.models import Role
from app.modules.users.models import User
from app.tenancy.context import OrgContext
from app.tenancy.scoped import get_scoped

MEMBER_SORTS = {"name": User.full_name, "email": User.email,
                "joined_at": OrganizationMember.created_at}


def _to_out(member: OrganizationMember, user: User, role: Role, ctx: OrgContext) -> MemberOut:
    return MemberOut(
        id=member.id, user_id=user.id, email=user.email, full_name=user.full_name,
        role=RoleRef(id=role.id, name=role.name, system_key=role.system_key),
        status=member.status, joined_at=member.created_at, is_you=user.id == ctx.user.id,
    )


def list_members(db: Session, ctx: OrgContext, params: PageParams, *, q: str | None,
                 status: str | None, role_id: uuid.UUID | None,
                 sort: str | None) -> tuple[list[MemberOut], int]:
    stmt = (
        select(OrganizationMember, User, Role)
        .join(User, User.id == OrganizationMember.user_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.organization_id == ctx.org.id)
    )
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.full_name).like(like), User.email.like(like)))
    if status:
        stmt = stmt.where(OrganizationMember.status == status)
    if role_id:
        stmt = stmt.where(OrganizationMember.role_id == role_id)
    stmt = apply_sort(stmt, sort, MEMBER_SORTS, "name")
    rows, total = paginate(db, stmt, params)
    return [_to_out(m, u, r, ctx) for m, u, r in rows], total


def _load(db: Session, ctx: OrgContext, member_id: uuid.UUID):
    member = get_scoped(db, OrganizationMember, member_id, ctx, label="Member", for_update=True)
    return member, db.get(User, member.user_id), db.get(Role, member.role_id)


def _active_owner_count(db: Session, ctx: OrgContext) -> int:
    return db.scalar(
        select(func.count()).select_from(OrganizationMember)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.organization_id == ctx.org.id,
               OrganizationMember.status == "active", Role.system_key == OWNER)
    ) or 0


def _guard_owner_change(db: Session, ctx: OrgContext, target_role: Role,
                        loses_ownership: bool) -> None:
    if target_role.system_key == OWNER and not ctx.is_owner:
        raise Forbidden("Only an owner can change another owner.", code="owner_required")
    if target_role.system_key == OWNER and loses_ownership and _active_owner_count(db, ctx) <= 1:
        raise Conflict("An organization needs at least one active owner.", code="last_owner")


def update_member(db: Session, ctx: OrgContext, member_id: uuid.UUID, *,
                  role_id: uuid.UUID | None, status: str | None, ip: str | None) -> MemberOut:
    member, user, role = _load(db, ctx, member_id)
    if user.id == ctx.user.id:
        raise Forbidden("You can't change your own role or status.", code="cannot_modify_self")

    new_role = role
    if role_id is not None and role_id != role.id:
        new_role = get_scoped(db, Role, role_id, ctx, label="Role")
        if new_role.system_key == OWNER and not ctx.is_owner:
            raise Forbidden("Only an owner can make someone an owner.", code="owner_required")
        if (role.system_key == CLIENT) != (new_role.system_key == CLIENT):
            raise Conflict(
                "Client users and team members can't be switched into each other. "
                "Remove the member and send a new invitation instead.",
                code="role_kind_change",
            )
    loses_ownership = (new_role.system_key != OWNER) or (status == "disabled")
    _guard_owner_change(db, ctx, role, loses_ownership)

    changes: dict = {}
    if new_role.id != role.id:
        changes["role"] = {"from": role.name, "to": new_role.name}
        member.role_id = new_role.id
    if status is not None and status != member.status:
        changes["status"] = {"from": member.status, "to": status}
        member.status = status
    if changes:
        record(db, "member.update", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="member", target_id=member.id,
               meta={"user_email": user.email, **changes}, ip=ip)
    db.commit()
    return _to_out(member, user, new_role, ctx)


def _delete_membership(db: Session, ctx: OrgContext, member: OrganizationMember) -> None:
    db.execute(delete(ClientUser).where(ClientUser.organization_id == ctx.org.id,
                                        ClientUser.user_id == member.user_id))
    db.delete(member)


def remove_member(db: Session, ctx: OrgContext, member_id: uuid.UUID, ip: str | None) -> None:
    member, user, role = _load(db, ctx, member_id)
    if user.id == ctx.user.id:
        raise Forbidden("To leave the organization, use “Leave” instead.",
                        code="cannot_modify_self")
    _guard_owner_change(db, ctx, role, loses_ownership=member.status == "active")
    _delete_membership(db, ctx, member)
    record(db, "member.remove", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="user", target_id=user.id,
           meta={"user_email": user.email, "role": role.name}, ip=ip)
    db.commit()


def leave(db: Session, ctx: OrgContext, ip: str | None) -> None:
    if ctx.is_owner and _active_owner_count(db, ctx) <= 1:
        raise Conflict("You're the only owner. Make someone else an owner before leaving.",
                       code="last_owner")
    member = db.get(OrganizationMember, ctx.member.id, with_for_update=True)
    if member is None:
        raise NotFound("Member not found.")
    _delete_membership(db, ctx, member)
    record(db, "member.leave", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="user", target_id=ctx.user.id, ip=ip)
    db.commit()
