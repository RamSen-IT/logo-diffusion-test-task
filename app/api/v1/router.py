from fastapi import APIRouter

from app.api.v1 import health, generations

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(generations.router)
