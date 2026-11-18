import pytest
from sqlalchemy import select

from app.models import AuditLog, Invitation, Website, Workspace, WorkspaceAssignment
from tests.conftest import link_client, register, seed_client, signed_in_as, slug_of


@pytest.fixture
def acme(client):
    return slug_of(register(client, "owner@acme.example.com", org="Acme"))


def url(slug, *parts):
    return "/".join([f"/api/v1/orgs/{slug}/clients", *map(str, parts)])


def make_client(c, slug, name="Bakery Ltd", **extra):
    res = c.post(url(slug), json={"name": name, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def add_site(c, slug, client_id, address):
    res = c.post(f"/api/v1/orgs/{slug}/websites", json={"client_id": client_id, "url": address})
    assert res.status_code == 201, res.text
    return res.json()


# --- CRUD -----------------------------------------------------------------------------------

def test_create_get_update_client(client, acme, db):
    created = make_client(client, acme, contact_email="Jo@Bakery.example.com",
                         notes="Pays late")
    assert created["contact_email"] == "jo@bakery.example.com"
    assert created["website_count"] == 0 and created["portal_user_count"] == 0

    res = client.patch(url(acme, created["id"]), json={"status": "archived", "notes": None})
    assert res.status_code == 200
    assert res.json()["status"] == "archived" and res.json()["notes"] is None
    # name can't be cleared
    res = client.patch(url(acme, created["id"]), json={"name": None})
    assert res.json()["name"] == "Bakery Ltd"

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "client.update"))
    assert entry.meta["fields"] == ["notes", "status"]
    assert entry.meta["status"] == "archived"


def test_list_clients_search_filter_sort(client, acme):
    for name in ("Zebra Co", "apple Inc", "Mango_Ltd"):
        make_client(client, acme, name)
    client.patch(url(acme, make_client(client, acme, "Archived Ltd")["id"]),
                 json={"status": "archived"})

    names = [c["name"] for c in client.get(url(acme)).json()["items"]]
    assert names == ["apple Inc", "Archived Ltd", "Mango_Ltd", "Zebra Co"]  # case-insensitive
    assert client.get(url(acme), params={"status": "active"}).json()["total"] == 3
    assert [c["name"] for c in client.get(url(acme), params={"q": "ZEB"}).json()["items"]] == [
        "Zebra Co"]
    # LIKE wildcards in the search are literal.
    assert [c["name"] for c in client.get(url(acme), params={"q": "_"}).json()["items"]] == [
        "Mango_Ltd"]
    newest = client.get(url(acme), params={"sort": "-created_at"}).json()["items"][0]
    assert newest["name"] == "Archived Ltd"


def test_delete_client_removes_websites_portal_access_and_invites(client, new_client, acme, db):
    c = make_client(client, acme)
    add_site(client, acme, c["id"], "bakery.example.com")
    client.post(f"/api/v1/orgs/{acme}/invitations", json={
        "email": "jo@bakery.example.com", "client_id": c["id"],
        "role_id": next(r["id"] for r in client.get(f"/api/v1/orgs/{acme}/roles").json()["items"]
                        if r["system_key"] == "client")})

    assert client.delete(url(acme, c["id"])).status_code == 204
    assert client.get(url(acme, c["id"])).status_code == 404
    assert db.scalar(select(Website)) is None
    assert db.scalar(select(Invitation)) is None
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "client.delete"))
    assert entry.meta["websites"] == 1


@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "X", "contact_email": "nope"},
                                     {"name": "X", "status": "deleted"}])
def test_client_validation(client, acme, payload):
    assert client.post(url(acme), json=payload).status_code == 422


def test_team_member_can_edit_but_not_delete(new_client, db, acme, client):
    c = make_client(client, acme)
    member, _ = signed_in_as(new_client, db, acme, "tm@acme.example.com", "member")
    assert member.patch(url(acme, c["id"]), json={"name": "Renamed"}).status_code == 200
    res = member.delete(url(acme, c["id"]))
    assert res.status_code == 403
    assert res.json()["error"]["details"] == {"required_permission": "clients.delete"}


# --- client-portal users --------------------------------------------------------------------

@pytest.fixture
def portal(client, new_client, db, acme):
    """Two clients; a portal user linked only to the first."""
    mine = seed_client(db, acme, "Bakery Ltd")
    other = seed_client(db, acme, "Garage Ltd")
    client.patch(url(acme, mine.id), json={"notes": "Internal: renewal due"})
    add_site(client, acme, str(mine.id), "bakery.example.com")
    add_site(client, acme, str(other.id), "garage.example.com")
    browser, member = signed_in_as(new_client, db, acme, "jo@bakery.example.com", "client")
    link_client(db, member, mine)
    return browser, member, mine, other


