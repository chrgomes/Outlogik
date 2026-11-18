"""Plans and limits.

`check_limit(...)` is called by the services that add things (websites, clients, team
members), never by the interface. Counted limits use live counts, so there's nothing to keep
in step. When a trial has ended (or a subscription is cancelled) nothing is deleted: the
organization just can't add more until it has a plan.
"""

import uuid
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, Forbidden
from app.core.models import utcnow
from app.modules.audit.service import record
from app.modules.audits.models import UsageRecord
from app.modules.clients.models import Client
from app.modules.organizations.models import Invitation, Organization, OrganizationMember
from app.modules.plans.catalogue import CAPS, ENTITLEMENTS, METERED, TRIAL_DAYS, TRIAL_PLAN
from app.modules.plans.models import Plan, PlanEntitlement, Subscription
from app.modules.rbac.catalogue import CLIENT
from app.modules.rbac.models import Role
from app.modules.websites.models import Website

NOUNS = {"limits.websites": ("website", "websites"), "limits.clients": ("client", "clients"),
         "limits.team_members": ("team member", "team members"),
         "limits.audits_per_month": ("website audit a month", "website audits a month")}
CONTACT = "Contact Outlogik to move to a bigger plan."


def plan_by_key(db: Session, key: str) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.key == key))
    if plan is None:
        raise AppError(f"Unknown plan {key!r}.", code="unknown_plan", status_code=422)
    return plan


def subscription_for(db: Session, org_id: uuid.UUID) -> Subscription | None:
    return db.scalar(select(Subscription).where(Subscription.organization_id == org_id))


def effective_status(sub: Subscription | None) -> str:
    """trialing, active, past_due or cancelled; or trial_ended once a trial runs out."""
    if sub is None:
        return "active"
    if sub.status == "trialing" and sub.trial_ends_at and sub.trial_ends_at <= utcnow():
        return "trial_ended"
    return sub.status


def limits(db: Session, plan_id: uuid.UUID) -> dict[str, int | None]:
    rows = db.execute(select(PlanEntitlement.key, PlanEntitlement.value)
                      .where(PlanEntitlement.plan_id == plan_id)).all()
    values = dict(rows)
    # A limit the plan doesn't mention is unlimited.
    return {key: values.get(key) for key in ENTITLEMENTS}


def period(when=None) -> str:
    return (when or utcnow()).strftime("%Y-%m")


def metered_use(db: Session, org_id: uuid.UUID, metric: str) -> int:
    return db.scalar(select(UsageRecord.count).where(
        UsageRecord.organization_id == org_id, UsageRecord.metric == metric,
        UsageRecord.period == period())) or 0


def record_use(db: Session, org_id: uuid.UUID, metric: str) -> None:
    """Count one more use this month (atomic, so simultaneous requests can't undercount)."""
    db.execute(text("""
        INSERT INTO usage_records (id, organization_id, metric, period, count)
        VALUES (gen_random_uuid(), :org, :metric, :period, 1)
        ON CONFLICT (organization_id, metric, period)
        DO UPDATE SET count = usage_records.count + 1, updated_at = now()
    """), {"org": org_id, "metric": metric, "period": period()})


def cap(db: Session, org_id: uuid.UUID, key: str) -> int | None:
    """A cap from the organization's plan (for example pages per audit); None: no cap."""
    sub = subscription_for(db, org_id)
    return limits(db, sub.plan_id)[key] if sub else None


def usage(db: Session, org_id: uuid.UUID) -> dict[str, int | None]:
    websites = db.scalar(select(func.count()).select_from(Website).where(
        Website.organization_id == org_id, Website.status != "archived")) or 0
    clients = db.scalar(select(func.count()).select_from(Client).where(
        Client.organization_id == org_id, Client.status != "archived")) or 0
    counts: dict[str, int | None] = {
        "limits.websites": websites, "limits.clients": clients,
        "limits.team_members": team_count(db, org_id)}
    counts |= {key: metered_use(db, org_id, metric) for key, metric in METERED.items()}
    counts |= {key: None for key in CAPS}
    return counts


