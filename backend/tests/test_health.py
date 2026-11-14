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
