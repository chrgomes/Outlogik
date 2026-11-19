"""A polite crawl of one website: robots.txt first, then pages breadth-first from the home page
and the sitemap, staying on the site's own host (with or without www)."""

import re
import time
import urllib.robotparser
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from app.core.config import get_settings
from app.modules.audits.fetch import USER_AGENT, Fetched, client, fetch
from app.modules.audits.parse import Page, parse_html

BOT_NAME = "OutlogikBot"
SITEMAP_URLS_CONSIDERED = 5000
SKIP_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".pdf", ".zip",
                   ".mp4", ".mp3", ".css", ".js", ".woff", ".woff2", ".xml", ".json", ".avif")


@dataclass
class CrawledPage:
    url: str
    depth: int
    fetched: Fetched
    found_on: str | None = None  # the first page that linked here
    page: Page | None = None  # set for HTML pages that loaded


@dataclass
class CrawlResult:
    start_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    robots: Fetched | None = None
    robots_parser: urllib.robotparser.RobotFileParser | None = None
    sitemap_found: bool = False
    sitemap_urls: int = 0
    skipped_by_robots: int = 0
    hit_page_limit: bool = False
    hit_time_limit: bool = False
    home: CrawledPage | None = None


DEFAULT_PORTS = {"http": 80, "https": 443}


def _site(url: str) -> tuple[str, int | None]:
    """The site a URL belongs to: its host (with or without www) and its port. http and
    https on their default ports count as the same site; another port is another site."""
    p = urlsplit(url)
    port = p.port if p.port not in (None, DEFAULT_PORTS.get(p.scheme)) else None
    return (p.hostname or "").removeprefix("www."), port


def normalize(url: str) -> str:
    url, _ = urldefrag(url)
    parts = urlsplit(url)
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _sitemap_locs(text: str) -> list[str]:
    # A regular expression rather than an XML parser: a sitemap is untrusted input.
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)[:SITEMAP_URLS_CONSIDERED]


def crawl(start_url: str, *, max_pages: int, max_seconds: int = 40 * 60) -> CrawlResult:
    delay = get_settings().crawler_delay_seconds
    started = time.monotonic()
    home = normalize(start_url)
    origin = urlsplit(home)
    this_site = _site(home)
    result = CrawlResult(start_url=home)

    def on_site(url: str) -> bool:
        return urlsplit(url).scheme in ("http", "https") and _site(url) == this_site

    with client() as c:
        base = f"{origin.scheme}://{origin.netloc}"
        result.robots = fetch(c, f"{base}/robots.txt", max_bytes=500_000)
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(result.robots.text().splitlines() if result.robots.ok else [])
        result.robots_parser = rp

        sitemaps = [line.split(":", 1)[1].strip() for line in result.robots.text().splitlines()
                    if result.robots.ok and line.lower().startswith("sitemap:")] or \
            [f"{base}/sitemap.xml"]
        seeds: list[str] = []
        for sm in sitemaps[:3]:
            if not on_site(sm):
                continue
            got = fetch(c, sm, max_bytes=5_000_000)
            if got.ok and "<loc>" in got.text():
                result.sitemap_found = True
                locs = _sitemap_locs(got.text())
                result.sitemap_urls += len(locs)
                seeds += [normalize(u) for u in locs if on_site(u)]

        queue: deque[tuple[str, int, str | None]] = deque(
            [(home, 0, None)] + [(u, 1, "sitemap") for u in seeds])
        seen = {home, *seeds}
        while queue:
            if len(result.pages) >= max_pages:
                result.hit_page_limit = True
                break
            if time.monotonic() - started > max_seconds:
                result.hit_time_limit = True
                break
            url, depth, found_on = queue.popleft()
            if not rp.can_fetch(BOT_NAME, url):
                result.skipped_by_robots += 1
                continue
            if result.pages:
                time.sleep(delay)
            got = fetch(c, url)
            item = CrawledPage(url=url, depth=depth, fetched=got, found_on=found_on)
            result.pages.append(item)
            if url == home:
                result.home = item
            if not (got.ok and got.is_html):
                continue
            item.page = parse_html(got.text())
            if item.page.noindex and "nofollow" in item.page.meta_robots:
                continue
            for href in item.page.links:
                target = normalize(urljoin(got.final_url, href))
                if (on_site(target) and target not in seen
                        and not urlsplit(target).path.lower().endswith(SKIP_EXTENSIONS)):
                    seen.add(target)
                    queue.append((target, depth + 1, url))
    return result


__all__ = ["BOT_NAME", "USER_AGENT", "CrawlResult", "CrawledPage", "crawl", "normalize"]
