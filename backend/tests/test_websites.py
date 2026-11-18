import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.models import AuditLog, Website
from app.modules.websites.urls import normalize_url
from tests.conftest import register, seed_client, signed_in_as, slug_of


@pytest.fixture
def acme(client):
    return slug_of(register(client, "owner@acme.example.com", org="Acme"))


def url(slug, *parts):
    return "/".join([f"/api/v1/orgs/{slug}/websites", *map(str, parts)])


def add(c, slug, client_id, address, **extra):
    return c.post(url(slug), json={"client_id": str(client_id), "url": address, **extra})


# --- URL normalisation ----------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("example.com", ("https://example.com", "example.com")),
    ("  HTTPS://WWW.Example.COM/ ", ("https://www.example.com", "example.com")),
    ("http://shop.example.com/fr/?utm=1#top", ("http://shop.example.com/fr", "shop.example.com")),
    ("https://example.com:443/blog/", ("https://example.com/blog", "example.com")),
    ("https://example.com:8443", ("https://example.com:8443", "example.com")),
    ("https://bücher.example.com", ("https://xn--bcher-kva.example.com",
                                    "xn--bcher-kva.example.com")),
])
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("raw", [
    "ftp://example.com", "javascript:alert(1)", "https://", "https://localhost",
    "http://127.0.0.1", "http://[::1]/", "http://10.0.0.5", "http://169.254.169.254/latest",
    "http://intranet", "http://printer.local", "http://db.internal", "https://user:pw@example.com",
    "http://example.com:99999",
])
def test_rejects_non_public_or_invalid_urls(raw):
    with pytest.raises(AppError) as err:
        normalize_url(raw)
    assert err.value.status_code == 422


# --- CRUD -----------------------------------------------------------------------------------

def test_create_and_read_website(client, acme, db):
    c = seed_client(db, acme, "Bakery Ltd")
    res = add(client, acme, c.id, "www.bakery.example.com/")
    assert res.status_code == 201, res.text
    site = res.json()
    assert site["url"] == "https://www.bakery.example.com"
    assert site["domain"] == "bakery.example.com"
    assert site["name"] == "bakery.example.com"  # defaults to the domain
    assert site["client_name"] == "Bakery Ltd"
    assert client.get(url(acme, site["id"])).json()["id"] == site["id"]
    assert client.get(f"/api/v1/orgs/{acme}/clients/{c.id}").json()["website_count"] == 1
    assert "website.create" in set(db.scalars(select(AuditLog.action)))


def test_bad_url_is_a_field_error(client, acme, db):
    c = seed_client(db, acme)
    res = add(client, acme, c.id, "http://192.168.1.1")
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "url"


def test_duplicate_url_in_org_is_rejected(client, acme, db):
    a, b = seed_client(db, acme, "A"), seed_client(db, acme, "B")
    assert add(client, acme, a.id, "https://example.com").status_code == 201
    res = add(client, acme, b.id, "EXAMPLE.com/")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "website_exists"
    # A different path on the same domain is a separate website.
    assert add(client, acme, b.id, "example.com/shop").status_code == 201


def test_same_url_allowed_in_different_orgs(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    assert add(client, acme, seed_client(db, acme).id, "example.com").status_code == 201
    assert add(globex_owner, globex, seed_client(db, globex).id,
               "example.com").status_code == 201


def test_update_and_move_website(client, acme, db):
    a, b = seed_client(db, acme, "A"), seed_client(db, acme, "B")
    site = add(client, acme, a.id, "example.com").json()
    res = client.patch(url(acme, site["id"]), json={
        "client_id": str(b.id), "url": "https://example.com/new/", "name": "Main site",
        "status": "paused"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["client_name"], body["url"], body["name"], body["status"]) == (
        "B", "https://example.com/new", "Main site", "paused")
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "website.update"))
    assert entry.meta["workspace"] == {"from": "A", "to": "B"}


def test_list_websites_filters(client, acme, db):
    a, b = seed_client(db, acme, "A"), seed_client(db, acme, "B")
    add(client, acme, a.id, "alpha.example.com")
    add(client, acme, a.id, "beta.example.com", status="paused")
    add(client, acme, b.id, "gamma.example.com")
    listed = lambda **p: [s["domain"] for s in client.get(url(acme), params=p).json()["items"]]  # noqa: E731
    assert listed() == ["alpha.example.com", "beta.example.com", "gamma.example.com"]
    assert listed(client_id=str(a.id)) == ["alpha.example.com", "beta.example.com"]
    assert listed(status="paused") == ["beta.example.com"]
    assert listed(q="GAM") == ["gamma.example.com"]
    assert listed(sort="-domain")[0] == "gamma.example.com"


def test_delete_website(client, acme, db):
    site = add(client, acme, seed_client(db, acme).id, "example.com").json()
    assert client.delete(url(acme, site["id"])).status_code == 204
    assert client.get(url(acme, site["id"])).status_code == 404


def test_team_member_cannot_delete_websites(client, new_client, db, acme):
    site = add(client, acme, seed_client(db, acme).id, "example.com").json()
    tm, _ = signed_in_as(new_client, db, acme, "tm@acme.example.com", "member")
    assert tm.patch(url(acme, site["id"]), json={"name": "X"}).status_code == 200
    assert tm.delete(url(acme, site["id"])).status_code == 403


# --- tenant isolation -----------------------------------------------------------------------

def test_cannot_reach_or_attach_to_another_orgs_data(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    their_client = seed_client(db, globex, "Their Client")
    theirs = add(globex_owner, globex, their_client.id, "their.example.com").json()
    mine = seed_client(db, acme, "Mine")
    my_site = add(client, acme, mine.id, "mine.example.com").json()

    assert client.get(url(globex)).status_code == 404
    assert client.get(url(acme, theirs["id"])).status_code == 404
    assert client.patch(url(acme, theirs["id"]), json={"name": "Pwned"}).status_code == 404
    assert client.delete(url(acme, theirs["id"])).status_code == 404
    # Creating in, or moving into, their client.
    assert add(client, acme, their_client.id, "x.example.com").status_code == 404
    res = client.patch(url(acme, my_site["id"]), json={"client_id": str(their_client.id)})
    assert res.status_code == 404
    # Filtering by their client id leaks nothing.
    assert client.get(url(acme), params={"client_id": str(their_client.id)}).json()["total"] == 0

    db.expire_all()
    site = db.get(Website, theirs["id"])
    assert (site.name, site.organization_id) == ("their.example.com",
                                                 their_client.organization_id)
    assert db.get(Website, my_site["id"]).client_id == mine.id
