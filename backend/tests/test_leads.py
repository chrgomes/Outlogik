import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.core import email
from app.core.config import get_settings
from app.main import app
from app.models import Lead, NewsletterSubscriber
from app.modules.leads.service import NEWSLETTER_CONSENT_TEXT

CONSULT = "/api/v1/public/leads/consultation"
CONTACT = "/api/v1/public/leads/contact"
NEWS = "/api/v1/public/newsletter"


@pytest.fixture
def site():
    """A browser on the public website: sends the site's Origin, no CSRF token, no session."""
    with TestClient(app, base_url="https://testserver",
                    headers={"Origin": get_settings().site_url}) as c:
        yield c


@pytest.fixture
def notify(monkeypatch):
    monkeypatch.setattr(get_settings(), "lead_notification_emails",
                        "sales@outlogik.example.com, ops@outlogik.example.com")


def consultation(**over):
    return {
        "name": "Casey Client", "email": "Casey@Bakery.example.com", "company": "Harbour Bakery",
        "website": "harbourbakery.example.com", "services": ["seo", "content-marketing"],
        "budget": "1k-2.5k", "message": "We want more local customers.",
        "preferred_contact": "Weekday mornings", "elapsed_ms": 20000, "nickname": "",
        "attribution": {"page": "/services/seo", "landing_page": "/?utm_source=newsletter",
                        "referrer": "https://search.example.com/", "utm_source": "newsletter",
                        "utm_medium": "email"},
        **over,
    }


def contact(**over):
    return {"name": "Pat", "email": "pat@example.com", "topic": "partnerships",
            "message": "Hello there", "elapsed_ms": 9000, **over}


# --- consultation and contact ------------------------------------------------------------------

def test_consultation_is_stored_with_attribution(site, db, notify):
    res = site.post(CONSULT, json=consultation())
    assert res.status_code == 201
    assert res.json() == {"received": True}
    lead = db.scalar(select(Lead))
    assert (lead.kind, lead.status) == ("consultation", "new")
    assert lead.email == "casey@bakery.example.com"
    assert lead.details == {"services": ["seo", "content-marketing"], "budget": "1k-2.5k",
                            "preferred_contact": "Weekday mornings"}
    assert lead.attribution["utm_source"] == "newsletter"
    assert lead.attribution["page"] == "/services/seo"
    assert lead.ip and lead.user_agent


def test_consultation_notifies_the_team_and_acknowledges_the_sender(site, notify):
    site.post(CONSULT, json=consultation())
    to = sorted(m.to for m in email.outbox)
    assert to == ["casey@bakery.example.com", "ops@outlogik.example.com",
                  "sales@outlogik.example.com"]
    team = next(m for m in email.outbox if m.to == "sales@outlogik.example.com")
    assert team.subject == "New consultation request from Casey Client"
    for text in ["SEO, Content Marketing", "$1,000 to $2,500 a month", "Weekday mornings",
                 "Sent from: /services/seo", "utm_source=newsletter", "We want more local"]:
        assert text in team.body
    ack = next(m for m in email.outbox if m.to == "casey@bakery.example.com")
    assert "consultation" in ack.subject


def test_no_team_email_until_addresses_are_configured(site, db):
    assert get_settings().lead_notification_recipients == []
    site.post(CONSULT, json=consultation())
    assert [m.to for m in email.outbox] == ["casey@bakery.example.com"]
    assert db.scalar(select(Lead)).status == "new"


def test_budget_and_extra_fields_are_optional(site, db):
    body = consultation()
    for key in ["company", "website", "budget", "message", "preferred_contact", "attribution"]:
        body.pop(key)
    assert site.post(CONSULT, json=body).status_code == 201
    lead = db.scalar(select(Lead))
    assert lead.details["budget"] is None and lead.attribution == {}


@pytest.mark.parametrize("bad", [
    {"services": []}, {"services": ["paid-ads"]}, {"budget": "a-lot"}, {"name": " "},
    {"email": "not-an-email"}, {"message": "x" * 5001}, {"is_admin": True},
])
def test_consultation_is_validated(site, db, bad):
    assert site.post(CONSULT, json=consultation(**bad)).status_code == 422
    assert db.scalar(select(Lead)) is None


