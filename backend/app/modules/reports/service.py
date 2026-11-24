"""Making, finding and deleting saved reports.

A report is put together from the same calculations as the dashboard (dashboard/analytics.py),
so the two always agree, and saved whole. It names its period, its sources and anything that
wasn't available, as the spec asks (§10).
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, Forbidden, NotFound
from app.modules.audit.service import record
from app.modules.audits import service as audits
from app.modules.audits.models import Audit
from app.modules.dashboard.analytics import workspace_dashboard
from app.modules.dashboard.schemas import WorkspaceDashboardOut
from app.modules.integrations.models import DataSource, Integration
from app.modules.reports.models import Report
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.service import get_workspace, reachable
from app.tenancy.context import OrgContext

SECTIONS = ("traffic", "ai", "search", "audit")
SECTION_NAMES = {"traffic": "Traffic", "ai": "Visits from AI tools", "search": "Google search",
                 "audit": "Website audit"}
# What a person needs to read each section
SECTION_PERMISSION = {"traffic": "analytics.read", "ai": "analytics.read",
                      "search": "analytics.read", "audit": "audits.read"}
AUDIT_ISSUE_ROWS = 15
NOT_FOUND = "Report not found."


def _fmt(d: date | str | None) -> str:
    if d is None:
        return ""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d:%B} {d.day}, {d.year}"


def can_read(ctx: OrgContext, sections: list[str]) -> bool:
    return ctx.can("reports.read") and all(ctx.can(SECTION_PERMISSION[s]) for s in sections)


def _sources(db: Session, ws: Workspace, dash: dict, sections: list[str]) -> list[dict]:
    integration = db.scalar(select(Integration).where(Integration.workspace_id == ws.id))
    by_kind = {s.kind: s for s in db.scalars(
        select(DataSource).where(DataSource.integration_id == integration.id))} \
        if integration else {}
    out = []
    if ({"traffic", "ai"} & set(sections)) and dash["ga4"]:
        out.append({"name": "Google Analytics 4", "detail": by_kind["ga4"].name,
                    "through": dash["ga4"]["through"]})
    if "search" in sections and dash["search_console"]:
        out.append({"name": "Google Search Console", "detail": by_kind["search_console"].name,
                    "through": dash["search_console"]["through"]})
    if "audit" in sections and dash["audit"]:
        out.append({"name": "Outlogik website audit", "detail": dash["audit"]["website_name"],
                    "through": dash["audit"]["finished_at"][:10]})
    return out


def _unavailable(dash: dict, sections: list[str]) -> list[str]:
    """Plain sentences about anything missing or limited, so nobody reads more into a number
    than it says."""
    out = []
    p, setup = dash["period"], dash["setup"]
    wants_ga4 = bool({"traffic", "ai"} & set(sections))
    if wants_ga4 and not dash["ga4"]:
        out.append("Traffic and visits from AI tools: Google Analytics isn't connected"
                   + (" (Google needs reconnecting)." if setup["google"] == "error" else "."))
    if "search" in sections and not dash["search_console"]:
        out.append("Google search: Search Console isn't connected.")
    if "audit" in sections and not dash["audit"]:
        out.append("Website audit: no audit has been run yet.")
    compared = [x for x in (dash["ga4"] if wants_ga4 else None,
                            dash["search_console"] if "search" in sections else None) if x]
    if p["compare"] != "none" and compared and any(
            m["previous"] is None for x in compared for m in x["metrics"].values()):
        out.append(f"Comparison with {_fmt(p['compare_start'])} to {_fmt(p['compare_end'])}: "
                   "not available for every figure, because Outlogik's history from Google "
                   "doesn't go back that far.")
    if "search" in sections and dash["search_console"] \
            and dash["search_console"]["through"] < p["end"]:
        out.append(f"Google search figures run to {_fmt(dash['search_console']['through'])}: "
                   "Search Console reports 2–3 days behind.")
    if "traffic" in sections and dash["pages_from"]:
        out.append(f"Visits by page start on {_fmt(dash['pages_from'])}, when Outlogik began "
                   "collecting them.")
    return out


def build(db: Session, ctx: OrgContext, ws: Workspace, *, sections: list[str],
          title: str | None, days: int | None, start: date | None, end: date | None,
          compare: str) -> Report:
    sections = [s for s in SECTIONS if s in set(sections)]
    if not sections:
        raise AppError("Choose at least one section.", code="no_sections", status_code=422)
    missing = [SECTION_NAMES[s] for s in sections if not ctx.can(SECTION_PERMISSION[s])]
    if missing:
        raise Forbidden(f"Your role can't include: {', '.join(missing)}.",
                        code="section_not_allowed")
    raw = workspace_dashboard(db, ctx, ws, days=days, start=start, end=end, compare=compare)
    dash = WorkspaceDashboardOut(**raw).model_dump(mode="json")
    issues = []
    if "audit" in sections and dash["audit"]:
        audit = db.get(Audit, uuid.UUID(dash["audit"]["id"]))
        issues = [{"title": g.title, "severity": g.severity, "area": g.area, "count": g.count,
                   "new": g.new, "fix": g.fix}
                  for g in audits.issues(db, audit)][:AUDIT_ISSUE_ROWS]
    p = dash["period"]
    data = {
        "workspace_name": ws.name,
        "prepared_by": ctx.org.name,
        "prepared_for": _prepared_for(db, ctx, ws),
        "sources": _sources(db, ws, dash, sections),
        "unavailable": _unavailable(dash, sections),
        "dashboard": dash,
        "audit_issues": issues,
    }
    report = Report(
        organization_id=ctx.org.id, workspace_id=ws.id, created_by_user_id=ctx.user.id,
        title=(title or "").strip()[:200] or f"{ws.name}: marketing report",
        sections=sections, period_start=date.fromisoformat(p["start"]),
        period_end=date.fromisoformat(p["end"]), compare=p["compare"], data=data)
    db.add(report)
    db.flush()
    record(db, "report.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="report", target_id=report.id,
           meta={"title": report.title, "workspace": ws.name})
    db.commit()
    return report


def _prepared_for(db: Session, ctx: OrgContext, ws: Workspace) -> str | None:
    """The client or business the report is about, when that isn't the organization itself."""
    if ws.organization_id != ctx.org.id:
        from app.modules.organizations.models import Organization
        return db.scalar(select(Organization.name).where(Organization.id == ws.organization_id))
    return ws.name if ws.kind == "client" else None


def visible(ctx: OrgContext):
    """WHERE clause: the organization's reports, in workspaces the caller can see."""
    return (Report.organization_id == ctx.org.id) & Report.workspace_id.in_(
        select(Workspace.id).where(reachable(ctx)))


def get(db: Session, ctx: OrgContext, report_id: uuid.UUID) -> Report:
    report = db.scalar(select(Report).where(Report.id == report_id, visible(ctx)))
    if report is None or not can_read(ctx, report.sections):
        raise NotFound(NOT_FOUND)
    return report


def list_reports(db: Session, ctx: OrgContext, workspace_id: uuid.UUID | None) -> list[Report]:
    stmt = select(Report).where(visible(ctx))
    if workspace_id:
        stmt = stmt.where(Report.workspace_id == workspace_id)
    rows = db.scalars(stmt.order_by(Report.created_at.desc()).limit(200))
    return [r for r in rows if can_read(ctx, r.sections)]


def delete(db: Session, ctx: OrgContext, report: Report) -> None:
    record(db, "report.delete", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="report", target_id=report.id, meta={"title": report.title})
    db.delete(report)
    db.commit()


__all__ = ["SECTIONS", "build", "delete", "get", "get_workspace", "list_reports"]
