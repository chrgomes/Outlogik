"""H1-7: connecting Google, syncing Analytics and Search Console, and the summary.

Google is replaced by a fake that answers like the real APIs (same paths, same JSON shapes).
"""

import json
from datetime import date, timedelta
from urllib.parse import parse_qs, unquote, urlparse

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.models import utcnow
from app.core.redis import get_redis
from app.models import AuditLog, DataSource, Ga4Breakdown, Ga4Daily, GscQuery, Integration
from app.modules.integrations import google
from app.modules.integrations.crypto import decrypt
from app.modules.integrations.sync import sync_all
from tests.conftest import register, signed_in_as, slug_of

API = "/api/v1/orgs"
PROPERTY, SITE = "properties/123", "sc-domain:bakery.example.com"
READ_SCOPES = " ".join(google.SCOPES)


class FakeGoogle:
    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.revoked: list[str] = []
        self.scope = READ_SCOPES
        self.refresh_fails = False
        self.give_refresh_token = True
        self.report_status = 200

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        url, path = str(request.url), request.url.path
        if url.startswith(google.TOKEN_URL):
            form = parse_qs(request.content.decode())
            if form["grant_type"] == ["authorization_code"]:
                assert form["code_verifier"][0] and form["code"] == ["good-code"]
                body = {"access_token": "at-1", "scope": self.scope, "expires_in": 3599}
                if self.give_refresh_token:
                    body["refresh_token"] = "rt-secret-1"
                return httpx.Response(200, json=body)
            if self.refresh_fails:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "at-2", "expires_in": 3599})
        if url.startswith(google.REVOKE_URL):
            self.revoked.append(parse_qs(request.content.decode())["token"][0])
            return httpx.Response(200)
        if url.startswith(google.USERINFO_URL):
            return httpx.Response(200, json={"email": "marketing@bakery.example.com"})
        if path.endswith("/accountSummaries"):
            return httpx.Response(200, json={"accountSummaries": [{
                "account": "accounts/1", "displayName": "Bakery",
                "propertySummaries": [{"property": PROPERTY, "displayName": "bakery.example.com"}],
            }]})
        if path.endswith("/webmasters/v3/sites"):
            return httpx.Response(200, json={"siteEntry": [
                {"siteUrl": SITE, "permissionLevel": "siteOwner"},
                {"siteUrl": "https://other.example.com/", "permissionLevel": "siteUnverifiedUser"},
            ]})
        if self.report_status != 200:
            return httpx.Response(self.report_status, json={})
        if path.endswith(":runReport"):
            return httpx.Response(200, json=self.ga4(json.loads(request.content)))
        if path.endswith("/searchAnalytics/query"):
            assert unquote(path.split("/sites/")[1].split("/")[0]) == SITE
            return httpx.Response(200, json=self.gsc(json.loads(request.content)))
        return httpx.Response(404)

    @staticmethod
    def days(body):
        r = body["dateRanges"][0] if "dateRanges" in body else body
        start = date.fromisoformat(r.get("startDate"))
        end = date.fromisoformat(r.get("endDate"))
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    def ga4(self, body):
        dims = [d["name"] for d in body["dimensions"]]
        rows = []
        for d in self.days(body):
            key = d.strftime("%Y%m%d")
            if dims == ["date"]:
                rows.append({"dimensionValues": [{"value": key}], "metricValues": [
                    {"value": v} for v in ("100", "80", "30", "60", "250", "4.0")]})
            elif dims[1] == "sessionDefaultChannelGroup":
                rows += [{"dimensionValues": [{"value": key}, {"value": "Organic Search"}],
                          "metricValues": [{"value": "70"}]},
                         {"dimensionValues": [{"value": key}, {"value": "Direct"}],
                          "metricValues": [{"value": "30"}]}]
            else:
                assert "chatgpt.com" in body["dimensionFilter"]["filter"]["inListFilter"]["values"]
                rows += [{"dimensionValues": [{"value": key}, {"value": "chatgpt.com"}],
                          "metricValues": [{"value": "3"}]},
                         {"dimensionValues": [{"value": key}, {"value": "chat.openai.com"}],
                          "metricValues": [{"value": "1"}]},
                         {"dimensionValues": [{"value": key}, {"value": "perplexity.ai"}],
                          "metricValues": [{"value": "2"}]}]
        return {"rows": rows}

    def gsc(self, body):
        if body["dimensions"] == ["date"]:
            # Search Console is 2–3 days behind
            return {"rows": [{"keys": [d.isoformat()], "clicks": 10, "impressions": 200,
                              "position": 8.0} for d in self.days(body)[:-2]]}
        return {"rows": [{"keys": ["sourdough near me"], "clicks": 40, "impressions": 900,
                          "position": 3.2},
                         {"keys": ["bakery toronto"], "clicks": 12, "impressions": 1500,
                          "position": 9.1}]}


