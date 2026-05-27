# Logo Diffusion B2B API

FastAPI service for AI logo generation with credit management, rate limiting, and webhook delivery.

## Quick Start (Docker)

```bash
# Start all services (API + Worker + Redis)
docker compose up --build

# API available at http://localhost:8000
```

On startup, the API seeds two test clients and outputs their credentials:

```
[seed] Rich Client: ld_live_...
[seed] Poor Client: ld_live_...
```

- **Rich Client**: 1000 credits (plenty for testing)
- **Poor Client**: 7 credits (enough for three 512px or one 1024px generation, but not enough for 2048px — good for testing insufficient credits)

**Note**: Seed balances are defined in `app/services/client_service.py`. To change them, edit the file and restart with `docker compose down && docker compose up` to flush Redis and re-seed.

## Local Development

### Prerequisites

- Python 3.11+
- Redis 7+

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env for local Redis
# Change REDIS_URL=redis://redis:6379/0 to:
# REDIS_URL=redis://localhost:6379/0

# Or use sed to replace automatically:
sed -i 's/redis:\/\/redis:/redis:\/\/localhost:/g' .env

# Start Redis (if not running)
redis-server

# Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run worker (in separate terminal)
source venv/bin/activate
celery -A worker.celery_app worker --loglevel=info
```

### Running Tests

```bash
pytest tests/ -v
```

Tests cover credit system atomicity, rate limiter accuracy, and generation service operations.

## API Endpoints

Interactive API documentation available at http://localhost:8000/docs

### Authentication

All endpoints require an API key in the `Authorization` header:

```
Authorization: Bearer ld_live_...
```

### POST /v1/generations

Submit a new generation request.

**Request:**

```json
{
  "prompt": "modern coffee shop logo",
  "style": "minimalist",
  "output_size": "1024"
}
```

**Parameters:**

- `prompt` (string, required) — text description
- `style` (string, optional) — style preference
- `output_size` (enum, optional) — "512", "1024", or "2048" (default: "1024")

**Credit costs:**

- 512px: 2 credits
- 1024px: 5 credits
- 2048px: 10 credits

**Response (202 Accepted):**

```json
{
  "id": "gen_AbCd1234",
  "status": "queued",
  "created_at": "2026-05-27T15:30:00Z"
}
```

**Errors:**

- `401` — invalid or missing API key
- `402` — insufficient credits
- `429` — rate limit exceeded (max 5 concurrent per client)
- `503` — generation queue unavailable

### GET /v1/generations/{id}

Poll generation status.

**Response:**

```json
{
  "id": "gen_AbCd1234",
  "status": "completed",
  "created_at": "2026-05-27T15:30:00Z",
  "updated_at": "2026-05-27T15:30:12Z",
  "result_url": "https://cdn.logodiffusion.com/fake/gen_AbCd1234.png"
}
```

**Status values:**

- `queued` — waiting for worker
- `processing` — AI model running
- `completed` — result ready (includes `result_url`)
- `failed` — generation failed (includes `error` object)

**Failed example:**

```json
{
  "id": "gen_AbCd1234",
  "status": "failed",
  "created_at": "2026-05-27T15:30:00Z",
  "updated_at": "2026-05-27T15:30:08Z",
  "error": {
    "code": "generation_failed",
    "message": "AI provider returned an error"
  }
}
```

**Errors:**

- `404` — generation not found (or belongs to different client)

### GET /v1/account

Get current client information.

**Response:**

```json
{
  "id": "client_rich",
  "name": "Rich Client",
  "balance": 1000,
  "webhook_url": "https://example.com/webhooks/generations"
}
```

### PATCH /v1/account/webhook

Register webhook URL for generation notifications.

**Request:**

```json
{
  "webhook_url": "https://example.com/webhooks/generations"
}
```

**Response (200 OK):**

```json
{
  "webhook_url": "https://example.com/webhooks/generations"
}
```

**Webhook payload (POST):**

```json
{
  "generation_id": "gen_AbCd1234",
  "status": "completed",
  "timestamp": "2026-05-27T15:30:12Z",
  "result_url": "https://cdn.logodiffusion.com/fake/gen_AbCd1234.png"
}
```

### GET /v1/health

Service health and metrics.

**Response:**

```json
{
  "status": "ok",
  "redis": "ok",
  "celery": "ok",
  "metrics": {
    "total_generations": 42,
    "completed": 35,
    "failed": 7,
    "queue_depth": 3
  }
}
```

## Testing the API

```bash
# Get API key from startup logs
API_KEY="ld_live_..."

# Submit generation
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/generations \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "tech startup logo", "output_size": "1024"}')

GEN_ID=$(echo $RESPONSE | jq -r '.id')
echo "Generation ID: $GEN_ID"

# Poll status (wait 5-15 seconds for mock AI)
curl http://localhost:8000/v1/generations/$GEN_ID \
  -H "Authorization: Bearer $API_KEY"

# Get account info (balance, webhook, etc)
curl http://localhost:8000/v1/account \
  -H "Authorization: Bearer $API_KEY"

# Register webhook
curl -X PATCH http://localhost:8000/v1/account/webhook \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://webhook.site/your-unique-id"}'

