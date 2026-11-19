# ruff: noqa: F811 - pytest fixtures shared from test_integrations
"""H1-8: the workspace dashboard and the agency overview.

Google data comes from the fake Google in test_integrations, synced through the real code.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.models import utcnow
from app.models import Audit, AuditIssue, Ga4Daily, Organization, Website, Workspace
from tests.conftest import link_client, register, seed_client, seed_member, signed_in_as, slug_of
from tests.test_integrations import bakery, choose, connect, fake  # noqa: F401 - fixtures

API = "/api/v1/orgs"


def seed_audits(db, ws_id, history):
    """Completed audits of the workspace's first website: one per (errors, warnings, issues)."""
    site = db.scalar(select(Website).where(Website.workspace_id == ws_id))
    if site is None:
        org_id = db.scalar(select(Workspace.organization_id).where(Workspace.id == ws_id))
        site = Website(organization_id=org_id, workspace_id=ws_id, name="Bakery",
                       url="https://bakery.example.com", domain="bakery.example.com")
        db.add(site)
        db.flush()
    now = utcnow()
    for i, (errors, warnings, keys) in enumerate(history):
        when = now - timedelta(days=30 * (len(history) - i))
        a = Audit(organization_id=site.organization_id, workspace_id=ws_id, website_id=site.id,
                  url=site.url, page_limit=100, status="completed", errors=errors,
                  warnings=warnings, pages_crawled=10, created_at=when, finished_at=when)
        db.add(a)
        db.flush()
        for key, url in keys:
            db.add(AuditIssue(audit_id=a.id, organization_id=site.organization_id,
                              check_key=key, severity="error" if key == "page_broken"
                              else "warning", area="technical", url=url, details={}))
    db.commit()
    return site


@pytest.fixture
def synced(client, fake, bakery):
    slug, ws, base = bakery
    connect(client, base)
    choose(client, base)
    return slug, ws, base


def dash(client, base, **params):
    res = client.get(f"{base}/dashboard", params=params)
    assert res.status_code == 200, res.text
    return res.json()


# --- the workspace dashboard ----------------------------------------------------------------

def test_default_period_compares_the_last_28_days_with_the_28_before(client, synced):
    _, _, base = synced
    d = dash(client, base)
    yesterday = utcnow().date() - timedelta(days=1)
    assert d["period"]["end"] == yesterday.isoformat() and d["period"]["days"] == 28
    assert d["ga4"]["metrics"]["sessions"] == {"value": 2800.0, "previous": 2800.0}
    assert d["search_console"]["through"] == (yesterday - timedelta(days=2)).isoformat()
    assert d["series"][-1]["sessions"] == 100 and d["series"][-1]["previous_sessions"] == 100
    assert d["series"][-1]["clicks"] is None  # Search Console hasn't reported it yet
    assert d["ai_referrals"][0] == {"name": "ChatGPT", "sessions": 112, "previous": 112}
    assert d["changes"] == [
        "Visits are about the same (2,800) compared with before.",
        "AI tools sent the same number of visits as before; ChatGPT sent 112 of the 168.",
        "Google search clicks are about the same (260).",
    ]


def test_same_period_last_year_uses_the_16_month_history(client, synced):
    _, _, base = synced
    d = dash(client, base, compare="year")
    assert d["period"]["compare"] == "year"
    assert d["ga4"]["metrics"]["sessions"]["previous"] == 2800.0
    assert d["changes"][0].endswith("compared with the same period last year.")
    # Visits by page only go back 90 days, so pages have no year-ago numbers.
    assert {p["previous"] for p in d["top_pages"]} == {None}


def test_no_comparison(client, synced):
    _, _, base = synced
    d = dash(client, base, compare="none")
    assert d["ga4"]["metrics"]["sessions"]["previous"] is None
    assert d["changes"] == [] and "previous_sessions" not in [
        k for k, v in d["series"][-1].items() if v is not None]


def test_comparison_left_out_before_the_history_starts(client, db, synced):
    _, _, base = synced
    d = dash(client, base, days=365, compare="year")
    assert d["ga4"]["metrics"]["sessions"]["previous"] is None
    assert not any(c.startswith("Visits") for c in d["changes"])


def test_visits_change_is_explained_by_the_channel_that_moved(client, db, synced):
    _, _, base = synced
    start = utcnow().date() - timedelta(days=28)
    db.execute(update(Ga4Daily).where(Ga4Daily.day >= start).values(sessions=150))
    from app.models import Ga4Breakdown
    db.execute(update(Ga4Breakdown).where(Ga4Breakdown.day >= start,
                                          Ga4Breakdown.value == "Organic Search")
               .values(sessions=120))
    db.commit()
    assert dash(client, base)["changes"][0] == (
        "Visits are up 50% (4,200), mostly from Organic Search (+1,400) compared with before.")


