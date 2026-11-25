"""Copying Google data into Outlogik's daily history (snapshots).

- The first sync fetches the last 16 months (what Search Console keeps), so a period can be
  compared with the same period last year straight away; visits by landing page start with
  the last 90 days. Later syncs refetch the last 7 days (Google revises recent days) and
  replace those days.
- Search Console data arrives 2–3 days late; it's stored for the days Google returns.
- Visits from AI tools are GA4 sessions whose source is one of AI_SOURCES.
"""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.models import utcnow
from app.jobs.service import enqueue
from app.modules.integrations import google
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
from app.modules.integrations.service import access_token
from app.modules.organizations.models import Organization

log = logging.getLogger(__name__)

FIRST_SYNC_DAYS = 486  # 16 months
FIRST_SYNC_PAGE_DAYS = 90
REFRESH_DAYS = 7
TOP_QUERIES = 250
TOP_PAGES = 500
TOP_QUERY_PAGES = 1000
MAX_PAGE_ROWS = 100_000
# Referring sites of AI assistants and answer engines → the name shown
AI_SOURCES = {
    "chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT",
    "perplexity.ai": "Perplexity", "www.perplexity.ai": "Perplexity",
    "gemini.google.com": "Gemini", "bard.google.com": "Gemini",
    "copilot.microsoft.com": "Microsoft Copilot",
    "claude.ai": "Claude", "you.com": "You.com",
}


def _range(source: DataSource, first: int = FIRST_SYNC_DAYS) -> tuple[date, date]:
    end = utcnow().date() - timedelta(days=1)  # yesterday: today isn't complete
    days = REFRESH_DAYS if source.synced_through else first
    return end - timedelta(days=days - 1), end


def _ga4_rows(report: dict) -> list[tuple[list[str], list[str]]]:
    return [([d["value"] for d in r.get("dimensionValues", [])],
             [m["value"] for m in r.get("metricValues", [])]) for r in report.get("rows", [])]


def _day(value: str) -> date:
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))  # GA4: YYYYMMDD


