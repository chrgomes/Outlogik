import pytest
from sqlalchemy import select, update

from app.models import AuditLog, Organization, OrganizationMember, WorkspaceAssignment
from tests.conftest import (
    link_client,
    login,
    register,
    role_id,
    seed_client,
    seed_member,
    slug_of,
)


@pytest.fixture
def acme(client):
    """Org 'acme' with its owner signed in on `client`."""
    return slug_of(register(client, "owner@acme.example.com", org="Acme"))


def signed_in(new_client, db, slug, email, role_key, **kw):
    member = seed_member(db, slug, email, role_key, **kw)
    browser = new_client()
    assert login(browser, email).status_code == 200
    return browser, member


def members_url(slug, member_id=""):
    return f"/api/v1/orgs/{slug}/members" + (f"/{member_id}" if member_id else "")


# --- organization ---------------------------------------------------------------------------

def test_list_my_organizations(client, acme, db):
    res = client.get("/api/v1/organizations")
    assert res.status_code == 200
    assert [o["organization_slug"] for o in res.json()] == [acme]


def test_get_organization(client, acme):
    res = client.get(f"/api/v1/orgs/{acme}")
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == acme
    assert body["your_role"] == "Owner"
    assert "members.invite" in body["your_permissions"]


def test_unknown_and_foreign_org_look_the_same(client, acme, new_client):
    register(new_client(), "boss@globex.example.com", org="Globex")
    foreign = client.get("/api/v1/orgs/globex")
    missing = client.get("/api/v1/orgs/does-not-exist")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_org_routes_require_login(new_client, acme):
    assert new_client().get(f"/api/v1/orgs/{acme}").status_code == 401


def test_update_organization_name(client, acme, db):
    res = client.patch(f"/api/v1/orgs/{acme}", json={"name": "Acme Digital"})
    assert res.status_code == 200
    assert res.json()["name"] == "Acme Digital"
    assert res.json()["slug"] == acme  # slugs don't change, so links keep working
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "organization.update"))
    assert entry.meta["name"] == {"from": "Acme", "to": "Acme Digital"}


def test_team_member_cannot_update_organization(new_client, db, acme):
    browser, _ = signed_in(new_client, db, acme, "tm@acme.example.com", "member")
    res = browser.patch(f"/api/v1/orgs/{acme}", json={"name": "Hijacked"})
    assert res.status_code == 403
    assert res.json()["error"]["details"] == {"required_permission": "organization.update"}


def test_suspended_organization_is_blocked(client, acme, db):
    db.execute(update(Organization).values(status="suspended"))
    db.commit()
    res = client.get(f"/api/v1/orgs/{acme}")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "org_suspended"


# --- members: list --------------------------------------------------------------------------

def test_list_members_with_search_sort_and_pagination(client, acme, db):
    seed_member(db, acme, "alice@acme.example.com", "admin", name="Alice")
    seed_member(db, acme, "bob@acme.example.com", "member", name="Bob")
    seed_member(db, acme, "carol@acme.example.com", "member", name="Carol", status="disabled")

    res = client.get(members_url(acme), params={"sort": "name", "page_size": 2})
    body = res.json()
    assert res.status_code == 200
    assert body["total"] == 4
    assert [m["full_name"] for m in body["items"]] == ["Alice", "Bob"]

    page2 = client.get(members_url(acme), params={"sort": "name", "page_size": 2, "page": 2})
    assert [m["full_name"] for m in page2.json()["items"]] == ["Carol", "Olive Owner"]

    found = client.get(members_url(acme), params={"q": "BOB"}).json()
    assert [m["email"] for m in found["items"]] == ["bob@acme.example.com"]

    disabled = client.get(members_url(acme), params={"status": "disabled"}).json()
    assert [m["full_name"] for m in disabled["items"]] == ["Carol"]

    by_role = client.get(members_url(acme), params={"role_id": role_id(db, acme, "member")})
    assert by_role.json()["total"] == 2

    me = next(m for m in client.get(members_url(acme)).json()["items"] if m["is_you"])
    assert me["role"]["system_key"] == "owner"


def test_invalid_sort_is_rejected(client, acme):
    res = client.get(members_url(acme), params={"sort": "password_hash"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_sort"


def test_client_user_cannot_list_members(new_client, db, acme):
    browser, _ = signed_in(new_client, db, acme, "cu@client.example.com", "client")
    assert browser.get(members_url(acme)).status_code == 403


# --- members: change role / status ----------------------------------------------------------

def test_owner_changes_member_role(client, acme, db):
    member = seed_member(db, acme, "bob@acme.example.com", "member")
    res = client.patch(members_url(acme, member.id), json={"role_id": role_id(db, acme, "admin")})
    assert res.status_code == 200
    assert res.json()["role"]["name"] == "Administrator"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "member.update"))
    assert entry.meta["role"] == {"from": "Marketing Manager", "to": "Administrator"}


