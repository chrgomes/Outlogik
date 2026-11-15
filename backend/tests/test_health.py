def test_liveness(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_readiness_checks_database_and_redis(client):
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 200
    assert res.json()["checks"] == {"database": "ok", "redis": "ok"}


def test_openapi_is_served(client):
    assert client.get("/api/openapi.json").status_code == 200


def test_unknown_route_uses_error_format(client):
    res = client.get("/api/v1/nope")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_security_headers_on_api_responses(client):
    for res in (client.get("/api/v1/health"), client.get("/api/v1/auth/me"),
                client.post("/api/v1/auth/logout", headers={"X-XSRF-TOKEN": "wrong"})):
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["Cache-Control"] == "no-store"
        assert res.headers["Referrer-Policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in res.headers["Content-Security-Policy"]


def test_api_docs_page_still_loads(client):
    res = client.get("/api/docs")
    assert res.status_code == 200
    assert "Content-Security-Policy" not in res.headers