def test_contact_message(site, db, notify):
    assert site.post(CONTACT, json=contact()).status_code == 201
    lead = db.scalar(select(Lead))
    assert (lead.kind, lead.details, lead.message) == ("contact", {"topic": "partnerships"},
                                                        "Hello there")
    team = next(m for m in email.outbox if m.to == "sales@outlogik.example.com")
    assert "Topic: Partnerships" in team.body
    assert site.post(CONTACT, json=contact(message="")).status_code == 422


# --- protection --------------------------------------------------------------------------------

@pytest.mark.parametrize("trap, reason", [({"nickname": "bot"}, "honeypot"),
                                          ({"elapsed_ms": 800}, "too_fast")])
def test_spam_is_kept_for_review_but_never_emailed(site, db, notify, trap, reason):
    res = site.post(CONSULT, json=consultation(**trap))
    assert res.status_code == 201  # looks like success, so bots learn nothing
    lead = db.scalar(select(Lead))
    assert (lead.status, lead.spam_reason) == ("spam", reason)
    assert email.outbox == []


@pytest.mark.parametrize("origin", [None, "https://evil.example.com", "http://localhost:4200"])
def test_forms_only_accept_the_website_origin(origin, db):
    headers = {"Origin": origin} if origin else {}
    with TestClient(app, base_url="https://testserver", headers=headers) as c:
        res = c.post(CONSULT, json=consultation())
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bad_origin"
    assert db.scalar(select(Lead)) is None


def test_extra_origins_can_be_allowed(monkeypatch, db):
    monkeypatch.setattr(get_settings(), "public_form_extra_origins", "https://staging.example.com/")
    with TestClient(app, base_url="https://testserver",
                    headers={"Origin": "https://staging.example.com"}) as c:
        assert c.post(CONTACT, json=contact()).status_code == 201


def test_forms_need_no_csrf_token_but_the_app_still_does(site, client):
    assert site.post(CONTACT, json=contact()).status_code == 201
    # Everything outside /api/v1/public still requires the CSRF token.
    bare = TestClient(app, base_url="https://testserver")
    assert bare.post("/api/v1/auth/login", json={"email": "a@b.co", "password": "x"}
                     ).status_code == 403


def test_rate_limited_per_email_and_per_ip(site):
    # 3 per email address per hour...
    for _ in range(3):
        assert site.post(CONTACT, json=contact()).status_code == 201
    res = site.post(CONTACT, json=contact())
    assert res.status_code == 429 and "Retry-After" in res.headers
    # ...and 5 per IP address per 10 minutes (the refused attempt above counts too).
    assert site.post(CONTACT, json=contact(email="other@example.com")).status_code == 201
    assert site.post(CONTACT, json=contact(email="new@example.com")).status_code == 429


# --- newsletter (CASL double opt-in) ------------------------------------------------------------

def news(**over):
    return {"email": "Reader@Example.com", "consent": True, "elapsed_ms": 5000,
            "attribution": {"page": "/about"}, **over}


def link_token(kind: str) -> str:
    match = re.search(rf"/newsletter/{kind}\?token=([\w-]+)", email.outbox[-1].body)
    assert match, email.outbox[-1].body
    return match.group(1)


def test_newsletter_double_opt_in_and_unsubscribe(site, db):
    assert site.post(NEWS, json=news()).status_code == 202
    sub = db.scalar(select(NewsletterSubscriber))
    assert (sub.email, sub.status) == ("reader@example.com", "pending")
    assert sub.consent_text == NEWSLETTER_CONSENT_TEXT and sub.consent_at
    msg = email.outbox[-1]
    assert msg.to == "reader@example.com"
    assert f"{get_settings().site_url}/newsletter/confirm?token=" in msg.body
    assert NEWSLETTER_CONSENT_TEXT in msg.body

    confirm, unsubscribe = link_token("confirm"), link_token("unsubscribe")
    assert sub.confirm_token_hash != confirm  # only hashes are stored
    assert site.post(f"{NEWS}/confirm", json={"token": confirm}).status_code == 200
    db.refresh(sub)
    assert sub.status == "confirmed" and sub.confirmed_at
    # Links work once.
    assert site.post(f"{NEWS}/confirm", json={"token": confirm}).status_code == 400

    assert site.post(f"{NEWS}/unsubscribe", json={"token": unsubscribe}).status_code == 200
    db.refresh(sub)
    assert sub.status == "unsubscribed" and sub.unsubscribed_at
    # Unsubscribing twice is fine.
    assert site.post(f"{NEWS}/unsubscribe", json={"token": unsubscribe}).status_code == 200