@pytest.fixture
def fake(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "client-123.apps.googleusercontent.com")
    monkeypatch.setattr(s, "google_client_secret", "test-secret")
    g = FakeGoogle()
    monkeypatch.setattr(google, "TRANSPORT", httpx.MockTransport(g))
    return g


@pytest.fixture
def bakery(client):
    slug = slug_of(register(client, "owner@bakery.example.com", org="Bakery",
                            account_type="business"))
    ws = client.get(f"{API}/{slug}/workspaces").json()[0]["id"]
    return slug, ws, f"{API}/{slug}/workspaces/{ws}"


def connect(client, base, code="good-code"):
    res = client.post(f"{base}/integrations/google/connect")
    assert res.status_code == 200, res.text
    url = urlparse(res.json()["url"])
    q = parse_qs(url.query)
    return client.get("/api/v1/integrations/google/callback",
                      params={"state": q["state"][0], "code": code}, follow_redirects=False), q


def choose(client, base, ga4=PROPERTY, site=SITE):
    return client.put(f"{base}/integrations/google/sources",
                      json={"ga4_property": ga4, "search_console_site": site})


# --- connecting -----------------------------------------------------------------------------

def test_without_google_set_up_the_page_says_so(client, bakery):
    _, _, base = bakery
    assert client.get(f"{base}/integrations/google").json() == {
        "configured": False, "connected": False, "status": None, "account_email": None,
        "connected_at": None, "last_error": None, "sources": []}
    res = client.post(f"{base}/integrations/google/connect")
    assert res.status_code == 409 and res.json()["error"]["code"] == "google_not_configured"


def test_connect_round_trip(client, db, fake, bakery):
    slug, ws, base = bakery
    res, q = connect(client, base)
    assert q["access_type"] == ["offline"] and q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["https://app.test/api/v1/integrations/google/callback"]
    assert set(q["scope"][0].split()) == set(google.SCOPES)  # read-only scopes only
    assert res.status_code == 303
    assert res.headers["location"] == (
        f"https://app.test/o/{slug}/integrations?workspace={ws}&google=connected")
    body = client.get(f"{base}/integrations/google").json()
    assert body["connected"] and body["account_email"] == "marketing@bakery.example.com"
    assert "rt-secret-1" not in json.dumps(body)
    row = db.scalar(select(Integration))
    assert "rt-secret-1" not in row.refresh_token_encrypted  # encrypted at rest
    assert decrypt(row.refresh_token_encrypted) == "rt-secret-1"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "integration.connect"))


def test_the_sign_in_state_works_once_and_only_for_who_started_it(client, new_client, db,
                                                                   fake, bakery):
    slug, _, base = bakery
    url = urlparse(client.post(f"{base}/integrations/google/connect").json()["url"])
    state = parse_qs(url.query)["state"][0]
    other, _ = signed_in_as(new_client, db, slug, "admin@bakery.example.com", "admin")
    res = other.get("/api/v1/integrations/google/callback",
                    params={"state": state, "code": "good-code"}, follow_redirects=False)
    assert res.headers["location"].endswith(
        f"/o/{slug}/integrations?google_error=oauth_state_invalid")
    # It's been used up, so even the right person can't use it now.
    res = client.get("/api/v1/integrations/google/callback",
                     params={"state": state, "code": "good-code"}, follow_redirects=False)
    assert "google_error=oauth_state_invalid" in res.headers["location"]
    assert db.scalar(select(func.count()).select_from(Integration)) == 0
    res = client.get("/api/v1/integrations/google/callback",
                     params={"state": "made-up", "code": "good-code"}, follow_redirects=False)
    assert res.headers["location"] == "https://app.test/?google_error=oauth_state_invalid"


