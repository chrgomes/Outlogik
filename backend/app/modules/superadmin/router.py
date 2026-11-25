"""The platform (Super Admin) API: an overview, organizations, users and sign-up codes.

Outlogik staff only (see app/platform.py for who can do what); everyone else gets 404. Every
change is recorded in the audit log with who made it. Staff can't suspend themselves, and only
Super Admins can suspend other staff.
"""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, Forbidden, NotFound
from app.core.models import utcnow
from app.core.pagination import Page, Paging, like_pattern, paginate
from app.core.request import client_ip
from app.jobs.models import Job
from app.modules.audit.models import AuditLog
from app.modules.audit.service import record
from app.modules.auth.deps import DB
from app.modules.auth.service import revoke_all_sessions
from app.modules.clients.models import Client
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.plans import service as plans
from app.modules.plans.catalogue import ENTITLEMENTS
from app.modules.plans.models import Plan, Subscription
from app.modules.rbac.models import Role
from app.modules.superadmin import codes
from app.modules.superadmin.models import SignupCode
from app.modules.superadmin.schemas import (
    AdminAction,
    LimitRow,
    MemberRow,
    MembershipRow,
    OrgDetail,
    OrgRow,
    Overview,
    PlanIn,
    PlanOption,
    SignupCodeCreated,
    SignupCodeIn,
    SignupCodeOut,
    SuspendIn,
    UserDetail,
    UserRow,
)
from app.modules.users.models import User
from app.modules.websites.models import Website
from app.platform import require_platform, staff_role

router = APIRouter(prefix="/admin/platform", tags=["platform admin"])

Reader = Annotated[User, Depends(require_platform("platform.read"))]
HISTORY = 20


# --- overview -------------------------------------------------------------------------------

