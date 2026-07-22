from fastapi import APIRouter

from .dashboard import router as dashboard_router
from .products import router as products_router


router = APIRouter()

router.include_router(products_router)
router.include_router(dashboard_router)