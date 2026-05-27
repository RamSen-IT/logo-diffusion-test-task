from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from app.api.v1.router import router as v1_router
from app.core.exceptions import APIError
from app.services.client_service import seed_clients
from app.storage.redis_store import close_pool, get_redis, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    redis = await get_redis()
    await seed_clients(redis)
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(v1_router)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    msg = error["msg"]
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "invalid_request", "message": msg}},
    )


@app.exception_handler(RedisError)
async def redis_error_handler(request: Request, exc: RedisError):
    # TODO: add logging for Redis connection errors
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "service_unavailable", "message": "Service temporarily unavailable"}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # TODO: add logging for unhandled errors (with stack trace)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Something went wrong"}},
    )
