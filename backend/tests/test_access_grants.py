"""H1-3: a business lets an agency work in its workspace (access grants)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import email
from app.models import AuditLog, Organization, Website, WorkspaceAssignment, WorkspaceGrant
from tests.conftest import register, signed_in_as, slug_of, token_from_last_email

API = "/api/v1/orgs"
GRANTS = "/api/v1/access-grants"


@pytest.fixture
def parties(client, new_client):
    """A business (signed in as `client`) and an agency (its owner in `agency`)."""
    business = slug_of(register(client, "owner@bakery.example.com", org="Bakery",
                                account_type="business"))
    agency_browser = new_client()
    agency = slug_of(register(agency_browser, "owner@agency.example.com", org="Agency"))
    return {"business": business, "agency": agency, "agency_browser": agency_browser}


def workspaces(c, slug):
    return {w["name"]: w for w in c.get(f"{API}/{slug}/workspaces").json()}


def send(c, slug, to="owner@agency.example.com", access="manage"):
    res = c.post(f"{API}/{slug}/access-grants", json={"email": to, "access": access})
    assert res.status_code == 201, res.text
    return res.json(), token_from_last_email("/agency-access")


def org_id(db, slug):
    return str(db.scalar(select(Organization.id).where(Organization.slug == slug)))


def accept(browser, db, token, agency_slug):
    return browser.post(f"{GRANTS}/accept",
                        json={"token": token, "organization_id": org_id(db, agency_slug)})


@pytest.fixture
def linked(client, db, parties):
    grant, token = send(client, parties["business"])
    assert accept(parties["agency_browser"], db, token, parties["agency"]).status_code == 200
    return {**parties, "grant": grant}


# --- sending and accepting ------------------------------------------------------------------

def test_business_sends_access_by_email(client, db, parties):
    grant, _ = send(client, parties["business"])
    assert grant["status"] == "pending" and grant["access"] == "manage"
    assert "Bakery gave your agency access" in email.outbox[-1].subject
    listed = client.get(f"{API}/{parties['business']}/access-grants").json()
    assert [g["email"] for g in listed] == ["owner@agency.example.com"]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "access_grant.create"))


def test_only_businesses_send_access(parties):
    res = parties["agency_browser"].post(f"{API}/{parties['agency']}/access-grants",
                                         json={"email": "x@example.com"})
    assert res.status_code == 409 and res.json()["error"]["code"] == "business_only"


def test_preview_shows_the_offer_and_the_agencies_that_can_accept(client, db, parties):
    _, token = send(client, parties["business"])
    res = parties["agency_browser"].post(f"{GRANTS}/preview", json={"token": token})
    assert res.status_code == 200
    body = res.json()
    assert body["business_name"] == "Bakery" and body["access"] == "manage"
    assert [a["name"] for a in body["agencies"]] == ["Agency"]


def test_only_the_invited_account_can_open_or_accept(client, new_client, db, parties):
    _, token = send(client, parties["business"])
    stranger = new_client()
    register(stranger, "someone@else.example.com", org="Else")
    res = stranger.post(f"{GRANTS}/preview", json={"token": token})
    assert res.status_code == 403 and res.json()["error"]["code"] == "wrong_account"
    res = accept(stranger, db, token, parties["agency"])
    assert res.status_code == 403
    # Signed out: no access at all.
    assert new_client().post(f"{GRANTS}/preview", json={"token": token}).status_code == 401


def test_accept_links_the_workspace_into_the_agency(client, db, linked):
    agency = linked["agency_browser"]
    ws = workspaces(agency, linked["agency"])
    assert set(ws) == {"Agency", "Bakery"}
    shared = ws["Bakery"]
    assert shared["linked"] and shared["organization_name"] == "Bakery"
    assert shared["access"] == "manage"
    listed = client.get(f"{API}/{linked['business']}/access-grants").json()
    assert listed[0]["status"] == "active" and listed[0]["agency_name"] == "Agency"
    # Recorded in both organizations' logs.
    orgs = set(db.scalars(select(AuditLog.organization_id)
                          .where(AuditLog.action == "access_grant.accept")))
    assert len(orgs) == 2


def test_accept_errors(client, new_client, db, linked):
    agency = linked["agency_browser"]
    # A used link doesn't work again.
    grant, token = send(client, linked["business"])
    assert accept(agency, db, token, linked["agency"]).status_code == 409  # already linked
    # Into the business itself, or an organization they don't belong to: not found.
    _, token = send(client, linked["business"])
    assert accept(agency, db, token, linked["business"]).status_code == 404
    other = new_client()
    other_slug = slug_of(register(other, "x@other.example.com", org="Other Agency"))
    assert accept(agency, db, token, other_slug).status_code == 404
    # Expired.
    g = db.scalars(select(WorkspaceGrant).where(WorkspaceGrant.status == "pending")).first()
    g.expires_at = g.expires_at - timedelta(days=30)
    db.commit()
    res = accept(agency, db, token, linked["agency"])
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_token"


def test_members_without_the_permission_cant_accept(client, new_client, db, parties):
    browser, _ = signed_in_as(new_client, db, parties["agency"], "mm@agency.example.com",
                              "member")
    _, token = send(client, parties["business"], to="mm@agency.example.com")
    assert browser.post(f"{GRANTS}/preview", json={"token": token}).json()["agencies"] == []
    assert accept(browser, db, token, parties["agency"]).status_code == 404


# --- working in a linked workspace ----------------------------------------------------------

def test_agency_works_on_the_business_websites(client, db, linked):
    agency = linked["agency_browser"]
    ws_id = workspaces(agency, linked["agency"])["Bakery"]["id"]
    res = agency.post(f"{API}/{linked['agency']}/workspaces/{ws_id}/websites",
                      json={"url": "bakery.example.com"})
    assert res.status_code == 201, res.text
    site = db.get(Website, res.json()["id"])
    # It belongs to the business, which sees it at once.
    assert str(site.organization_id) == org_id(db, linked["business"])
    assert client.get(f"{API}/{linked['business']}/websites").json()["total"] == 1
    # It shows in the agency's organization-wide list too.
    assert agency.get(f"{API}/{linked['agency']}/websites").json()["total"] == 1
    # Both logs record the change, the business's naming the agency.
    entries = db.scalars(select(AuditLog).where(AuditLog.action == "website.create")).all()
    assert len(entries) == 2 and all(e.meta["agency"] == "Agency" for e in entries)


def test_websites_stay_in_the_business(client, db, linked):
    agency = linked["agency_browser"]
    ws = workspaces(agency, linked["agency"])
    site = agency.post(f"{API}/{linked['agency']}/workspaces/{ws['Bakery']['id']}/websites",
                       json={"url": "bakery.example.com"}).json()
    res = agency.patch(f"{API}/{linked['agency']}/websites/{site['id']}",
                       json={"workspace_id": ws["Agency"]["id"]})
    assert res.status_code == 404


def test_view_only_access_refuses_changes(client, db, parties):
    _, token = send(client, parties["business"], access="view")
    agency = parties["agency_browser"]
    accept(agency, db, token, parties["agency"])
    site = client.post(f"{API}/{parties['business']}/websites",
                       json={"url": "bakery.example.com"}).json()
    ws_id = workspaces(agency, parties["agency"])["Bakery"]["id"]
    base = f"{API}/{parties['agency']}/workspaces/{ws_id}/websites"
    assert agency.get(base).json()["total"] == 1
    res = agency.post(base, json={"url": "new.example.com"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "view_only_access"
    assert agency.patch(f"{base}/{site['id']}", json={"name": "x"}).status_code == 403
    res = agency.patch(f"{API}/{parties['agency']}/websites/{site['id']}", json={"name": "x"})
    assert res.status_code == 403
    assert agency.delete(f"{API}/{parties['agency']}/websites/{site['id']}").status_code == 403


def test_limited_agency_members_need_an_assignment(client, new_client, db, linked):
    am_browser, am = signed_in_as(new_client, db, linked["agency"], "am@agency.example.com",
                                  "account_manager")
    agency = linked["agency_browser"]
    assert workspaces(am_browser, linked["agency"]) == {}
    ws_id = workspaces(agency, linked["agency"])["Bakery"]["id"]
    res = agency.put(f"{API}/{linked['agency']}/members/{am.id}/workspaces",
                     json={"workspace_ids": [ws_id]})
    assert res.status_code == 200
    assert set(workspaces(am_browser, linked["agency"])) == {"Bakery"}
    # Client Viewers can't be given a business's workspace.
    _, viewer = signed_in_as(new_client, db, linked["agency"], "cv@x.example.com", "client")
    res = agency.put(f"{API}/{linked['agency']}/members/{viewer.id}/workspaces",
                     json={"workspace_ids": [ws_id]})
    assert res.status_code == 409


# --- ending access --------------------------------------------------------------------------

def test_business_revokes_and_access_stops_at_once(client, new_client, db, linked):
    agency = linked["agency_browser"]
    _, am = signed_in_as(new_client, db, linked["agency"], "am@agency.example.com",
                         "account_manager")
    ws_id = workspaces(agency, linked["agency"])["Bakery"]["id"]
    agency.put(f"{API}/{linked['agency']}/members/{am.id}/workspaces",
               json={"workspace_ids": [ws_id]})

    res = client.delete(f"{API}/{linked['business']}/access-grants/{linked['grant']['id']}")
    assert res.status_code == 204
    assert "Bakery" not in workspaces(agency, linked["agency"])
    assert agency.get(f"{API}/{linked['agency']}/workspaces/{ws_id}/websites").status_code == 404
    assert db.scalar(select(WorkspaceAssignment).where(
        WorkspaceAssignment.workspace_id == ws_id)) is None
    orgs = set(db.scalars(select(AuditLog.organization_id)
                          .where(AuditLog.action == "access_grant.revoke")))
    assert len(orgs) == 2
    # Revoking again: not found.
    res = client.delete(f"{API}/{linked['business']}/access-grants/{linked['grant']['id']}")
    assert res.status_code == 404


def test_agency_can_disconnect(client, db, linked):
    agency = linked["agency_browser"]
    ws_id = workspaces(agency, linked["agency"])["Bakery"]["id"]
    assert agency.delete(f"{API}/{linked['agency']}/workspaces/{ws_id}/access").status_code == 204
    assert "Bakery" not in workspaces(agency, linked["agency"])
    listed = client.get(f"{API}/{linked['business']}/access-grants").json()
    assert listed[0]["status"] == "revoked"


# --- isolation ------------------------------------------------------------------------------

def test_a_grant_opens_only_the_shared_workspace(client, new_client, db, linked):
    agency = linked["agency_browser"]
    # The agency still isn't a member of the business: its organization API is a 404.
    for path in ("", "/members", "/roles", "/access-grants", "/workspaces", "/dashboard"):
        assert agency.get(f"{API}/{linked['business']}{path}").status_code == 404, path
    # Other agencies see nothing of it.
    other = new_client()
    other_slug = slug_of(register(other, "x@other.example.com", org="Other Agency"))
    ws_id = workspaces(agency, linked["agency"])["Bakery"]["id"]
    assert other.get(f"{API}/{other_slug}/workspaces/{ws_id}").status_code == 404
    assert other.get(f"{API}/{other_slug}/workspaces/{ws_id}/websites").status_code == 404
    assert other.delete(f"{API}/{other_slug}/workspaces/{ws_id}/access").status_code == 404
    # And another business can't revoke this business's grant.
    biz2 = new_client()
    biz2_slug = slug_of(register(biz2, "b2@example.com", org="Shop", account_type="business"))
    assert biz2.delete(
        f"{API}/{biz2_slug}/access-grants/{linked['grant']['id']}").status_code == 404
