from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.api.deps import get_current_client
from app.models.client import Client
from app.storage.redis_store import get_redis

router = APIRouter(prefix="/account")


class UpdateAccountRequest(BaseModel):
    webhook_url: str | None = None


@router.patch("")
async def update_account(
    body: UpdateAccountRequest,
    client: Client = Depends(get_current_client),
    redis: Redis = Depends(get_redis),
):
    await redis.hset(f"client:{client.id}", mapping={
        "webhook_url": body.webhook_url or "",
    })
    return {
        "id": client.id,
        "name": client.name,
        "webhook_url": body.webhook_url,
    }
