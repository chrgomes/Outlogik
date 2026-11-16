import csv
import io

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, Lead, LeadNote, NewsletterSubscriber
from app.modules.leads.service import NEWSLETTER_CONSENT_TEXT
from tests.conftest import register
from tests.test_site import make_staff

LEADS = "/api/v1/admin/leads"
SUBS = "/api/v1/admin/newsletter/subscribers"


@pytest.fixture
def admin(client, db):
    register(client, "admin@outlogik.example.com", name="Ada Admin", org="Outlogik HQ")
    make_staff(db, "admin@outlogik.example.com", "site_admin")
    return client


def add_lead(db, **over) -> Lead:
    values = {
        "kind": "consultation", "status": "new", "name": "Casey Client",
        "email": "casey@bakery.example.com", "company": "Harbour Bakery",
        "details": {"services": ["seo"], "budget": "1k-2.5k", "preferred_contact": None},
        "attribution": {"page": "/services/seo", "utm_source": "linkedin"},
        **over,
    }
    lead = Lead(**values)
    db.add(lead)
    db.commit()
    return lead


def add_subscriber(db, email: str, status: str = "confirmed") -> NewsletterSubscriber:
    sub = NewsletterSubscriber(email=email, status=status, consent_text=NEWSLETTER_CONSENT_TEXT,
                               consent_at=func.now(), unsubscribe_token_hash=email.ljust(64, "x"),
                               attribution={"page": "/about"})
    db.add(sub)
    db.commit()
    return sub


# --- access ------------------------------------------------------------------------------------

@pytest.mark.parametrize("role", [None, "content_editor"])
def test_only_site_admins_see_leads(client, db, role):
    register(client, "person@example.com")
    make_staff(db, "person@example.com", role)
    lead = add_lead(db)
    for path in [LEADS, f"{LEADS}/counts", f"{LEADS}/export.csv", f"{LEADS}/{lead.id}", SUBS]:
        assert client.get(path).status_code == 404, path
    assert client.patch(f"{LEADS}/{lead.id}", json={"status": "closed"}).status_code == 404


def test_signed_out_gets_401(new_client):
    assert new_client().get(LEADS).status_code == 401


# --- inbox -------------------------------------------------------------------------------------

def test_inbox_lists_newest_first_without_spam(admin, db):
    add_lead(db, name="Older")
    add_lead(db, name="Spammy", status="spam", spam_reason="honeypot")
    add_lead(db, name="Newer", kind="contact", details={"topic": "press"}, attribution={})
    body = admin.get(LEADS).json()
    assert [i["name"] for i in body["items"]] == ["Newer", "Older"]
    assert body["total"] == 2
    older = body["items"][1]
    assert older["services"] == ["seo"] and older["utm_source"] == "linkedin"
    assert [i["name"] for i in admin.get(LEADS, params={"status": "spam"}).json()["items"]] == [
        "Spammy"]
    assert admin.get(f"{LEADS}/counts").json() == {
        "new": 2, "contacted": 0, "qualified": 0, "closed": 0, "spam": 1}


def test_inbox_filters_and_search(admin, db):
    add_lead(db, name="Casey", company="Harbour Bakery")
    add_lead(db, name="Pat", email="pat@press.example.com", kind="contact", company=None)
    assert [i["name"] for i in admin.get(LEADS, params={"kind": "contact"}).json()["items"]] == [
        "Pat"]
    assert [i["name"] for i in admin.get(LEADS, params={"q": "harbour"}).json()["items"]] == [
        "Casey"]
    assert [i["name"] for i in admin.get(LEADS, params={"q": "PRESS"}).json()["items"]] == ["Pat"]
    assert admin.get(LEADS, params={"q": "100%_"}).json()["total"] == 0
    assert admin.get(LEADS, params={"status": "bogus"}).status_code == 422


