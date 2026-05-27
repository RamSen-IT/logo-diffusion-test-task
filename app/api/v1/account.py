from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.api.deps import get_current_client
from app.models.client import Client
from app.services.credit_service import get_balance
from app.storage.redis_store import get_redis

router = APIRouter(prefix="/account")


class SetWebhookRequest(BaseModel):
    webhook_url: str


@router.get("")
async def get_account(
    client: Client = Depends(get_current_client),
    redis: Redis = Depends(get_redis),
):
    balance = await get_balance(redis, client.id)
    return {
        "id": client.id,
        "name": client.name,
        "balance": balance,
        "webhook_url": client.webhook_url or None,
    }


@router.patch("/webhook")
async def set_webhook(
    body: SetWebhookRequest,
    client: Client = Depends(get_current_client),
    redis: Redis = Depends(get_redis),
):
    await redis.hset(f"client:{client.id}", "webhook_url", body.webhook_url)
    return {"webhook_url": body.webhook_url}
