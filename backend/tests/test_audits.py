"""H1-6: website audits end to end: starting one through the API, the crawl and checks running
as a job, results, comparison with the previous audit, limits, schedules and access."""

import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.models import utcnow
from app.models import Audit, Organization, UsageRecord, Website, Workspace
from app.modules.audits import pagespeed
from app.modules.audits.service import schedule_due
from app.modules.plans.service import set_plan
from tests.conftest import register, signed_in_as, slug_of, token_from_last_email

API = "/api/v1/orgs"
PAGES: dict[str, tuple[int, str, str]] = {}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        status, ctype, body = PAGES.get(self.path, (404, "text/html", "<title>Not found</title>"))
        self.send_response(status)
        if status in (301, 302):
            self.send_header("Location", body)
            body = ""
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


def page(title, body="", head="", lang="en"):
    words = " ".join(["word"] * 250)
    return (200, "text/html", f"<html lang='{lang}'><head><title>{title}</title>"
            f"<meta name='viewport' content='width=device-width'>"
            f"<meta name='description' content='About {title}.'>{head}</head>"
            f"<body><h1>{title}</h1>{body}<p>{words}</p></body></html>")


BUSINESS = ('<script type="application/ld+json">{"@type":"LocalBusiness","name":"Corner Bakery",'
            '"telephone":"%s"}</script>')


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setattr(get_settings(), "crawler_allow_private", True)
    monkeypatch.setattr(get_settings(), "crawler_delay_seconds", 0)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    PAGES.clear()
    PAGES.update({
        "/": page("Corner Bakery home", "<a href='/menu'>Menu</a> <a href='/old-page'>Old</a> "
                  "<a href='/faq'>FAQ</a> <img src='bread.jpg'>", head=BUSINESS % "416-555-0100"),
        "/menu": page("Menu", "<a href='/'>Home</a>", head=BUSINESS % "416-555-0199"),
        "/faq": page("Questions", "<h2>Do you deliver?</h2><h2>Are you open Sundays?</h2>"),
        "/robots.txt": (200, "text/plain", "User-agent: GPTBot\nDisallow: /\n\n"
                        "User-agent: PerplexityBot\nDisallow: /\n"),
    })
    yield base
    server.shutdown()


@pytest.fixture
def business(client, db, site):
    slug = slug_of(register(client, "owner@bakery.example.com", org="Bakery",
                            account_type="business"))
    org = db.scalar(select(Organization).where(Organization.slug == slug))
    ws = db.scalar(select(Workspace).where(Workspace.organization_id == org.id))
    # Added directly: the API refuses local addresses (as it should).
    website = Website(organization_id=org.id, workspace_id=ws.id, url=site, domain="127.0.0.1",
                      name="Corner Bakery")
    db.add(website)
    db.commit()
    return {"slug": slug, "org": org, "ws": str(ws.id), "site": str(website.id)}


def audits_url(b, *parts):
    return "/".join([f"{API}/{b['slug']}/workspaces/{b['ws']}/audits", *map(str, parts)])


def run_audit(c, b):
    res = c.post(audits_url(b), json={"website_id": b["site"]})
    assert res.status_code == 202, res.text
    return res.json()["id"]


def groups(c, b, audit_id):
    return {g["check"]: g for g in c.get(audits_url(b, audit_id, "issues")).json()}


# --- running and results --------------------------------------------------------------------

def test_an_audit_finds_the_sites_problems(client, business):
    audit_id = run_audit(client, business)
    detail = client.get(audits_url(business, audit_id)).json()
    assert detail["status"] == "completed" and detail["pages_crawled"] == 4
    assert detail["errors"] >= 1 and detail["new_issues"] is None  # nothing to compare yet
    found = groups(client, business, audit_id)

    broken = found["page_broken"]
    assert broken["severity"] == "error" and broken["area"] == "technical"
    assert broken["items"][0]["url"].endswith("/old-page")
    assert broken["items"][0]["details"]["linked_from"].endswith("/")
    assert "Fix or remove the links" in broken["fix"]
    assert found["images_missing_alt"]["items"][0]["details"] == {"images": 1, "of": 1}
    assert found["not_https"]["severity"] == "error"
    assert found["sitemap_missing"]["area"] == "technical"
    # AI search readiness
    blocked = found["ai_search_crawlers_blocked"]["items"][0]["details"]["blocked"]
    assert blocked == ["PerplexityBot (Perplexity)"]  # GPTBot (training) isn't an issue
    inconsistent = found["business_details_inconsistent"]["items"][0]["details"]
    assert set(inconsistent["telephone"]) == {"4165550100", "4165550199"}
    assert found["questions_not_marked_up"]["items"][0]["url"].endswith("/faq")
    assert detail["facts"]["ai_training_crawlers"]["GPTBot"] is False
    assert detail["facts"]["pagespeed"] == {"connected": False}
    # Most serious first.
    listed = client.get(audits_url(business, audit_id, "issues")).json()
    severities = [g["severity"] for g in listed]
    assert severities == sorted(severities, key=["error", "warning", "notice"].index)
    pages = client.get(audits_url(business, audit_id, "pages")).json()
    assert {p["status_code"] for p in pages} == {200, 404}