def test_newsletter_needs_consent(site, db):
    assert site.post(NEWS, json=news(consent=False)).status_code == 422
    body = news()
    body.pop("consent")
    assert site.post(NEWS, json=body).status_code == 422
    assert db.scalar(select(NewsletterSubscriber)) is None


def test_newsletter_does_not_reveal_who_is_subscribed(site, db):
    site.post(NEWS, json=news())
    site.post(f"{NEWS}/confirm", json={"token": link_token("confirm")})
    sent = len(email.outbox)
    res = site.post(NEWS, json=news())
    assert res.status_code == 202 and res.json() == {"received": True}
    assert len(email.outbox) == sent  # no second email to someone already confirmed


def test_expired_and_unknown_links_fail(site, db):
    site.post(NEWS, json=news())
    token = link_token("confirm")
    db.execute(update(NewsletterSubscriber).values(
        confirm_token_expires_at=NewsletterSubscriber.consent_at - timedelta(minutes=1)))
    db.commit()
    res = site.post(f"{NEWS}/confirm", json={"token": token})
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_link"
    assert site.post(f"{NEWS}/unsubscribe", json={"token": "x" * 40}).status_code == 400


def test_newsletter_spam_is_ignored(site, db):
    assert site.post(NEWS, json=news(nickname="bot")).status_code == 202
    assert db.scalar(select(NewsletterSubscriber)) is None and email.outbox == []


def test_unsubscribed_reader_can_opt_in_again(site, db):
    site.post(NEWS, json=news())
    site.post(f"{NEWS}/unsubscribe", json={"token": link_token("unsubscribe")})
    site.post(NEWS, json=news())
    sub = db.scalar(select(NewsletterSubscriber))
    assert sub.status == "pending" and sub.unsubscribed_at is None
    assert site.post(f"{NEWS}/confirm", json={"token": link_token("confirm")}).status_code == 200


# --- the website and the API agree ------------------------------------------------------------

def test_website_form_choices_match_the_api():
    """The website's options (config/forms.ts) must be values the API accepts, and the consent
    wording shown must be exactly what is stored."""
    from pathlib import Path
    from typing import get_args

    from app.modules.leads import schemas

    forms = (Path(__file__).parents[2] / "frontend/projects/marketing/src/app/config/forms.ts"
             ).read_text()

    def values(const: str) -> list[str]:
        block = forms.split(f"export const {const}")[1].split("];")[0]
        return re.findall(r"value: '([^']+)'", block)

    assert values("SERVICE_OPTIONS") == list(get_args(schemas.SERVICE_CHOICES))
    assert values("BUDGET_OPTIONS") == list(get_args(schemas.BUDGET_CHOICES))
    assert values("CONTACT_TOPICS") == list(get_args(schemas.CONTACT_TOPICS))
    consent = forms.split("NEWSLETTER_CONSENT_TEXT =")[1].split(";")[0]
    parts = re.findall(r""""([^"]*)"|'([^']*)'""", consent)  # concatenated string literals
    text = "".join(double or single for double, single in parts)
    assert text == NEWSLETTER_CONSENT_TEXT


# --- duplicates and content checks (2026-11-17) --------------------------------------------------

def test_same_person_sending_the_same_form_again_adds_a_note_not_a_lead(site, db, notify):
    from app.models import LeadNote

    assert site.post(CONSULT, json=consultation()).status_code == 201
    sent = len(email.outbox)
    again = consultation(message="Also interested in a new website.",
                         services=["seo", "social-media-management"])
    assert site.post(CONSULT, json=again).status_code == 201  # looks the same to the sender
    assert db.scalar(select(func.count()).select_from(Lead)) == 1
    note = db.scalar(select(LeadNote))
    assert note.source == "website"
    assert "Sent the consultation request form again." in note.body
    assert "Also interested in a new website." in note.body
    assert "Services this time: SEO, Social Media Management" in note.body
    assert len(email.outbox) == sent  # nobody is emailed again