def test_portal_user_sees_only_linked_clients_without_notes(portal, acme):
    browser, _, mine, other = portal
    listed = browser.get(url(acme)).json()
    assert [c["name"] for c in listed["items"]] == ["Bakery Ltd"]
    detail = browser.get(url(acme, mine.id)).json()
    assert detail["notes"] is None
    assert detail["portal_user_count"] is None
    assert detail["website_count"] == 1
    assert browser.get(url(acme, other.id)).status_code == 404


def test_portal_user_sees_only_their_websites(portal, acme):
    browser, _, mine, other = portal
    sites = browser.get(f"/api/v1/orgs/{acme}/websites").json()["items"]
    assert [s["domain"] for s in sites] == ["bakery.example.com"]
    # Filtering by a hidden client returns nothing rather than leaking.
    res = browser.get(f"/api/v1/orgs/{acme}/websites", params={"client_id": str(other.id)})
    assert res.json()["total"] == 0


def test_portal_user_cannot_write(portal, acme):
    browser, _, mine, _ = portal
    assert browser.post(url(acme), json={"name": "Mine now"}).status_code == 403
    assert browser.patch(url(acme, mine.id), json={"name": "X"}).status_code == 403
    assert browser.post(f"/api/v1/orgs/{acme}/websites", json={
        "client_id": str(mine.id), "url": "evil.example.com"}).status_code == 403


def test_portal_user_with_no_links_sees_nothing(new_client, db, acme, client):
    seed_client(db, acme, "Bakery Ltd")
    browser, _ = signed_in_as(new_client, db, acme, "lonely@example.com", "client")
    assert browser.get(url(acme)).json()["total"] == 0
    assert browser.get(f"/api/v1/orgs/{acme}/websites").json()["total"] == 0


def test_link_and_unlink_portal_user(portal, client, acme, db):
    browser, member, mine, other = portal
    res = client.post(url(acme, other.id, "users"), json={"member_id": str(member.id)})
    assert res.status_code == 200
    assert [u["email"] for u in res.json()] == ["jo@bakery.example.com"]
    assert browser.get(url(acme)).json()["total"] == 2

    assert client.delete(url(acme, other.id, "users", member.user_id)).status_code == 204
    assert browser.get(url(acme, other.id)).status_code == 404
    assert client.delete(url(acme, other.id, "users", member.user_id)).status_code == 404
    actions = set(db.scalars(select(AuditLog.action)))
    assert {"client_user.link", "client_user.unlink"} <= actions


def test_only_client_role_members_can_be_linked(client, new_client, db, acme):
    c = seed_client(db, acme)
    _, team_member = signed_in_as(new_client, db, acme, "tm@acme.example.com", "member")
    res = client.post(url(acme, c.id, "users"), json={"member_id": str(team_member.id)})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "not_client_role"


def test_team_member_cannot_manage_portal_access(new_client, db, acme, client):
    c = seed_client(db, acme)
    tm, _ = signed_in_as(new_client, db, acme, "tm@acme.example.com", "member")
    assert tm.get(url(acme, c.id, "users")).status_code == 403


# --- tenant isolation -----------------------------------------------------------------------

def test_cannot_reach_another_orgs_clients(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    theirs = seed_client(db, globex, "Their Client")
    _, their_portal_user = signed_in_as(new_client, db, globex, "p@their.example.com", "client")
    link_client(db, their_portal_user, theirs)
    mine = seed_client(db, acme, "My Client")

    assert client.get(url(globex)).status_code == 404
    assert client.get(url(acme, theirs.id)).status_code == 404
    assert client.patch(url(acme, theirs.id), json={"name": "Pwned"}).status_code == 404
    assert client.delete(url(acme, theirs.id)).status_code == 404
    assert client.get(url(acme, theirs.id, "users")).status_code == 404
    # Linking their member to my client, or unlinking their user from their client.
    res = client.post(url(acme, mine.id, "users"), json={"member_id": str(their_portal_user.id)})
    assert res.status_code == 404
    res = client.delete(url(acme, theirs.id, "users", their_portal_user.user_id))
    assert res.status_code == 404
    assert client.get(url(acme)).json()["total"] == 1

    db.expire_all()
    assert db.get(type(theirs), theirs.id).name == "Their Client"
    assert db.scalar(select(WorkspaceAssignment).join(
        Workspace, Workspace.id == WorkspaceAssignment.workspace_id)
        .where(Workspace.client_id == theirs.id)) is not None
