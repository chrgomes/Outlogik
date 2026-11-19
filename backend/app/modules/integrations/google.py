"""Every call Outlogik makes to Google: sign-in (OAuth 2.0 with PKCE), the account's Analytics
properties and Search Console sites, report data, and revoking access.

Only read-only scopes are requested. Tests replace TRANSPORT with recorded responses.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - an address, not a secret
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
ANALYTICS_ADMIN = "https://analyticsadmin.googleapis.com/v1beta"
ANALYTICS_DATA = "https://analyticsdata.googleapis.com/v1beta"
SEARCH_CONSOLE = "https://www.googleapis.com/webmasters/v3"
SCOPES = [
    "openid", "email",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

TRANSPORT: httpx.BaseTransport | None = None  # tests only


class GoogleError(AppError):
    """Google refused or failed. `reconnect` means the stored access is no longer valid.
    Shown to the person as a 502 (Google failed) or 409 (reconnect needed)."""

    def __init__(self, message: str, *, reconnect: bool = False):
        super().__init__(message, code="google_reconnect_needed" if reconnect else "google_error",
                         status_code=409 if reconnect else 502)
        self.reconnect = reconnect


def configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def _client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0), transport=TRANSPORT)


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.rstrip(b"=").decode()


def authorization_url(state: str, challenge: str) -> str:
    s = get_settings()
    return AUTH_URL + "?" + urlencode({
        "client_id": s.google_client_id, "redirect_uri": s.google_callback_url,
        "response_type": "code", "scope": " ".join(SCOPES), "state": state,
        "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true",
        "code_challenge": challenge, "code_challenge_method": "S256",
    })


@dataclass
class Tokens:
    access_token: str
    refresh_token: str | None
    scopes: list[str]


def _token(data: dict[str, str]) -> dict[str, Any]:
    s = get_settings()
    with _client() as c:
        r = c.post(TOKEN_URL, data={**data, "client_id": s.google_client_id,
                                    "client_secret": s.google_client_secret})
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200:
        error = body.get("error", "")
        raise GoogleError(f"Google refused ({error or r.status_code}).",
                          reconnect=error in ("invalid_grant", "unauthorized_client"))
    return body


def exchange_code(code: str, verifier: str) -> Tokens:
    body = _token({"grant_type": "authorization_code", "code": code, "code_verifier": verifier,
                   "redirect_uri": get_settings().google_callback_url})
    return Tokens(body["access_token"], body.get("refresh_token"),
                  body.get("scope", "").split())


def access_token(refresh_token: str) -> str:
    return _token({"grant_type": "refresh_token", "refresh_token": refresh_token})["access_token"]


def revoke(token: str) -> None:
    try:
        with _client() as c:
            c.post(REVOKE_URL, data={"token": token})
    except httpx.HTTPError:
        pass  # removing our copy is what matters; Google also expires unused tokens


def _call(method: str, url: str, token: str, **kw) -> dict[str, Any]:
    try:
        with _client() as c:
            r = c.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kw)
    except httpx.HTTPError as exc:
        raise GoogleError(f"Couldn't reach Google ({type(exc).__name__}).") from exc
    if r.status_code == 401:
        raise GoogleError("Google no longer accepts this connection.", reconnect=True)
    if r.status_code == 403:
        raise GoogleError("The connected Google account can't read this data any more.",
                          reconnect=True)
    if r.status_code != 200:
        raise GoogleError(f"Google answered {r.status_code}.")
    return r.json()


def email(token: str) -> str | None:
    return _call("GET", USERINFO_URL, token).get("email")


def ga4_properties(token: str) -> list[dict[str, str]]:
    out, page = [], None
    for _ in range(20):  # 20 pages of 200 accounts is plenty
        params = {"pageSize": 200, **({"pageToken": page} if page else {})}
        body = _call("GET", f"{ANALYTICS_ADMIN}/accountSummaries", token, params=params)
        for account in body.get("accountSummaries", []):
            for prop in account.get("propertySummaries", []):
                out.append({"id": prop["property"], "name": prop.get("displayName", ""),
                            "account": account.get("displayName", "")})
        page = body.get("nextPageToken")
        if not page:
            break
    return out


def search_console_sites(token: str) -> list[dict[str, str]]:
    body = _call("GET", f"{SEARCH_CONSOLE}/sites", token)
    return [{"site_url": e["siteUrl"], "permission": e.get("permissionLevel", "")}
            for e in body.get("siteEntry", []) if e.get("permissionLevel") != "siteUnverifiedUser"]


def ga4_report(token: str, property_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return _call("POST", f"{ANALYTICS_DATA}/{property_id}:runReport", token, json=body)


def search_analytics(token: str, site_url: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{SEARCH_CONSOLE}/sites/{quote(site_url, safe='')}/searchAnalytics/query"
    return _call("POST", url, token, json=body)
