"""Access grants: a business lets an agency work in its own workspace.

- A business owner or administrator sends a grant to someone at the agency (by email).
- That person accepts it into one of their agencies. The workspace then appears in the
  agency's workspace list, and the agency's own roles apply inside it ("manage"), or
  read-only permissions ("view").
- Nothing is copied. Either side can end it at any time; the agency's access stops at once.
- Every step is recorded in both organizations' activity logs.
"""

import uuid
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.models import utcnow
from app.core.security import generate_token, hash_token
from app.modules.audit.service import record
from app.modules.grants.models import WorkspaceGrant
from app.modules.grants.schemas import AgencyChoice, GrantOut, GrantPreviewOut
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.rbac.catalogue import AGENCY, BUSINESS
from app.modules.rbac.service import role_permission_codes
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace, WorkspaceAssignment
from app.modules.workspaces.service import own_workspace
from app.tenancy.context import OrgContext

GRANT_DAYS = 14
INVALID_GRANT = "This access link is invalid, has expired or was cancelled."
ACCEPT_PERMISSION = "linked_accounts.manage"


def _status(g: WorkspaceGrant) -> str:
    if g.status == "pending" and g.expires_at <= utcnow():
        return "expired"
    return g.status


def _name(db: Session, user_id: uuid.UUID | None) -> str | None:
    user = db.get(User, user_id) if user_id else None
    return user.full_name if user else None


def _out(db: Session, g: WorkspaceGrant) -> GrantOut:
    agency = db.get(Organization, g.agency_organization_id) if g.agency_organization_id else None
    return GrantOut(id=g.id, email=g.email, access=g.access, status=_status(g),
                    agency_name=agency.name if agency else None,
                    invited_by=_name(db, g.invited_by_user_id),
                    accepted_by=_name(db, g.accepted_by_user_id), created_at=g.created_at,
                    expires_at=g.expires_at, accepted_at=g.accepted_at, revoked_at=g.revoked_at)


def _record_both(db: Session, g: WorkspaceGrant, action: str, actor_id: uuid.UUID,
                 meta: dict, ip: str | None) -> None:
    for org_id in {g.organization_id, g.agency_organization_id} - {None}:
        record(db, action, actor_user_id=actor_id, organization_id=org_id,
               target_type="access_grant", target_id=g.id, meta=meta, ip=ip)


# --- business side --------------------------------------------------------------------------

def _require_business(ctx: OrgContext) -> None:
    if ctx.org.kind != BUSINESS:
        raise Conflict("Only business accounts share their workspace with an agency.",
                       code="business_only")


def list_grants(db: Session, ctx: OrgContext) -> list[GrantOut]:
    rows = db.scalars(select(WorkspaceGrant).where(WorkspaceGrant.organization_id == ctx.org.id)
                      .order_by(WorkspaceGrant.created_at.desc()))
    return [_out(db, g) for g in rows]


def create_grant(db: Session, ctx: OrgContext, *, email: str, access: str,
                 ip: str | None) -> GrantOut:
    _require_business(ctx)
    if email == ctx.user.email:
        raise AppError("Send it to someone at the agency, not to yourself.",
                       code="validation_error", status_code=422,
                       details=[{"field": "email", "message": "That's your own email."}])
    ws = own_workspace(db, ctx.org.id)
    # A new link replaces any pending one sent to the same person.
    db.execute(update(WorkspaceGrant).where(
        WorkspaceGrant.organization_id == ctx.org.id, WorkspaceGrant.email == email,
        WorkspaceGrant.status == "pending").values(status="revoked", revoked_at=utcnow(),
                                                   token_hash=None,
                                                   revoked_by_user_id=ctx.user.id))
    token = generate_token()
    g = WorkspaceGrant(organization_id=ctx.org.id, workspace_id=ws.id, access=access,
                       email=email, token_hash=hash_token(token),
                       expires_at=utcnow() + timedelta(days=GRANT_DAYS),
                       invited_by_user_id=ctx.user.id)
    db.add(g)
    db.flush()
    _record_both(db, g, "access_grant.create", ctx.user.id,
                 {"email": email, "access": access}, ip)
    db.commit()
    s = get_settings()
    level = "work on" if access == "manage" else "view"
    send_email(
        email, f"{ctx.org.name} gave your agency access on {s.app_name}",
        f"Hi,\n\n{ctx.user.full_name} at {ctx.org.name} has given your agency access to "
        f"{level} their marketing workspace on {s.app_name}: websites and results.\n\n"
        f"Accept it here, and choose which of your agencies it's for:\n"
        f"{s.frontend_url}/agency-access?token={token}\n\n"
        f"The link expires in {GRANT_DAYS} days. {ctx.org.name} can end the access at any "
        f"time.",
    )
    return _out(db, g)


