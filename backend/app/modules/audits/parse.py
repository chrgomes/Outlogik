"""Reading the parts of an HTML page an audit needs, with the standard library's parser."""

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

SKIP_TEXT = {"script", "style", "noscript", "template", "svg"}


@dataclass
class Page:
    title: str | None = None
    meta_description: str | None = None
    meta_robots: str = ""
    canonical: str | None = None
    lang: str | None = None
    has_viewport: bool = False
    h1: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)       # h2–h3
    links: list[str] = field(default_factory=list)          # raw href values
    images: int = 0
    images_without_alt: int = 0
    structured_data: list[dict[str, Any]] = field(default_factory=list)  # JSON-LD objects
    microdata_types: list[str] = field(default_factory=list)
    word_count: int = 0

    @property
    def noindex(self) -> bool:
        return "noindex" in self.meta_robots

    def schema_types(self) -> set[str]:
        types: set[str] = set(self.microdata_types)
        for item in self.structured_data:
            t = item.get("@type")
            for value in t if isinstance(t, list) else [t]:
                if isinstance(value, str):
                    types.add(value)
        return types


def _flatten(data: Any) -> list[dict[str, Any]]:
    """JSON-LD can be one object, a list, or an @graph."""
    if isinstance(data, list):
        return [x for item in data for x in _flatten(item)]
    if isinstance(data, dict):
        return [data] + _flatten(data["@graph"]) if "@graph" in data else [data]
    return []


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page()
        self._stack: list[str] = []
        self._capture: str | None = None  # title, h1, h2, h3, json-ld
        self._buffer: list[str] = []
        self._words = 0
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in SKIP_TEXT:
            self._skip += 1
        if tag == "html" and a.get("lang"):
            self.page.lang = a["lang"]
        elif tag == "title" and self.page.title is None:
            self._start("title")
        elif tag in ("h1", "h2", "h3"):
            self._start(tag)
        elif tag == "meta":
            name = a.get("name", "").lower()
            if name == "description" and self.page.meta_description is None:
                self.page.meta_description = a.get("content", "").strip()
            elif name == "robots":
                self.page.meta_robots = a.get("content", "").lower()
            elif name == "viewport":
                self.page.has_viewport = True
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.page.canonical = a.get("href") or None
        elif tag == "a" and a.get("href"):
            self.page.links.append(a["href"])
        elif tag == "img":
            self.page.images += 1
            if not a.get("alt", "").strip() and a.get("role") != "presentation":
                self.page.images_without_alt += 1
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._start("json-ld")
        if a.get("itemtype"):
            self.page.microdata_types += [t.rstrip("/").rsplit("/", 1)[-1]
                                          for t in a["itemtype"].split()]

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT and self._skip:
            self._skip -= 1
        if self._capture and (tag == self._capture or
                              (self._capture == "json-ld" and tag == "script")):
            text = "".join(self._buffer).strip()
            if self._capture == "title":
                self.page.title = re.sub(r"\s+", " ", text)
            elif self._capture == "h1":
                self.page.h1.append(re.sub(r"\s+", " ", text))
            elif self._capture in ("h2", "h3"):
                self.page.headings.append(re.sub(r"\s+", " ", text))
            elif self._capture == "json-ld":
                try:
                    self.page.structured_data += _flatten(json.loads(text))
                except ValueError:
                    pass  # broken JSON-LD: a check reports structured data as missing
            self._capture, self._buffer = None, []

    def handle_data(self, data):
        if self._capture:
            self._buffer.append(data)
        if not self._skip:
            self._words += len(data.split())

    def _start(self, what: str) -> None:
        self._capture, self._buffer = what, []


def parse_html(html: str) -> Page:
    p = _Parser()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001, S110 - a malformed page still gives what was read
        pass
    p.page.word_count = p._words
    return p.page
