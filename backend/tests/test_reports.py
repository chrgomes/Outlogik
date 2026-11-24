# ruff: noqa: F811 - pytest fixtures shared from test_integrations and test_dashboards
"""H1-9: saved reports, their PDF and their CSV files."""

import csv
import io
from datetime import timedelta

import pytest
from pypdf import PdfReader
from sqlalchemy import select, update

from app.core.models import utcnow
from app.models import AuditLog, Ga4Daily, GscQuery, Organization, Report, Workspace
from tests.conftest import (
    link_client,
    login,
    register,
    seed_client,
    seed_member,
    signed_in_as,
    slug_of,
    token_from_last_email,
)
from tests.test_dashboards import seed_audits, synced  # noqa: F401 - fixtures
from tests.test_integrations import bakery, choose, connect, fake  # noqa: F401 - fixtures

API = "/api/v1/orgs"
ALL = ["traffic", "ai", "search", "audit"]


def make(client, base, slug, **body):
    body.setdefault("sections", ALL)
    res = client.post(f"{base}/reports", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def pdf_text(client, slug, report_id) -> str:
    res = client.get(f"{API}/{slug}/reports/{report_id}/pdf")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(res.content)).pages)


def csv_rows(client, slug, report_id, table) -> list[list[str]]:
    res = client.get(f"{API}/{slug}/reports/{report_id}/csv/{table}")
    assert res.status_code == 200, res.text
    assert res.text.startswith("﻿")
    return list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))


@pytest.fixture
def full(client, db, synced):
    slug, ws, base = synced
    seed_audits(db, ws, [(3, 4, [("page_broken", "/a"), ("page_broken", "/b"),
                                 ("slow_page", "/c")]),
                         (2, 4, [("page_broken", "/a"), ("slow_page", "/c"),
                                 ("slow_page", "/d")])])
    return slug, ws, base


# --- making a report ------------------------------------------------------------------------

def test_a_report_names_its_period_sources_and_what_is_unavailable(client, db, full):
    slug, ws, base = full
    r = make(client, base, slug)
    yesterday = utcnow().date() - timedelta(days=1)
    assert r["title"] == "Bakery: marketing report" and r["sections"] == ALL
    assert r["period_end"] == yesterday.isoformat() and r["compare"] == "previous"
    assert [s["name"] for s in r["sources"]] == [
        "Google Analytics 4", "Google Search Console", "Outlogik website audit"]
    assert r["sources"][0]["detail"] == "bakery.example.com (Bakery)"
    assert any("Search Console reports 2–3 days behind" in u for u in r["unavailable"])
    assert {f["name"] for f in r["csv_files"]} == {
        "daily", "channels", "pages", "ai_tools", "searches", "almost_ranking",
        "rarely_clicked", "audit_issues"}
    assert r["created_by"] == "Olive Owner"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "report.create"))


def test_the_pdf_has_every_part_of_the_report(client, full):
    slug, _, base = full
    r = make(client, base, slug, title="November report", compare="year")
    text = pdf_text(client, slug, r["id"])
    for part in ("November report", "Prepared by Bakery", "About this report",
                 "Google Analytics 4: bakery.example.com (Bakery)", "Not available or limited",
                 "Outlogik doesn't estimate", "What changed", "Key figures", "Visits per day",
                 "Where visits came from", "Pages that bring the most visits",
                 "Visits from AI tools", "ChatGPT", "Google search", "sourdough near me",
                 "Searches you almost rank for", "birthday cakes toronto",
                 "Shown in search, rarely clicked", "Website audit", "HOW TO FIX IT",
                 "compared with the same period last year", "Page 1"):
        assert part in text, part


def test_pdf_download_name_is_safe(client, full):
    slug, _, base = full
    r = make(client, base, slug, title='Q4 "report" / ../etc')
    res = client.get(f"{API}/{slug}/reports/{r['id']}/pdf")
    name = res.headers["content-disposition"]
    assert name.startswith('attachment; filename="Q4-report-etc-') and name.endswith('.pdf"')


