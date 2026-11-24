"""CSV files from a saved report: one per table, only for the sections the report includes.

Text that came from outside (search terms, page addresses, titles) could start with `=`, `+`,
`-` or `@`, which spreadsheet apps run as a formula ("CSV injection"). Such cells get a leading
apostrophe, as OWASP recommends, so they open as plain text.
"""

import csv
import io
from collections.abc import Callable

from app.modules.reports.models import Report

FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _safe(value):
    if isinstance(value, str) and value.startswith(FORMULA_START):
        return "'" + value
    return value


def _daily(d: dict) -> list[list]:
    return [[p["day"], p["sessions"], p["previous_sessions"], p["clicks"], p["impressions"]]
            for p in d["dashboard"]["series"]]


def _shares(key: str) -> Callable[[dict], list[list]]:
    return lambda d: [[r["name"], r["sessions"], r["previous"]] for r in d["dashboard"][key]]


# name → (section, file label, header, rows)
TABLES: dict[str, tuple[str, str, list[str], Callable[[dict], list[list]]]] = {
    "daily": ("traffic", "Daily figures",
              ["Day", "Visits", "Visits (comparison period)", "Search clicks",
               "Search impressions"], _daily),
    "channels": ("traffic", "Where visits came from",
                 ["Channel", "Visits", "Visits (comparison period)"], _shares("channels")),
    "pages": ("traffic", "Pages that bring the most visits",
              ["Landing page", "Visits", "Visits (comparison period)", "Key events"],
              lambda d: [[r["path"], r["sessions"], r["previous"], r["key_events"]]
                         for r in d["dashboard"]["top_pages"]]),
    "ai_tools": ("ai", "Visits from AI tools",
                 ["AI tool", "Visits", "Visits (comparison period)"], _shares("ai_referrals")),
    "searches": ("search", "Top Google searches",
                 ["Search", "Clicks", "Impressions", "Click rate", "Average position"],
                 lambda d: [[r["query"], r["clicks"], r["impressions"], round(r["ctr"], 4),
                             round(r["position"], 1)] for r in d["dashboard"]["top_queries"]]),
    "almost_ranking": ("search", "Searches you almost rank for",
                       ["Search", "Page", "Clicks", "Impressions", "Average position"],
                       lambda d: [[r["query"], r["page"], r["clicks"], r["impressions"],
                                   round(r["position"], 1)]
                                  for r in d["dashboard"]["almost_ranking"]]),
    "rarely_clicked": ("search", "Shown in search, rarely clicked",
                       ["Page", "Clicks", "Impressions", "Click rate", "Average position"],
                       lambda d: [[r["page"], r["clicks"], r["impressions"], round(r["ctr"], 4),
                                   round(r["position"], 1)]
                                  for r in d["dashboard"]["low_ctr_pages"]]),
    "audit_issues": ("audit", "Website audit issues",
                     ["Issue", "Severity", "Area", "Pages or items", "New since last audit",
                      "How to fix it"],
                     lambda d: [[i["title"], i["severity"], i["area"], i["count"], i["new"],
                                 i["fix"]] for i in d["audit_issues"]]),
}


def available(report: Report) -> list[dict]:
    """The CSV files this report has, with at least one row."""
    return [{"name": name, "label": label}
            for name, (section, label, _, rows) in TABLES.items()
            if section in report.sections and rows(report.data)]


def to_csv(report: Report, name: str) -> str:
    _, _, header, rows = TABLES[name]
    out = io.StringIO()
    out.write("﻿")  # so Excel reads accents correctly
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows(report.data):
        writer.writerow([_safe(v) if v is not None else "" for v in row])
    return out.getvalue()
