"""H1-6: the crawler: safe fetching, reading pages, robots.txt, sitemaps and limits."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.core.config import get_settings
from app.modules.audits.crawler import crawl, normalize
from app.modules.audits.fetch import address_allowed, client, fetch
from app.modules.audits.parse import parse_html

PAGES: dict[str, tuple[int, str, str]] = {}  # path → (status, content type, body)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        status, ctype, body = PAGES.get(self.path, (404, "text/html", "<title>Not found</title>"))
        self.send_response(status)
        if status in (301, 302):
            self.send_header("Location", body)
            body = ""
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def site(monkeypatch):
    """A local website on 127.0.0.1, which the crawler may visit only in tests."""
    monkeypatch.setattr(get_settings(), "crawler_allow_private", True)
    monkeypatch.setattr(get_settings(), "crawler_delay_seconds", 0)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    PAGES.clear()
    yield base
    server.shutdown()


def html(title="Page", body="", head=""):
    return (200, "text/html; charset=utf-8",
            f"<html lang='en'><head><title>{title}</title>{head}</head><body>{body}</body></html>")


# --- safety ---------------------------------------------------------------------------------

@pytest.mark.parametrize("ip,allowed", [
    ("8.8.8.8", True), ("2606:4700:4700::1111", True),
    ("127.0.0.1", False), ("10.0.0.5", False), ("172.16.3.4", False), ("192.168.1.1", False),
    ("169.254.169.254", False), ("100.64.0.1", False), ("0.0.0.0", False), ("::1", False),  # noqa: S104
    ("fd00::1", False), ("fe80::1%eth0", False), ("::ffff:127.0.0.1", False),
    ("::ffff:10.0.0.1", False), ("224.0.0.1", False),
])
def test_only_public_internet_addresses_are_fetched(ip, allowed):
    assert address_allowed(ip) is allowed


def test_private_addresses_are_refused_at_connection_time():
    with client() as c:
        for url in ("http://127.0.0.1:9/", "http://localhost:9/", "http://[::1]:9/"):
            got = fetch(c, url)
            assert got.status is None and got.error.startswith("Not fetched"), url


def test_redirects_to_private_addresses_are_refused(site, monkeypatch):
    """The test site (127.0.0.1) counts as public here; the redirect target (127.0.0.2,
    standing in for an internal service) doesn't. Each hop is checked."""
    import app.modules.audits.fetch as fetch_module

    monkeypatch.setattr(get_settings(), "crawler_allow_private", False)
    real = fetch_module.address_allowed
    monkeypatch.setattr(fetch_module, "address_allowed",
                        lambda ip: ip == "127.0.0.1" or real(ip))
    PAGES["/go"] = (302, "text/html", "http://127.0.0.2:9/admin")
    with client() as c:
        got = fetch(c, f"{site}/go")
    assert got.redirects == [f"{site}/go"]
    assert got.status is None and got.error.startswith("Not fetched: 127.0.0.2")


def test_only_http_and_https(site):
    PAGES["/ftp"] = (302, "text/html", "ftp://example.com/file")
    with client() as c:
        got = fetch(c, f"{site}/ftp")
    assert got.error == "Redirects to an address that isn't http or https."


def test_responses_are_capped(site):
    PAGES["/big"] = (200, "text/html", "x" * 50_000)
    with client() as c:
        got = fetch(c, f"{site}/big", max_bytes=10_000)
    assert got.truncated and len(got.body) == 10_000


