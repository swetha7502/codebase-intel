"""
Shared Redis client factory. Handles the rediss:// SSL quirk required
by Upstash (and other managed Redis providers) where redis-py needs an
explicit ssl_cert_reqs value for TLS connections.
"""
import ssl
import redis
import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()


def get_redis_client() -> redis.Redis:
    if settings.redis_url.startswith("rediss://"):
        return redis.from_url(settings.redis_url, ssl_cert_reqs=ssl.CERT_NONE)
    return redis.from_url(settings.redis_url)


def get_async_redis_client() -> aioredis.Redis:
    if settings.redis_url.startswith("rediss://"):
        return aioredis.from_url(settings.redis_url, ssl_cert_reqs=ssl.CERT_NONE)
    return aioredis.from_url(settings.redis_url)