def sync_ga4(db: Session, source: DataSource, token: str) -> date | None:
    start, end = _range(source)
    if source.history_from is None:
        source.history_from = start
    dates = [{"startDate": start.isoformat(), "endDate": end.isoformat()}]
    totals = google.ga4_report(token, source.external_id, {
        "dateRanges": dates, "dimensions": [{"name": "date"}], "limit": 1000,
        "metrics": [{"name": m} for m in ("sessions", "totalUsers", "newUsers",
                                          "engagedSessions", "screenPageViews", "keyEvents")]})
    channels = google.ga4_report(token, source.external_id, {
        "dateRanges": dates, "limit": 10000,
        "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}]})
    ai = google.ga4_report(token, source.external_id, {
        "dateRanges": dates, "limit": 10000,
        "dimensions": [{"name": "date"}, {"name": "sessionSource"}],
        "metrics": [{"name": "sessions"}],
        "dimensionFilter": {"filter": {"fieldName": "sessionSource", "inListFilter": {
            "values": sorted(AI_SOURCES), "caseSensitive": False}}}})

    db.execute(delete(Ga4Daily).where(Ga4Daily.source_id == source.id,
                                      Ga4Daily.day.between(start, end)))
    db.execute(delete(Ga4Breakdown).where(Ga4Breakdown.source_id == source.id,
                                          Ga4Breakdown.day.between(start, end)))
    latest = None
    for (day,), (sessions, users, new, engaged, views, events) in _ga4_rows(totals):
        d = _day(day)
        latest = max(latest or d, d)
        db.add(Ga4Daily(source_id=source.id, organization_id=source.organization_id, day=d,
                        sessions=int(sessions), users=int(users), new_users=int(new),
                        engaged_sessions=int(engaged), page_views=int(views),
                        key_events=float(events)))
    for (day, channel), (sessions,) in _ga4_rows(channels):
        db.add(Ga4Breakdown(source_id=source.id, organization_id=source.organization_id,
                            day=_day(day), dimension="channel", value=channel[:200],
                            sessions=int(sessions)))
    merged: dict[tuple[date, str], int] = {}
    for (day, src), (sessions,) in _ga4_rows(ai):
        name = AI_SOURCES.get(src.lower())
        if name:
            key = (_day(day), name)
            merged[key] = merged.get(key, 0) + int(sessions)
    for (d, name), sessions in merged.items():
        db.add(Ga4Breakdown(source_id=source.id, organization_id=source.organization_id,
                            day=d, dimension="ai_source", value=name, sessions=sessions))
    _sync_ga4_pages(db, source, token)
    return latest or end


def _sync_ga4_pages(db: Session, source: DataSource, token: str) -> None:
    start, end = _range(source, FIRST_SYNC_PAGE_DAYS)
    if source.pages_from is None:
        source.pages_from = start
    report = google.ga4_report(token, source.external_id, {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": "date"}, {"name": "landingPage"}],
        "metrics": [{"name": "sessions"}, {"name": "keyEvents"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": MAX_PAGE_ROWS})
    db.execute(delete(Ga4Page).where(Ga4Page.source_id == source.id,
                                     Ga4Page.day.between(start, end)))
    merged: dict[tuple[date, str], list[float]] = {}
    for (day, path), (sessions, events) in _ga4_rows(report):
        path = (path or "(not set)")[:1000]
        row = merged.setdefault((_day(day), path), [0, 0.0])
        row[0] += int(sessions)
        row[1] += float(events)
    for (d, path), (sessions, events) in merged.items():
        db.add(Ga4Page(source_id=source.id, organization_id=source.organization_id, day=d,
                       path=path, sessions=sessions, key_events=events))


def sync_search_console(db: Session, source: DataSource, token: str) -> date | None:
    start, end = _range(source)
    if source.history_from is None:
        source.history_from = start
    daily = google.search_analytics(token, source.external_id, {
        "startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["date"],
        "rowLimit": 1000})
    db.execute(delete(GscDaily).where(GscDaily.source_id == source.id,
                                      GscDaily.day.between(start, end)))
    latest = None
    for row in daily.get("rows", []):
        d = date.fromisoformat(row["keys"][0])
        latest = max(latest or d, d)
        db.add(GscDaily(source_id=source.id, organization_id=source.organization_id, day=d,
                        clicks=int(row.get("clicks", 0)),
                        impressions=int(row.get("impressions", 0)),
                        position=float(row.get("position", 0))))
    period_end = latest or source.synced_through
    if period_end:
        queries = google.search_analytics(token, source.external_id, {
            "startDate": (period_end - timedelta(days=27)).isoformat(),
            "endDate": period_end.isoformat(), "dimensions": ["query"],
            "rowLimit": TOP_QUERIES})
        db.execute(delete(GscQuery).where(GscQuery.source_id == source.id))
        for row in queries.get("rows", []):
            db.add(GscQuery(source_id=source.id, organization_id=source.organization_id,
                            period_end=period_end, query=row["keys"][0][:500],
                            **_gsc_numbers(row)))
        window = {"startDate": (period_end - timedelta(days=27)).isoformat(),
                  "endDate": period_end.isoformat()}
        pages = google.search_analytics(token, source.external_id, {
            **window, "dimensions": ["page"], "rowLimit": TOP_PAGES})
        db.execute(delete(GscPage).where(GscPage.source_id == source.id))
        for row in pages.get("rows", []):
            db.add(GscPage(source_id=source.id, organization_id=source.organization_id,
                           period_end=period_end, page=row["keys"][0][:2048],
                           **_gsc_numbers(row)))
        pairs = google.search_analytics(token, source.external_id, {
            **window, "dimensions": ["query", "page"], "rowLimit": TOP_QUERY_PAGES})
        db.execute(delete(GscQueryPage).where(GscQueryPage.source_id == source.id))
        for row in pairs.get("rows", []):
            db.add(GscQueryPage(source_id=source.id, organization_id=source.organization_id,
                                period_end=period_end, query=row["keys"][0][:500],
                                page=row["keys"][1][:2048], **_gsc_numbers(row)))
    return latest


def _gsc_numbers(row: dict) -> dict:
    return {"clicks": int(row.get("clicks", 0)), "impressions": int(row.get("impressions", 0)),
            "position": float(row.get("position", 0))}


def sync_source(db: Session, source_id: uuid.UUID) -> None:
    source = db.get(DataSource, source_id)
    if source is None:
        return  # removed since it was queued
    integration = db.get(Integration, source.integration_id)
    try:
        token = access_token(db, integration)
        run = sync_ga4 if source.kind == "ga4" else sync_search_console
        latest = run(db, source, token)
    except google.GoogleError as exc:
        db.rollback()
        source = db.get(DataSource, source_id)
        source.sync_status, source.last_error = "failed", str(exc)[:500]
        source.last_synced_at = utcnow()
        db.commit()
        if exc.reconnect:
            return  # waits for the person to reconnect; retrying wouldn't help
        raise  # the job system retries
    source.sync_status, source.last_error, source.last_synced_at = "ok", None, utcnow()
    if latest:
        source.synced_through = max(source.synced_through or latest, latest)
    db.commit()


def sync_all(db: Session) -> int:
    """Nightly: queue a sync of every source whose connection works, except in suspended
    organizations."""
    ids = list(db.scalars(select(DataSource.id).join(
        Integration, Integration.id == DataSource.integration_id)
        .join(Organization, Organization.id == DataSource.organization_id)
        .where(Integration.status == "connected", Organization.status != "suspended")))
    for source_id in ids:
        source = db.get(DataSource, source_id)
        enqueue("integrations.sync", {"source_id": str(source_id)},
                organization_id=source.organization_id, dedupe_key=f"sync:{source_id}")
    return len(ids)


__all__ = ["AI_SOURCES", "sync_all", "sync_source"]