def test_other_forms_people_and_older_leads_are_not_duplicates(site, db):
    site.post(CONSULT, json=consultation())
    site.post(CONTACT, json=contact(email="casey@bakery.example.com"))  # a different form
    site.post(CONSULT, json=consultation(email="someone@else.example.com"))  # another person
    db.execute(update(Lead).values(created_at=Lead.created_at - timedelta(hours=25)))
    db.commit()
    site.post(CONSULT, json=consultation())  # more than 24 hours later
    assert db.scalar(select(func.count()).select_from(Lead)) == 4


@pytest.mark.parametrize("over, reason", [
    ({"message": "Great deals http://a.example http://b.example https://c.example"},
     "too_many_links"),
    ({"message": "Visit <a href='http://x.example'>here</a>"}, "markup"),
    ({"message": "[url=http://x.example]cheap[/url]"}, "markup"),
    ({"name": "Buy now www.spam.example"}, "link_in_name"),
    ({"email": "someone@mailinator.com"}, "disposable_email"),
    ({"email": "someone@inbox.yopmail.com"}, "disposable_email"),
])
def test_spammy_content_is_kept_as_spam_and_never_emailed(site, db, notify, over, reason):
    assert site.post(CONSULT, json=consultation(**over)).status_code == 201
    lead = db.scalar(select(Lead))
    assert (lead.status, lead.spam_reason) == ("spam", reason)
    assert email.outbox == []


def test_normal_links_are_fine(site, db):
    body = consultation(website="https://harbourbakery.example.com",
                        message="Our site is https://harbourbakery.example.com and the shop is "
                                "www.shop.example.com.")
    site.post(CONSULT, json=body)
    assert db.scalar(select(Lead)).status == "new"


def test_spam_reasons_are_explained_in_the_admin_area(site, db, client):
    from tests.conftest import register
    from tests.test_site import make_staff

    site.post(CONSULT, json=consultation(email="x@mailinator.com"))
    register(client, "admin@outlogik.example.com", org="Outlogik HQ")
    make_staff(db, "admin@outlogik.example.com", "site_admin")
    lead = db.scalar(select(Lead))
    body = client.get(f"/api/v1/admin/leads/{lead.id}").json()
    assert body["spam_reason_text"] == "The email address is from a throwaway email service."


def test_email_domains_that_cannot_receive_email(site, db, monkeypatch):
    from app.modules.leads import spam

    monkeypatch.setattr(get_settings(), "email_domain_check", True)
    answers = {"gmail.com": True, "nomail.example": False, "flaky.example": None}
    monkeypatch.setattr(spam, "domain_accepts_mail", lambda d: answers.get(d, True))
    monkeypatch.setattr(spam, "dns_is_working", lambda: True)
    site.post(CONTACT, json=contact(email="a@nomail.example"))
    site.post(CONTACT, json=contact(email="b@flaky.example"))  # couldn't tell: not flagged
    leads = {x.email: (x.status, x.spam_reason) for x in db.scalars(select(Lead))}
    assert leads == {"a@nomail.example": ("spam", "email_domain"), "b@flaky.example": ("new", None)}


def test_nothing_is_flagged_when_dns_itself_is_broken(site, db, monkeypatch):
    from app.modules.leads import spam

    monkeypatch.setattr(get_settings(), "email_domain_check", True)
    monkeypatch.setattr(spam, "domain_accepts_mail", lambda d: False)  # everything "fails"...
    monkeypatch.setattr(spam, "dns_is_working", lambda: False)  # ...because DNS is broken
    site.post(CONTACT, json=contact(email="a@gmail.com"))
    assert db.scalar(select(Lead)).status == "new"


def test_dns_check_reads_mail_records(monkeypatch):
    import dns.resolver

    from app.modules.leads import spam

    class Record:
        def __init__(self, exchange):
            self.exchange = exchange

    zones = {("ok.example", "MX"): [Record("mx.ok.example.")],
             ("nullmx.example", "MX"): [Record(".")],
             ("aonly.example", "A"): ["192.0.2.1"]}

    def resolve(self, domain, rtype):
        if domain == "missing.example":
            raise dns.resolver.NXDOMAIN
        if (domain, rtype) in zones:
            return zones[(domain, rtype)]
        raise dns.resolver.NoAnswer

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)
    spam.domain_accepts_mail.cache_clear()
    assert spam.domain_accepts_mail("ok.example") is True
    assert spam.domain_accepts_mail("nullmx.example") is False  # RFC 7505: takes no email
    assert spam.domain_accepts_mail("aonly.example") is True  # falls back to its address
    assert spam.domain_accepts_mail("missing.example") is False
    spam.domain_accepts_mail.cache_clear()


