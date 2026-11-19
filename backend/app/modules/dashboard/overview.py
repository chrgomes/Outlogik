"""The agency dashboard: every workspace the caller can see, side by side, for the last N days
against the N days before, plus what needs attention.

Workspaces of archived clients are left out. Team details (account managers, reviews) are only
included for people who can see the team (`members.read`), so client-portal users never get
them.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import utcnow
from app.modules.audits.models import Audit
from app.modules.clients.models import Client
from app.modules.dashboard.models import WorkspaceReview
from app.modules.integrations.models import (
    DataSource,
    Ga4Breakdown,
    Ga4Daily,
    GscDaily,
    Integration,
)
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.rbac.catalogue import ACCOUNT_MANAGER
from app.modules.rbac.models import Role
from app.modules.users.models import User
from app.modules.websites.models import Website
from app.modules.workspaces.models import Workspace, WorkspaceAssignment
from app.modules.workspaces.service import reachable
from app.tenancy.context import OrgContext

WEEKS = 12
DROP_ALERT = -0.20  # visits down 20% or more…
DROP_MIN_SESSIONS = 50  # …from at least this many, so tiny numbers don't raise alarms


def _covered(src: DataSource, a: date, b: date) -> bool:
    return bool(src.history_from and src.synced_through
                and src.history_from <= a and b <= src.synced_through)


def _sum(db: Session, col, source_col, day_col, src_id, a: date, b: date) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(col), 0))
                         .where(source_col == src_id, day_col.between(a, b))) or 0)


def _ai(db: Session, src_id, a: date, b: date) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(Ga4Breakdown.sessions), 0)).where(
        Ga4Breakdown.source_id == src_id, Ga4Breakdown.dimension == "ai_source",
        Ga4Breakdown.day.between(a, b))) or 0)


def overview(db: Session, ctx: OrgContext, days: int = 28) -> dict:
    end = utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    p_end = start - timedelta(days=1)
    p_start = p_end - timedelta(days=days - 1)
    team = ctx.can("members.read")
    analytics, audits = ctx.can("analytics.read"), ctx.can("audits.read")

    rows = db.execute(
        select(Workspace, Client.status).outerjoin(Client, Client.id == Workspace.client_id)
        .where(reachable(ctx)).order_by(func.lower(Workspace.name))).all()
    workspaces = [ws for ws, status in rows if status != "archived"]
    ids = [ws.id for ws in workspaces]
    other_orgs = {ws.organization_id for ws in workspaces if ws.organization_id != ctx.org.id}
    org_names = dict(db.execute(select(Organization.id, Organization.name)
                                .where(Organization.id.in_(other_orgs))).all()) \
        if other_orgs else {}

    integrations = {i.workspace_id: i for i in db.scalars(
        select(Integration).where(Integration.workspace_id.in_(ids)))} if ids else {}
    sources: dict = {}
    for s in db.scalars(select(DataSource).where(DataSource.workspace_id.in_(ids))) if ids else []:
        sources.setdefault(s.workspace_id, {})[s.kind] = s
    first_site = {}
    for wid, url in db.execute(select(Website.workspace_id, Website.url)
                               .where(Website.workspace_id.in_(ids),
                                      Website.status != "archived")
                               .order_by(Website.created_at)).all() if ids else []:
        first_site.setdefault(wid, url)

    managers: dict = {}
    reviews: dict = {}
    if team and ids:
        for wid, name in db.execute(
                select(WorkspaceAssignment.workspace_id, User.full_name)
                .join(OrganizationMember, OrganizationMember.id == WorkspaceAssignment.member_id)
                .join(Role, Role.id == OrganizationMember.role_id)
                .join(User, User.id == OrganizationMember.user_id)
                .where(WorkspaceAssignment.organization_id == ctx.org.id,
                       WorkspaceAssignment.workspace_id.in_(ids),
                       OrganizationMember.status == "active",
                       Role.system_key == ACCOUNT_MANAGER)
                .order_by(User.full_name)).all():
            managers.setdefault(wid, []).append(name)
        for r, name in db.execute(
                select(WorkspaceReview, User.full_name)
                .outerjoin(User, User.id == WorkspaceReview.reviewed_by_user_id)
                .where(WorkspaceReview.organization_id == ctx.org.id,
                       WorkspaceReview.workspace_id.in_(ids))).all():
            reviews[r.workspace_id] = {"reviewed_at": r.reviewed_at, "reviewed_by": name}
    mine = set(db.scalars(select(WorkspaceAssignment.workspace_id).where(
        WorkspaceAssignment.member_id == ctx.member.id))) if ids else set()

    out_rows, attention = [], []
    total = {"visits": 0, "visits_prev": 0, "ai": 0, "ai_prev": 0}
    prev_complete = True
    weekly_ids = []
    for ws in workspaces:
        src = sources.get(ws.id, {}) if analytics else {}
        ga4, gsc = src.get("ga4"), src.get("search_console")
        integration = integrations.get(ws.id)
        google = integration.status if integration else "not_connected"
        row: dict = {
            "id": ws.id, "name": ws.name, "kind": ws.kind,
            "linked": ws.id in ctx.linked, "organization_name": org_names.get(ws.organization_id),
            "website": first_site.get(ws.id), "google": google,
            "has_analytics": bool(ga4 and ga4.synced_through),
            "has_search_console": bool(gsc and gsc.synced_through),
            "visits": None, "visits_previous": None, "spark": [], "ai_visits": None,
            "search_clicks": None, "audit": None, "assigned_to_me": ws.id in mine,
            "managers": managers.get(ws.id, []) if team else None,
            "review": reviews.get(ws.id) if team else None,
        }
        if row["has_analytics"]:
            weekly_ids.append(ga4.id)
            row["visits"] = _sum(db, Ga4Daily.sessions, Ga4Daily.source_id, Ga4Daily.day,
                                 ga4.id, start, end)
            row["ai_visits"] = _ai(db, ga4.id, start, end)
            total["visits"] += row["visits"]
            total["ai"] += row["ai_visits"]
            if _covered(ga4, p_start, p_end):
                row["visits_previous"] = _sum(db, Ga4Daily.sessions, Ga4Daily.source_id,
                                              Ga4Daily.day, ga4.id, p_start, p_end)
                total["visits_prev"] += row["visits_previous"]
                total["ai_prev"] += _ai(db, ga4.id, p_start, p_end)
            else:
                prev_complete = False
            daily = dict(db.execute(select(Ga4Daily.day, Ga4Daily.sessions).where(
                Ga4Daily.source_id == ga4.id, Ga4Daily.day.between(start, end))).all())
            row["spark"] = [daily.get(start + timedelta(days=i), 0) for i in range(days)]
        if row["has_search_console"]:
            row["search_clicks"] = _sum(db, GscDaily.clicks, GscDaily.source_id, GscDaily.day,
                                        gsc.id, start, end)
        if audits:
            latest = db.execute(
                select(Audit.website_id, func.max(Audit.finished_at))
                .where(Audit.workspace_id == ws.id, Audit.status == "completed")
                .group_by(Audit.website_id)).all()
            if latest:
                errors = warnings = 0
                for website_id, finished in latest:
                    a = db.scalar(select(Audit).where(Audit.website_id == website_id,
                                                      Audit.finished_at == finished))
                    errors += a.errors
                    warnings += a.warnings
                row["audit"] = {"errors": errors, "warnings": warnings}
        out_rows.append(row)

        # What needs attention, most urgent first
        if integration and integration.status == "error":
            attention.append({"workspace_id": ws.id, "name": ws.name, "kind": "reconnect",
                              "text": "Google stopped accepting the connection."})
        prev = row["visits_previous"]
        if prev and prev >= DROP_MIN_SESSIONS and (row["visits"] - prev) / prev <= DROP_ALERT:
            attention.append({"workspace_id": ws.id, "name": ws.name, "kind": "visits_drop",
                              "text": f"Visits down {round((prev - row['visits']) / prev * 100)}%"
                                      f" compared with the {days} days before."})
        if row["audit"] and row["audit"]["errors"]:
            n = row["audit"]["errors"]
            attention.append({"workspace_id": ws.id, "name": ws.name, "kind": "audit_errors",
                              "text": f"{n} audit error{'s' if n != 1 else ''}."})
        if integration is None and analytics:
            attention.append({"workspace_id": ws.id, "name": ws.name, "kind": "not_connected",
                              "text": "Google isn't connected yet."})
    order = {"reconnect": 0, "visits_drop": 1, "audit_errors": 2, "not_connected": 3}
    attention.sort(key=lambda a: order[a["kind"]])

    weekly = []
    first_week = end - timedelta(days=WEEKS * 7 - 1)
    for w in range(WEEKS):
        a = first_week + timedelta(days=w * 7)
        b = a + timedelta(days=6)
        sessions = ai = 0
        if weekly_ids:
            sessions = int(db.scalar(select(func.coalesce(func.sum(Ga4Daily.sessions), 0)).where(
                Ga4Daily.source_id.in_(weekly_ids), Ga4Daily.day.between(a, b))) or 0)
            ai = int(db.scalar(select(func.coalesce(func.sum(Ga4Breakdown.sessions), 0)).where(
                Ga4Breakdown.source_id.in_(weekly_ids), Ga4Breakdown.dimension == "ai_source",
                Ga4Breakdown.day.between(a, b))) or 0)
        weekly.append({"week_start": a, "sessions": sessions, "ai_visits": ai})

    with_analytics = [r for r in out_rows if r["has_analytics"]]
    return {
        "period": {"start": start, "end": end, "days": days,
                   "compare_start": p_start, "compare_end": p_end},
        "totals": {
            "workspaces": len(out_rows),
            "clients": sum(1 for r in out_rows if r["kind"] == "client" or r["linked"]),
            "websites": db.scalar(select(func.count()).select_from(Website).where(
                Website.workspace_id.in_(ids), Website.status != "archived")) if ids else 0,
            "visits": total["visits"] if with_analytics else None,
            "visits_previous": total["visits_prev"] if with_analytics and prev_complete else None,
            "ai_visits": total["ai"] if with_analytics else None,
            "ai_visits_previous": total["ai_prev"] if with_analytics and prev_complete else None,
            "with_audit_errors": sum(1 for r in out_rows if r["audit"] and r["audit"]["errors"])
            if audits else None,
            "google_not_connected": sum(1 for r in out_rows if r["google"] == "not_connected")
            if analytics else None,
        },
        "weekly": weekly if with_analytics else [],
        "attention": attention[:10],
        "workspaces": out_rows,
    }
