"""Invitations for team members and client-portal users."""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError, Conflict, Forbidden, NotFound, Unauthorized
from app.core.models import utcnow
from app.core.pagination import PageParams, apply_sort, paginate
from app.core.security import generate_token, hash_password, hash_token
from app.modules.audit.service import record
from app.modules.clients.models import Client
from app.modules.organizations.models import Invitation, Organization, OrganizationMember
from app.modules.organizations.schemas import InvitationOut, RoleRef
from app.modules.plans.service import check_limit, team_count
from app.modules.rbac.catalogue import CLIENT
from app.modules.rbac.models import Role
from app.modules.rbac.service import ensure_can_grant
from app.modules.users.models import User
from app.tenancy.context import OrgContext
from app.tenancy.scoped import get_scoped

INVALID_INVITE = "This invitation is invalid, has expired or was cancelled."
INVITE_SORTS = {"created_at": Invitation.created_at, "email": Invitation.email,
                "expires_at": Invitation.expires_at}


def _open(stmt):
    return stmt.where(Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None))


def _to_out(inv: Invitation, role: Role, client: Client | None,
            inviter: User | None) -> InvitationOut:
    return InvitationOut(
        id=inv.id, email=inv.email,
        role=RoleRef(id=role.id, name=role.name, system_key=role.system_key),
        client_id=inv.client_id, client_name=client.name if client else None,
        invited_by=inviter.full_name if inviter else None,
        status="pending" if inv.expires_at > utcnow() else "expired",
        expires_at=inv.expires_at, created_at=inv.created_at,
    )


def _out_for(db: Session, inv: Invitation) -> InvitationOut:
    return _to_out(inv, db.get(Role, inv.role_id),
                   db.get(Client, inv.client_id) if inv.client_id else None,
                   db.get(User, inv.invited_by_user_id) if inv.invited_by_user_id else None)


def list_invitations(db: Session, ctx: OrgContext, params: PageParams,
                     sort: str | None) -> tuple[list[InvitationOut], int]:
    stmt = _open(select(Invitation).where(Invitation.organization_id == ctx.org.id))
    stmt = apply_sort(stmt, sort, INVITE_SORTS, "-created_at")
    rows, total = paginate(db, stmt, params)
    return [_out_for(db, inv) for (inv,) in rows], total


def _issue_token(inv: Invitation) -> str:
    token = generate_token()
    inv.token_hash = hash_token(token)
    inv.expires_at = utcnow() + timedelta(days=get_settings().invitation_token_days)
    return token


def _send(org: Organization, inv: Invitation, token: str, inviter: User,
          client: Client | None) -> None:
    s = get_settings()
    link = f"{s.frontend_url}/accept-invite?token={token}"
    what = f"the {client.name} client portal at {org.name}" if client else org.name
    send_email(
        inv.email, f"{inviter.full_name} invited you to {org.name} on {s.app_name}",
        f"Hi,\n\n{inviter.full_name} has invited you to join {what} on {s.app_name}.\n\n"
        f"Accept the invitation here:\n{link}\n\n"
        f"The link expires in {s.invitation_token_days} days.",
    )


def create_invitation(db: Session, ctx: OrgContext, *, email: str, role_id: uuid.UUID,
                      client_id: uuid.UUID | None, ip: str | None) -> InvitationOut:
    role = get_scoped(db, Role, role_id, ctx, label="Role")
    ensure_can_grant(db, ctx.permissions, ctx.is_owner, role, ctx.role.workspace_scope)

    client = None
    if role.system_key != CLIENT:
        check_limit(db, ctx.org.id, "limits.team_members")
    if role.system_key == CLIENT:
        if client_id is None:
            raise AppError("Choose which client this person can see.", code="client_required")
        client = get_scoped(db, Client, client_id, ctx, label="Client")
    elif client_id is not None:
        raise AppError("Only invitations with the Client role are linked to a client.",
                       code="client_not_allowed")

    already_member = db.scalar(
        select(OrganizationMember.id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == ctx.org.id, User.email == email)
    )
    if already_member:
        raise Conflict("This person is already a member of the organization.",
                       code="already_member")

    # A new invitation replaces any open one for the same email.
    db.execute(_open(update(Invitation))
               .where(Invitation.organization_id == ctx.org.id, Invitation.email == email)
               .values(revoked_at=utcnow()))

    inv = Invitation(organization_id=ctx.org.id, email=email, role_id=role.id,
                     client_id=client.id if client else None, invited_by_user_id=ctx.user.id)
    token = _issue_token(inv)
    db.add(inv)
    db.flush()
    record(db, "invitation.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="invitation", target_id=inv.id,
           meta={"email": email, "role": role.name,
                 "client_id": str(client.id) if client else None}, ip=ip)
    db.commit()
    _send(ctx.org, inv, token, ctx.user, client)
    return _to_out(inv, role, client, ctx.user)


