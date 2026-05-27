from typing import AsyncGenerator

import pytest_asyncio
from redis.asyncio import Redis


@pytest_asyncio.fixture
async def redis() -> AsyncGenerator[Redis, None]:
    client = Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()