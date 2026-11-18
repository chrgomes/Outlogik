"""Account types and workspaces (H1-2): every organization has an own workspace, every agency
client has a client workspace, and websites live in workspaces."""

import pytest
from sqlalchemy import select

from app.models import AuditLog, Organization, Website, Workspace
from tests.conftest import link_client, register, seed_client, signed_in_as, slug_of

API = "/api/v1/orgs"


@pytest.fixture
def agency(client):
    return slug_of(register(client, "owner@agency.example.com", org="Agency"))


def workspaces(c, slug):
    res = c.get(f"{API}/{slug}/workspaces")
    assert res.status_code == 200, res.text
    return res.json()


def ws_url(slug, ws_id, *parts):
    return "/".join([f"{API}/{slug}/workspaces/{ws_id}/websites", *map(str, parts)])


def add_client(c, slug, name):
    res = c.post(f"{API}/{slug}/clients", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()


# --- account types --------------------------------------------------------------------------

def test_register_defaults_to_agency_and_reports_kind(client):
    me = register(client, "a@example.com", org="Agency")
    assert me["memberships"][0]["organization_kind"] == "agency"
    detail = client.get(f"{API}/{slug_of(me)}").json()
    assert detail["kind"] == "agency"


def test_register_as_business(client, db):
    me = register(client, "b@example.com", org="Bakery", account_type="business")
    assert me["memberships"][0]["organization_kind"] == "business"
    org = db.scalar(select(Organization).where(Organization.slug == slug_of(me)))
    assert org.kind == "business"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "organization.create"))
    assert entry.meta["kind"] == "business"


def test_register_rejects_unknown_account_type(client):
    client.get("/api/v1/auth/csrf")
    res = client.post("/api/v1/auth/register", json={
        "email": "c@example.com", "password": "example password 1", "full_name": "C",
        "organization_name": "C", "account_type": "reseller"})
    assert res.status_code == 422


def test_business_accounts_cannot_add_clients(client):
    slug = slug_of(register(client, "b@example.com", org="Bakery", account_type="business"))
    res = client.post(f"{API}/{slug}/clients", json={"name": "Someone"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "business_account"
    assert [w["kind"] for w in workspaces(client, slug)] == ["own"]


# --- workspaces follow organizations and clients --------------------------------------------

def test_new_organization_has_one_own_workspace(client, agency):
    [own] = workspaces(client, agency)
    assert own["kind"] == "own" and own["name"] == "Agency" and own["client_id"] is None


def test_client_gets_workspace_that_follows_its_name_and_is_deleted_with_it(client, agency, db):
    c = add_client(client, agency, "Zeta Co")
    add_client(client, agency, "Alpha Co")
    names = [(w["kind"], w["name"]) for w in workspaces(client, agency)]
    assert names == [("own", "Agency"), ("client", "Alpha Co"), ("client", "Zeta Co")]

    client.patch(f"{API}/{agency}/clients/{c['id']}", json={"name": "Zeta Group"})
    assert any(w["name"] == "Zeta Group" and w["client_id"] == c["id"]
               for w in workspaces(client, agency))

    client.delete(f"{API}/{agency}/clients/{c['id']}")
    assert db.scalar(select(Workspace).where(Workspace.name == "Zeta Group")) is None


def test_own_workspace_follows_organization_name(client, agency):
    client.patch(f"{API}/{agency}", json={"name": "Agency Inc"})
    assert workspaces(client, agency)[0]["name"] == "Agency Inc"


def test_organization_cannot_have_two_own_workspaces(client, agency, db):
    org = db.scalar(select(Organization).where(Organization.slug == agency))
    db.add(Workspace(organization_id=org.id, kind="own", name="Second"))
    with pytest.raises(Exception, match="uq_workspaces_one_own_per_organization"):
        db.commit()
    db.rollback()


# --- websites in workspaces -----------------------------------------------------------------

def test_websites_in_own_and_client_workspaces(client, agency):
    own, = workspaces(client, agency)
    c = add_client(client, agency, "Bakery")
    bakery = next(w for w in workspaces(client, agency) if w["kind"] == "client")

    res = client.post(ws_url(agency, own["id"]), json={"url": "agency.example.com"})
    assert res.status_code == 201, res.text
    mine = res.json()
    assert mine["workspace_id"] == own["id"] and mine["client_id"] is None
    assert mine["workspace_name"] == "Agency" and mine["client_name"] is None

    # The older, client-based endpoint still works and lands in the client's workspace.
    res = client.post(f"{API}/{agency}/websites",
                      json={"client_id": c["id"], "url": "bakery.example.com"})
    assert res.status_code == 201
    assert res.json()["workspace_id"] == bakery["id"]
    assert res.json()["client_name"] == "Bakery"

    # Without client_id, the older endpoint uses the own workspace.
    res = client.post(f"{API}/{agency}/websites", json={"url": "blog.agency.example.com"})
    assert res.json()["workspace_id"] == own["id"]

    listed = client.get(ws_url(agency, own["id"])).json()
    assert {s["domain"] for s in listed["items"]} == {"agency.example.com",
                                                      "blog.agency.example.com"}
    assert client.get(ws_url(agency, bakery["id"])).json()["total"] == 1
    assert client.get(f"{API}/{agency}/websites").json()["total"] == 3
    assert client.get(f"{API}/{agency}/websites",
                      params={"workspace_id": bakery["id"]}).json()["total"] == 1
    counts = {w["kind"]: w["website_count"] for w in workspaces(client, agency)}
    assert counts == {"own": 2, "client": 1}


def test_website_is_only_reachable_through_its_own_workspace(client, agency):
    own, = workspaces(client, agency)
    add_client(client, agency, "Bakery")
    bakery = next(w for w in workspaces(client, agency) if w["kind"] == "client")
    site = client.post(ws_url(agency, own["id"]), json={"url": "agency.example.com"}).json()

    for method in ("GET", "PATCH", "DELETE"):
        res = client.request(method, ws_url(agency, bakery["id"], site["id"]),
                             json={"name": "x"} if method == "PATCH" else None)
        assert res.status_code == 404, method
    assert client.get(ws_url(agency, own["id"], site["id"])).status_code == 200


def test_move_website_between_workspaces(client, agency, db):
    own, = workspaces(client, agency)
    c = add_client(client, agency, "Bakery")
    bakery = next(w for w in workspaces(client, agency) if w["kind"] == "client")
    site = client.post(ws_url(agency, own["id"]), json={"url": "shop.example.com"}).json()

    res = client.patch(ws_url(agency, own["id"], site["id"]), json={"workspace_id": bakery["id"]})
    assert res.status_code == 200
    assert res.json()["workspace_id"] == bakery["id"] and res.json()["client_id"] == c["id"]
    row = db.get(Website, site["id"])
    db.refresh(row)
    assert row.client_id is not None and str(row.client_id) == c["id"]
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "website.update")).one()
    assert entry.meta["workspace"] == {"from": "Agency", "to": "Bakery"}

    res = client.patch(f"{API}/{agency}/websites/{site['id']}", json={"workspace_id": own["id"]})
    assert res.json()["client_id"] is None