def _end(db: Session, g: WorkspaceGrant, actor: User, ip: str | None, action: str) -> None:
    was_active = g.status == "active"
    g.status, g.revoked_at, g.revoked_by_user_id, g.token_hash = (
        "revoked", utcnow(), actor.id, None)
    if was_active:
        # The agency's members lose their assignments to the workspace.
        member_ids = select(OrganizationMember.id).where(
            OrganizationMember.organization_id == g.agency_organization_id)
        db.execute(delete(WorkspaceAssignment).where(
            WorkspaceAssignment.workspace_id == g.workspace_id,
            WorkspaceAssignment.member_id.in_(member_ids)))
    _record_both(db, g, action, actor.id, {"email": g.email, "was": "active" if was_active
                                           else "pending"}, ip)
    db.commit()


def revoke_grant(db: Session, ctx: OrgContext, grant_id: uuid.UUID, ip: str | None) -> None:
    g = db.scalar(select(WorkspaceGrant).where(
        WorkspaceGrant.id == grant_id, WorkspaceGrant.organization_id == ctx.org.id)
        .with_for_update())
    if g is None or g.status == "revoked":
        raise NotFound("Access grant not found.")
    _end(db, g, ctx.user, ip, "access_grant.revoke")


# --- agency side ----------------------------------------------------------------------------

def _agencies_for(db: Session, user: User) -> list[AgencyChoice]:
    rows = db.execute(
        select(Organization, OrganizationMember.role_id)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id, OrganizationMember.status == "active",
               Organization.kind == AGENCY, Organization.status == "active")
        .order_by(Organization.name)
    ).all()
    return [AgencyChoice(organization_id=o.id, slug=o.slug, name=o.name) for o, role_id in rows
            if ACCEPT_PERMISSION in role_permission_codes(db, role_id)]


def _find_open(db: Session, token: str, user: User, *, for_update: bool = False):
    stmt = select(WorkspaceGrant).where(WorkspaceGrant.token_hash == hash_token(token),
                                        WorkspaceGrant.status == "pending")
    if for_update:
        stmt = stmt.with_for_update()
    g = db.scalar(stmt)
    if g is None or g.expires_at <= utcnow():
        raise AppError(INVALID_GRANT, code="invalid_token")
    if g.email != user.email:
        raise Forbidden("This access link was sent to a different email address. Sign in with "
                        "that account, then open the link again.", code="wrong_account")
    return g


def preview(db: Session, token: str, user: User) -> GrantPreviewOut:
    g = _find_open(db, token, user)
    business = db.get(Organization, g.organization_id)
    return GrantPreviewOut(business_name=business.name,
                           workspace_name=db.get(Workspace, g.workspace_id).name,
                           access=g.access, email=g.email,
                           invited_by=_name(db, g.invited_by_user_id),
                           expires_at=g.expires_at, agencies=_agencies_for(db, user))


def accept(db: Session, token: str, organization_id: uuid.UUID, user: User,
           ip: str | None) -> Organization:
    g = _find_open(db, token, user, for_update=True)
    if organization_id not in {a.organization_id for a in _agencies_for(db, user)}:
        # Not an agency they can accept for: don't reveal which organizations exist.
        raise NotFound("Agency not found.")
    already = db.scalar(select(WorkspaceGrant.id).where(
        WorkspaceGrant.workspace_id == g.workspace_id,
        WorkspaceGrant.agency_organization_id == organization_id,
        WorkspaceGrant.status == "active"))
    if already:
        raise Conflict("Your agency already has access to this workspace.",
                       code="already_linked")
    g.status, g.agency_organization_id = "active", organization_id
    g.accepted_by_user_id, g.accepted_at, g.token_hash = user.id, utcnow(), None
    db.flush()
    _record_both(db, g, "access_grant.accept", user.id,
                 {"business": db.get(Organization, g.organization_id).name,
                  "agency": db.get(Organization, organization_id).name, "access": g.access}, ip)
    db.commit()
    return db.get(Organization, organization_id)


def disconnect(db: Session, ctx: OrgContext, workspace_id: uuid.UUID, ip: str | None) -> None:
    """The agency ends its own access to a business's workspace."""
    g = db.scalar(select(WorkspaceGrant).where(
        WorkspaceGrant.workspace_id == workspace_id,
        WorkspaceGrant.agency_organization_id == ctx.org.id,
        WorkspaceGrant.status == "active").with_for_update())
    if g is None:
        raise NotFound("Workspace not found.")
    _end(db, g, ctx.user, ip, "access_grant.disconnect")
