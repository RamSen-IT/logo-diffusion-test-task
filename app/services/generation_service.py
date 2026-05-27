import secrets
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.models.generation import Generation, GenerationStatus
from shared.redis_keys import generation as gen_key

GENERATION_TTL = 86400  # 24h


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"gen_{secrets.token_urlsafe(8)}"


async def create_generation(
    redis: Redis,
    client_id: str,
    prompt: str,
    style: str | None,
    output_size: str,
    cost: int,
) -> Generation:
    gen_id = _new_id()
    now = _now()
    gen = Generation(
        id=gen_id,
        client_id=client_id,
        status=GenerationStatus.QUEUED,
        prompt=prompt,
        style=style or "",
        output_size=output_size,
        cost=cost,
        created_at=now,
        updated_at=now,
    )
    await redis.hset(gen_key(gen_id), mapping={
        "id": gen_id,
        "client_id": client_id,
        "status": gen.status.value,
        "prompt": prompt,
        "style": style or "",
        "output_size": output_size,
        "cost": str(cost),
        "created_at": now,
        "updated_at": now,
    })
    await redis.expire(gen_key(gen_id), GENERATION_TTL)
    return gen


async def get_generation(redis: Redis, generation_id: str) -> Generation | None:
    data = await redis.hgetall(gen_key(generation_id))
    if not data:
        return None
    return Generation(
        id=data["id"],
        client_id=data["client_id"],
        status=GenerationStatus(data["status"]),
        prompt=data["prompt"],
        style=data.get("style") or None,
        output_size=data["output_size"],
        cost=int(data["cost"]),
        result_url=data.get("result_url") or None,
        error_code=data.get("error_code") or None,
        error_message=data.get("error_message") or None,
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


async def update_generation_status(
    redis: Redis,
    generation_id: str,
    status: GenerationStatus,
    **kwargs: str,
) -> None:
    mapping = {"status": status.value, "updated_at": _now()}
    mapping.update(kwargs)
    await redis.hset(gen_key(generation_id), mapping=mapping)
