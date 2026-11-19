"""What an audit checks, and the checks themselves.

Each check has a severity (error, warning, notice), an area (seo, technical, ai_search), and
plain explanations of why it matters and how to fix it. Checks only report what was found on
the pages crawled; nothing here is a ranking or a score from a search engine.
"""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from app.modules.audits.crawler import BOT_NAME, CrawlResult, normalize


@dataclass(frozen=True)
class Check:
    title: str
    severity: str  # error | warning | notice
    area: str      # seo | technical | ai_search
    why: str
    fix: str


CHECKS: dict[str, Check] = {
    # --- technical --------------------------------------------------------------------------
    "home_unreachable": Check(
        "The home page didn't load", "error", "technical",
        "If the home page can't be loaded, search engines and visitors can't reach the site, "
        "and the rest of the audit can't run.",
        "Check the address is right and the site is online. The details show the error."),
    "not_https": Check(
        "The site isn't served over HTTPS", "error", "technical",
        "Browsers mark plain http:// pages as not secure, and search engines prefer HTTPS.",
        "Install a certificate (most hosts offer a free one) and redirect http:// to https://."),
    "page_broken": Check(
        "Broken page (4xx)", "error", "technical",
        "Visitors and search engines following this link reach an error page.",
        "Fix or remove the links to it, or redirect the address to the right page."),
    "server_error": Check(
        "Server error (5xx)", "error", "technical",
        "The server failed to answer. Repeated errors can drop pages from search results.",
        "Check the server or hosting logs for this page."),
    "fetch_failed": Check(
        "Page couldn't be loaded", "error", "technical",
        "The page didn't answer in time, or the connection failed.",
        "Check that the page loads in a browser, and that the server isn't overloaded."),
    "robots_blocks_all": Check(
        "robots.txt blocks all search engines", "error", "technical",
        "A 'Disallow: /' rule for every crawler keeps the whole site out of search results.",
        "Remove the rule unless the site really should be hidden (for example, a staging site)."),
    "redirect_chain": Check(
        "Redirect chain", "warning", "technical",
        "Several redirects in a row slow pages down and waste search engines' crawl time.",
        "Point links and the first redirect straight at the final address."),
    "slow_page": Check(
        "Slow to respond", "warning", "technical",
        "The page took more than 3 seconds to arrive. Slow pages lose visitors.",
        "Look at hosting, caching and page size. The page speed results go into more detail."),
    "sitemap_missing": Check(
        "No XML sitemap", "warning", "technical",
        "A sitemap tells search engines which pages exist, so new pages are found sooner.",
        "Most website builders and SEO plugins create one. Add its address to robots.txt."),
    "viewport_missing": Check(
        "Not set up for phones", "warning", "technical",
        "Without a viewport tag, phones show the desktop layout zoomed out. Search engines "
        "index the mobile version of pages.",
        'Add <meta name="viewport" content="width=device-width, initial-scale=1"> to the page.'),
    "robots_missing": Check(
        "No robots.txt", "notice", "technical",
        "Not a problem by itself, but robots.txt is where you list your sitemap and steer "
        "crawlers.",
        "Add a robots.txt with at least a Sitemap: line."),
    "noindex": Check(
        "Hidden from search engines", "notice", "technical",
        "This page asks search engines not to index it (noindex).",
        "Fine for pages like thank-you pages. If it should appear in search, remove noindex."),
    "slow_mobile_performance": Check(
        "Slow on mobile (PageSpeed)", "warning", "technical",
        "Google's PageSpeed test scored the home page below 50 for mobile.",
        "The PageSpeed results list what slows the page down, largest first."),
    # --- SEO --------------------------------------------------------------------------------
    "title_missing": Check(
        "Missing page title", "error", "seo",
        "The title is the headline shown in search results and browser tabs.",
        "Give every page a unique title describing what it's about."),
    "title_too_long": Check(
        "Page title too long", "warning", "seo",
        "Titles over about 60 characters are cut off in search results.",
        "Shorten it, putting the most important words first."),
    "title_too_short": Check(
        "Page title very short", "notice", "seo",
        "A very short title gives search engines and people little to go on.",
        "Describe the page in a few more words."),
    "title_duplicate": Check(
        "Same title as other pages", "warning", "seo",
        "When pages share a title, search engines can't tell which one to show.",
        "Make each page's title unique."),
    "meta_description_missing": Check(
        "Missing meta description", "warning", "seo",
        "The description is often the text shown under the title in search results.",
        "Write one or two sentences (up to about 155 characters) summarising the page."),
    "meta_description_too_long": Check(
        "Meta description too long", "notice", "seo",
        "Descriptions over about 160 characters are cut off in search results.",
        "Shorten it to about 155 characters."),
    "meta_description_duplicate": Check(
        "Same meta description as other pages", "notice", "seo",
        "Repeated descriptions make pages look the same in search results.",
        "Write a description for each page."),
    "h1_missing": Check(
        "No main heading (H1)", "warning", "seo",
        "The main heading tells visitors and search engines what the page is about.",
        "Add one H1 heading near the top of the page."),
    "h1_multiple": Check(
        "Several main headings (H1)", "notice", "seo",
        "More than one H1 makes the page's main topic less clear.",
        "Keep one H1 and use H2 or H3 for the other headings."),
    "images_missing_alt": Check(
        "Images without alt text", "warning", "seo",
        "Alt text describes images to screen readers and search engines.",
        "Add a short description to each meaningful image (decorative ones can stay empty)."),
    "thin_content": Check(
        "Very little text", "notice", "seo",
        "Pages with under 200 words often don't answer a searcher's question well.",
        "If the page should rank, add useful detail. If not, consider noindex."),
    "canonical_elsewhere": Check(
        "Canonical points to another page", "notice", "seo",
        "This page tells search engines that another address is the main version, so this "
        "one usually won't appear in results.",
        "Fine for duplicates. If this page should appear in search, point the canonical at "
        "itself."),
    "lang_missing": Check(
        "Page language not set", "notice", "seo",
        "The lang attribute helps search engines and screen readers handle the page's language.",
        'Add lang to the html tag, for example <html lang="en-CA">.'),
    # --- AI search readiness ----------------------------------------------------------------
    "ai_search_crawlers_blocked": Check(
        "AI search crawlers are blocked", "warning", "ai_search",
        "robots.txt keeps out crawlers that AI search tools (ChatGPT search, Perplexity, "
        "Copilot, Google's AI features) use to read and cite websites.",
        "Allow the search crawlers named in the details. Blocking AI training crawlers is a "
        "separate choice and doesn't affect this."),
    "structured_data_missing": Check(
        "No structured data on the home page", "warning", "ai_search",
        "Structured data (schema.org) states facts about the business plainly, which search "
        "engines and AI answers can use.",
        "Add JSON-LD describing the business (Organization or LocalBusiness): name, address, "
        "phone, opening hours, website."),
    "organization_schema_missing": Check(
        "Business details aren't in structured data", "notice", "ai_search",
        "The home page has structured data, but none that describes the business itself.",
        "Add an Organization or LocalBusiness item with the business's name, address and phone."),
    "business_details_inconsistent": Check(
        "Business details differ between pages", "warning", "ai_search",
        "Different names, phone numbers or addresses in structured data make it unclear which "
        "is right, for search engines and AI answers alike.",
        "Use the same details everywhere. The details show each version and where it appears."),
    "questions_not_marked_up": Check(
        "Questions without FAQ structured data", "notice", "ai_search",
        "The page answers several questions, but they aren't marked up, so the answers are "
        "harder for search engines and AI tools to pick out.",
        "Add FAQPage structured data for the questions and answers on this page."),
}

