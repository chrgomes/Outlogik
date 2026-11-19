"""The dashboard for one workspace: traffic, AI tools, search, pages and the latest audit for a
chosen period, compared with the period before or the same period last year.

Rules that keep the numbers honest:
- Only synced data is used; nothing is estimated.
- A comparison is shown only when the whole comparison period was synced (`history_from`).
  Otherwise "previous" is None and the app says there's no earlier data to compare.
- Search Console runs 2-3 days behind Analytics, so each source's totals cover the chosen
  period as far as that source has data, and say so (`through`).
- "What changed" is written from these numbers by fixed rules. No AI, no forecasts.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.models import utcnow
from app.modules.audits import service as audits
from app.modules.audits.models import Audit
from app.modules.integrations.models import (
    DataSource,
    Ga4Breakdown,
    Ga4Daily,
    Ga4Page,
    GscDaily,
    GscPage,
    GscQuery,
    GscQueryPage,
    Integration,
)
from app.modules.websites.models import Website
from app.modules.workspaces.models import Workspace
from app.tenancy.context import OrgContext

MAX_DAYS = 486
GA4_METRICS = ("sessions", "users", "new_users", "engaged_sessions", "page_views", "key_events")
ALMOST_RANGE = (8.0, 20.0)  # positions just off, or at the bottom of, Google's first page
LOW_CTR_MIN_IMPRESSIONS = 100


@dataclass
class Period:
    start: date
    end: date
    compare: str  # previous | year | none
    c_start: date | None
    c_end: date | None

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def _year_before(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # 29 February
        return d.replace(year=d.year - 1, day=28)


def make_period(latest: date, *, days: int | None, start: date | None, end: date | None,
                compare: str) -> Period:
    if start or end:
        if not (start and end):
            raise AppError("Choose both a start and an end date.", code="invalid_period",
                           status_code=422)
        if start > end:
            raise AppError("The start date is after the end date.", code="invalid_period",
                           status_code=422)
        if (end - start).days + 1 > MAX_DAYS:
            raise AppError("Choose a period of 16 months or less.", code="invalid_period",
                           status_code=422)
    else:
        end = latest
        start = end - timedelta(days=(days or 28) - 1)
    n = (end - start).days + 1
    if compare == "previous":
        c_end = start - timedelta(days=1)
        c_start = c_end - timedelta(days=n - 1)
    elif compare == "year":
        c_start, c_end = _year_before(start), _year_before(end)
    else:
        c_start = c_end = None
    return Period(start, end, compare, c_start, c_end)


def _sources(db: Session, ws: Workspace) -> tuple[Integration | None, dict[str, DataSource]]:
    integration = db.scalar(select(Integration).where(Integration.workspace_id == ws.id))
    if integration is None:
        return None, {}
    rows = db.scalars(select(DataSource).where(DataSource.integration_id == integration.id))
    return integration, {s.kind: s for s in rows}


def latest_day(db: Session, ws: Workspace) -> date:
    """The default period ends on the latest day Analytics (else Search Console) has data."""
    _, sources = _sources(db, ws)
    for kind in ("ga4", "search_console"):
        if sources.get(kind) and sources[kind].synced_through:
            return sources[kind].synced_through
    return utcnow().date() - timedelta(days=1)


def _covered(source: DataSource, start: date | None, end: date | None,
             from_attr: str = "history_from") -> bool:
    first = getattr(source, from_attr)
    return bool(start and first and source.synced_through
                and first <= start and end <= source.synced_through)


def _pct(now: float, before: float | None) -> float | None:
    if before is None or before == 0:
        return None
    return (now - before) / before


# --- Analytics ------------------------------------------------------------------------------

def _ga4_totals(db: Session, src: DataSource, a: date, b: date) -> dict[str, float]:
    cols = [func.coalesce(func.sum(getattr(Ga4Daily, m)), 0) for m in GA4_METRICS]
    row = db.execute(select(*cols).where(Ga4Daily.source_id == src.id,
                                         Ga4Daily.day.between(a, b))).one()
    return {m: float(row[i]) for i, m in enumerate(GA4_METRICS)}


def _daily(db: Session, column, source_col, day_col, src_id, a: date, b: date) -> dict:
    return dict(db.execute(select(day_col, column).where(source_col == src_id,
                                                         day_col.between(a, b))).all())


def _shares(db: Session, src: DataSource, dimension: str, p: Period, covered: bool) -> list:
    def by_value(a, b):
        return dict(db.execute(select(Ga4Breakdown.value, func.sum(Ga4Breakdown.sessions))
                               .where(Ga4Breakdown.source_id == src.id,
                                      Ga4Breakdown.dimension == dimension,
                                      Ga4Breakdown.day.between(a, b))
                               .group_by(Ga4Breakdown.value)).all())
    now = by_value(p.start, p.end)
    before = by_value(p.c_start, p.c_end) if covered else None
    # Names only seen in the earlier period stay in, with 0 now, so totals compare fairly.
    names = set(now) | set(before or {})
    rows = [{"name": k, "sessions": int(now.get(k, 0)),
             "previous": int(before.get(k, 0)) if before is not None else None}
            for k in names]
    return sorted(rows, key=lambda r: (-r["sessions"], -(r["previous"] or 0), r["name"]))


def _top_pages(db: Session, src: DataSource, p: Period, limit: int = 10) -> dict:
    if src.pages_from is None:
        return {"rows": [], "from": None}

    def by_path(a, b):
        return db.execute(select(Ga4Page.path, func.sum(Ga4Page.sessions),
                                 func.sum(Ga4Page.key_events))
                          .where(Ga4Page.source_id == src.id, Ga4Page.day.between(a, b))
                          .group_by(Ga4Page.path)
                          .order_by(func.sum(Ga4Page.sessions).desc()).limit(500)).all()
    now = by_path(p.start, p.end)[:limit]
    covered = _covered(src, p.c_start, p.c_end, "pages_from")
    before = {path: s for path, s, _ in by_path(p.c_start, p.c_end)} if covered else None
    rows = [{"path": path, "sessions": int(s), "key_events": float(k),
             "previous": int(before.get(path, 0)) if before is not None else None}
            for path, s, k in now]
    # Visits by page started later than the totals: say from when, if inside the period.
    return {"rows": rows, "from": src.pages_from if src.pages_from > p.start else None}


def _ga4_block(db: Session, src: DataSource, p: Period) -> dict:
    end = min(p.end, src.synced_through)
    covered = _covered(src, p.c_start, p.c_end)
    now = _ga4_totals(db, src, p.start, end)
    before = _ga4_totals(db, src, p.c_start, p.c_end) if covered else None
    daily = _daily(db, Ga4Daily.sessions, Ga4Daily.source_id, Ga4Daily.day, src.id,
                   p.start, end)
    prev_daily = _daily(db, Ga4Daily.sessions, Ga4Daily.source_id, Ga4Daily.day, src.id,
                        p.c_start, p.c_end) if covered else {}
    return {
        "through": end,
        "metrics": {m: {"value": v, "previous": before[m] if before else None}
                    for m, v in now.items()},
        "daily": daily, "prev_daily": prev_daily, "covered": covered,
        "channels": _shares(db, src, "channel", p, covered),
        "ai": _shares(db, src, "ai_source", p, covered),
        "pages": _top_pages(db, src, p),
    }


# --- Search Console -------------------------------------------------------------------------

def _gsc_totals(db: Session, src: DataSource, a: date, b: date) -> dict[str, float]:
    clicks, impressions, weighted = db.execute(select(
        func.coalesce(func.sum(GscDaily.clicks), 0),
        func.coalesce(func.sum(GscDaily.impressions), 0),
        func.coalesce(func.sum(GscDaily.position * GscDaily.impressions), 0))
        .where(GscDaily.source_id == src.id, GscDaily.day.between(a, b))).one()
    return {"clicks": float(clicks), "impressions": float(impressions),
            "ctr": clicks / impressions if impressions else 0.0,
            "position": weighted / impressions if impressions else 0.0}


def _gsc_block(db: Session, src: DataSource, p: Period) -> dict:
    end = min(p.end, src.synced_through)
    # Search Console is behind: compare the same number of days it actually has.
    lag = (p.end - end).days
    c_end = p.c_end - timedelta(days=lag) if p.c_end else None
    covered = _covered(src, p.c_start, c_end)
    now = _gsc_totals(db, src, p.start, end)
    before = _gsc_totals(db, src, p.c_start, c_end) if covered else None
    daily = {d: (c, i) for d, c, i in db.execute(
        select(GscDaily.day, GscDaily.clicks, GscDaily.impressions)
        .where(GscDaily.source_id == src.id, GscDaily.day.between(p.start, end)))}

    snapshot_end = db.scalar(select(func.max(GscQueryPage.period_end))
                             .where(GscQueryPage.source_id == src.id))
    almost = [{"query": r.query, "page": r.page, "clicks": r.clicks,
               "impressions": r.impressions, "position": r.position}
              for r in db.scalars(select(GscQueryPage).where(
                  GscQueryPage.source_id == src.id,
                  GscQueryPage.position.between(*ALMOST_RANGE))
                  .order_by(GscQueryPage.impressions.desc()).limit(10))]
    pages = list(db.scalars(select(GscPage).where(GscPage.source_id == src.id)))
    total_clicks = sum(x.clicks for x in pages)
    total_impr = sum(x.impressions for x in pages)
    site_ctr = total_clicks / total_impr if total_impr else 0.0
    # Shown on Google's first page, seen often, clicked less than half as often as the site's
    # pages are on average: the title and description are worth a look.
    low = sorted((x for x in pages if x.impressions >= LOW_CTR_MIN_IMPRESSIONS
                  and x.position <= 10 and site_ctr
                  and x.clicks / x.impressions < site_ctr / 2),
                 key=lambda x: -x.impressions)[:5]
    queries = list(db.scalars(select(GscQuery).where(GscQuery.source_id == src.id)
                              .order_by(GscQuery.clicks.desc(), GscQuery.impressions.desc())
                              .limit(10)))
    return {
        "through": end, "covered": covered,
        "metrics": {k: {"value": v, "previous": before[k] if before else None}
                    for k, v in now.items()},
        "daily": daily,
        "snapshot_end": snapshot_end,
        "almost": almost,
        "low_ctr": [{"page": x.page, "clicks": x.clicks, "impressions": x.impressions,
                     "ctr": x.clicks / x.impressions, "position": x.position} for x in low],
        "site_ctr": site_ctr,
        "queries": [{"query": q.query, "clicks": q.clicks, "impressions": q.impressions,
                     "ctr": q.clicks / q.impressions if q.impressions else 0.0,
                     "position": q.position} for q in queries],
    }


# --- Audits ---------------------------------------------------------------------------------

def _audit_block(db: Session, ws: Workspace) -> dict | None:
    latest = db.scalar(select(Audit).where(Audit.workspace_id == ws.id,
                                           Audit.status == "completed")
                       .order_by(Audit.finished_at.desc()).limit(1))
    if latest is None:
        return None
    site = db.get(Website, latest.website_id)
    history = list(db.scalars(select(Audit).where(Audit.website_id == latest.website_id,
                                                  Audit.status == "completed")
                              .order_by(Audit.finished_at.desc()).limit(6)))[::-1]
    detail = audits.detail(db, latest)
    fix_first = [{"check": g.check, "title": g.title, "severity": g.severity, "count": g.count}
                 for g in audits.issues(db, latest) if g.severity != "notice"][:3]
    return {"id": latest.id, "workspace_id": latest.workspace_id,
            "website_name": site.name if site else latest.url, "finished_at": latest.finished_at,
            "pages_crawled": latest.pages_crawled, "errors": latest.errors,
            "warnings": latest.warnings, "notices": latest.notices,
            "new_issues": detail.new_issues, "fixed_issues": detail.fixed_issues,
            "history": [{"finished_at": a.finished_at, "errors": a.errors,
                         "warnings": a.warnings} for a in history],
            "fix_first": fix_first}


# --- "What changed" -------------------------------------------------------------------------

def _num(n: float) -> str:
    return f"{round(n):,}"


def _change_words(now: float, before: float) -> str:
    pct = _pct(now, before)
    if pct is None:
        return "new this period" if now else "unchanged"
    if abs(pct) < 0.01:
        return "about the same"
    return f"{'up' if pct > 0 else 'down'} {abs(round(pct * 100))}%"


def changes(ga4: dict | None, gsc: dict | None, audit: dict | None, p: Period) -> list[str]:
    against = "the same period last year" if p.compare == "year" else "before"
    out: list[str] = []
    if ga4 and ga4["covered"]:
        s = ga4["metrics"]["sessions"]
        line = f"Visits are {_change_words(s['value'], s['previous'])} ({_num(s['value'])})"
        diff = s["value"] - s["previous"]
        deltas = sorted(((c["sessions"] - (c["previous"] or 0), c["name"])
                         for c in ga4["channels"]), reverse=diff > 0)
        if deltas and diff and (deltas[0][0] > 0) == (diff > 0) \
                and abs(deltas[0][0]) >= abs(diff) / 2:
            line += f", mostly from {deltas[0][1]} ({deltas[0][0]:+,})"
        out.append(line + f" compared with {against}.")
        ai_now = sum(x["sessions"] for x in ga4["ai"])
        ai_before = sum(x["previous"] or 0 for x in ga4["ai"])
        if ai_now or ai_before:
            d = ai_now - ai_before
            line = ("AI tools sent the same number of visits as before" if d == 0 else
                    f"AI tools sent {_num(abs(d))} {'more' if d > 0 else 'fewer'} "
                    f"visit{'s' if abs(d) != 1 else ''} than {against}")
            if ai_now:
                top = ga4["ai"][0]
                line += f"; {top['name']} sent {_num(top['sessions'])} of the {_num(ai_now)}"
            out.append(line + ".")
    if gsc and gsc["covered"]:
        c = gsc["metrics"]["clicks"]
        out.append(f"Google search clicks are {_change_words(c['value'], c['previous'])} "
                   f"({_num(c['value'])}).")
    if audit and audit["new_issues"] is not None:
        new, fixed = audit["new_issues"], audit["fixed_issues"]
        if new or fixed:
            out.append(f"The latest audit found {new} new issue{'s' if new != 1 else ''} "
                       f"and {fixed} fixed since the one before.")
        else:
            out.append("The latest audit found the same issues as the one before.")
    return out


# --- the whole dashboard --------------------------------------------------------------------

def workspace_dashboard(db: Session, ctx: OrgContext, ws: Workspace, *, days: int | None,
                        start: date | None, end: date | None, compare: str) -> dict:
    p = make_period(latest_day(db, ws), days=days, start=start, end=end, compare=compare)
    integration, sources = _sources(db, ws)
    can_analytics, can_audits = ctx.can("analytics.read"), ctx.can("audits.read")
    ga4_src = sources.get("ga4") if can_analytics else None
    gsc_src = sources.get("search_console") if can_analytics else None
    ga4 = _ga4_block(db, ga4_src, p) if ga4_src and ga4_src.synced_through else None
    gsc = _gsc_block(db, gsc_src, p) if gsc_src and gsc_src.synced_through else None
    audit = _audit_block(db, ws) if can_audits else None

    series = []
    for i in range(p.days):
        d = p.start + timedelta(days=i)
        point: dict = {"day": d}
        if ga4 and d <= ga4["through"]:
            point["sessions"] = ga4["daily"].get(d, 0)
            if ga4["covered"]:
                point["previous_sessions"] = ga4["prev_daily"].get(p.c_start + timedelta(days=i), 0)
        if gsc and d <= gsc["through"]:
            point["clicks"], point["impressions"] = gsc["daily"].get(d, (0, 0))
        series.append(point)

    websites = db.scalar(select(func.count()).select_from(Website).where(
        Website.workspace_id == ws.id, Website.status != "archived")) or 0
    any_audit = db.scalar(select(func.count()).select_from(Audit).where(
        Audit.workspace_id == ws.id, Audit.status == "completed")) or 0
    return {
        "workspace_id": ws.id, "workspace_name": ws.name,
        "period": {"start": p.start, "end": p.end, "days": p.days, "compare": p.compare,
                   "compare_start": p.c_start, "compare_end": p.c_end},
        "setup": {"websites": websites, "audited": bool(any_audit),
                  "google": integration.status if integration else "not_connected",
                  "ga4": "ga4" in sources, "search_console": "search_console" in sources,
                  "analytics_visible": can_analytics, "audits_visible": can_audits},
        "changes": changes(ga4, gsc, audit, p),
        "ga4": ga4 and {"through": ga4["through"], "metrics": ga4["metrics"]},
        "search_console": gsc and {"through": gsc["through"], "metrics": gsc["metrics"]},
        "series": series,
        "channels": ga4["channels"] if ga4 else [],
        "ai_referrals": ga4["ai"] if ga4 else [],
        "top_pages": ga4["pages"]["rows"] if ga4 else [],
        "pages_from": ga4["pages"]["from"] if ga4 else None,
        "search_snapshot_end": gsc["snapshot_end"] if gsc else None,
        "almost_ranking": gsc["almost"] if gsc else [],
        "low_ctr_pages": gsc["low_ctr"] if gsc else [],
        "site_ctr": gsc["site_ctr"] if gsc else None,
        "top_queries": gsc["queries"] if gsc else [],
        "audit": audit,
    }
