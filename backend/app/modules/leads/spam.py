"""Spam checks for the website's forms (step: form protection, 2026-11-17).

Every check only *flags*: flagged submissions are stored with status "spam" and a reason, so
staff can review them, and they never trigger emails. Bots see the same success message.
"""

import logging
import re
import time
from functools import lru_cache

import dns.exception
import dns.resolver

from app.core.config import get_settings

log = logging.getLogger(__name__)

MAX_LINKS = 2
LINK = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
# Markup a person typing a message wouldn't write: HTML tags, forum link code.
MARKUP = re.compile(r"<\s*(?:a|script|iframe|img|div|span|p)\b|\[/?(?:url|link|img)\b|&lt;a\b",
                    re.IGNORECASE)

# Common throwaway email services. Not exhaustive: the mail check below catches many others.
DISPOSABLE_DOMAINS = frozenset({
    "10minutemail.com", "10minutemail.net", "20minutemail.com", "33mail.com", "anonaddy.me",
    "burnermail.io", "discard.email", "dispostable.com", "emailondeck.com", "fakeinbox.com",
    "getairmail.com", "getnada.com", "guerrillamail.biz", "guerrillamail.com",
    "guerrillamail.de", "guerrillamail.info", "guerrillamail.net", "guerrillamail.org",
    "guerrillamailblock.com", "inboxkitten.com", "jetable.org", "mail.tm", "maildrop.cc",
    "mailinator.com", "mailinator.net", "mailnesia.com", "mailpoof.com", "mintemail.com",
    "moakt.com", "mohmal.com", "mytemp.email", "nada.email", "sharklasers.com",
    "spam4.me", "spamgourmet.com", "temp-mail.io", "temp-mail.org", "tempail.com",
    "tempmail.com", "tempmail.net", "tempmailo.com", "tempr.email", "throwawaymail.com",
    "trashmail.com", "trashmail.de", "trashmail.net", "yopmail.com", "yopmail.fr",
    "yopmail.net",
})

REASONS = {
    "honeypot": "A hidden field that people never see was filled in.",
    "too_fast": "The form was sent within a few seconds of opening.",
    "too_many_links": f"The message contains more than {MAX_LINKS} links.",
    "markup": "The message contains HTML or link code.",
    "link_in_name": "The name contains a link.",
    "disposable_email": "The email address is from a throwaway email service.",
    "email_domain": "The email address's domain can't receive email.",
}


def content_reason(name: str, texts: list[str | None]) -> str | None:
    """Checks the words people wrote."""
    if LINK.search(name):
        return "link_in_name"
    text = "\n".join(t for t in texts if t)
    if MARKUP.search(text):
        return "markup"
    if len(LINK.findall(text)) > MAX_LINKS:
        return "too_many_links"
    return None


def email_reason(email: str) -> str | None:
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in DISPOSABLE_DOMAINS or any(domain.endswith("." + d) for d in DISPOSABLE_DOMAINS):
        return "disposable_email"
    if (get_settings().email_domain_check and domain_accepts_mail(domain) is False
            and dns_is_working()):
        return "email_domain"
    return None


def _records(resolver: dns.resolver.Resolver, domain: str, rtype: str) -> list:
    try:
        return list(resolver.resolve(domain, rtype))
    except dns.resolver.NoAnswer:
        return []


@lru_cache(maxsize=2048)
def domain_accepts_mail(domain: str) -> bool | None:
    """True if the domain can receive email, False if it can't (it doesn't exist, or publishes
    a "null MX" saying it takes no email), None if we couldn't tell (a DNS problem): the caller
    then doesn't flag anything."""
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 2.0
    try:
        mx = _records(resolver, domain, "MX")
        if mx:
            # RFC 7505 "null MX" is a single record pointing at "." (no mail accepted).
            return any(str(r.exchange).rstrip(".") for r in mx)
        # No MX record: mail falls back to the domain's own address (RFC 5321).
        return bool(_records(resolver, domain, "A") or _records(resolver, domain, "AAAA"))
    except dns.resolver.NXDOMAIN:
        return False
    except dns.exception.DNSException:
        log.warning("Couldn't check whether %s accepts email; not flagging it", domain)
        return None


# A domain that certainly accepts email. If even it looks unable to, DNS itself is broken (for
# example a resolver answering "no such domain" for everything), so nothing is flagged.
CANARY_DOMAIN = "gmail.com"
_dns_state = {"checked_at": -1e9, "working": False}


def dns_is_working() -> bool:
    """Re-checked every 10 minutes. When DNS recovers, answers cached while it was broken are
    dropped."""
    if time.monotonic() - _dns_state["checked_at"] > 600:
        working = domain_accepts_mail.__wrapped__(CANARY_DOMAIN) is True
        if working and not _dns_state["working"]:
            domain_accepts_mail.cache_clear()
        if not working:
            log.warning("DNS looks broken (%s can't be resolved); not flagging email domains",
                        CANARY_DOMAIN)
        _dns_state.update(checked_at=time.monotonic(), working=working)
    return bool(_dns_state["working"])