def team_count(db: Session, org_id: uuid.UUID, *, include_pending: bool = True) -> int:
    """Active team members, plus open team invitations. Client-portal users don't count."""
    team_role = (Role.system_key.is_(None)) | (Role.system_key != CLIENT)
    members = db.scalar(
        select(func.count()).select_from(OrganizationMember)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.organization_id == org_id,
               OrganizationMember.status == "active", team_role)) or 0
    if not include_pending:
        return members
    pending = db.scalar(
        select(func.count()).select_from(Invitation)
        .join(Role, Role.id == Invitation.role_id)
        .where(Invitation.organization_id == org_id, Invitation.accepted_at.is_(None),
               Invitation.revoked_at.is_(None), Invitation.expires_at > utcnow(),
               team_role)) or 0
    return members + pending


def check_limit(db: Session, org_id: uuid.UUID, key: str, *, used: int | None = None) -> None:
    """Refuse to add one more of `key` if the organization's plan doesn't allow it."""
    sub = subscription_for(db, org_id)
    if sub is None:
        return  # organizations without a subscription aren't limited
    status = effective_status(sub)
    if status == "trial_ended":
        raise Forbidden("Your free trial has ended, so nothing new can be added. Everything "
                        f"you've added is kept. {CONTACT}", code="trial_ended")
    if status == "cancelled":
        raise Forbidden("This subscription was cancelled, so nothing new can be added. "
                        f"Everything you've added is kept. {CONTACT}",
                        code="subscription_cancelled")
    plan = db.get(Plan, sub.plan_id)
    limit = limits(db, plan.id)[key]
    if limit is None:
        return
    current = usage(db, org_id)[key] if used is None else used
    if current + 1 > limit:
        one, many = NOUNS[key]
        included = (f"doesn't include {many}" if limit == 0
                    else f"includes {limit} {one if limit == 1 else many}")
        raise Forbidden(f"The {plan.name} plan {included}. {CONTACT}",
                        code="plan_limit_reached",
                        details={"limit": key, "allowed": limit, "used": current})


# --- assigning plans ------------------------------------------------------------------------

def start_trial(db: Session, org: Organization) -> Subscription:
    plan = plan_by_key(db, TRIAL_PLAN[org.kind])
    sub = Subscription(organization_id=org.id, plan_id=plan.id, status="trialing",
                       trial_ends_at=utcnow() + timedelta(days=TRIAL_DAYS))
    db.add(sub)
    db.flush()
    return sub


def set_plan(db: Session, org: Organization, plan_key: str, *, status: str = "active",
             interval: str = "monthly", trial_days: int | None = None,
             actor_id: uuid.UUID | None = None, via: str = "cli") -> Subscription:
    """Assign a plan by hand (staff, until billing exists)."""
    plan = plan_by_key(db, plan_key)
    if plan.account_kind != org.kind:
        raise AppError(f"{plan.name} is for {plan.account_kind} accounts; {org.name} is a "
                       f"{org.kind}.", code="plan_kind_mismatch", status_code=422)
    sub = subscription_for(db, org.id)
    before = None
    if sub is None:
        sub = Subscription(organization_id=org.id, plan_id=plan.id, status=status)
        db.add(sub)
    else:
        before = {"plan": db.get(Plan, sub.plan_id).key, "status": sub.status,
                  "interval": sub.billing_interval}
    sub.plan_id, sub.status, sub.billing_interval, sub.source = plan.id, status, interval, "manual"
    sub.trial_ends_at = (utcnow() + timedelta(days=trial_days or TRIAL_DAYS)
                         if status == "trialing" else None)
    db.flush()
    record(db, "subscription.change", actor_user_id=actor_id, organization_id=org.id,
           target_type="subscription", target_id=sub.id,
           meta={"from": before, "to": {"plan": plan.key, "status": status,
                                        "interval": interval}, "via": via})
    return sub
