"""Every organization endpoint must declare a permission, and each built-in role must get
exactly the access its permission set implies."""

import uuid

import pytest
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import app
from app.modules.rbac.catalogue import DEFAULT_ROLES
from app.tenancy.context import get_org_context
from tests.conftest import login, register, seed_member, slug_of

ORG_PREFIX = "/api/v1/orgs/{org_slug}"
# Endpoints any active member may use, by design.
NO_PERMISSION_NEEDED = {("POST", f"{ORG_PREFIX}/leave")}


def _walk(dependant):
    for dep in dependant.dependencies:
        yield dep
        yield from _walk(dep)


def org_routes():
    # iter_route_contexts flattens included routers (FastAPI keeps them nested).
    for rc in iter_route_contexts(app.routes):
        route = rc.original_route
        if isinstance(route, APIRoute) and (rc.path or "").startswith(ORG_PREFIX):
            for method in rc.methods:
                deps = list(_walk(route.dependant))
                perms = {d.call.required_permission for d in deps
                         if hasattr(d.call, "required_permission")}
                uses_org = any(d.call is get_org_context for d in deps)
                yield method, rc.path, perms, uses_org


ROUTES = sorted(org_routes(), key=lambda r: (r[1], r[0]))


def test_there_are_org_routes_to_check():
    assert len(ROUTES) >= 15


@pytest.mark.parametrize("method,path,perms,uses_org", ROUTES,
                         ids=[f"{m} {p.removeprefix(ORG_PREFIX) or '/'}" for m, p, *_ in ROUTES])
def test_every_org_route_resolves_tenant_and_declares_one_permission(method, path, perms,
                                                                    uses_org):
    assert uses_org, "route must resolve the organization through get_org_context"
    if (method, path) in NO_PERMISSION_NEEDED:
        assert perms == set()
    else:
        assert len(perms) == 1, f"{method} {path} declares {perms or 'no permission'}"


def _fill(path: str, slug: str) -> str:
    out = path.replace("{org_slug}", slug)
    while "{" in out:
        start = out.index("{")
        out = out[:start] + str(uuid.uuid4()) + out[out.index("}") + 1:]
    return out


@pytest.mark.parametrize("role_key", list(DEFAULT_ROLES))
def test_each_role_gets_exactly_its_permissions(client, new_client, db, role_key):
    slug = slug_of(register(client, "owner@acme.example.com", org="Acme"))
    if role_key == "owner":
        browser = client
    else:
        email = f"{role_key}@acme.example.com"
        seed_member(db, slug, email, role_key)
        browser = new_client()
        assert login(browser, email).status_code == 200

    allowed = DEFAULT_ROLES[role_key]["permissions"]
    checked = 0
    for method, path, perms, _ in ROUTES:
        if not perms or (method, path) in NO_PERMISSION_NEEDED:
            continue
        [perm] = perms
        # Random IDs and an empty body: the permission check runs before anything else,
        # so a denied role always gets 403, and an allowed one gets 2xx/4xx but never
        # the permission error.
        res = browser.request(method, _fill(path, slug),
                              json={} if method in {"POST", "PATCH", "PUT"} else None)
        denied = (res.status_code == 403 and res.json()["error"].get("details")
                  == {"required_permission": perm})
        assert denied is (perm not in allowed), (
            f"{role_key}: {method} {path} ({perm}) -> {res.status_code} {res.text[:200]}")
        checked += 1
    assert checked >= 15
