"""Google PageSpeed Insights for an audit's home page (mobile). Needs PAGESPEED_API_KEY; without
it, audits record that page speed isn't connected. The request goes to Google, not the site."""

from typing import Any

import httpx

from app.core.config import get_settings

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def run(url: str, *, transport: httpx.BaseTransport | None = None) -> dict[str, Any]:
    key = get_settings().pagespeed_api_key
    if not key:
        return {"connected": False}
    try:
        with httpx.Client(timeout=90.0, transport=transport) as c:
            r = c.get(API, params={"url": url, "strategy": "mobile", "category": "performance",
                                   "key": key})
        if r.status_code != 200:
            return {"connected": True, "error": f"PageSpeed answered {r.status_code}."}
        lh = r.json()["lighthouseResult"]
        audits = lh["audits"]

        def metric(name: str) -> float | None:
            value = audits.get(name, {}).get("numericValue")
            return round(value, 3) if isinstance(value, int | float) else None

        score = lh["categories"]["performance"]["score"]
        return {"connected": True, "strategy": "mobile",
                "score": round(score * 100) if score is not None else None,
                "lcp_ms": metric("largest-contentful-paint"),
                "cls": metric("cumulative-layout-shift"),
                "tbt_ms": metric("total-blocking-time")}
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        return {"connected": True, "error": f"PageSpeed couldn't run: {type(exc).__name__}."}