def test_newsletter_ignores_throwaway_addresses(site, db):
    assert site.post(NEWS, json=news(email="reader@mailinator.com")).status_code == 202
    assert db.scalar(select(NewsletterSubscriber)) is None and email.outbox == []


# --- invisible proof of work ---------------------------------------------------------------------

def solve(ch: dict) -> dict:
    import hashlib

    number = next(n for n in range(ch["max_number"] + 1)
                  if hashlib.sha256(f"{ch['salt']}{n}".encode()).hexdigest() == ch["challenge"])
    return {"algorithm": ch["algorithm"], "challenge": ch["challenge"], "salt": ch["salt"],
            "number": number, "signature": ch["signature"]}


@pytest.fixture
def pow_on(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "form_challenge_required", True)
    monkeypatch.setattr(s, "form_challenge_max_number", 2000)  # quick to solve in tests


def test_challenge_needs_no_origin_and_is_never_cached(pow_on):
    with TestClient(app, base_url="https://testserver") as c:
        res = c.get("/api/v1/public/challenge")
    assert res.status_code == 200 and res.headers["cache-control"] == "no-store"
    ch = res.json()
    assert ch["algorithm"] == "SHA-256" and ch["max_number"] == 2000
    assert "?expires=" in ch["salt"] and len(ch["signature"]) == 64


def test_forms_with_a_solved_challenge_are_accepted(site, db, pow_on, notify):
    proof = solve(site.get("/api/v1/public/challenge").json())
    assert site.post(CONTACT, json=contact(pow=proof)).status_code == 201
    assert db.scalar(select(Lead)).status == "new"


@pytest.mark.parametrize("tamper", ["missing", "wrong_number", "forged_signature", "expired",
                                    "reused"])
def test_missing_wrong_or_reused_proof_is_spam(site, db, pow_on, notify, monkeypatch, tamper):
    import hashlib
    import time
    from types import SimpleNamespace

    from app.modules.leads import challenge

    proof = solve(site.get("/api/v1/public/challenge").json())
    body = contact(pow=proof)
    if tamper == "missing":
        body.pop("pow")
    elif tamper == "wrong_number":
        body["pow"] = {**proof, "number": proof["number"] + 1}
    elif tamper == "forged_signature":  # a made-up challenge the server never signed
        salt = "abc?expires=9999999999"
        body["pow"] = {**proof, "salt": salt, "number": 1,
                       "challenge": hashlib.sha256(f"{salt}1".encode()).hexdigest()}
    elif tamper == "expired":  # sent 11 minutes later
        later = time.time() + 11 * 60
        monkeypatch.setattr(challenge, "time", SimpleNamespace(time=lambda: later))
    elif tamper == "reused":
        site.post(CONTACT, json=contact(email="first@example.com", pow=proof))
    assert site.post(CONTACT, json=body).status_code == 201  # looks the same to a bot
    lead = db.scalar(select(Lead).where(Lead.email == "pat@example.com"))
    assert lead.status == "spam"
    assert lead.spam_reason == ("no_proof" if tamper == "missing" else "bad_proof")
    assert all(m.to != "sales@outlogik.example.com" for m in email.outbox
               if "pat@example.com" in m.body)


def test_newsletter_needs_the_proof_too(site, db, pow_on):
    assert site.post(NEWS, json=news()).status_code == 202
    assert db.scalar(select(NewsletterSubscriber)) is None
    proof = solve(site.get("/api/v1/public/challenge").json())
    assert site.post(NEWS, json=news(pow=proof)).status_code == 202
    assert db.scalar(select(NewsletterSubscriber)).status == "pending"


def test_production_refuses_to_run_without_a_secret(monkeypatch):
    from app.modules.leads import challenge

    s = get_settings()
    monkeypatch.setattr(s, "app_env", "production")
    monkeypatch.setattr(s, "site_proxy_secret", None)
    monkeypatch.setattr(s, "form_challenge_secret", None)
    with pytest.raises(RuntimeError):
        challenge.create()
