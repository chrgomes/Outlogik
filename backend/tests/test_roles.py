import pytest
from sqlalchemy import delete, select

from app.models import AuditLog, Permission, Role, RolePermission
from app.modules.rbac.catalogue import DEFAULT_ROLES, PERMISSIONS
from app.modules.rbac.service import role_permission_codes, sync_permissions
from tests.conftest import login, register, role_id, seed_member, slug_of


@pytest.fixture
def acme(client):
    return slug_of(register(client, "owner@acme.example.com", org="Acme"))


def as_role(new_client, db, slug, role_key, email=None):
    email = email or f"{role_key}@acme.example.com"
    member = seed_member(db, slug, email, role_key)
    browser = new_client()
    assert login(browser, email).status_code == 200
    return browser, member


def roles_url(slug, rid=""):
    return f"/api/v1/orgs/{slug}/roles" + (f"/{rid}" if rid else "")


def create(client, slug, name="SEO Specialist", perms=("clients.read", "websites.read")):
    return client.post(roles_url(slug), json={"name": name, "description": "Does SEO",
                                              "permissions": list(perms)})


# --- catalogue and listing ------------------------------------------------------------------

def test_permission_catalogue(client, acme):
    res = client.get(f"/api/v1/orgs/{acme}/permissions")
    assert res.status_code == 200
    codes = {p["code"]: p for p in res.json()}
    assert set(codes) == set(PERMISSIONS)
    assert codes["members.invite"]["group"] == "Team"


def test_list_roles_shows_system_roles_first_with_counts(client, acme):
    create(client, acme)
    items = client.get(roles_url(acme)).json()["items"]
    assert [r["name"] for r in items] == ["Owner", "Administrator", "Marketing Manager",
                                          "Account Manager", "Reporting Viewer",
                                          "Client Viewer", "SEO Specialist"]
    owner = items[0]
    assert owner["is_system"] and owner["member_count"] == 1
    assert set(owner["permissions"]) == set(PERMISSIONS)


def test_admin_no_longer_manages_roles(client, acme, db):
    admin_perms = set(client.get(roles_url(acme)).json()["items"][1]["permissions"])
    assert admin_perms == set(PERMISSIONS) - {"roles.manage"}


# --- create / update / delete ---------------------------------------------------------------

def test_owner_creates_updates_and_deletes_custom_role(client, acme, db):
    res = create(client, acme)
    assert res.status_code == 201, res.text
    role = res.json()
    assert role["is_system"] is False
    assert role["permissions"] == ["clients.read", "websites.read"]

    res = client.patch(roles_url(acme, role["id"]), json={
        "name": "SEO Lead", "permissions": ["clients.read", "clients.write"]})
    assert res.status_code == 200
    assert res.json()["name"] == "SEO Lead"
    assert res.json()["permissions"] == ["clients.read", "clients.write"]
    update = db.scalar(select(AuditLog).where(AuditLog.action == "role.update"))
    assert update.meta["permissions"] == {"added": ["clients.write"],
                                          "removed": ["websites.read"]}

    assert client.get(roles_url(acme, role["id"])).status_code == 200
    assert client.delete(roles_url(acme, role["id"])).status_code == 204
    assert client.get(roles_url(acme, role["id"])).status_code == 404
    actions = set(db.scalars(select(AuditLog.action)))
    assert {"role.create", "role.update", "role.delete"} <= actions


def test_role_names_are_unique_case_insensitively(client, acme):
    create(client, acme, "Writers")
    for name in ("writers", "OWNER"):
        res = create(client, acme, name)
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "role_name_taken"


def test_unknown_permission_is_rejected(client, acme):
    res = create(client, acme, perms=["clients.read", "billing.steal"])
    assert res.status_code == 422
    assert "billing.steal" in res.json()["error"]["details"][0]["message"]


def test_system_roles_are_read_only(client, acme, db):
    rid = role_id(db, acme, "member")
    res = client.patch(roles_url(acme, rid), json={"permissions": list(PERMISSIONS)})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "system_role"
    assert client.delete(roles_url(acme, rid)).status_code == 409


def test_role_in_use_cannot_be_deleted(client, acme, db):
    role = create(client, acme).json()
    client.post(f"/api/v1/orgs/{acme}/invitations",
                json={"email": "x@example.com", "role_id": role["id"]})
    res = client.delete(roles_url(acme, role["id"]))
    assert res.status_code == 409
    assert res.json()["error"]["details"] == {"members": 0, "open_invitations": 1}


