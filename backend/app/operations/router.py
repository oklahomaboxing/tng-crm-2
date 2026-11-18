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
from app.phone.tickets import router as phone_ticket_router
router.include_router(phone_ticket_router)
from app.phone.tracking import router as phone_tracking_router
router.include_router(phone_tracking_router)

from app.messaging.inbox import router as text_inbox_router
router.include_router(text_inbox_router)

from app.phone.signup import router as phone_signup_router
router.include_router(phone_signup_router)
from app.phone.coaches import router as phone_coaches_router
router.include_router(phone_coaches_router)
from app.matchmaker.deductions import router as contract_deductions_router
router.include_router(contract_deductions_router)
from app.ticketing.commission_reports import router as commission_reports_router
router.include_router(commission_reports_router)

from app.ticketing.followup import router as ticket_followup_router
router.include_router(ticket_followup_router)

from app.events.media import router as event_media_router
router.include_router(event_media_router)

from app.ticketing.sales_links import router as public_ticket_portal_router
router.include_router(public_ticket_portal_router)

from app.events.recap import router as event_recap_router
router.include_router(event_recap_router)

from app.events.fighter_contribution import router as fighter_contribution_router
router.include_router(fighter_contribution_router)

from app.events.results import router as boxing_results_router
router.include_router(boxing_results_router)

from app.matchmaker.desk import router as matchmaker_desk_router
router.include_router(matchmaker_desk_router)
from app.events.partners import router as partner_router
router.include_router(partner_router)
from app.events.concessions import router as concessions_router
router.include_router(concessions_router)
from app.managers.routes import router as manager_workspace_router
router.include_router(manager_workspace_router)

from app.events.venue import router as venue_router
router.include_router(venue_router)
