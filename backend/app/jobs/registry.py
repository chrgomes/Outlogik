"""Job kinds and the functions that do them. A handler gets the job's payload and a database
session (no organization set: handlers filter by organization themselves). Raising means the
attempt failed and the job is retried, with a growing wait, until max_attempts."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Handler:
    kind: str
    run: Callable[[Session, dict[str, Any]], None]
    max_attempts: int
    # Called after the job finishes or gives up: returns what's left of the payload, so
    # sensitive content (an email body with a sign-in link) isn't kept.
    scrub: Callable[[dict[str, Any]], dict[str, Any]] | None


HANDLERS: dict[str, Handler] = {}


def handler(kind: str, *, max_attempts: int = 5,
            scrub: Callable[[dict[str, Any]], dict[str, Any]] | None = None):
    def register(fn: Callable[[Session, dict[str, Any]], None]):
        if kind in HANDLERS:
            raise ValueError(f"Job kind {kind!r} is registered twice")
        HANDLERS[kind] = Handler(kind, fn, max_attempts, scrub)
        return fn
    return register