def test_custom_period_and_its_limits(client, synced):
    _, _, base = synced
    end = utcnow().date() - timedelta(days=1)
    d = dash(client, base, start=(end - timedelta(days=6)).isoformat(), end=end.isoformat())
    assert d["period"]["days"] == 7 and d["ga4"]["metrics"]["sessions"]["value"] == 700
    for params in ({"start": end.isoformat()}, {"start": end.isoformat(),
                                                "end": (end - timedelta(days=1)).isoformat()},
                   {"start": (end - timedelta(days=600)).isoformat(), "end": end.isoformat()}):
        res = client.get(f"{base}/dashboard", params=params)
        assert res.status_code == 422 and res.json()["error"]["code"] == "invalid_period"


def test_top_pages_almost_ranking_and_rarely_clicked(client, synced):
    _, _, base = synced
    d = dash(client, base)
    assert d["top_pages"][0] == {"path": "/", "sessions": 1680, "previous": 1680,
                                 "key_events": 56.0}
    assert [a["query"] for a in d["almost_ranking"]] == ["birthday cakes toronto",
                                                         "wedding cakes"]
    assert [p["page"] for p in d["low_ctr_pages"]] == ["https://bakery.example.com/cakes"]
    assert d["site_ctr"] == pytest.approx(209 / 5100)
    assert d["top_queries"][0]["query"] == "sourdough near me"


def test_latest_audit_with_history_and_what_to_fix_first(client, db, synced):
    _, ws, base = synced
    seed_audits(db, ws, [
        (3, 4, [("page_broken", "/a"), ("page_broken", "/b"), ("slow_page", "/c")]),
        (2, 4, [("page_broken", "/a"), ("slow_page", "/c"), ("slow_page", "/d")]),
    ])
    d = dash(client, base)
    a = d["audit"]
    assert (a["errors"], a["warnings"]) == (2, 4)
    assert [(h["errors"], h["warnings"]) for h in a["history"]] == [(3, 4), (2, 4)]
    assert (a["new_issues"], a["fixed_issues"]) == (1, 1)
    assert [f["check"] for f in a["fix_first"]] == ["page_broken", "slow_page"]
    assert d["changes"][-1] == (
        "The latest audit found 1 new issue and 1 fixed since the one before.")


def test_nothing_connected_yet(client, bakery):
    _, _, base = bakery
    d = dash(client, base)
    assert d["setup"] == {"websites": 0, "audited": False, "google": "not_connected",
                          "ga4": False, "search_console": False, "analytics_visible": True,
                          "audits_visible": True}
    assert d["ga4"] is None and d["audit"] is None and d["changes"] == []
    assert d["top_pages"] == [] and d["almost_ranking"] == []


def test_without_analytics_or_audit_permission_those_parts_are_left_out(
        client, new_client, db, synced):
    slug, ws, base = synced
    seed_audits(db, ws, [(1, 0, [])])
    role = client.post(f"{API}/{slug}/roles", json={
        "name": "Dashboard only", "permissions": ["organization.read", "dashboard.read"]}).json()
    browser, member = signed_in_as(new_client, db, slug, "d@bakery.example.com", "member")
    client.patch(f"{API}/{slug}/members/{member.id}", json={"role_id": role["id"]})
    d = dash(browser, base)
    assert d["ga4"] is None and d["search_console"] is None and d["audit"] is None
    assert d["setup"]["analytics_visible"] is False and d["changes"] == []


# --- the agency overview --------------------------------------------------------------------

@pytest.fixture
def agency(client, new_client, db, fake):
    slug = slug_of(register(new_client_browser := new_client(), "owner@agency.example.com",
                            org="Agency"))
    alpha, beta = seed_client(db, slug, "Alpha Dental"), seed_client(db, slug, "Beta Cycles")
    ws = {c.name: db.scalar(select(Workspace.id).where(Workspace.client_id == c.id))
          for c in (alpha, beta)}
    base = f"{API}/{slug}/workspaces/{ws['Alpha Dental']}"
    connect(new_client_browser, base)
    choose(new_client_browser, base)
    seed_audits(db, ws["Beta Cycles"], [(2, 1, [("page_broken", "/x")])])
    return {"slug": slug, "browser": new_client_browser, "ws": ws,
            "alpha": alpha, "beta": beta}


def test_overview_compares_clients_and_lists_what_needs_attention(db, agency):
    b, slug = agency["browser"], agency["slug"]
    res = b.get(f"{API}/{slug}/dashboard/overview")
    assert res.status_code == 200, res.text
    o = res.json()
    rows = {r["name"]: r for r in o["workspaces"]}
    alpha, beta = rows["Alpha Dental"], rows["Beta Cycles"]
    assert alpha["visits"] == 2800 and alpha["visits_previous"] == 2800
    assert alpha["ai_visits"] == 168 and alpha["google"] == "connected"
    assert len(alpha["spark"]) == 28 and alpha["audit"] is None
    assert beta["visits"] is None and beta["google"] == "not_connected"
    assert beta["audit"] == {"errors": 2, "warnings": 1}
    assert o["totals"]["visits"] == 2800 and o["totals"]["with_audit_errors"] == 1
    assert o["totals"]["clients"] == 2 and o["totals"]["websites"] == 1
    assert len(o["weekly"]) == 12 and o["weekly"][-1]["sessions"] == 700
    kinds = [(a["name"], a["kind"]) for a in o["attention"]]
    assert ("Beta Cycles", "audit_errors") in kinds and ("Beta Cycles", "not_connected") in kinds
    assert ("Agency", "not_connected") in kinds  # its own workspace
    assert kinds.index(("Beta Cycles", "audit_errors")) < kinds.index(
        ("Beta Cycles", "not_connected"))


