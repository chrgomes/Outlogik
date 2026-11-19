"""The traffic and search summary for a workspace: the last N days against the N before.

Only days Outlogik has synced count. "previous" is None unless the whole previous period was
synced, so a comparison is never made against a partial period.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.integrations.models import (
    DataSource,
    Ga4Breakdown,
    Ga4Daily,
    GscDaily,
    GscQuery,
)

GA4_METRICS = ("sessions", "users", "new_users", "engaged_sessions", "page_views", "key_events")


def _windows(end: date, days: int) -> tuple[date, date, date]:
    start = end - timedelta(days=days - 1)
    return start, start - timedelta(days=days), start - timedelta(days=1)


def _ga4(db: Session, src: DataSource, days: int) -> dict:
    end = src.synced_through
    start, p_start, p_end = _windows(end, days)
    cols = [func.coalesce(func.sum(getattr(Ga4Daily, m)), 0) for m in GA4_METRICS]

    def totals(a, b):
        row = db.execute(select(*cols, func.count()).where(
            Ga4Daily.source_id == src.id, Ga4Daily.day.between(a, b))).one()
        return row[:-1], row[-1]

    now, _ = totals(start, end)
    before, before_days = totals(p_start, p_end)
    full = before_days >= days
    metrics = {m: {"value": float(now[i]), "previous": float(before[i]) if full else None}
               for i, m in enumerate(GA4_METRICS)}
    series = {d: (s, u) for d, s, u in db.execute(
        select(Ga4Daily.day, Ga4Daily.sessions, Ga4Daily.users).where(
            Ga4Daily.source_id == src.id, Ga4Daily.day.between(start, end)))}

    def shares(dimension):
        def by_value(a, b):
            return dict(db.execute(select(Ga4Breakdown.value, func.sum(Ga4Breakdown.sessions))
                                   .where(Ga4Breakdown.source_id == src.id,
                                          Ga4Breakdown.dimension == dimension,
                                          Ga4Breakdown.day.between(a, b))
                                   .group_by(Ga4Breakdown.value)).all())
        cur, prev = by_value(start, end), by_value(p_start, p_end)
        return sorted(({"name": k, "sessions": int(v), "previous": int(prev.get(k, 0))}
                       for k, v in cur.items()), key=lambda x: -x["sessions"])

    return {"start": start, "end": end, "metrics": metrics, "series": series,
            "channels": shares("channel"), "ai": shares("ai_source")}


def _gsc(db: Session, src: DataSource, days: int) -> dict:
    end = src.synced_through
    start, p_start, p_end = _windows(end, days)

    def totals(a, b):
        clicks, impressions, weighted, n = db.execute(select(
            func.coalesce(func.sum(GscDaily.clicks), 0),
            func.coalesce(func.sum(GscDaily.impressions), 0),
            func.coalesce(func.sum(GscDaily.position * GscDaily.impressions), 0),
            func.count()).where(GscDaily.source_id == src.id,
                                GscDaily.day.between(a, b))).one()
        return {"clicks": float(clicks), "impressions": float(impressions),
                "ctr": clicks / impressions if impressions else 0.0,
                # average position, weighted by impressions, as Search Console reports it
                "position": weighted / impressions if impressions else 0.0}, n

    now, _ = totals(start, end)
    before, before_days = totals(p_start, p_end)
    # Search Console can leave out days with no impressions, so most of the period is enough.
    full = before_days >= days * 0.8
    metrics = {k: {"value": v, "previous": before[k] if full else None} for k, v in now.items()}
    series = {d: (c, i) for d, c, i in db.execute(
        select(GscDaily.day, GscDaily.clicks, GscDaily.impressions).where(
            GscDaily.source_id == src.id, GscDaily.day.between(start, end)))}
    queries = list(db.scalars(select(GscQuery).where(GscQuery.source_id == src.id)
                              .order_by(GscQuery.clicks.desc(), GscQuery.impressions.desc())
                              .limit(25)))
    return {"start": start, "end": end, "metrics": metrics, "series": series,
            "queries": [{"query": q.query, "clicks": q.clicks, "impressions": q.impressions,
                         "ctr": q.clicks / q.impressions if q.impressions else 0.0,
                         "position": q.position} for q in queries],
            "queries_through": queries[0].period_end if queries else None}


def summary(db: Session, sources: list[DataSource], days: int) -> dict:
    by_kind = {s.kind: s for s in sources if s.synced_through}
    ga4 = _ga4(db, by_kind["ga4"], days) if "ga4" in by_kind else None
    gsc = _gsc(db, by_kind["search_console"], days) if "search_console" in by_kind else None
    parts = [p for p in (ga4, gsc) if p]
    # The chart covers the last `days` days with any data; each source's totals cover its own
    # last `days` days (Search Console runs 2–3 days behind Analytics).
    end = max((p["end"] for p in parts), default=None)
    start = end - timedelta(days=days - 1) if end else None
    series = []
    if start:
        day = start
        while day <= end:
            point = {"day": day}
            if ga4 and ga4["start"] <= day <= ga4["end"]:
                point["sessions"], point["users"] = ga4["series"].get(day, (0, 0))
            if gsc and gsc["start"] <= day <= gsc["end"]:
                point["clicks"], point["impressions"] = gsc["series"].get(day, (0, 0))
            series.append(point)
            day += timedelta(days=1)
    return {"days": days, "start": start, "end": end,
            "ga4": ga4["metrics"] if ga4 else None,
            "search_console": gsc["metrics"] if gsc else None,
            "series": series,
            "channels": ga4["channels"] if ga4 else [],
            "ai_referrals": ga4["ai"] if ga4 else [],
            "top_queries": gsc["queries"] if gsc else [],
            "top_queries_through": gsc["queries_through"] if gsc else None}
