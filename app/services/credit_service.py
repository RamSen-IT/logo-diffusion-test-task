from pathlib import Path

from redis.asyncio import Redis

from shared.redis_keys import client_balance

_lua_dir = Path(__file__).parent.parent.parent / "shared" / "lua"

_reserve_script: str = (_lua_dir / "reserve_credits.lua").read_text()
_release_script: str = (_lua_dir / "release_credits.lua").read_text()


async def reserve_credits(redis: Redis, client_id: str, cost: int) -> None:
    try:
        await redis.eval(_reserve_script, 1, client_balance(client_id), cost)
    except Exception as e:
        err = str(e)
        if "INSUFFICIENT_CREDITS" in err:
            from app.core.exceptions import APIError
            raise APIError(402, "insufficient_credits",
                           f"Not enough credits. This request requires {cost} credits.")
        if "CLIENT_NOT_FOUND" in err:
            from app.core.exceptions import APIError
            raise APIError(401, "unauthorized", "Invalid or missing API key")
        raise


async def release_credits(redis: Redis, client_id: str, cost: int) -> None:
    await redis.eval(_release_script, 1, client_balance(client_id), cost)


async def get_balance(redis: Redis, client_id: str) -> int:
    val = await redis.get(client_balance(client_id))
    return int(val) if val is not None else 0