def test_state_expires_after_ten_minutes(client, fake, bakery):
    _, _, base = bakery
    client.post(f"{base}/integrations/google/connect")
    key = next(get_redis().scan_iter("oauth:google:*"))
    assert 590 <= get_redis().ttl(key) <= 600


def test_signed_out_callback_goes_to_login(new_client, fake):
    res = new_client().get("/api/v1/integrations/google/callback",
                           params={"state": "x", "code": "y"}, follow_redirects=False)
    assert res.headers["location"] == "https://app.test/login"


def test_cancelling_at_google(client, fake, bakery):
    slug, _, base = bakery
    url = urlparse(client.post(f"{base}/integrations/google/connect").json()["url"])
    state = parse_qs(url.query)["state"][0]
    res = client.get("/api/v1/integrations/google/callback",
                     params={"state": state, "error": "access_denied"}, follow_redirects=False)
    assert res.headers["location"] == f"https://app.test/o/{slug}/integrations?google=cancelled"
    assert list(get_redis().scan_iter("oauth:google:*")) == []


def test_unticked_scopes_are_refused_and_revoked(client, db, fake, bakery):
    _, _, base = bakery
    fake.scope = "openid email https://www.googleapis.com/auth/analytics.readonly"
    res, _ = connect(client, base)
    assert "google_error=oauth_scopes_missing" in res.headers["location"]
    assert fake.revoked == ["rt-secret-1"]
    assert db.scalar(select(func.count()).select_from(Integration)) == 0


def test_no_refresh_token(client, db, fake, bakery):
    _, _, base = bakery
    fake.give_refresh_token = False
    res, _ = connect(client, base)
    assert "google_error=oauth_no_refresh_token" in res.headers["location"]