def test_text_from_outside_cannot_change_the_pdf(client, db, full):
    """Search terms are typed by strangers. ReportLab markup in them is shown, not obeyed."""
    slug, _, base = full
    db.execute(update(GscQuery).where(GscQuery.query == "sourdough near me")
               .values(query='<font size="60">big</font> & <b>bold</b> 你好'))
    db.commit()
    text = pdf_text(client, slug, make(client, base, slug)["id"])
    assert '<font size="60">big</font> & <b>bold</b> ??' in text


def test_a_report_keeps_its_numbers_after_new_syncs(client, db, full):
    slug, _, base = full
    r = make(client, base, slug)
    before = csv_rows(client, slug, r["id"], "daily")
    db.execute(update(Ga4Daily).values(sessions=999))
    db.commit()
    assert csv_rows(client, slug, r["id"], "daily") == before
    assert before[-1][1] == "100"


def test_only_the_chosen_sections(client, full):
    slug, _, base = full
    r = make(client, base, slug, sections=["audit"])
    assert [s["name"] for s in r["sources"]] == ["Outlogik website audit"]
    assert [f["name"] for f in r["csv_files"]] == ["audit_issues"]
    text = pdf_text(client, slug, r["id"])
    assert "Website audit" in text and "Visits per day" not in text
    res = client.get(f"{API}/{slug}/reports/{r['id']}/csv/daily")
    assert res.status_code == 404
    res = client.post(f"{base}/reports", json={"sections": []})
    assert res.status_code == 422


def test_a_report_before_anything_is_connected_says_so(client, bakery):
    slug, _, base = bakery
    r = make(client, base, slug)
    assert r["sources"] == []
    assert r["unavailable"] == [
        "Traffic and visits from AI tools: Google Analytics isn't connected.",
        "Google search: Search Console isn't connected.",
        "Website audit: no audit has been run yet."]
    assert "Search Console isn't connected" in pdf_text(client, slug, r["id"])


def test_custom_period(client, full):
    slug, _, base = full
    end = utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=6)
    r = make(client, base, slug, start=start.isoformat(), end=end.isoformat(), compare="none")
    assert (r["period_start"], r["period_end"]) == (start.isoformat(), end.isoformat())
    assert r["compare_start"] is None
    assert len(csv_rows(client, slug, r["id"], "daily")) == 8  # header and 7 days


# --- CSV ------------------------------------------------------------------------------------

def test_csv_cells_that_look_like_formulas_are_made_safe(client, db, full):
    slug, _, base = full
    db.execute(update(GscQuery).where(GscQuery.query == "sourdough near me")
               .values(query='=HYPERLINK("http://evil.example.com","x")'))
    db.commit()
    rows = csv_rows(client, slug, make(client, base, slug)["id"], "searches")
    assert rows[0] == ["Search", "Clicks", "Impressions", "Click rate", "Average position"]
    assert rows[1][0] == '\'=HYPERLINK("http://evil.example.com","x")'
    assert rows[1][1] == "40"


def test_csv_audit_issues_include_how_to_fix(client, full):
    slug, _, base = full
    rows = csv_rows(client, slug, make(client, base, slug)["id"], "audit_issues")
    assert rows[0][-1] == "How to fix it"
    assert rows[1][1] == "error" and rows[1][-1]


def test_unknown_csv_table(client, full):
    slug, _, base = full
    r = make(client, base, slug)
    assert client.get(f"{API}/{slug}/reports/{r['id']}/csv/passwords").status_code == 422


# --- listing, deleting, who may do what ----------------------------------------------------

def test_list_and_delete(client, db, full):
    slug, ws, base = full
    a = make(client, base, slug, title="First")
    b = make(client, base, slug, title="Second")
    listed = client.get(f"{API}/{slug}/reports").json()
    assert [r["title"] for r in listed] == ["Second", "First"]
    assert client.get(f"{API}/{slug}/reports", params={"workspace_id": ws}).json()[0]["id"] \
        == b["id"]
    assert client.delete(f"{API}/{slug}/reports/{a['id']}").status_code == 204
    assert client.get(f"{API}/{slug}/reports/{a['id']}").status_code == 404
    assert db.scalar(select(AuditLog).where(AuditLog.action == "report.delete"))