# Check service health
curl http://localhost:8000/v1/health
```

## Architecture

- **FastAPI** — async HTTP API with lifespan event handlers
- **Celery** — background task queue for AI generation (mocked with random delay + success/failure)
- **Redis** — broker, backend, and datastore (client state, generation state, metrics)
- **Lua scripts** — atomic credit reserve/release and rate limiting
- **Webhooks** — fire-and-forget delivery in background threads

## Credit System

Credits are **reserved** on submission and **released** on failure:

1. Client submits generation → credits deducted immediately
2. Generation fails → credits returned to balance
3. Generation succeeds → credits remain deducted

This prevents concurrent requests from overdrawing the balance.

## Rate Limiting

Per-client concurrency limit: **5 simultaneous generations**

Enforced with Redis atomic counter and TTL. Slots released when generation completes or fails.

## Error Response Format

All errors return structured JSON:

```json
{
  "error": {
    "code": "insufficient_credits",
    "message": "Not enough credits. This request requires 5 credits."
  }
}
```

**Error codes:**

- `invalid_request` — validation failed
- `unauthorized` — invalid/missing API key
- `insufficient_credits` — not enough credits
- `rate_limit_exceeded` — too many concurrent generations
- `not_found` — generation not found
- `generation_failed` — AI provider error
- `generation_timeout` — task exceeded time limit
- `service_unavailable` — queue connection failed
- `internal_error` — unexpected server error

## Architectural Decisions

### Project Structure

```
app/
├── api/v1/          # API endpoints (generations, account, health)
├── core/            # Configuration, exceptions, shared utilities
├── models/          # Domain models (Client, Generation)
├── schemas/         # Request/response schemas, validation
├── services/        # Business logic (credits, rate limiting, webhooks)
└── storage/         # Redis connection pool management

worker/
├── tasks/           # Celery tasks (generation processing)
├── celery_app.py    # Celery configuration
└── redis_client.py  # Sync Redis client for workers

shared/
├── lua/             # Atomic Redis operations (credit reserve/release, rate limit)
└── redis_keys.py    # Centralized key naming to prevent collisions

tests/               # Unit tests for credit system, rate limiter, generation service
```

The API and worker are separated but share common code through `shared/`. Services contain business logic isolated from HTTP and task layers, making them independently testable. Lua scripts live in `shared/` since both API (reserve) and worker (release) need them.

### Why Lua Scripts for Credit Management

Redis Lua scripts execute atomically, preventing race conditions when multiple requests check and deduct credits simultaneously. Alternative approaches (WATCH/MULTI/EXEC or distributed locks) are more complex and error-prone.

The `reserve_credits.lua` script atomically checks balance and decrements in a single Redis operation, ensuring the "three concurrent 5-credit requests with 12 credits" scenario correctly rejects the third request.

### Separate Redis Clients for Async/Sync

FastAPI uses async Redis (`redis.asyncio`) while Celery workers use sync Redis (`redis.Redis`). This prevents event loop conflicts and follows each framework's concurrency model.

### Credit Deduction Strategy

Credits are deducted immediately on submission (not just "reserved"), then refunded on failure. This is simpler than a two-phase freeze/commit system and prevents the "reserved but never resolved" state if a worker crashes before committing.

### Why 404 for Cross-Client Access

When client A requests client B's generation, we return 404 (not 401/403) to avoid leaking information about which generation IDs exist. This prevents enumeration attacks.

### Fire-and-Forget Webhooks

Webhooks dispatch in background daemon threads with a 5-second timeout. We don't retry or log failures — the client can poll `/v1/generations/{id}` if the webhook doesn't arrive. This keeps the system simple and prevents webhook delivery issues from blocking generation processing.

### Single Redis Database for Everything

We use Redis as broker, result backend, client state store, and metrics store. For a production system serving multiple clients, you'd separate these (dedicated message broker, persistent database for client state). For this scale, Redis handles it cleanly.

### Account Endpoint Structure

Added `GET /v1/account` to expose balance and settings, and nested webhook config under `/v1/account/webhook`. This groups account-related operations under a clear namespace and makes the API more discoverable for API consumers.

## What I'd Add With More Time

### Production Readiness

- **Persistent storage**: Move client accounts and generation history to PostgreSQL. Redis is great for ephemeral state, but client balances and audit logs need durability. Replace hardcoded seed clients with proper account management.
- **Proper secrets management**: API keys should be rotated, scoped by permission, and stored hashed with bcrypt (not SHA-256).
- **Observability**: Structured logging (structlog), distributed tracing (OpenTelemetry), and Prometheus metrics export.
- **Webhook retries**: Exponential backoff with a dead-letter queue for failed deliveries.

### Features

- **Batch generations**: Submit multiple prompts in one request, track as a batch job.
- **Generation history**: `/v1/generations?limit=50&cursor=...` to list and filter client's past generations.
- **Idempotency keys**: Let clients safely retry requests without creating duplicate generations.
- **Priority queue**: Premium clients get faster processing (separate Celery queue).
- **Usage analytics**: Detailed reports on credit consumption, success/failure rates, popular styles.
- **Admin API**: Separate endpoints for internal tools to create clients, adjust balances, view metrics (currently clients are hardcoded in seed).

### Testing

- **Integration tests**: Full request → worker → webhook flow with a real Redis instance.
- **Concurrency tests**: Spawn 10 concurrent requests and verify credit/rate-limit correctness.
- **Chaos testing**: Kill worker mid-task and verify credits are released correctly.

### Developer Experience

- **OpenAPI customization**: Add request/response examples to auto-generated docs.
- **SDK**: Python/TypeScript client libraries wrapping the API.
- **Webhook signature verification**: HMAC-signed payloads so clients can verify authenticity.