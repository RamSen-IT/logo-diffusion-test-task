from pathlib import Path

from redis.asyncio import Redis

from shared.redis_keys import rate_slot

_lua_dir = Path(__file__).parent.parent.parent / "shared" / "lua"

_acquire_script: str = (_lua_dir / "acquire_slot.lua").read_text()
_release_script: str = (_lua_dir / "release_slot.lua").read_text()

MAX_CONCURRENT = 5


async def acquire_slot(redis: Redis, client_id: str) -> None:
    try:
        await redis.eval(_acquire_script, 1, rate_slot(client_id), MAX_CONCURRENT)
    except Exception as e:
        if "RATE_LIMIT_EXCEEDED" in str(e):
            from app.core.exceptions import APIError
            raise APIError(
                429,
                "rate_limit_exceeded",
                f"You have reached the limit of {MAX_CONCURRENT} concurrent generations.",
            )
        raise


async def release_slot(redis: Redis, client_id: str) -> None:
    await redis.eval(_release_script, 1, rate_slot(client_id))