def test_proxies_are_never_used(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://10.0.0.1:3128")
    with client() as c:
        assert c._trust_env is False


# --- reading pages --------------------------------------------------------------------------

def test_parse_reads_what_audits_need():
    page = parse_html("""
      <html lang="en-CA"><head>
        <title>  Corner   Bakery </title>
        <meta name="description" content="Fresh bread daily.">
        <meta name="robots" content="NOINDEX, follow">
        <meta name="viewport" content="width=device-width">
        <link rel="canonical" href="https://cornerbakery.example.com/">
        <script type="application/ld+json">{"@context":"https://schema.org","@graph":[
          {"@type":"LocalBusiness","name":"Corner Bakery","telephone":"+1 416 555 0100"},
          {"@type":["WebSite","Thing"]}]}</script>
        <script type="application/ld+json">{broken</script>
        <style>.a { color: red }</style>
      </head><body>
        <h1>Bread</h1><h1>And cakes</h1>
        <h2>Do you deliver?</h2>
        <div itemscope itemtype="https://schema.org/Product">Rye</div>
        <a href="/menu">Menu</a> <a href="https://other.example.com">Other</a>
        <img src="a.jpg" alt="Rye loaf"><img src="b.jpg"><img src="c.jpg" alt=" ">
        <script>var words = "not counted at all here";</script>
        <p>Fresh bread every morning.</p>
      </body></html>""")
    assert page.title == "Corner Bakery"
    assert page.meta_description == "Fresh bread daily." and page.noindex and page.has_viewport
    assert page.canonical == "https://cornerbakery.example.com/" and page.lang == "en-CA"
    assert page.h1 == ["Bread", "And cakes"] and page.headings == ["Do you deliver?"]
    assert page.links == ["/menu", "https://other.example.com"]
    assert (page.images, page.images_without_alt) == (3, 2)
    assert page.schema_types() == {"LocalBusiness", "WebSite", "Thing", "Product"}
    business = next(x for x in page.structured_data if x.get("@type") == "LocalBusiness")
    assert business["telephone"] == "+1 416 555 0100"
    assert 15 <= page.word_count <= 25  # visible text only, no script or style


def test_parse_survives_broken_html():
    page = parse_html("<html><body><h1>Open <a href='/x'>link<p>never closed <img src=y")
    assert page.links == ["/x"]


def test_normalize():
    assert normalize("HTTPS://Example.com/a#top") == "https://example.com/a"
    assert normalize("https://example.com") == "https://example.com/"


# --- crawling -------------------------------------------------------------------------------

def test_crawl_follows_links_and_the_sitemap_and_respects_robots(site):
    PAGES.update({
        "/": html("Home", "<a href='/about'>About</a> <a href='/old'>Old</a> "
                          "<a href='/private/x'>Private</a> <a href='https://elsewhere.example.com/'>"
                          "Out</a> <a href='/logo.png'>Logo</a> <a href='/missing'>Gone</a>"),
        "/about": html("About", "<a href='/'>Home</a>"),
        "/old": (301, "text/html", "/about"),
        "/only-in-sitemap": html("Hidden"),
        "/private/x": html("Private"),
        "/robots.txt": (200, "text/plain",
                        "User-agent: *\nDisallow: /private\nSitemap: " + "{base}/sitemap.xml"),
        "/sitemap.xml": (200, "application/xml",
                         "<urlset><url><loc>{base}/only-in-sitemap</loc></url></urlset>"),
    })
    for key in ("/robots.txt", "/sitemap.xml"):
        status, ctype, body = PAGES[key]
        PAGES[key] = (status, ctype, body.replace("{base}", site))

    result = crawl(site, max_pages=50)
    urls = {p.url.removeprefix(site) for p in result.pages}
    assert urls == {"/", "/about", "/old", "/only-in-sitemap", "/missing"}
    assert result.sitemap_found and result.sitemap_urls == 1
    assert result.skipped_by_robots == 1  # /private/x
    by_path = {p.url.removeprefix(site): p for p in result.pages}
    assert by_path["/old"].fetched.redirects and by_path["/old"].fetched.status == 200
    assert by_path["/missing"].fetched.status == 404
    assert result.home.page.title == "Home"


def test_crawl_stops_at_the_page_limit(site):
    PAGES["/"] = html("Home", " ".join(f"<a href='/p{i}'>p</a>" for i in range(30)))
    for i in range(30):
        PAGES[f"/p{i}"] = html(f"P{i}")
    result = crawl(site, max_pages=10)
    assert len(result.pages) == 10 and result.hit_page_limit


def test_crawl_without_robots_or_sitemap(site):
    PAGES["/"] = html("Home")
    result = crawl(site, max_pages=5)
    assert result.robots.status == 404 and not result.sitemap_found
    assert [p.url for p in result.pages] == [f"{site}/"]


def test_another_port_is_another_site(site):
    """Locally, the website and the client portal differ only by port."""
    PAGES["/"] = html("Home", "<a href='http://127.0.0.1:9/login'>Log in</a> "
                              f"<a href='{site}/about'>About</a>")
    PAGES["/about"] = html("About")
    result = crawl(site, max_pages=10)
    assert [p.url.removeprefix(site) for p in result.pages] == ["/", "/about"]
