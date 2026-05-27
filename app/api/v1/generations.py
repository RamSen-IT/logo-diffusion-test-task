from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.deps import get_current_client
from app.core.exceptions import APIError
from app.models.client import Client
from app.models.generation import GenerationStatus
from app.schemas.generation import CreateGenerationRequest, CREDIT_COSTS
from app.services.credit_service import reserve_credits
from app.services.generation_service import create_generation, get_generation
from app.services.rate_limiter import acquire_slot, release_slot
from app.storage.redis_store import get_redis
from worker.tasks.generation import run_generation

router = APIRouter(prefix="/generations")


@router.post("", status_code=202)
async def submit_generation(
    body: CreateGenerationRequest,
    client: Client = Depends(get_current_client),
    redis: Redis = Depends(get_redis),
):
    cost = CREDIT_COSTS[body.output_size]

    await acquire_slot(redis, client.id)
    try:
        await reserve_credits(redis, client.id, cost)
    except APIError:
        await release_slot(redis, client.id)
        raise

    gen = await create_generation(
        redis,
        client_id=client.id,
        prompt=body.prompt,
        style=body.style,
        output_size=body.output_size,
        cost=cost,
    )

    try:
        run_generation.delay(gen.id, client.id, cost)
    except Exception:
        from app.services.credit_service import release_credits
        await release_credits(redis, client.id, cost)
        await release_slot(redis, client.id)
        raise APIError(503, "service_unavailable", "Generation queue is unavailable. Please try again later.")

    return {"id": gen.id, "status": gen.status.value, "created_at": gen.created_at}


@router.get("/{generation_id}")
async def get_generation_status(
    generation_id: str,
    client: Client = Depends(get_current_client),
    redis: Redis = Depends(get_redis),
):
    gen = await get_generation(redis, generation_id)

    if not gen or gen.client_id != client.id:
        raise APIError(404, "not_found", "Generation not found")

    response: dict = {
        "id": gen.id,
        "status": gen.status.value,
        "created_at": gen.created_at,
        "updated_at": gen.updated_at,
    }

    if gen.status == GenerationStatus.COMPLETED:
        response["result_url"] = gen.result_url

    if gen.status == GenerationStatus.FAILED:
        response["error"] = {
            "code": gen.error_code,
            "message": gen.error_message,
        }

    return response
