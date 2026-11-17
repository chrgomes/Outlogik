"""Invisible proof-of-work check for the website's forms (built in; no third-party service, no
cookies). Same idea as the open ALTCHA scheme:

1. The browser asks for a challenge: a random salt (with an expiry), the SHA-256 hash of the salt
   plus a secret number between 0 and `max_number`, and an HMAC signature of that hash.
2. It tries numbers until one produces the same hash: about `max_number / 2` hashes on average,
   a fraction of a second for a person's browser, but real work for every one of thousands of
   bot submissions.
3. The form is sent with the number. The API checks the signature, the expiry and the hash,
   and accepts each challenge once (remembered in Redis until it expires).
"""

import hashlib
import hmac
import secrets
import time

from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import get_redis

ALGORITHM = "SHA-256"
# Used only outside production when no SITE_PROXY_SECRET is set (development, tests).
DEV_KEY = "outlogik-development-only-challenge-key"


class Challenge(BaseModel):
    algorithm: str = ALGORITHM
    challenge: str
    salt: str
    max_number: int
    signature: str


class Solution(BaseModel):
    """What the browser sends back with a form."""

    algorithm: str = Field(max_length=20)
    challenge: str = Field(max_length=128)
    salt: str = Field(max_length=128)
    number: int = Field(ge=0)
    signature: str = Field(max_length=128)


def _key() -> bytes:
    s = get_settings()
    secret = s.form_challenge_secret or s.site_proxy_secret
    if not secret:
        if s.app_env == "production":
            raise RuntimeError("Set SITE_PROXY_SECRET (or FORM_CHALLENGE_SECRET) in production.")
        secret = DEV_KEY
    # A key of its own, derived from the shared secret, so the two uses never mix.
    return hmac.new(secret.encode(), b"form-challenge", hashlib.sha256).digest()


def _sign(challenge: str) -> str:
    return hmac.new(_key(), challenge.encode(), hashlib.sha256).hexdigest()


def _hash(salt: str, number: int) -> str:
    return hashlib.sha256(f"{salt}{number}".encode()).hexdigest()


def create() -> Challenge:
    s = get_settings()
    expires = int(time.time()) + s.form_challenge_minutes * 60
    salt = f"{secrets.token_hex(12)}?expires={expires}"
    number = secrets.randbelow(s.form_challenge_max_number + 1)
    challenge = _hash(salt, number)
    return Challenge(challenge=challenge, salt=salt, max_number=s.form_challenge_max_number,
                     signature=_sign(challenge))


def problem(solution: Solution | None) -> str | None:
    """None if the solution is valid (and marks it used); otherwise a spam reason."""
    if solution is None:
        return "no_proof"
    if solution.algorithm != ALGORITHM:
        return "bad_proof"
    if not hmac.compare_digest(_sign(solution.challenge), solution.signature):
        return "bad_proof"
    try:
        expires = int(solution.salt.rsplit("?expires=", 1)[1])
    except (IndexError, ValueError):
        return "bad_proof"
    if expires < time.time():
        return "bad_proof"
    if not hmac.compare_digest(_hash(solution.salt, solution.number), solution.challenge):
        return "bad_proof"
    # Each challenge works once. If Redis is down, the signature and expiry still apply.
    try:
        fresh = get_redis().set(f"pow:{solution.challenge}", 1, nx=True,
                                ex=max(int(expires - time.time()), 1))
        if not fresh:
            return "bad_proof"
    except RedisError:
        pass
    return None