def test_the_next_audit_shows_what_is_new_and_what_was_fixed(client, business):
    first = run_audit(client, business)
    # Fix the broken link and the inconsistent phone number; add a slow-looking problem.
    PAGES["/"] = page("Corner Bakery home", "<a href='/menu'>Menu</a> <a href='/faq'>FAQ</a> "
                      "<a href='/new'>New</a> <img src='bread.jpg' alt='Bread'>",
                      head=BUSINESS % "416-555-0100")
    PAGES["/menu"] = page("Menu", "<a href='/'>Home</a>", head=BUSINESS % "416-555-0100")
    PAGES["/new"] = page("")  # missing title
    second = run_audit(client, business)
    detail = client.get(audits_url(business, second)).json()
    assert detail["previous_audit_id"] == first
    assert detail["new_issues"] >= 1 and detail["fixed_issues"] >= 3
    fixed = {f["check"] for f in client.get(audits_url(business, second, "fixed")).json()}
    assert {"page_broken", "images_missing_alt", "business_details_inconsistent"} <= fixed
    new = groups(client, business, second)["title_missing"]
    assert new["new"] == 1 and new["items"][0]["is_new"]


def test_an_unreachable_site_fails_cleanly(client, db, business):
    db.get(Website, business["site"]).url = "http://127.0.0.1:9"
    db.commit()
    audit_id = run_audit(client, business)
    detail = client.get(audits_url(business, audit_id)).json()
    assert detail["status"] == "completed"
    assert list(groups(client, business, audit_id)) == ["home_unreachable"]


def test_one_audit_at_a_time_per_website(client, db, business):
    db.add(Audit(organization_id=business["org"].id, workspace_id=business["ws"],
                 website_id=business["site"], url="x", page_limit=1, status="running"))
    db.commit()
    res = client.post(audits_url(business), json={"website_id": business["site"]})
    assert res.status_code == 409 and res.json()["error"]["code"] == "audit_running"


def test_pagespeed_when_connected(monkeypatch):
    monkeypatch.setattr(get_settings(), "pagespeed_api_key", "test-key")
    body = {"lighthouseResult": {"categories": {"performance": {"score": 0.42}}, "audits": {
        "largest-contentful-paint": {"numericValue": 4120.5},
        "cumulative-layout-shift": {"numericValue": 0.12},
        "total-blocking-time": {"numericValue": 640}}}}
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=body)
    result = pagespeed.run("https://example.com/", transport=httpx.MockTransport(handler))
    assert result == {"connected": True, "strategy": "mobile", "score": 42, "lcp_ms": 4120.5,
                      "cls": 0.12, "tbt_ms": 640}
    assert "key=test-key" in seen["url"] and "strategy=mobile" in seen["url"]
    failed = pagespeed.run("https://example.com/", transport=httpx.MockTransport(
        lambda r: httpx.Response(429)))
    assert failed == {"connected": True, "error": "PageSpeed answered 429."}


# --- limits ---------------------------------------------------------------------------------

def test_audits_count_against_the_monthly_limit(client, db, business):
    set_plan(db, business["org"], "digital_starter")  # 4 audits a month, 100 pages each
    db.commit()
    for _ in range(4):
        run_audit(client, business)
    res = client.post(audits_url(business), json={"website_id": business["site"]})
    assert res.status_code == 403
    assert "includes 4 website audits a month" in res.json()["error"]["message"]
    used = db.scalar(select(UsageRecord.count).where(UsageRecord.metric == "audits"))
    assert used == 4
    plan = client.get(f"{API}/{business['slug']}/subscription").json()
    limits = {x["key"]: x for x in plan["limits"]}
    assert limits["limits.audits_per_month"]["used"] == 4
    assert limits["limits.pages_per_audit"] == {
        "key": "limits.pages_per_audit", "label": "Pages checked per audit",
        "limit": 100, "used": None}


