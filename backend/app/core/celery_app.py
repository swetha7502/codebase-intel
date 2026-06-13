import ssl
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "codebase_intel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.ingestion"],
)

ssl_options = {}
if settings.redis_url.startswith("rediss://"):
    ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_use_ssl=ssl_options or None,
    redis_backend_use_ssl=ssl_options or None,
)