"""Fixed-window rate limiting backed by Redis.

If Redis is unreachable the limiter fails open (and logs), so an outage of the cache
does not lock every user out of login.
"""

import hashlib
import logging

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import TooManyRequests
from app.core.redis import get_redis

log = logging.getLogger(__name__)


def hit(bucket: str, identifier: str, limit: tuple[int, int]) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    max_hits, window = limit
    digest = hashlib.sha256(identifier.lower().encode()).hexdigest()[:32]
    key = f"rl:{bucket}:{digest}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        pipe.ttl(key)
        count, _, ttl = pipe.execute()
    except RedisError:
        log.warning("Rate limiter unavailable; allowing request", exc_info=True)
        return
    if count > max_hits:
        raise TooManyRequests(details={"retry_after": max(int(ttl), 1)})