def test_each_audit_stops_at_the_plans_page_limit(client, db, business):
    set_plan(db, business["org"], "digital_starter")
    db.commit()
    PAGES["/"] = page("Home", " ".join(f"<a href='/p{i}'>p</a>" for i in range(150)))
    for i in range(150):
        PAGES[f"/p{i}"] = page(f"Page number {i}")
    detail = client.get(audits_url(business, run_audit(client, business))).json()
    assert detail["page_limit"] == 100 and detail["pages_crawled"] == 100
    assert detail["hit_page_limit"]


# --- schedules ------------------------------------------------------------------------------

def test_scheduled_audits(client, db, business):
    client.patch(f"{API}/{business['slug']}/websites/{business['site']}",
                 json={"audit_frequency": "weekly"})
    assert schedule_due(db) == 1
    assert schedule_due(db) == 0  # one a week
    audit = db.scalars(select(Audit)).one()
    assert audit.trigger == "scheduled" and audit.status == "completed"
    audit.created_at = utcnow() - timedelta(days=8)
    db.commit()
    assert schedule_due(db) == 1


def test_schedules_respect_the_monthly_limit(client, db, business):
    set_plan(db, business["org"], "digital_starter")
    db.add(UsageRecord(organization_id=business["org"].id, metric="audits",
                       period=utcnow().strftime("%Y-%m"), count=4))
    db.get(Website, business["site"]).audit_frequency = "monthly"
    db.commit()
    assert schedule_due(db) == 0  # skipped, tried again tomorrow


# --- access ---------------------------------------------------------------------------------

def test_who_can_see_and_run_audits(client, new_client, db, business):
    run_audit(client, business)
    viewer, _ = signed_in_as(new_client, db, business["slug"], "v@bakery.example.com", "viewer")
    assert viewer.get(audits_url(business)).status_code == 200
    res = viewer.post(audits_url(business), json={"website_id": business["site"]})
    assert res.status_code == 403
    manager, _ = signed_in_as(new_client, db, business["slug"], "m@bakery.example.com", "member")
    assert manager.post(audits_url(business), json={"website_id": business["site"]}).status_code \
        == 202


def test_another_workspaces_website_cant_be_audited_here(client, new_client, db, business):
    other = new_client()
    rival = slug_of(register(other, "x@rival.example.com", org="Rival"))
    rival_ws = other.get(f"{API}/{rival}/workspaces").json()[0]["id"]
    res = other.post(f"{API}/{rival}/workspaces/{rival_ws}/audits",
                     json={"website_id": business["site"]})
    assert res.status_code == 404


def test_an_agency_audits_a_shared_workspace_on_the_business_plan(client, new_client, db, business):
    agency = new_client()
    agency_slug = slug_of(register(agency, "owner@agency.example.com", org="Agency"))
    client.post(f"{API}/{business['slug']}/access-grants",
                json={"email": "owner@agency.example.com"})
    token = token_from_last_email("/agency-access")
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == agency_slug))
    agency.post("/api/v1/access-grants/accept", json={"token": token,
                                                      "organization_id": str(agency_id)})
    res = agency.post(f"{API}/{agency_slug}/workspaces/{business['ws']}/audits",
                      json={"website_id": business["site"]})
    assert res.status_code == 202
    usage = db.scalars(select(UsageRecord)).one()
    assert usage.organization_id == business["org"].id  # the business's plan
    # The business sees the agency's audit.
    assert len(client.get(audits_url(business)).json()) == 1
    overview = agency.get(f"{API}/{agency_slug}/audits/websites").json()
    assert overview[0]["latest"]["status"] == "completed"


def test_redirects_and_declared_duplicates_arent_reported_as_duplicates(client, business):
    PAGES["/"] = page("Corner Bakery home", "<a href='/home'>Home</a> <a href='/book'>Book</a> "
                      "<a href='/book?service=bread'>Bread</a>")
    PAGES["/home"] = (301, "text/html", "/")
    PAGES["/book"] = page("Book a visit")
    PAGES["/book?service=bread"] = page("Book a visit",
                                        head="<link rel='canonical' href='/book'>")
    found = groups(client, business, run_audit(client, business))
    assert "title_duplicate" not in found and "meta_description_duplicate" not in found
    assert found["canonical_elsewhere"]["count"] == 1