def test_admin_cannot_promote_to_owner_or_touch_owners(new_client, db, acme):
    admin, _ = signed_in(new_client, db, acme, "admin@acme.example.com", "admin")
    bob = seed_member(db, acme, "bob@acme.example.com", "member")
    owner_id = db.scalar(select(OrganizationMember.id).where(
        OrganizationMember.role_id == role_id(db, acme, "owner")))

    res = admin.patch(members_url(acme, bob.id), json={"role_id": role_id(db, acme, "owner")})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "owner_required"

    res = admin.patch(members_url(acme, owner_id), json={"status": "disabled"})
    assert res.status_code == 403
    assert admin.delete(members_url(acme, owner_id)).status_code == 403


def test_cannot_change_own_role(client, acme, db):
    me = client.get(members_url(acme)).json()["items"][0]
    res = client.patch(members_url(acme, me["id"]), json={"role_id": role_id(db, acme, "admin")})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "cannot_modify_self"


def test_last_owner_is_protected(new_client, db, acme):
    other_owner, _ = signed_in(new_client, db, acme, "owner2@acme.example.com", "owner")
    first_owner_id = db.scalar(
        select(OrganizationMember.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.role_id == role_id(db, acme, "owner"))
        .order_by(OrganizationMember.created_at)
    )
    # With two owners, one can demote the other...
    res = other_owner.patch(members_url(acme, first_owner_id),
                            json={"role_id": role_id(db, acme, "admin")})
    assert res.status_code == 200
    # ...but the last owner can't leave.
    res = other_owner.post(f"/api/v1/orgs/{acme}/leave")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "last_owner"


def test_client_and_team_roles_cannot_be_swapped(client, acme, db):
    cu = seed_member(db, acme, "cu@client.example.com", "client")
    res = client.patch(members_url(acme, cu.id), json={"role_id": role_id(db, acme, "member")})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "role_kind_change"


def test_disabled_member_loses_access_immediately(client, new_client, db, acme):
    browser, member = signed_in(new_client, db, acme, "bob@acme.example.com", "member")
    assert browser.get(f"/api/v1/orgs/{acme}").status_code == 200
    assert client.patch(members_url(acme, member.id),
                        json={"status": "disabled"}).status_code == 200
    assert browser.get(f"/api/v1/orgs/{acme}").status_code == 404
    assert browser.get("/api/v1/organizations").json() == []


def test_team_member_cannot_change_roles(new_client, db, acme):
    browser, _ = signed_in(new_client, db, acme, "tm@acme.example.com", "member")
    bob = seed_member(db, acme, "bob@acme.example.com", "member")
    res = browser.patch(members_url(acme, bob.id), json={"status": "disabled"})
    assert res.status_code == 403


# --- members: remove / leave ----------------------------------------------------------------

def test_remove_member_also_removes_client_access(client, new_client, db, acme):
    browser, member = signed_in(new_client, db, acme, "cu@client.example.com", "client")
    c = seed_client(db, acme)
    link_client(db, member, c)

    assert client.delete(members_url(acme, member.id)).status_code == 204
    assert db.scalar(select(WorkspaceAssignment)) is None
    assert browser.get(f"/api/v1/orgs/{acme}").status_code == 404
    assert "member.remove" in db.scalars(select(AuditLog.action)).all()


def test_member_can_leave(new_client, db, acme):
    browser, _ = signed_in(new_client, db, acme, "bob@acme.example.com", "member")
    assert browser.post(f"/api/v1/orgs/{acme}/leave").status_code == 204
    assert browser.get(f"/api/v1/orgs/{acme}").status_code == 404


# --- tenant isolation -----------------------------------------------------------------------

def test_cannot_reach_another_orgs_members(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    victim = seed_member(db, globex, "victim@globex.example.com", "member")
    globex_admin_role = role_id(db, globex, "admin")

    # Through the other org's slug: not a member, so 404.
    assert client.get(members_url(globex)).status_code == 404
    assert client.patch(members_url(globex, victim.id),
                        json={"status": "disabled"}).status_code == 404

    # Through our own slug with their IDs: still 404, nothing changes.
    assert client.patch(members_url(acme, victim.id),
                        json={"status": "disabled"}).status_code == 404
    assert client.delete(members_url(acme, victim.id)).status_code == 404
    acme_member = seed_member(db, acme, "bob@acme.example.com", "member")
    res = client.patch(members_url(acme, acme_member.id), json={"role_id": globex_admin_role})
    assert res.status_code == 404

    db.expire_all()
    assert db.get(OrganizationMember, victim.id).status == "active"
