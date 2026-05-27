from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.storage.redis_store import get_redis
from worker.celery_app import celery_app

router = APIRouter()


@router.get("/health")
async def health(redis: Redis = Depends(get_redis)):
    # check redis
    try:
        await redis.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "unavailable"

    # check celery — any worker responds within 1s
    try:
        responses = celery_app.control.ping(timeout=1.0)
        celery_status = "ok" if responses else "unavailable"
    except Exception:
        celery_status = "unavailable"

    # metrics
    total = int(await redis.get("metrics:total") or 0)
    completed = int(await redis.get("metrics:completed") or 0)
    failed = int(await redis.get("metrics:failed") or 0)
    queue_depth = await redis.llen("celery")

    overall = "ok" if redis_status == "ok" and celery_status == "ok" else "degraded"

    return {
        "status": overall,
        "redis": redis_status,
        "celery": celery_status,
        "metrics": {
            "total_generations": total,
            "completed": completed,
            "failed": failed,
            "queue_depth": queue_depth,
        },
    }
