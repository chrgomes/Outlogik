"""Fetching other people's websites safely (server-side request forgery protection).

Every connection resolves the host name itself, refuses it unless *every* address it resolves
to is a public internet address, and then connects to the address it checked, so a DNS answer
can't change between the check and the connection. Redirects are followed by hand, each hop
checked the same way. No proxies are used (trust_env=False), so the check is on the real
destination. Responses are capped in size and time.
"""

import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import certifi
import httpcore
import httpx

from app.core.config import get_settings

USER_AGENT = "OutlogikBot/1.0 (+https://outlogik.com)"
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
READABLE = ("text/html", "application/xhtml", "text/plain", "application/xml", "text/xml")


class BlockedAddress(httpcore.ConnectError):
    """The host resolves to an address that isn't on the public internet."""


def address_allowed(ip: str) -> bool:
    if get_settings().crawler_allow_private:  # tests only; refused in production (config)
        return True
    addr = ipaddress.ip_address(ip.split("%", 1)[0])
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


class _SafeBackend(httpcore.SyncBackend):
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise httpcore.ConnectError(f"Couldn't find {host}") from exc
        ips = list(dict.fromkeys(info[4][0] for info in infos))
        if not ips or not all(address_allowed(ip) for ip in ips):
            raise BlockedAddress(f"{host} isn't a public internet address")
        # Connect to the address that was checked. TLS still verifies the certificate against
        # the original host name (httpcore passes it as server_hostname).
        return super().connect_tcp(ips[0], port, timeout, local_address, socket_options)


class _SafeTransport(httpx.HTTPTransport):
    def __init__(self) -> None:
        super().__init__(retries=0)
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(cafile=certifi.where()),
            network_backend=_SafeBackend(), max_connections=4, http1=True, http2=False)


def client() -> httpx.Client:
    return httpx.Client(transport=_SafeTransport(), trust_env=False, follow_redirects=False,
                        timeout=httpx.Timeout(10.0, connect=5.0),
                        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})


@dataclass
class Fetched:
    url: str                      # what was asked for
    final_url: str                # after redirects
    status: int | None = None     # None: no response (error)
    content_type: str = ""
    body: bytes = b""
    elapsed_ms: int = 0
    redirects: list[str] = field(default_factory=list)
    error: str | None = None
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def fetch(c: httpx.Client, url: str, *, max_bytes: int = MAX_BYTES) -> Fetched:
    result = Fetched(url=url, final_url=url)
    current = url
    started = time.perf_counter()
    for _ in range(MAX_REDIRECTS + 1):
        if urlsplit(current).scheme not in ("http", "https"):
            result.error = "Redirects to an address that isn't http or https."
            return result
        try:
            with c.stream("GET", current) as r:
                if r.is_redirect and "location" in r.headers:
                    result.redirects.append(current)
                    current = urljoin(current, r.headers["location"])
                    result.final_url = current
                    continue
                result.status = r.status_code
                result.final_url = current
                result.content_type = r.headers.get("content-type", "").lower()
                if any(t in result.content_type for t in READABLE):
                    chunks, size = [], 0
                    for chunk in r.iter_bytes():
                        chunks.append(chunk)
                        size += len(chunk)
                        if size > max_bytes:
                            result.truncated = True
                            break
                    result.body = b"".join(chunks)[:max_bytes]
                break
        except httpx.ConnectError as exc:
            blocked = isinstance(exc.__cause__, BlockedAddress) or isinstance(exc, BlockedAddress)
            result.error = (f"Not fetched: {exc.__cause__ or exc}." if blocked
                            else f"Couldn't connect: {exc}"[:300])
            break
        except httpx.TimeoutException:
            result.error = "The server took too long to answer."
            break
        except httpx.HTTPError as exc:
            result.error = f"Couldn't connect: {exc}"[:300]
            break
    else:
        result.error = "Too many redirects."
    result.elapsed_ms = int((time.perf_counter() - started) * 1000)
    return result