def test_lead_detail_status_and_notes(admin, db):
    lead = add_lead(db, message="We want more customers.")
    detail = admin.get(f"{LEADS}/{lead.id}").json()
    assert detail["message"] == "We want more customers." and detail["notes"] == []
    assert detail["details"]["budget"] == "1k-2.5k"

    res = admin.patch(f"{LEADS}/{lead.id}", json={"status": "contacted"})
    assert res.status_code == 200 and res.json()["status"] == "contacted"
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "lead.status_change"))
    assert audit.meta == {"from": "new", "to": "contacted"}

    res = admin.post(f"{LEADS}/{lead.id}/notes", json={"body": "  Called, booked for Tuesday. "})
    assert res.status_code == 201
    notes = res.json()["notes"]
    assert [(n["body"], n["author_name"]) for n in notes] == [
        ("Called, booked for Tuesday.", "Ada Admin")]
    assert admin.get(LEADS).json()["items"][0]["note_count"] == 1
    assert admin.post(f"{LEADS}/{lead.id}/notes", json={"body": " "}).status_code == 422
    assert admin.patch(f"{LEADS}/{lead.id}", json={"status": "won"}).status_code == 422


def test_unknown_lead_is_404(admin):
    missing = "00000000-0000-0000-0000-000000000000"
    assert admin.get(f"{LEADS}/{missing}").status_code == 404
    assert admin.delete(f"{LEADS}/{missing}").status_code == 404


def test_delete_lead_removes_notes_and_keeps_no_personal_data_in_audit(admin, db):
    lead = add_lead(db)
    admin.post(f"{LEADS}/{lead.id}/notes", json={"body": "note"})
    assert admin.delete(f"{LEADS}/{lead.id}").status_code == 204
    assert db.scalar(select(func.count()).select_from(Lead)) == 0
    assert db.scalar(select(func.count()).select_from(LeadNote)) == 0
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "lead.delete"))
    assert "casey" not in str(audit.meta).lower()


# --- export ------------------------------------------------------------------------------------

def read_csv(res) -> list[dict]:
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    return list(csv.DictReader(io.StringIO(res.content.decode("utf-8-sig"))))


def test_export_leads_csv(admin, db):
    add_lead(db, message="=HYPERLINK(\"http://evil\")", phone="+1 555 0100")
    add_lead(db, name="Spam", status="spam")
    rows = read_csv(admin.get(f"{LEADS}/export.csv"))
    assert len(rows) == 1
    row = rows[0]
    assert row["services"] == "SEO" and row["budget"] == "$1,000 to $2,500 a month"
    assert row["utm_source"] == "linkedin" and row["page"] == "/services/seo"
    # Cells that a spreadsheet would run as formulas are neutralised.
    assert row["message"].startswith("'=") and row["phone"] == "'+1 555 0100"
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "lead.export"))
    assert audit.meta["count"] == 1


# --- newsletter subscribers ---------------------------------------------------------------------

def test_subscribers_list_filter_export_and_delete(admin, db):
    add_subscriber(db, "a@example.com")
    add_subscriber(db, "b@example.com", status="pending")
    gone = add_subscriber(db, "c@example.com", status="unsubscribed")
    body = admin.get(SUBS).json()
    assert body["total"] == 3 and body["items"][0]["source_page"] == "/about"
    assert [s["email"] for s in admin.get(SUBS, params={"status": "pending"}).json()["items"]
            ] == ["b@example.com"]
    assert admin.get(SUBS, params={"q": "c@"}).json()["total"] == 1

    rows = read_csv(admin.get(f"{SUBS}/export.csv"))  # confirmed only by default
    assert [r["email"] for r in rows] == ["a@example.com"]
    assert rows[0]["consent_text"] == NEWSLETTER_CONSENT_TEXT
    assert db.scalar(select(AuditLog).where(AuditLog.action == "newsletter.export"))

    assert admin.delete(f"{SUBS}/{gone.id}").status_code == 204
    assert admin.get(SUBS).json()["total"] == 2
