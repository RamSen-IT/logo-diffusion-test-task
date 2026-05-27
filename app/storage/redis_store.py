from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


def create_pool() -> ConnectionPool:
    return ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Redis pool is not initialized")
    return _pool


async def get_redis() -> Redis:
    return Redis(connection_pool=get_pool())


async def init_pool() -> None:
    global _pool
    _pool = create_pool()
    async with Redis(connection_pool=_pool) as r:
        await r.ping()


async def close_pool() -> None:
    if _pool:
        await _pool.disconnect()
