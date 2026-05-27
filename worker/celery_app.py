from celery import Celery

from app.core.config import settings

# app data on db /0, celery backend on db /1
_broker = settings.redis_url
_backend = settings.redis_url.rsplit("/", 1)[0] + "/1"

celery_app = Celery("logo_diffusion", broker=_broker, backend=_backend)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=30,
    task_time_limit=35,
    broker_connection_retry_on_startup=True,
)
