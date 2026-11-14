"""Website URL normalisation and validation.

Websites will be fetched by crawlers in Phase 2, so addresses that point at the server's own
network are refused here. This is a first line only: the crawler must also check the
resolved IP address at fetch time (DNS can change after a site is added).
"""

import ipaddress
from urllib.parse import urlsplit

from app.core.errors import AppError

BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa", ".test",
                    ".invalid", ".example", ".onion")


def _invalid(message: str) -> AppError:
    return AppError(message, code="validation_error", status_code=422,
                    details=[{"field": "url", "message": message}])


def normalize_url(raw: str) -> tuple[str, str]:
    """Return (normalised URL, domain). The domain drops a leading 'www.'."""
    value = raw.strip()
    if "://" not in value:
        value = "https://" + value
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise _invalid("This isn't a valid web address.") from None
    if parts.scheme.lower() not in {"http", "https"}:
        raise _invalid("Only http:// and https:// addresses are supported.")
    if parts.username or parts.password:
        raise _invalid("Addresses with a username or password aren't allowed.")
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise _invalid("This isn't a valid web address.")
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise _invalid("This domain name isn't valid.") from None
    try:
        ipaddress.ip_address(host)
        raise _invalid("Use the website's domain name, not an IP address.")
    except ValueError:
        pass
    if host == "localhost" or host.endswith(BLOCKED_SUFFIXES) or "." not in host:
        raise _invalid("This address isn't a public website.")

    scheme = parts.scheme.lower()
    default_port = {"http": 80, "https": 443}[scheme]
    netloc = host if port in (None, default_port) else f"{host}:{port}"
    path = parts.path.rstrip("/")
    url = f"{scheme}://{netloc}{path}"
    domain = host.removeprefix("www.")
    if len(url) > 2048:
        raise _invalid("This address is too long.")
    return url, domain
