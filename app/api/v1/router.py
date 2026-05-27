from fastapi import APIRouter

from app.api.v1 import account, generations, health

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(generations.router)
router.include_router(account.router)