def _load_open(db: Session, ctx: OrgContext, invitation_id: uuid.UUID) -> Invitation:
    inv = get_scoped(db, Invitation, invitation_id, ctx, label="Invitation", for_update=True)
    if inv.accepted_at or inv.revoked_at:
        raise NotFound("Invitation not found.")
    return inv


def resend_invitation(db: Session, ctx: OrgContext, invitation_id: uuid.UUID,
                      ip: str | None) -> InvitationOut:
    inv = _load_open(db, ctx, invitation_id)
    ensure_can_grant(db, ctx.permissions, ctx.is_owner, db.get(Role, inv.role_id),
                     ctx.role.workspace_scope)
    token = _issue_token(inv)
    record(db, "invitation.resend", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="invitation", target_id=inv.id, meta={"email": inv.email}, ip=ip)
    db.commit()
    client = db.get(Client, inv.client_id) if inv.client_id else None
    _send(ctx.org, inv, token, ctx.user, client)
    return _out_for(db, inv)


def revoke_invitation(db: Session, ctx: OrgContext, invitation_id: uuid.UUID,
                      ip: str | None) -> None:
    inv = _load_open(db, ctx, invitation_id)
    inv.revoked_at = utcnow()
    record(db, "invitation.revoke", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="invitation", target_id=inv.id, meta={"email": inv.email}, ip=ip)
    db.commit()


# --- the invitee's side ---------------------------------------------------------------------

@dataclass
class OpenInvite:
    invitation: Invitation
    organization: Organization
    role: Role
    client: Client | None
    inviter: User | None
    existing_user: User | None


def find_open(db: Session, token: str, *, for_update: bool = False) -> OpenInvite:
    stmt = select(Invitation).where(Invitation.token_hash == hash_token(token))
    if for_update:
        stmt = stmt.with_for_update()
    inv = db.scalar(stmt)
    if inv is None or inv.accepted_at or inv.revoked_at or inv.expires_at <= utcnow():
        raise AppError(INVALID_INVITE, code="invalid_token")
    org = db.get(Organization, inv.organization_id)
    if org.status != "active":
        raise AppError(INVALID_INVITE, code="invalid_token")
    return OpenInvite(
        invitation=inv, organization=org, role=db.get(Role, inv.role_id),
        client=db.get(Client, inv.client_id) if inv.client_id else None,
        inviter=db.get(User, inv.invited_by_user_id) if inv.invited_by_user_id else None,
        existing_user=db.scalar(select(User).where(User.email == inv.email)),
    )


def accept(db: Session, token: str, *, current_user: User | None, full_name: str | None,
           password: str | None, ip: str | None) -> tuple[User, Organization, bool]:
    """Accept an invitation. Returns (user, organization, created_new_account)."""
    found = find_open(db, token, for_update=True)
    inv, org = found.invitation, found.organization
    user = found.existing_user
    created = False

    if user is not None:
        if current_user is None:
            raise Unauthorized("Sign in as the invited email to accept this invitation.",
                               code="login_required", details={"email": inv.email})
        if current_user.id != user.id:
            raise Forbidden("This invitation is for a different email address. "
                            "Sign out, then open the link again.", code="wrong_account")
        if not user.is_active:
            raise AppError(INVALID_INVITE, code="invalid_token")
    else:
        if current_user is not None:
            raise Forbidden("This invitation is for a different email address. "
                            "Sign out, then open the link again.", code="wrong_account")
        if not full_name or not password:
            raise AppError("Enter your name and choose a password.", code="validation_error",
                           status_code=422,
                           details=[{"field": f, "message": "Field required"}
                                    for f, v in (("full_name", full_name),
                                                 ("password", password)) if not v])
        # Opening the emailed link proves the address, so it counts as verified.
        user = User(email=inv.email, full_name=full_name, password_hash=hash_password(password),
                    email_verified_at=utcnow())
        db.add(user)
        db.flush()
        created = True
        record(db, "auth.register", actor_user_id=user.id, target_type="user",
               target_id=user.id, meta={"via": "invitation"}, ip=ip)

    member = db.scalar(select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id, OrganizationMember.user_id == user.id))
    if member is None:
        if found.role.system_key != CLIENT:
            # The invitation was counted when it was sent; now only members count.
            check_limit(db, org.id, "limits.team_members",
                        used=team_count(db, org.id, include_pending=False))
        member = OrganizationMember(organization_id=org.id, user_id=user.id, role_id=inv.role_id)
        db.add(member)
        db.flush()
    if inv.client_id:
        from app.modules.workspaces.service import assign, client_workspace

        assign(db, member, client_workspace(db, inv.client_id))

    inv.accepted_at = utcnow()
    record(db, "invitation.accept", actor_user_id=user.id, organization_id=org.id,
           target_type="invitation", target_id=inv.id,
           meta={"email": inv.email, "role": found.role.name}, ip=ip)
    db.flush()
    return user, org, created
