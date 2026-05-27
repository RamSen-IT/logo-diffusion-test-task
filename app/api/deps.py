from fastapi import Header, Depends
from redis.asyncio import Redis

from app.core.exceptions import APIError
from app.models.client import Client
from app.services.client_service import get_client_by_key
from app.storage.redis_store import get_redis


async def get_current_client(
    x_api_key: str = Header(alias="X-API-Key"),
    redis: Redis = Depends(get_redis),
) -> Client:
    client = await get_client_by_key(redis, x_api_key)
    if not client:
        raise APIError(401, "unauthorized", "Invalid or missing API key")
    return client
