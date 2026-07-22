from fastapi import APIRouter

from .attendance import router as attendance_router
from .checkin import router as checkin_router
from .dashboard import router as dashboard_router
from .members import router as members_router
from .products import router as products_router

router = APIRouter()

router.include_router(products_router)
router.include_router(dashboard_router)
router.include_router(members_router)
router.include_router(checkin_router)
router.include_router(attendance_router)
