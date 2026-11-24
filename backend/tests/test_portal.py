"""H1-10: the client portal (a client sees their own workspace, never the agency's overview),
contacts, and everyone's own account settings."""

import pytest
from sqlalchemy import select

from app.core import email
from app.models import AuditLog, Workspace
from tests.conftest import (
    PASSWORD,
    link_client,
    login,
    register,
    seed_client,
    seed_member,
    signed_in_as,
    slug_of,
)

API = "/api/v1/orgs"
AUTH = "/api/v1/auth"


@pytest.fixture
def agency(client, new_client, db):
    slug = slug_of(register(client, "owner@agency.example.com", org="Northline"))
    alpha, beta = seed_client(db, slug, "Alpha Dental"), seed_client(db, slug, "Beta Cycles")
    ws = {c.name: str(db.scalar(select(Workspace.id).where(Workspace.client_id == c.id)))
          for c in (alpha, beta)}
    portal = seed_member(db, slug, "jo@alpha.example.com", "client", name="Jo Client")
    link_client(db, portal, alpha)
    browser = new_client()
    assert login(browser, "jo@alpha.example.com").status_code == 200
    return {"slug": slug, "ws": ws, "alpha": alpha, "portal": browser}


# --- the client portal ----------------------------------------------------------------------

def test_clients_get_their_own_dashboard_not_the_agency_overview(client, agency):
    slug, portal, ws = agency["slug"], agency["portal"], agency["ws"]
    res = portal.get(f"{API}/{slug}/dashboard/overview")
    assert res.status_code == 403 and res.json()["error"]["code"] == "client_portal"
    assert client.get(f"{API}/{slug}/dashboard/overview").status_code == 200
    assert portal.get(f"{API}/{slug}/workspaces/{ws['Alpha Dental']}/dashboard").status_code \
        == 200
    assert portal.get(f"{API}/{slug}/workspaces/{ws['Beta Cycles']}/dashboard").status_code \
        == 404


def test_clients_see_their_account_manager(client, new_client, db, agency):
    slug, portal, ws = agency["slug"], agency["portal"], agency["ws"]
    url = f"{API}/{slug}/workspaces/{ws['Alpha Dental']}/contacts"
    # No account manager yet: the agency's owners
    body = portal.get(url).json()
    assert body == {"organization_name": "Northline", "contacts": [
        {"name": "Olive Owner", "email": "owner@agency.example.com", "role": "owner"}]}
    am = seed_member(db, slug, "sam@agency.example.com", "account_manager", name="Sam Kumar")
    other = seed_member(db, slug, "pat@agency.example.com", "account_manager", name="Pat Lee")
    client.put(f"{API}/{slug}/members/{am.id}/workspaces",
               json={"workspace_ids": [ws["Alpha Dental"]]})
    client.put(f"{API}/{slug}/members/{other.id}/workspaces",
               json={"workspace_ids": [ws["Beta Cycles"]]})
    assert portal.get(url).json()["contacts"] == [
        {"name": "Sam Kumar", "email": "sam@agency.example.com", "role": "account_manager"}]
    # Another client's contacts are off limits
    other_ws = f"{API}/{slug}/workspaces/{ws['Beta Cycles']}/contacts"
    assert portal.get(other_ws).status_code == 404


def test_disabled_account_managers_are_not_listed(client, db, agency):
    slug, portal, ws = agency["slug"], agency["portal"], agency["ws"]
    am = seed_member(db, slug, "sam@agency.example.com", "account_manager", name="Sam Kumar")
    client.put(f"{API}/{slug}/members/{am.id}/workspaces",
               json={"workspace_ids": [ws["Alpha Dental"]]})
    client.patch(f"{API}/{slug}/members/{am.id}", json={"status": "disabled"})
    contacts = portal.get(f"{API}/{slug}/workspaces/{ws['Alpha Dental']}/contacts").json()
    assert [c["role"] for c in contacts["contacts"]] == ["owner"]


def test_client_portal_users_still_get_no_team_or_internal_details(agency):
    slug, portal = agency["slug"], agency["portal"]
    assert portal.get(f"{API}/{slug}/members").status_code == 403
    clients = portal.get(f"{API}/{slug}/clients").json()["items"]
    assert [c["name"] for c in clients] == ["Alpha Dental"]
    assert clients[0]["notes"] is None and clients[0]["portal_user_count"] is None


# --- your account ---------------------------------------------------------------------------

def test_change_your_name(client, db):
    register(client)
    res = client.patch(f"{AUTH}/me", json={"full_name": "  Olive Baker  "})
    assert res.status_code == 200 and res.json()["user"]["full_name"] == "Olive Baker"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "auth.profile_update"))
    assert entry.meta["full_name"] == {"from": "Olive Owner", "to": "Olive Baker"}
    assert client.patch(f"{AUTH}/me", json={"full_name": "   "}).status_code == 422


def test_change_password_signs_out_other_devices_and_tells_you(client, new_client, db):
    register(client)
    other_device = new_client()
    assert login(other_device, "owner@agency.example.com").status_code == 200
    email.outbox.clear()
    res = client.post(f"{AUTH}/change-password",
                      json={"current_password": PASSWORD, "new_password": "A-new-long-password"})
    assert res.status_code == 204
    assert client.get(f"{AUTH}/me").status_code == 200  # this device stays signed in
    assert other_device.get(f"{AUTH}/me").status_code == 401
    assert login(new_client(), "owner@agency.example.com").status_code == 401
    assert login(new_client(), "owner@agency.example.com", "A-new-long-password").status_code \
        == 200
    sent = email.outbox[-1]
    assert sent.subject.endswith("password was changed")
    assert "signed out on your other devices" in sent.body and "/forgot-password" in sent.body
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.password_change"))


def test_change_password_needs_the_current_one(client):
    register(client)
    res = client.post(f"{AUTH}/change-password",
                      json={"current_password": "wrong-password", "new_password": "A-new-long-pw"})
    assert res.status_code == 400
    assert res.json()["error"]["details"][0]["field"] == "current_password"
    res = client.post(f"{AUTH}/change-password",
                      json={"current_password": PASSWORD, "new_password": "short"})
    assert res.status_code == 422


def test_guessing_the_current_password_is_limited(client):
    register(client)
    for _ in range(5):
        client.post(f"{AUTH}/change-password",
                    json={"current_password": "wrong-password", "new_password": "A-new-long-pw"})
    res = client.post(f"{AUTH}/change-password",
                      json={"current_password": PASSWORD, "new_password": "A-new-long-pw"})
    assert res.status_code == 429


def test_account_changes_need_a_session(new_client):
    browser = new_client()
    assert browser.patch(f"{AUTH}/me", json={"full_name": "X"}).status_code == 401
    assert browser.post(f"{AUTH}/change-password", json={
        "current_password": "x", "new_password": "A-new-long-pw"}).status_code == 401


def test_staff_can_be_shown_as_contacts_to_their_team_too(client, new_client, db, agency):
    """Team members (who can see the team anyway) get the same contacts."""
    slug, ws = agency["slug"], agency["ws"]
    viewer, _ = signed_in_as(new_client, db, slug, "v@agency.example.com", "viewer")
    res = viewer.get(f"{API}/{slug}/workspaces/{ws['Alpha Dental']}/contacts")
    assert res.status_code == 200
