import pytest
from redis.asyncio import Redis

from app.core.exceptions import APIError
from app.services.rate_limiter import acquire_slot, release_slot, MAX_CONCURRENT
from shared.redis_keys import rate_slot


@pytest.mark.asyncio
async def test_acquire_slot_success(redis: Redis):
    await acquire_slot(redis, "test_client")

    count = await redis.get(rate_slot("test_client"))
    assert int(count) == 1


@pytest.mark.asyncio
async def test_acquire_slot_max_concurrent(redis: Redis):
    # Acquire max allowed slots
    for _ in range(MAX_CONCURRENT):
        await acquire_slot(redis, "test_client")

    # Next one should fail
    with pytest.raises(APIError) as exc_info:
        await acquire_slot(redis, "test_client")

    assert exc_info.value.code == "rate_limit_exceeded"
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_release_slot(redis: Redis):
    await redis.set(rate_slot("test_client"), 3)

    await release_slot(redis, "test_client")

    count = await redis.get(rate_slot("test_client"))
    assert int(count) == 2


@pytest.mark.asyncio
async def test_slot_ttl_is_set(redis: Redis):
    await acquire_slot(redis, "test_client")

    ttl = await redis.ttl(rate_slot("test_client"))
    assert ttl > 0 and ttl <= 300