import pytest
from redis.asyncio import Redis

from app.models.generation import GenerationStatus
from app.services.generation_service import (
    create_generation,
    get_generation,
    update_generation_status,
)


@pytest.mark.asyncio
async def test_create_generation(redis: Redis):
    gen = await create_generation(
        redis,
        client_id="test_client",
        prompt="logo for coffee shop",
        style="modern",
        output_size="1024",
        cost=5,
    )

    assert gen.id.startswith("gen_")
    assert gen.client_id == "test_client"
    assert gen.status == GenerationStatus.QUEUED
    assert gen.prompt == "logo for coffee shop"
    assert gen.style == "modern"
    assert gen.output_size == "1024"
    assert gen.cost == 5


@pytest.mark.asyncio
async def test_get_generation(redis: Redis):
    gen = await create_generation(
        redis,
        client_id="test_client",
        prompt="test prompt",
        style=None,
        output_size="512",
        cost=2,
    )

    retrieved = await get_generation(redis, gen.id)

    assert retrieved is not None
    assert retrieved.id == gen.id
    assert retrieved.client_id == "test_client"
    assert retrieved.prompt == "test prompt"
    assert retrieved.status == GenerationStatus.QUEUED


@pytest.mark.asyncio
async def test_get_generation_not_found(redis: Redis):
    result = await get_generation(redis, "gen_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_generation_status(redis: Redis):
    gen = await create_generation(
        redis,
        client_id="test_client",
        prompt="test",
        style=None,
        output_size="1024",
        cost=5,
    )

    await update_generation_status(
        redis,
        gen.id,
        GenerationStatus.COMPLETED,
        result_url="https://example.com/result.png",
    )

    updated = await get_generation(redis, gen.id)
    assert updated.status == GenerationStatus.COMPLETED
    assert updated.result_url == "https://example.com/result.png"
