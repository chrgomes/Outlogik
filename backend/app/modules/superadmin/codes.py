"""Invitation codes for signing up during the beta (SIGNUP_MODE=code).

Codes look like `K7PM-3QXR-9TWD`: 12 characters from an alphabet without look-alikes (no 0/O,
1/I/L), about 60 bits, so guessing one is impractical (and registration is rate-limited).
Only a hash is stored. People can type them with or without dashes, in any case.
"""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.models import utcnow
from app.core.security import hash_token
from app.modules.superadmin.models import SignupCode

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LENGTH = 12
INVALID = "That invitation code isn't valid. Check it, or ask Outlogik for a new one."


def generate() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
    return "-".join(raw[i:i + 4] for i in range(0, LENGTH, 4))


def normalize(code: str) -> str:
    return "".join(c for c in code.upper() if c.isalnum())


def code_hash(code: str) -> str:
    return hash_token(normalize(code))


def _invalid(message: str = INVALID) -> AppError:
    return AppError(message, code="signup_code_invalid", status_code=400,
                    details=[{"field": "signup_code", "message": message}])


def consume(db: Session, code: str | None, account_type: str) -> SignupCode:
    """Check a code and count one use. Locked while checking, so two people can't both take
    the last use."""
    if not code or not normalize(code):
        raise _invalid("Enter the invitation code you were given.")
    row = db.scalar(select(SignupCode).where(SignupCode.code_hash == code_hash(code))
                    .with_for_update())
    if row is None or row.revoked_at is not None:
        raise _invalid()
    if row.expires_at is not None and row.expires_at <= utcnow():
        raise _invalid("That invitation code has expired. Ask Outlogik for a new one.")
    if row.max_uses is not None and row.uses >= row.max_uses:
        raise _invalid("That invitation code has already been used. Ask Outlogik for a new one.")
    if row.account_type and row.account_type != account_type:
        kind = "businesses" if row.account_type == "business" else "agencies"
        raise _invalid(f"That invitation code is for {kind}.")
    row.uses += 1
    return row