# Crawlers AI search and answer tools use to read sites, and training-only crawlers.
AI_SEARCH_CRAWLERS = {
    "Googlebot": "Google Search, including AI Overviews",
    "Bingbot": "Bing and Microsoft Copilot",
    "OAI-SearchBot": "ChatGPT search",
    "ChatGPT-User": "ChatGPT reading a page for a user",
    "PerplexityBot": "Perplexity",
}
AI_TRAINING_CRAWLERS = {
    "GPTBot": "OpenAI model training",
    "Google-Extended": "Google AI model training",
    "ClaudeBot": "Anthropic model training",
    "CCBot": "Common Crawl (used to train many models)",
}
BUSINESS_TYPES = {"Organization", "LocalBusiness", "Corporation", "ProfessionalService",
                  "Store", "Restaurant", "MedicalBusiness", "LegalService",
                  "HomeAndConstructionBusiness"}
SLOW_MS = 3000


@dataclass
class Found:
    check: str
    url: str | None = None
    details: dict[str, Any] | None = None


def _business_items(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in data:
        t = item.get("@type")
        types = set(t if isinstance(t, list) else [t])
        if types & BUSINESS_TYPES or ({"address", "telephone"} & item.keys()
                                      and not types & {"WebSite", "WebPage", "Person"}):
            out.append(item)
    return out


def _address(value: Any) -> str | None:
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("streetAddress", "addressLocality", "postalCode")]
        value = ", ".join(str(p) for p in parts if p)
    return re.sub(r"\s+", " ", str(value)).strip().lower() if value else None


