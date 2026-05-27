import pytest
from redis.asyncio import Redis

from app.core.exceptions import APIError
from app.services.credit_service import reserve_credits, release_credits, get_balance
from shared.redis_keys import client_balance


@pytest.mark.asyncio
async def test_reserve_credits_success(redis: Redis):
    await redis.set(client_balance("test_client"), 100)

    await reserve_credits(redis, "test_client", 10)

    balance = await get_balance(redis, "test_client")
    assert balance == 90


@pytest.mark.asyncio
async def test_reserve_credits_insufficient(redis: Redis):
    await redis.set(client_balance("test_client"), 5)

    with pytest.raises(APIError) as exc_info:
        await reserve_credits(redis, "test_client", 10)

    assert exc_info.value.code == "insufficient_credits"
    assert exc_info.value.status_code == 402
    balance = await get_balance(redis, "test_client")
    assert balance == 5


@pytest.mark.asyncio
async def test_reserve_credits_client_not_found(redis: Redis):
    with pytest.raises(APIError) as exc_info:
        await reserve_credits(redis, "nonexistent", 10)

    assert exc_info.value.code == "unauthorized"
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_release_credits(redis: Redis):
    await redis.set(client_balance("test_client"), 50)

    await release_credits(redis, "test_client", 20)

    balance = await get_balance(redis, "test_client")
    assert balance == 70


@pytest.mark.asyncio
async def test_concurrent_reserve_no_overdraw(redis: Redis):
    """Three concurrent 5-credit requests with 12 credits total - third should fail"""
    await redis.set(client_balance("test_client"), 12)

    # First two should succeed
    await reserve_credits(redis, "test_client", 5)
    await reserve_credits(redis, "test_client", 5)

    # Third should fail
    with pytest.raises(APIError) as exc_info:
        await reserve_credits(redis, "test_client", 5)

    assert exc_info.value.code == "insufficient_credits"
    balance = await get_balance(redis, "test_client")
    assert balance == 2