def test_reconnecting_replaces_and_revokes_the_old_token(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    connect(client, base)
    assert fake.revoked == ["rt-secret-1"]
    assert db.scalar(select(func.count()).select_from(Integration)) == 1


# --- choosing and syncing -------------------------------------------------------------------

def test_available_lists_only_verified_sites(client, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    body = client.get(f"{base}/integrations/google/available").json()
    assert body["ga4"] == [{"id": PROPERTY, "name": "bakery.example.com", "account": "Bakery"}]
    assert body["search_console"] == [{"site_url": SITE, "permission": "siteOwner"}]


def test_only_what_the_account_can_see_can_be_chosen(client, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    res = choose(client, base, ga4="properties/999")
    assert res.status_code == 422 and res.json()["error"]["code"] == "source_not_available"
    res = choose(client, base, site="https://other.example.com/")
    assert res.status_code == 422


def test_choosing_syncs_90_days_then_the_summary_compares_periods(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    res = choose(client, base)
    assert res.status_code == 200, res.text
    sources = {s["kind"]: s for s in res.json()["sources"]}
    assert {s["sync_status"] for s in sources.values()} == {"ok"}
    yesterday = utcnow().date() - timedelta(days=1)
    assert sources["ga4"]["synced_through"] == yesterday.isoformat()
    gsc_through = yesterday - timedelta(days=2)
    assert sources["search_console"]["synced_through"] == gsc_through.isoformat()
    assert db.scalar(select(func.count()).select_from(Ga4Daily)) == 90

    s = client.get(f"{base}/analytics/summary").json()
    assert s["ga4"]["sessions"] == {"value": 2800.0, "previous": 2800.0}
    assert s["ga4"]["key_events"]["value"] == 112.0
    assert s["channels"][0] == {"name": "Organic Search", "sessions": 1960, "previous": 1960}
    # chatgpt.com and chat.openai.com are both ChatGPT
    assert s["ai_referrals"] == [{"name": "ChatGPT", "sessions": 112, "previous": 112},
                                 {"name": "Perplexity", "sessions": 56, "previous": 56}]
    sc = s["search_console"]
    assert sc["clicks"]["value"] == 280.0 and sc["ctr"]["value"] == pytest.approx(0.05)
    assert sc["position"]["value"] == pytest.approx(8.0)
    assert s["top_queries"][0]["query"] == "sourdough near me"
    assert len(s["series"]) == 28 and s["series"][-1]["sessions"] == 100
    assert s["series"][-1]["clicks"] is None  # Search Console hasn't reported those days yet


def test_later_syncs_refetch_only_the_last_week(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    fake.calls.clear()
    assert client.post(f"{base}/integrations/google/sync").status_code == 202
    reports = [json.loads(r.content) for r in fake.calls if r.url.path.endswith(":runReport")]
    assert len(reports) == 3
    assert len(FakeGoogle.days(reports[0])) == 7
    assert db.scalar(select(func.count()).select_from(Ga4Daily)) == 90  # replaced, not doubled


def test_summary_without_full_previous_period_has_no_comparison(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    s = client.get(f"{base}/analytics/summary?days=90").json()
    assert s["ga4"]["sessions"] == {"value": 9000.0, "previous": None}


def test_summary_before_anything_is_connected(client, bakery):
    _, _, base = bakery
    s = client.get(f"{base}/analytics/summary").json()
    assert s["ga4"] is None and s["search_console"] is None and s["series"] == []


def test_google_withdrawing_access_asks_for_reconnection(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    fake.refresh_fails = True
    client.post(f"{base}/integrations/google/sync")
    body = client.get(f"{base}/integrations/google").json()
    assert body["status"] == "error" and "Reconnect Google" in body["last_error"]
    assert {s["sync_status"] for s in body["sources"]} == {"failed"}
    res = client.post(f"{base}/integrations/google/sync")
    assert res.status_code == 409
    # The nightly sync skips it rather than failing every night.
    assert sync_all(db) == 0


def test_google_outage_fails_the_sync_and_keeps_the_history(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    fake.report_status = 503
    client.post(f"{base}/integrations/google/sync")
    body = client.get(f"{base}/integrations/google").json()
    assert body["status"] == "connected"
    assert {s["sync_status"] for s in body["sources"]} == {"failed"}
    assert db.scalar(select(func.count()).select_from(Ga4Daily)) == 90


def test_removing_a_source_deletes_its_history(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    choose(client, base, ga4=None)
    assert db.scalar(select(func.count()).select_from(Ga4Daily)) == 0
    assert db.scalar(select(func.count()).select_from(GscQuery)) == 2


def test_disconnect_revokes_and_deletes_everything(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    assert client.delete(f"{base}/integrations/google").status_code == 204
    assert fake.revoked == ["rt-secret-1"]
    for model in (Integration, DataSource, Ga4Daily, Ga4Breakdown, GscQuery):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model
    assert client.get(f"{base}/integrations/google").json()["connected"] is False


def test_nightly_sync_queues_every_working_source(client, db, fake, bakery):
    _, _, base = bakery
    connect(client, base)
    choose(client, base)
    assert sync_all(db) == 2


# --- who may do what ------------------------------------------------------------------------

def test_permissions(client, new_client, db, fake, bakery):
    slug, _, base = bakery
    connect(client, base)
    choose(client, base)
    viewer, _ = signed_in_as(new_client, db, slug, "viewer@bakery.example.com", "viewer")
    assert viewer.get(f"{base}/analytics/summary").status_code == 200
    assert viewer.get(f"{base}/integrations/google").status_code == 200
    for method, path in (("POST", "/integrations/google/connect"),
                         ("GET", "/integrations/google/available"),
                         ("PUT", "/integrations/google/sources"),
                         ("POST", "/integrations/google/sync"),
                         ("DELETE", "/integrations/google")):
        res = viewer.request(method, f"{base}{path}", json={})
        assert res.status_code == 403, (method, path)
    manager, _ = signed_in_as(new_client, db, slug, "mm@bakery.example.com", "member")
    assert manager.post(f"{base}/integrations/google/sync").status_code == 202


def test_an_agency_with_view_access_sees_but_cant_change(client, new_client, db, fake, bakery):
    from tests.conftest import token_from_last_email

    slug, ws, base = bakery
    connect(client, base)
    choose(client, base)
    agency = new_client()
    agency_slug = slug_of(register(agency, "owner@agency.example.com", org="Agency"))
    client.post(f"{API}/{slug}/access-grants",
                json={"email": "owner@agency.example.com", "access": "view"})
    from app.models import Organization
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == agency_slug))
    agency.post("/api/v1/access-grants/accept", json={
        "token": token_from_last_email("/agency-access"), "organization_id": str(agency_id)})
    shared = f"{API}/{agency_slug}/workspaces/{ws}"
    assert agency.get(f"{shared}/analytics/summary").json()["ga4"]["sessions"]["value"] == 2800
    assert agency.post(f"{shared}/integrations/google/sync").status_code == 403
    assert agency.delete(f"{shared}/integrations/google").status_code == 403