@router.get("/overview", response_model=Overview, summary="Platform totals and job health")
def overview(db: DB, _: Reader):
    now = utcnow()
    month_ago, day_ago = now - timedelta(days=30), now - timedelta(days=1)
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    users = {
        "total": count(select(func.count()).select_from(User)),
        "active": count(select(func.count()).select_from(User).where(User.is_active)),
        "suspended": count(select(func.count()).select_from(User).where(~User.is_active)),
        "unverified": count(select(func.count()).select_from(User)
                            .where(User.email_verified_at.is_(None))),
        "new_30_days": count(select(func.count()).select_from(User)
                             .where(User.created_at >= month_ago)),
    }
    kinds = dict(db.execute(select(Organization.kind, func.count())
                            .group_by(Organization.kind)).all())
    organizations = {
        "business": kinds.get("business", 0), "agency": kinds.get("agency", 0),
        "suspended": count(select(func.count()).select_from(Organization)
                           .where(Organization.status == "suspended")),
        "new_30_days": count(select(func.count()).select_from(Organization)
                             .where(Organization.created_at >= month_ago)),
    }
    subs = {s: 0 for s in ("trialing", "trial_ended", "active", "past_due", "cancelled")}
    for sub in db.scalars(select(Subscription)):
        subs[plans.effective_status(sub)] = subs.get(plans.effective_status(sub), 0) + 1
    oldest = db.scalar(select(func.min(Job.created_at)).where(Job.status == "queued"))
    jobs = {
        "queued": count(select(func.count()).select_from(Job).where(Job.status == "queued")),
        "running": count(select(func.count()).select_from(Job).where(Job.status == "running")),
        "failed_24h": count(select(func.count()).select_from(Job).where(
            Job.status == "failed", Job.updated_at >= day_ago)),
        "dead_24h": count(select(func.count()).select_from(Job).where(
            Job.status == "dead", Job.updated_at >= day_ago)),
        "oldest_queued_minutes": int((now - oldest).total_seconds() // 60) if oldest else None,
    }
    active_codes = sum(1 for c in db.scalars(select(SignupCode)) if _code_status(c) == "active")
    return Overview(
        users=users, organizations=organizations, subscriptions=subs,
        clients_active=count(select(func.count()).select_from(Client)
                             .where(Client.status == "active")),
        websites_active=count(select(func.count()).select_from(Website)
                              .where(Website.status == "active")),
        signup_codes_active=active_codes, jobs=jobs)


# --- organizations --------------------------------------------------------------------------

def _org_rows(db: Session, orgs: list[Organization]) -> list[dict]:
    ids = [o.id for o in orgs]
    if not ids:
        return []

    def per_org(model, *where):
        return dict(db.execute(select(model.organization_id, func.count())
                               .where(model.organization_id.in_(ids), *where)
                               .group_by(model.organization_id)).all())
    members = per_org(OrganizationMember, OrganizationMember.status == "active")
    clients = per_org(Client, Client.status != "archived")
    websites = per_org(Website, Website.status != "archived")
    subs = {s.organization_id: s for s in db.scalars(
        select(Subscription).where(Subscription.organization_id.in_(ids)))}
    plan_names = dict(db.execute(select(Plan.id, Plan.name)).all())
    out = []
    for o in orgs:
        sub = subs.get(o.id)
        out.append({"id": o.id, "name": o.name, "slug": o.slug, "kind": o.kind,
                    "status": o.status, "plan": plan_names.get(sub.plan_id) if sub else None,
                    "subscription_status": plans.effective_status(sub) if sub else None,
                    "trial_ends_at": sub.trial_ends_at if sub else None,
                    "members": members.get(o.id, 0), "clients": clients.get(o.id, 0),
                    "websites": websites.get(o.id, 0), "created_at": o.created_at})
    return out


def _history(db: Session, *where) -> list[AdminAction]:
    rows = db.execute(select(AuditLog, User.full_name)
                      .outerjoin(User, User.id == AuditLog.actor_user_id)
                      .where(*where).order_by(AuditLog.created_at.desc()).limit(HISTORY)).all()
    return [AdminAction(action=a.action, actor=name, meta=a.meta or {}, created_at=a.created_at)
            for a, name in rows]


def _org(db: Session, org_id: uuid.UUID) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise NotFound("Organization not found.")
    return org


@router.get("/organizations", response_model=Page[OrgRow], summary="Every organization")
def list_organizations(db: DB, paging: Paging, _: Reader,
                       q: Annotated[str | None, Query(max_length=100)] = None,
                       kind: Annotated[str | None, Query(pattern="^(business|agency)$")] = None,
                       org_status: Annotated[str | None, Query(alias="status",
                                                               pattern="^(active|suspended)$")]
                       = None):
    stmt = select(Organization)
    if q:
        stmt = stmt.where(or_(Organization.name.ilike(like_pattern(q)),
                              Organization.slug.ilike(like_pattern(q))))
    if kind:
        stmt = stmt.where(Organization.kind == kind)
    if org_status:
        stmt = stmt.where(Organization.status == org_status)
    rows, total = paginate(db, stmt.order_by(Organization.created_at.desc()), paging)
    return Page(items=_org_rows(db, [r[0] for r in rows]), total=total, page=paging.page,
                page_size=paging.page_size)


@router.get("/organizations/{org_id}", response_model=OrgDetail)
def get_organization(org_id: uuid.UUID, db: DB, _: Reader):
    org = _org(db, org_id)
    row = _org_rows(db, [org])[0]
    sub = plans.subscription_for(db, org.id)
    limits = []
    if sub:
        allowed, used = plans.limits(db, sub.plan_id), plans.usage(db, org.id)
        limits = [LimitRow(key=k, label=label, limit=allowed[k], used=used[k])
                  for k, label in ENTITLEMENTS.items()
                  if not (k == "limits.clients" and org.kind != "agency")]
    members = db.execute(
        select(OrganizationMember, User, Role.name)
        .join(User, User.id == OrganizationMember.user_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.organization_id == org.id)
        .order_by(User.full_name)).all()
    code = db.get(SignupCode, org.signup_code_id) if org.signup_code_id else None
    return OrgDetail(
        **row, suspended_reason=org.suspended_reason,
        signup_code=f"{code.label} (…{code.hint})" if code else None,
        billing_interval=sub.billing_interval if sub else None, limits=limits,
        members_list=[MemberRow(user_id=u.id, name=u.full_name, email=u.email, role=role,
                                status=m.status, user_active=u.is_active)
                      for m, u, role in members],
        history=_history(db, AuditLog.organization_id == org.id,
                         or_(AuditLog.action.like("platform.%"),
                             AuditLog.action == "subscription.change")))


@router.get("/plans", response_model=list[PlanOption], summary="Plans that can be assigned")
def list_plans(db: DB, _: Reader):
    return [PlanOption(key=p.key, name=p.name, account_kind=p.account_kind)
            for p in db.scalars(select(Plan).order_by(Plan.account_kind,
                                                      Plan.monthly_price_cents))]


@router.put("/organizations/{org_id}/plan", response_model=OrgDetail,
            summary="Assign a plan or a trial (by hand, until billing exists)")
def assign_plan(org_id: uuid.UUID, body: PlanIn, request: Request, db: DB,
                staff: User = Depends(require_platform("plans.assign"))):
    org = _org(db, org_id)
    if body.status == "trialing" and not body.trial_days:
        raise AppError("Choose how many days the trial lasts.", code="trial_days_required",
                       status_code=422, details=[{"field": "trial_days",
                                                  "message": "Required for a trial."}])
    plans.set_plan(db, org, body.plan, status=body.status, interval=body.interval,
                   trial_days=body.trial_days, actor_id=staff.id, via="platform admin")
    db.commit()
    return get_organization(org_id, db, staff)


@router.post("/organizations/{org_id}/suspend", response_model=OrgDetail)
def suspend_organization(org_id: uuid.UUID, body: SuspendIn, request: Request, db: DB,
                         staff: User = Depends(require_platform("orgs.suspend"))):
    """Members get "This organization is suspended" until it's reactivated; its scheduled
    audits and Google syncs stop. Nothing is deleted."""
    org = _org(db, org_id)
    if org.status != "suspended":
        org.status, org.suspended_reason = "suspended", body.reason
        record(db, "platform.org_suspend", actor_user_id=staff.id, organization_id=org.id,
               target_type="organization", target_id=org.id,
               meta={"reason": body.reason}, ip=client_ip(request))
        db.commit()
    return get_organization(org_id, db, staff)


@router.post("/organizations/{org_id}/reactivate", response_model=OrgDetail)
def reactivate_organization(org_id: uuid.UUID, request: Request, db: DB,
                            staff: User = Depends(require_platform("orgs.suspend"))):
    org = _org(db, org_id)
    if org.status == "suspended":
        org.status, org.suspended_reason = "active", None
        record(db, "platform.org_reactivate", actor_user_id=staff.id, organization_id=org.id,
               target_type="organization", target_id=org.id, ip=client_ip(request))
        db.commit()
    return get_organization(org_id, db, staff)


# --- users ----------------------------------------------------------------------------------

def _user_row(db: Session, u: User, orgs: int | None = None) -> dict:
    if orgs is None:
        orgs = db.scalar(select(func.count()).select_from(OrganizationMember)
                         .where(OrganizationMember.user_id == u.id)) or 0
    return {"id": u.id, "name": u.full_name, "email": u.email, "active": u.is_active,
            "verified": u.email_verified_at is not None,
            "staff_role": None if u.is_super_admin else u.platform_role,
            "super_admin": u.is_super_admin, "organizations": orgs,
            "last_login_at": u.last_login_at, "created_at": u.created_at}


def _user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found.")
    return user


@router.get("/users", response_model=Page[UserRow], summary="Every user")
def list_users(db: DB, paging: Paging, _: Reader,
               q: Annotated[str | None, Query(max_length=100)] = None,
               user_status: Annotated[str | None, Query(alias="status",
                                                        pattern="^(active|suspended)$")] = None):
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.email.ilike(like_pattern(q)),
                              User.full_name.ilike(like_pattern(q))))
    if user_status:
        stmt = stmt.where(User.is_active.is_(user_status == "active"))
    rows, total = paginate(db, stmt.order_by(User.created_at.desc()), paging)
    users = [r[0] for r in rows]
    counts = dict(db.execute(select(OrganizationMember.user_id, func.count())
                             .where(OrganizationMember.user_id.in_([u.id for u in users]))
                             .group_by(OrganizationMember.user_id)).all()) if users else {}
    return Page(items=[_user_row(db, u, counts.get(u.id, 0)) for u in users], total=total,
                page=paging.page, page_size=paging.page_size)


