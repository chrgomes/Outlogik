import sys

from sqlalchemy import select

from app import cli
from app.models import AuditLog, User
from tests.conftest import login, register


def run_cli(monkeypatch, *args: str, passwords=("a long admin password",) * 2) -> int:
    answers = iter(passwords)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))
    monkeypatch.setattr(sys, "argv", ["app.cli", *args])
    return cli.main()


def test_create_super_admin(monkeypatch, db, new_client):
    code = run_cli(monkeypatch, "create-super-admin", "--email", "Admin@Example.com",
                   "--name", "Ada Admin")
    assert code == 0
    user = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert user.is_super_admin
    assert db.scalar(select(AuditLog.action).where(AuditLog.target_id == str(user.id))) == \
        "admin.super_admin_granted"
    assert login(new_client(), "admin@example.com", "a long admin password").status_code == 200


def test_promotes_existing_user_without_changing_password(monkeypatch, client, db):
    register(client, "olive@example.com")
    # No password prompt for an existing account.
    assert run_cli(monkeypatch, "create-super-admin", "--email", "olive@example.com",
                   "--name", "Olive", passwords=()) == 0
    db.expire_all()
    assert db.scalar(select(User.is_super_admin).where(User.email == "olive@example.com"))
    assert login(client, "olive@example.com").status_code == 200  # original password


def test_rejects_short_or_mismatched_password(monkeypatch, db):
    assert run_cli(monkeypatch, "create-super-admin", "--email", "a@example.com", "--name", "A",
                   passwords=("short", "short")) == 1
    assert run_cli(monkeypatch, "create-super-admin", "--email", "a@example.com", "--name", "A",
                   passwords=("a long admin password", "a different password")) == 1
    assert db.scalar(select(User).where(User.email == "a@example.com")) is None
