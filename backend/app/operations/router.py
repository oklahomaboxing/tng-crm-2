from fastapi import APIRouter

from .duplicates import router as duplicates_router

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
router.include_router(duplicates_router)

from .overview import router as overview_router
router.include_router(overview_router)

from app.kiosk.routes import router as kiosk_router
router.include_router(kiosk_router)
from app.ai.assistant import router as assistant_router
router.include_router(assistant_router)
from .reconciliation import router as reconciliation_router
router.include_router(reconciliation_router)
from .renewal_reminders import router as renewal_reminders_router
router.include_router(renewal_reminders_router)
from app.apparel.routes import router as apparel_router
router.include_router(apparel_router)
from app.matchmaker.contract_library import router as signed_contract_library_router
router.include_router(signed_contract_library_router)
from app.matchmaker.welcome_letter import router as fighter_welcome_router
router.include_router(fighter_welcome_router)
from app.mail.microsoft365 import router as microsoft_mail_router
router.include_router(microsoft_mail_router)
from app.phone.routes import router as phone_assistant_router
router.include_router(phone_assistant_router)