def test_permission_changes_apply_immediately(client, new_client, acme, db):
    role = create(client, acme, perms=["organization.read"]).json()
    browser, member = as_role(new_client, db, acme, "member", "writer@acme.example.com")
    client.patch(f"/api/v1/orgs/{acme}/members/{member.id}", json={"role_id": role["id"]})
    assert browser.get(f"/api/v1/orgs/{acme}/members").status_code == 403

    client.patch(roles_url(acme, role["id"]),
                 json={"permissions": ["organization.read", "members.read"]})
    assert browser.get(f"/api/v1/orgs/{acme}/members").status_code == 200


# --- who may manage roles -------------------------------------------------------------------

@pytest.mark.parametrize("role_key,can_read", [("admin", True), ("member", True),
                                               ("client", False)])
def test_only_owners_manage_roles(new_client, db, acme, role_key, can_read):
    browser, _ = as_role(new_client, db, acme, role_key)
    assert (browser.get(roles_url(acme)).status_code == 200) is can_read
    res = create(browser, acme)
    assert res.status_code == 403
    assert res.json()["error"]["details"] == {"required_permission": "roles.manage"}


# --- no privilege escalation ----------------------------------------------------------------

def test_admin_cannot_assign_role_with_permissions_they_lack(client, new_client, db, acme):
    powerful = create(client, acme, "Role Manager", perms=["roles.manage"]).json()
    modest = create(client, acme, "Viewer", perms=["clients.read"]).json()
    admin, _ = as_role(new_client, db, acme, "admin")
    bob = seed_member(db, acme, "bob@acme.example.com", "member")

    res = admin.patch(f"/api/v1/orgs/{acme}/members/{bob.id}",
                      json={"role_id": powerful["id"]})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "role_exceeds_yours"
    assert res.json()["error"]["details"] == {"permissions": ["roles.manage"]}

    res = admin.post(f"/api/v1/orgs/{acme}/invitations",
                     json={"email": "x@example.com", "role_id": powerful["id"]})
    assert res.json()["error"]["code"] == "role_exceeds_yours"

    # A role within the admin's own permissions is fine.
    res = admin.patch(f"/api/v1/orgs/{acme}/members/{bob.id}", json={"role_id": modest["id"]})
    assert res.status_code == 200


def test_cannot_resend_invitation_for_role_beyond_yours(client, new_client, db, acme):
    powerful = create(client, acme, "Role Manager", perms=["roles.manage"]).json()
    inv = client.post(f"/api/v1/orgs/{acme}/invitations",
                      json={"email": "x@example.com", "role_id": powerful["id"]}).json()
    admin, _ = as_role(new_client, db, acme, "admin")
    res = admin.post(f"/api/v1/orgs/{acme}/invitations/{inv['id']}/resend")
    assert res.status_code == 403


# --- system role sync -----------------------------------------------------------------------

def test_startup_sync_restores_system_role_permissions(client, acme, db):
    admin = db.get(Role, role_id(db, acme, "admin"))
    member = db.get(Role, role_id(db, acme, "member"))
    # Simulate drift: an old catalogue gave admins roles.manage, and members lost one.
    db.add(RolePermission(role_id=admin.id, permission_id=db.scalar(
        select(Permission.id).where(Permission.code == "roles.manage"))))
    db.execute(delete(RolePermission).where(RolePermission.role_id == member.id))
    db.commit()

    sync_permissions(db)
    assert role_permission_codes(db, admin.id) == DEFAULT_ROLES["admin"]["permissions"]
    assert role_permission_codes(db, member.id) == DEFAULT_ROLES["member"]["permissions"]


def test_sync_leaves_custom_roles_alone(client, acme, db):
    role = create(client, acme, perms=["clients.read"]).json()
    sync_permissions(db)
    assert role_permission_codes(db, role["id"]) == {"clients.read"}


# --- tenant isolation -----------------------------------------------------------------------

def test_cannot_touch_another_orgs_roles(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    theirs = create(globex_owner, globex, "Their Role").json()

    assert client.get(roles_url(globex)).status_code == 404
    assert client.get(roles_url(acme, theirs["id"])).status_code == 404
    assert client.patch(roles_url(acme, theirs["id"]),
                        json={"permissions": list(PERMISSIONS)}).status_code == 404
    assert client.delete(roles_url(acme, theirs["id"])).status_code == 404
    assert role_permission_codes(db, theirs["id"]) == {"clients.read", "websites.read"}