def test_viewers_read_but_dont_make_reports(client, new_client, db, full):
    slug, _, base = full
    r = make(client, base, slug)
    viewer, _ = signed_in_as(new_client, db, slug, "v@bakery.example.com", "viewer")
    assert viewer.get(f"{API}/{slug}/reports/{r['id']}/pdf").status_code == 200
    assert viewer.post(f"{base}/reports", json={"sections": ALL}).status_code == 403
    assert viewer.delete(f"{API}/{slug}/reports/{r['id']}").status_code == 403


def test_sections_follow_the_role(client, new_client, db, full):
    """A role that can't see traffic can't make or open a report with traffic in it."""
    slug, _, base = full
    traffic = make(client, base, slug)
    audit_only = make(client, base, slug, sections=["audit"])
    role = client.post(f"{API}/{slug}/roles", json={"name": "Audits only", "permissions": [
        "organization.read", "dashboard.read", "audits.read", "reports.read",
        "reports.create"]}).json()
    browser, member = signed_in_as(new_client, db, slug, "a@bakery.example.com", "member")
    client.patch(f"{API}/{slug}/members/{member.id}", json={"role_id": role["id"]})
    res = browser.post(f"{base}/reports", json={"sections": ["traffic", "audit"]})
    assert res.status_code == 403 and res.json()["error"]["code"] == "section_not_allowed"
    assert browser.post(f"{base}/reports", json={"sections": ["audit"]}).status_code == 201
    assert browser.get(f"{API}/{slug}/reports/{traffic['id']}").status_code == 404
    ids = {r["id"] for r in browser.get(f"{API}/{slug}/reports").json()}
    assert audit_only["id"] in ids and traffic["id"] not in ids


def test_client_portal_users_see_only_their_reports(new_client, db, fake):
    agency = new_client()
    slug = slug_of(register(agency, "owner@agency.example.com", org="Agency"))
    alpha, beta = seed_client(db, slug, "Alpha"), seed_client(db, slug, "Beta")
    ws = {c.name: db.scalar(select(Workspace.id).where(Workspace.client_id == c.id))
          for c in (alpha, beta)}
    a = make(agency, f"{API}/{slug}/workspaces/{ws['Alpha']}", slug, sections=["audit"])
    b = make(agency, f"{API}/{slug}/workspaces/{ws['Beta']}", slug, sections=["audit"])
    assert a["title"] == "Alpha: marketing report"
    portal = seed_member(db, slug, "jo@alpha.example.com", "client")
    link_client(db, portal, alpha)
    browser = new_client()
    login(browser, "jo@alpha.example.com")
    assert [r["id"] for r in browser.get(f"{API}/{slug}/reports").json()] == [a["id"]]
    assert browser.get(f"{API}/{slug}/reports/{b['id']}/pdf").status_code == 404
    assert "Prepared by Agency for Alpha" in pdf_text(browser, slug, a["id"])


def test_an_agencys_report_on_a_shared_workspace_stays_the_agencys(new_client, db, fake):
    business = new_client()
    bslug = slug_of(register(business, "owner@shop.example.com", org="Shop",
                             account_type="business"))
    agency = new_client()
    aslug = slug_of(register(agency, "owner@agency.example.com", org="Agency"))
    business.post(f"{API}/{bslug}/access-grants", json={"email": "owner@agency.example.com",
                                                        "access": "view"})
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == aslug))
    agency.post("/api/v1/access-grants/accept", json={
        "token": token_from_last_email("/agency-access"), "organization_id": str(agency_id)})
    shared = db.scalar(select(Workspace.id).join(Organization).where(Organization.slug == bslug))
    r = make(agency, f"{API}/{aslug}/workspaces/{shared}", aslug, sections=["audit"])
    assert db.get(Report, r["id"]).organization_id == agency_id
    assert "Prepared by Agency for Shop" in pdf_text(agency, aslug, r["id"])
    assert business.get(f"{API}/{bslug}/reports").json() == []
