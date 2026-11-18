"""Dashboard summary: real counts from the organization's own records, and recent activity
from the audit log. Client-portal users get counts for their clients only."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import utcnow
from app.modules.audit.models import AuditLog
from app.modules.clients.models import Client
from app.modules.dashboard.schemas import (
    ActivityItem,
    ClientCounts,
    DashboardOut,
    TeamCounts,
    WebsiteCounts,
)
from app.modules.organizations.models import Invitation, OrganizationMember
from app.modules.rbac.catalogue import CLIENT
from app.modules.rbac.models import Role
from app.modules.users.models import User
from app.modules.websites.models import Website
from app.tenancy.context import OrgContext
from app.tenancy.scoped import client_visibility, workspace_visibility

ACTIVITY_LIMIT = 10


def _by_status(db: Session, model, visible, ctx: OrgContext) -> dict[str, int]:
    rows = db.execute(
        select(model.status, func.count())
        .where(model.organization_id == ctx.org.id, visible)
        .group_by(model.status)
    )
    return dict(rows.all())


def _team(db: Session, ctx: OrgContext) -> TeamCounts:
    rows = db.execute(
        select(Role.system_key, func.count())
        .select_from(OrganizationMember)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.organization_id == ctx.org.id,
               OrganizationMember.status == "active")
        .group_by(Role.system_key)
    ).all()
    counts = {True: 0, False: 0}
    for key, n in rows:
        counts[key == CLIENT] += n
    pending = None
    if ctx.can("members.invite"):
        pending = db.scalar(
            select(func.count()).select_from(Invitation).where(
                Invitation.organization_id == ctx.org.id, Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None), Invitation.expires_at > utcnow())
        ) or 0
    return TeamCounts(members=counts.get(False, 0), client_users=counts.get(True, 0),
                      pending_invitations=pending)


def _activity(db: Session, ctx: OrgContext) -> list[ActivityItem]:
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .where(AuditLog.organization_id == ctx.org.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(ACTIVITY_LIMIT)
    ).all()
    return [ActivityItem(id=a.id, action=a.action, actor_name=name, target_type=a.target_type,
                         target_id=a.target_id, meta=a.meta or {}, created_at=a.created_at)
            for a, name in rows]


def summary(db: Session, ctx: OrgContext) -> DashboardOut:
    clients = _by_status(db, Client, client_visibility(Client.id, ctx), ctx)
    sites = _by_status(db, Website, workspace_visibility(Website.workspace_id, ctx), ctx)
    return DashboardOut(
        clients=ClientCounts(total=sum(clients.values()), active=clients.get("active", 0),
                             archived=clients.get("archived", 0)),
        websites=WebsiteCounts(total=sum(sites.values()), active=sites.get("active", 0),
                               paused=sites.get("paused", 0), archived=sites.get("archived", 0)),
        team=_team(db, ctx) if ctx.can("members.read") else None,
        recent_activity=_activity(db, ctx) if ctx.can("audit.read") else None,
    )
