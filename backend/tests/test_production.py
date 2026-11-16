"""Settings and behaviour that matter once Outlogik is hosted (step 14)."""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.core.request import client_ip
from app.main import create_app


@pytest.mark.parametrize(
    "given, expected",
    [
        (
            "postgresql://u:p@db.example.com:25060/defaultdb?sslmode=require",
            "postgresql+psycopg://u:p@db.example.com:25060/defaultdb?sslmode=require",
        ),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_hosting_database_urls_use_the_psycopg_driver(given, expected):
    assert Settings(database_url=given).database_url == expected


def request(headers: dict[str, str], peer: str = "10.0.0.5") -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": (peer, 1234),
        }
    )


def test_client_ip_defaults_to_the_connection():
    assert client_ip(request({"do-connecting-ip": "1.2.3.4"})) == "10.0.0.5"


def test_client_ip_from_the_platform_header(monkeypatch):
    monkeypatch.setattr(get_settings(), "client_ip_header", "do-connecting-ip")
    assert client_ip(request({"do-connecting-ip": "203.0.113.7"})) == "203.0.113.7"
    assert client_ip(request({})) == "10.0.0.5"


def test_website_can_vouch_for_the_visitor_only_with_the_secret(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "client_ip_header", "do-connecting-ip")
    monkeypatch.setattr(s, "site_proxy_secret", "s3cret-value")
    vouched = {
        "x-site-proxy-key": "s3cret-value",
        "x-site-client-ip": "198.51.100.9",
        "do-connecting-ip": "10.1.1.1",
    }
    assert client_ip(request(vouched)) == "198.51.100.9"
    # A visitor sending the header themselves (wrong or missing secret) can't choose their IP.
    forged = {**vouched, "x-site-proxy-key": "guess"}
    assert client_ip(request(forged)) == "10.1.1.1"
    assert (
        client_ip(request({"x-site-client-ip": "198.51.100.9", "do-connecting-ip": "10.1.1.1"}))
        == "10.1.1.1"
    )


def test_api_docs_are_off_in_production(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    with TestClient(create_app()) as c:
        assert c.get("/api/docs").status_code == 404
        assert c.get("/api/openapi.json").status_code == 404
        assert c.get("/api/v1/health").status_code == 200
