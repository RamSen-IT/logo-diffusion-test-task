from fastapi import Header, Depends
from redis.asyncio import Redis

from app.core.exceptions import APIError
from app.models.client import Client
from app.services.client_service import get_client_by_key
from app.storage.redis_store import get_redis


async def get_current_client(
    authorization: str = Header(),
    redis: Redis = Depends(get_redis),
) -> Client:
    if not authorization.startswith("Bearer "):
        raise APIError(401, "unauthorized", "Invalid or missing API key")

    api_key = authorization[7:]  # Remove "Bearer " prefix
    client = await get_client_by_key(redis, api_key)
    if not client:
        raise APIError(401, "unauthorized", "Invalid or missing API key")
    return client