def test_unknown_workspace_is_404(client, agency):
    res = client.get(f"{API}/{agency}/workspaces/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


# --- isolation ------------------------------------------------------------------------------

def test_other_organizations_workspaces_are_invisible(client, new_client, agency):
    own, = workspaces(client, agency)
    site = client.post(ws_url(agency, own["id"]), json={"url": "agency.example.com"}).json()

    other = new_client()
    other_slug = slug_of(register(other, "rival@example.com", org="Rival"))
    rival_own, = workspaces(other, other_slug)

    # Through the rival's own organization, pointing at our workspace or website: 404.
    assert other.get(f"{API}/{other_slug}/workspaces/{own['id']}").status_code == 404
    assert other.get(ws_url(other_slug, own["id"])).status_code == 404
    assert other.get(ws_url(other_slug, rival_own["id"], site["id"])).status_code == 404
    assert other.patch(f"{API}/{other_slug}/websites/{site['id']}",
                       json={"workspace_id": own["id"]}).status_code == 404
    # And moving one of its own sites into our workspace is refused.
    theirs = other.post(ws_url(other_slug, rival_own["id"]), json={"url": "rival.example.com"})
    res = other.patch(ws_url(other_slug, rival_own["id"], theirs.json()["id"]),
                      json={"workspace_id": own["id"]})
    assert res.status_code == 404
    # Through our organization: not a member, so 404.
    assert other.get(f"{API}/{agency}/workspaces").status_code == 404


def test_portal_users_see_only_their_clients_workspaces(client, new_client, db, agency):
    own, = workspaces(client, agency)
    mine = seed_client(db, agency, "Linked Co")
    seed_client(db, agency, "Other Co")
    client.post(ws_url(agency, own["id"]), json={"url": "agency.example.com"})
    browser, member = signed_in_as(new_client, db, agency, "portal@example.com", "client")
    link_client(db, member, mine)

    visible = workspaces(browser, agency)
    assert [(w["kind"], w["name"]) for w in visible] == [("client", "Linked Co")]
    assert browser.get(f"{API}/{agency}/workspaces/{own['id']}").status_code == 404
    assert browser.get(ws_url(agency, own["id"])).status_code == 404
    # Nor does the organization-wide list include the agency's own websites.
    assert browser.get(f"{API}/{agency}/websites").json()["total"] == 0
    assert browser.get(ws_url(agency, visible[0]["id"])).status_code == 200


def test_portal_user_without_links_sees_no_workspaces(new_client, db, agency):
    seed_client(db, agency, "Some Co")
    browser, _ = signed_in_as(new_client, db, agency, "portal@example.com", "client")
    assert workspaces(browser, agency) == []
