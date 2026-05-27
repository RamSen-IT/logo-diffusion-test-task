import hashlib
import secrets

from redis.asyncio import Redis

from app.models.client import Client

SEED_CLIENTS = [
    {
        "id": "client_rich",
        "name": "Rich Client",
        "balance": 1000,
    },
    {
        "id": "client_poor",
        "name": "Poor Client",
        "balance": 4,
    },
]


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def seed_clients(redis: Redis) -> None:
    for client in SEED_CLIENTS:
        # use a stable key slot per client so restarts don't create duplicates
        key_slot = f"client:{client['id']}:apikey_raw"
        existing_raw = await redis.get(key_slot)

        if existing_raw:
            continue

        raw_key = f"ld_live_{secrets.token_hex(24)}"
        key_hash = _hash_key(raw_key)

        await redis.set(key_slot, raw_key)
        await redis.set(f"apikey:{key_hash}", client["id"])
        await redis.hset(f"client:{client['id']}", mapping={
            "id": client["id"],
            "name": client["name"],
        })
        await redis.set(f"client:{client['id']}:balance", client["balance"])

        print(f"[seed] {client['name']}: {raw_key}")


async def get_client_by_key(redis: Redis, raw_key: str) -> Client | None:
    key_hash = _hash_key(raw_key)
    client_id = await redis.get(f"apikey:{key_hash}")
    if not client_id:
        return None

    data = await redis.hgetall(f"client:{client_id}")
    if not data:
        return None

    return Client(
        id=data["id"],
        name=data["name"],
        webhook_url=data.get("webhook_url"),
    )
