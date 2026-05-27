import random
import time
from pathlib import Path

from billiard.exceptions import SoftTimeLimitExceeded

from worker.celery_app import celery_app
from worker.redis_client import get_redis
from shared.redis_keys import generation as gen_key, metrics

_lua_dir = Path(__file__).parent.parent.parent / "shared" / "lua"
_release_credits = (_lua_dir / "release_credits.lua").read_text()
_release_slot = (_lua_dir / "release_slot.lua").read_text()


def _update_status(r, generation_id: str, status: str, **fields) -> None:
    from datetime import datetime, timezone
    mapping = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    mapping.update(fields)
    r.hset(gen_key(generation_id), mapping=mapping)


def _release_resources(r, client_id: str, cost: int) -> None:
    from shared.redis_keys import client_balance, rate_slot
    r.eval(_release_credits, 1, client_balance(client_id), cost)
    r.eval(_release_slot, 1, rate_slot(client_id))


def _get_webhook_url(r, client_id: str) -> str | None:
    url = r.hget(f"client:{client_id}", "webhook_url")
    return url if url else None


@celery_app.task(bind=True, max_retries=0)
def run_generation(self, generation_id: str, client_id: str, cost: int) -> None:
    r = get_redis()
    try:
        _update_status(r, generation_id, "processing")
        time.sleep(random.uniform(5, 15))

        webhook_url = _get_webhook_url(r, client_id)

        if random.random() < 0.8:
            result_url = f"https://cdn.logodiffusion.com/fake/{generation_id}.png"
            _update_status(r, generation_id, "completed", result_url=result_url)
            from shared.redis_keys import rate_slot
            r.eval(_release_slot, 1, rate_slot(client_id))
            r.incr(metrics("total"))
            r.incr(metrics("completed"))
            if webhook_url:
                from app.services.webhook_service import dispatch_webhook
                dispatch_webhook(webhook_url, generation_id, "completed", result_url=result_url)
        else:
            _update_status(
                r, generation_id, "failed",
                error_code="generation_failed",
                error_message="AI provider returned an error",
            )
            _release_resources(r, client_id, cost)
            r.incr(metrics("total"))
            r.incr(metrics("failed"))
            if webhook_url:
                from app.services.webhook_service import dispatch_webhook
                dispatch_webhook(webhook_url, generation_id, "failed")

    except SoftTimeLimitExceeded:
        _update_status(
            r, generation_id, "failed",
            error_code="generation_timeout",
            error_message="Generation timed out",
        )
        _release_resources(r, client_id, cost)
        r.incr(metrics("failed"))
        r.incr(metrics("total"))
        raise
    except Exception:
        # TODO: add logging for unexpected worker errors
        _update_status(
            r, generation_id, "failed",
            error_code="internal_error",
            error_message="An unexpected error occurred",
        )
        _release_resources(r, client_id, cost)
        r.incr(metrics("failed"))
        r.incr(metrics("total"))
        raise