def run_checks(r: CrawlResult) -> tuple[list[Found], dict[str, Any]]:
    found: list[Found] = []
    home = r.home
    rp = r.robots_parser
    home_url = r.start_url
    facts: dict[str, Any] = {
        "robots_txt": r.robots.status if r.robots else None,
        "sitemap": r.sitemap_found, "sitemap_urls": r.sitemap_urls,
        "skipped_by_robots": r.skipped_by_robots,
        "hit_page_limit": r.hit_page_limit, "hit_time_limit": r.hit_time_limit,
    }

    if home is None or not home.fetched.ok:
        got = home.fetched if home else None
        found.append(Found("home_unreachable", home_url, {
            "status": got.status if got else None, "error": got.error if got else None}))
        return found, facts

    final = home.fetched.final_url
    facts["https"] = final.startswith("https://")
    if not facts["https"]:
        found.append(Found("not_https", final))

    # robots.txt and AI crawlers
    if r.robots and r.robots.status == 404:
        found.append(Found("robots_missing"))
    if rp is not None:
        if not rp.can_fetch("*", final) and not rp.can_fetch("Googlebot", final):
            found.append(Found("robots_blocks_all"))
        search = {name: rp.can_fetch(name, final) for name in AI_SEARCH_CRAWLERS}
        training = {name: rp.can_fetch(name, final) for name in AI_TRAINING_CRAWLERS}
        facts["ai_search_crawlers"] = search
        facts["ai_training_crawlers"] = training
        blocked = [n for n, ok in search.items() if not ok]
        if blocked:
            found.append(Found("ai_search_crawlers_blocked", None, {
                "blocked": [f"{n} ({AI_SEARCH_CRAWLERS[n]})" for n in blocked]}))
    if not r.sitemap_found:
        found.append(Found("sitemap_missing"))

    # each page
    titles: dict[str, list[str]] = {}
    descriptions: dict[str, list[str]] = {}
    checked: set[str] = set()
    for p in r.pages:
        got = p.fetched
        where = {"linked_from": p.found_on} if p.found_on else {}
        if got.status is None:
            found.append(Found("fetch_failed", p.url, {"error": got.error, **where}))
            continue
        if 400 <= got.status < 500:
            found.append(Found("page_broken", p.url, {"status": got.status, **where}))
            continue
        if got.status >= 500:
            found.append(Found("server_error", p.url, {"status": got.status, **where}))
            continue
        if len(got.redirects) >= 2:
            found.append(Found("redirect_chain", p.url, {"hops": got.redirects + [got.final_url]}))
        if got.elapsed_ms > SLOW_MS:
            found.append(Found("slow_page", p.url, {"seconds": round(got.elapsed_ms / 1000, 1)}))
        page = p.page
        if page is None or normalize(got.final_url) in checked:
            continue  # several addresses can redirect to the same page: check it once
        url = got.final_url
        checked.add(normalize(url))
        if not page.has_viewport:
            found.append(Found("viewport_missing", url))
        if page.noindex:
            found.append(Found("noindex", url))
        points_elsewhere = False
        if page.canonical:
            canonical = normalize(urljoin(url, page.canonical))
            if canonical != normalize(url):
                points_elsewhere = True
                found.append(Found("canonical_elsewhere", url, {"canonical": canonical}))
        title = page.title or ""
        if not title:
            found.append(Found("title_missing", url))
        else:
            if not points_elsewhere:  # a declared duplicate isn't a duplicate problem
                titles.setdefault(title.lower(), []).append(url)
            if len(title) > 60:
                found.append(Found("title_too_long", url, {"title": title, "length": len(title)}))
            elif len(title) < 10:
                found.append(Found("title_too_short", url, {"title": title}))
        desc = page.meta_description or ""
        if not desc:
            found.append(Found("meta_description_missing", url))
        else:
            if not points_elsewhere:
                descriptions.setdefault(desc.lower(), []).append(url)
            if len(desc) > 160:
                found.append(Found("meta_description_too_long", url, {"length": len(desc)}))
        if not page.h1:
            found.append(Found("h1_missing", url))
        elif len(page.h1) > 1:
            found.append(Found("h1_multiple", url, {"headings": page.h1[:5]}))
        if page.images_without_alt:
            found.append(Found("images_missing_alt", url, {
                "images": page.images_without_alt, "of": page.images}))
        if page.word_count < 200 and not page.noindex:
            found.append(Found("thin_content", url, {"words": page.word_count}))
        questions = [h for h in page.headings if h.rstrip().endswith("?")]
        if len(questions) >= 2 and "FAQPage" not in page.schema_types():
            found.append(Found("questions_not_marked_up", url, {"questions": questions[:5]}))

    duplicates = (("title_duplicate", titles), ("meta_description_duplicate", descriptions))
    for check, groups in duplicates:
        for urls in groups.values():
            if len(urls) > 1:
                for u in urls:
                    found.append(Found(check, u, {"same_as": [x for x in urls if x != u][:5]}))

    # home page language and structured data
    hp = home.page
    if hp is not None:
        if not hp.lang:
            found.append(Found("lang_missing", final))
        types = hp.schema_types()
        facts["structured_data_types"] = sorted(types)
        if not types:
            found.append(Found("structured_data_missing", final))
        elif not _business_items(hp.structured_data) and not types & BUSINESS_TYPES:
            found.append(Found("organization_schema_missing", final))

    # the same business details everywhere
    seen: dict[str, dict[str, list[str]]] = {"name": {}, "telephone": {}, "address": {}}
    for p in r.pages:
        if p.page is None:
            continue
        for item in _business_items(p.page.structured_data):
            values = {"name": str(item.get("name", "")).strip().lower() or None,
                      "telephone": re.sub(r"\D", "", str(item.get("telephone", ""))) or None,
                      "address": _address(item.get("address"))}
            for key, value in values.items():
                if value:
                    seen[key].setdefault(value, []).append(p.fetched.final_url)
    differing = {k: {v: urls[:3] for v, urls in vals.items()}
                 for k, vals in seen.items() if len(vals) > 1}
    if differing:
        found.append(Found("business_details_inconsistent", None, differing))
    return found, facts


__all__ = ["AI_SEARCH_CRAWLERS", "AI_TRAINING_CRAWLERS", "BOT_NAME", "CHECKS", "Found",
           "run_checks"]