@router.get("/users/{user_id}", response_model=UserDetail)
def get_user(user_id: uuid.UUID, db: DB, _: Reader):
    user = _user(db, user_id)
    rows = db.execute(
        select(OrganizationMember, Organization, Role.name)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.user_id == user.id).order_by(Organization.name)).all()
    return UserDetail(
        **_user_row(db, user, len(rows)), suspended_reason=user.suspended_reason,
        memberships=[MembershipRow(organization_id=o.id, organization_name=o.name,
                                   organization_slug=o.slug, organization_status=o.status,
                                   role=role, status=m.status) for m, o, role in rows],
        history=_history(db, AuditLog.target_type == "user", AuditLog.target_id == str(user.id),
                         AuditLog.action.like("platform.%")))


def _can_suspend(staff: User, user: User) -> None:
    if user.id == staff.id:
        raise Forbidden("You can't suspend your own account.", code="cannot_suspend_self")
    if (user.is_super_admin or staff_role(user)) and not staff.is_super_admin:
        raise Forbidden("Only a Super Admin can suspend Outlogik staff.",
                        code="cannot_suspend_staff")


@router.post("/users/{user_id}/suspend", response_model=UserDetail)
def suspend_user(user_id: uuid.UUID, body: SuspendIn, request: Request, db: DB,
                 staff: User = Depends(require_platform("users.suspend"))):
    """They're signed out everywhere and can't sign in until reactivated. Their organizations
    carry on; nothing is deleted."""
    user = _user(db, user_id)
    _can_suspend(staff, user)
    if user.is_active:
        user.is_active, user.suspended_reason = False, body.reason
        revoked = revoke_all_sessions(db, user.id)
        record(db, "platform.user_suspend", actor_user_id=staff.id, target_type="user",
               target_id=user.id, meta={"reason": body.reason, "sessions_revoked": revoked},
               ip=client_ip(request))
        db.commit()
    return get_user(user_id, db, staff)


