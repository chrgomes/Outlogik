"""Encrypting stored credentials (Google refresh tokens) with Fernet (AES, authenticated).

The key comes from INTEGRATIONS_ENCRYPTION_KEY. Development and tests derive one from a fixed
phrase; production refuses to start without a real key once Google is configured (config.py).
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

DEV_KEY = base64.urlsafe_b64encode(hashlib.sha256(b"outlogik-development-only").digest())


@lru_cache
def _fernet(key: str | None) -> Fernet:
    return Fernet(key.encode() if key else DEV_KEY)


def encrypt(value: str) -> str:
    return _fernet(get_settings().integrations_encryption_key).encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet(get_settings().integrations_encryption_key).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credentials can't be read with the current key.") from exc