def test_a_big_drop_in_visits_needs_attention(db, agency):
    b, slug = agency["browser"], agency["slug"]
    start = utcnow().date() - timedelta(days=28)
    db.execute(update(Ga4Daily).where(Ga4Daily.day >= start).values(sessions=60))
    db.commit()
    o = b.get(f"{API}/{slug}/dashboard/overview").json()
    drop = next(a for a in o["attention"] if a["kind"] == "visits_drop")
    assert drop["name"] == "Alpha Dental" and drop["text"].startswith("Visits down 40%")


def test_reconnect_needed_comes_first(db, agency):
    from app.models import Integration

    db.execute(update(Integration).values(status="error"))
    db.commit()
    o = agency["browser"].get(f"{API}/{agency['slug']}/dashboard/overview").json()
    assert o["attention"][0]["kind"] == "reconnect"


def test_account_managers_reviews_and_my_clients(new_client, db, agency):
    b, slug, ws = agency["browser"], agency["slug"], agency["ws"]
    am_browser, am = signed_in_as(new_client, db, slug, "am@agency.example.com",
                                  "account_manager")
    b.put(f"{API}/{slug}/members/{am.id}/workspaces",
          json={"workspace_ids": [str(ws["Alpha Dental"])]})
    res = am_browser.put(f"{API}/{slug}/workspaces/{ws['Alpha Dental']}/review")
    assert res.status_code == 200 and res.json()["reviewed_by"] == "Am"
    rows = {r["name"]: r for r in b.get(f"{API}/{slug}/dashboard/overview").json()["workspaces"]}
    alpha = rows["Alpha Dental"]
    assert alpha["managers"] == ["Am"]
    assert alpha["review"]["reviewed_by"] == "Am"
    mine = {r["name"]: r for r in
            am_browser.get(f"{API}/{slug}/dashboard/overview").json()["workspaces"]}
    assert list(mine) == ["Alpha Dental"] and mine["Alpha Dental"]["assigned_to_me"]


def test_client_portal_users_see_numbers_but_not_the_team(new_client, db, agency):
    slug = agency["slug"]
    portal = seed_member(db, slug, "jo@alpha.example.com", "client")
    link_client(db, portal, agency["alpha"])
    from tests.conftest import login
    browser = new_client()
    login(browser, "jo@alpha.example.com")
    o = browser.get(f"{API}/{slug}/dashboard/overview").json()
    assert [r["name"] for r in o["workspaces"]] == ["Alpha Dental"]
    row = o["workspaces"][0]
    assert row["visits"] == 2800 and row["managers"] is None and row["review"] is None
    res = browser.put(f"{API}/{slug}/workspaces/{agency['ws']['Alpha Dental']}/review")
    assert res.status_code == 403


def test_archived_clients_are_left_out(db, agency):
    from app.models import Client

    db.execute(update(Client).where(Client.id == agency["beta"].id).values(status="archived"))
    db.commit()
    o = agency["browser"].get(f"{API}/{agency['slug']}/dashboard/overview").json()
    assert "Beta Cycles" not in [r["name"] for r in o["workspaces"]]


def test_reviews_belong_to_the_reviewing_organization(new_client, db, agency):
    """An agency's review of a business's shared workspace isn't visible to the business."""
    from app.models import WorkspaceReview
    from tests.conftest import token_from_last_email

    business = new_client()
    bslug = slug_of(register(business, "owner@shop.example.com", org="Shop",
                             account_type="business"))
    business.post(f"{API}/{bslug}/access-grants", json={"email": "owner@agency.example.com",
                                                        "access": "view"})
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == agency["slug"]))
    agency["browser"].post("/api/v1/access-grants/accept", json={
        "token": token_from_last_email("/agency-access"), "organization_id": str(agency_id)})
    shared = db.scalar(select(Workspace.id).join(Organization).where(Organization.slug == bslug))
    res = agency["browser"].put(f"{API}/{agency['slug']}/workspaces/{shared}/review")
    assert res.status_code == 200  # view-only access still allows the agency's own note
    review = db.scalar(select(WorkspaceReview).where(WorkspaceReview.workspace_id == shared))
    assert review.organization_id == agency_id
    rows = business.get(f"{API}/{bslug}/dashboard/overview").json()["workspaces"]
    assert rows[0]["review"] is None