@router.post("/users/{user_id}/reactivate", response_model=UserDetail)
def reactivate_user(user_id: uuid.UUID, request: Request, db: DB,
                    staff: User = Depends(require_platform("users.suspend"))):
    user = _user(db, user_id)
    _can_suspend(staff, user)
    if not user.is_active:
        user.is_active, user.suspended_reason = True, None
        record(db, "platform.user_reactivate", actor_user_id=staff.id, target_type="user",
               target_id=user.id, ip=client_ip(request))
        db.commit()
    return get_user(user_id, db, staff)


# --- sign-up codes --------------------------------------------------------------------------

def _code_status(c: SignupCode) -> str:
    if c.revoked_at:
        return "revoked"
    if c.expires_at and c.expires_at <= utcnow():
        return "expired"
    if c.max_uses is not None and c.uses >= c.max_uses:
        return "used_up"
    return "active"


def _code_out(db: Session, c: SignupCode) -> dict:
    creator = db.scalar(select(User.full_name).where(User.id == c.created_by_user_id)) \
        if c.created_by_user_id else None
    return {"id": c.id, "label": c.label, "hint": c.hint, "account_type": c.account_type,
            "max_uses": c.max_uses, "uses": c.uses, "expires_at": c.expires_at,
            "revoked_at": c.revoked_at, "status": _code_status(c), "created_at": c.created_at,
            "created_by": creator}


Coder = Annotated[User, Depends(require_platform("signup_codes.manage"))]


@router.get("/signup-codes", response_model=list[SignupCodeOut])
def list_codes(db: DB, _: Coder):
    return [_code_out(db, c) for c in db.scalars(
        select(SignupCode).order_by(SignupCode.created_at.desc()).limit(500))]


@router.post("/signup-codes", response_model=SignupCodeCreated,
             status_code=status.HTTP_201_CREATED,
             summary="Make an invitation code; the code is shown only in this response")
def create_code(body: SignupCodeIn, request: Request, db: DB, staff: Coder):
    plain = codes.generate()
    code = SignupCode(code_hash=codes.code_hash(plain), hint=plain[-4:], label=body.label,
                      account_type=body.account_type, max_uses=body.max_uses,
                      expires_at=utcnow() + timedelta(days=body.expires_in_days)
                      if body.expires_in_days else None, created_by_user_id=staff.id)
    db.add(code)
    db.flush()
    record(db, "platform.signup_code_create", actor_user_id=staff.id,
           target_type="signup_code", target_id=code.id,
           meta={"label": code.label, "account_type": code.account_type,
                 "max_uses": code.max_uses}, ip=client_ip(request))
    db.commit()
    return SignupCodeCreated(**_code_out(db, code), code=plain)


@router.post("/signup-codes/{code_id}/revoke", response_model=SignupCodeOut)
def revoke_code(code_id: uuid.UUID, request: Request, db: DB, staff: Coder):
    code = db.get(SignupCode, code_id)
    if code is None:
        raise NotFound("Code not found.")
    if code.revoked_at is None:
        code.revoked_at = utcnow()
        record(db, "platform.signup_code_revoke", actor_user_id=staff.id,
               target_type="signup_code", target_id=code.id, meta={"label": code.label},
               ip=client_ip(request))
        db.commit()
    return _code_out(db, code)
