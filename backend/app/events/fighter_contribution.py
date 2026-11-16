"""Private, fighter-specific ticket contribution derived from the event recap."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from app.database import get_db
from app.core.dependencies import current_user
from app.matchmaker.models import BoxingFighter, BoxingBout, BoxingEvent
from app.fighter_portal.models import FighterAccount
from app.ticketing.models import EventSeller, TicketOrder, PaperTicket, PaperTicketBatch
from app.ticketing.sales_reports import commission_summary
from .recap import recap, CANCELLED

router = APIRouter(prefix='/api/events/fighters', tags=['Fighter contribution'])

@router.get('/{fighter_id}/contribution')
def fighter_contribution(fighter_id: int, response: Response, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), db=Depends(get_db), user=Depends(current_user)):
    if user.role not in ('admin', 'staff'):
        if user.role != 'fighter':
            raise HTTPException(403, 'Fighter or staff account required')
        account = db.query(FighterAccount).filter_by(user_id=user.id).first()
        if not account or account.fighter_id != fighter_id:
            raise HTTPException(403, 'You can view only your own contribution')
    if not db.get(BoxingFighter, fighter_id):
        raise HTTPException(404, 'Fighter not found')
    bouts = db.query(BoxingBout).filter(or_(BoxingBout.red_fighter_id == fighter_id, BoxingBout.blue_fighter_id == fighter_id)).all()
    event_ids = {b.event_id for b in bouts if b.event_id and str(b.status or '').strip().lower() not in CANCELLED}
    events = db.query(BoxingEvent).filter(BoxingEvent.id.in_(event_ids)).order_by(BoxingEvent.event_date.desc(), BoxingEvent.id.desc())
    result = []
    fields = ('ticket_quantity', 'ticket_sales_cents', 'gross_purse_cents', 'travel_cents', 'per_diem_cents', 'deductions_cents', 'net_obligation_cents', 'purse_paid_cents', 'purse_cost_cents', 'commission_earned_cents', 'commission_cost_cents', 'total_fighter_cost_cents', 'ticket_contribution_cents')
    for event in events.offset(offset).limit(limit):
        data = recap(db, event.id)
        row = next((r for r in data['fighters'] if r['fighter_id'] == fighter_id), None)
        if not row:
            continue
        event_bouts = db.query(BoxingBout).filter_by(event_id=event.id).all()
        event_bouts = [b for b in event_bouts if str(b.status or '').strip().lower() not in CANCELLED]
        opponents = {f for b in event_bouts if fighter_id in (b.red_fighter_id,b.blue_fighter_id) for f in (b.red_fighter_id,b.blue_fighter_id) if f != fighter_id}
        unrelated = any(fighter_id not in (b.red_fighter_id,b.blue_fighter_id) and opponents.intersection((b.red_fighter_id,b.blue_fighter_id)) for b in event_bouts)
        opponent_rows = [r for r in data['fighters'] if r['fighter_id'] in opponents]
        opponent_cost = sum(r['total_fighter_cost_cents'] for r in opponent_rows) if not unrelated and len(opponent_rows)==len(opponents) else None
        combined_cost = row['total_fighter_cost_cents'] + opponent_cost if opponent_cost is not None else None
        contribution = row['ticket_sales_cents'] - combined_cost if combined_cost is not None else None
        notes = []
        if combined_cost is None:
            notes.append('An opponent has other bouts on this event. Allocate those shared fighter costs before comparing this bout.')
        if any('not fully signed' in b or 'recorded purse only' in b for b in row['basis']):
            notes.append('Final signed bout terms are not fully recorded; these costs may change.')
        if row['purse_paid_cents'] is None:
            notes.append('Actual purse payments have not been recorded; cost uses the recorded obligation.')
        if row['purse_paid_cents'] is not None and row['purse_paid_cents'] > row['net_obligation_cents']:
            notes.append('Purse cost includes recorded payments above the current obligation; review the payment record.')
        if row['commission_cost_cents'] > row['commission_earned_cents']:
            notes.append('Commission cost includes recorded payments above current earned commission; review the payment record.')
        orders = db.query(TicketOrder).join(EventSeller, EventSeller.id == TicketOrder.seller_id).filter(TicketOrder.event_id == event.id, EventSeller.event_id == event.id, EventSeller.seller_type == 'fighter', EventSeller.seller_ref_id == fighter_id).all()
        health = commission_summary(db, event.id, orders)
        if health['partial_refund_orders']:
            notes.append('Partially refunded ticket orders need reconciliation and are excluded from these sales.')
        if health['paid_orders_missing_tickets']:
            notes.append('Paid ticket issuance needs reconciliation; commission costs may change.')
        seller_ids = [s[0] for s in db.query(EventSeller.id).filter_by(event_id=event.id, seller_type='fighter', seller_ref_id=fighter_id)]
        unrecorded_paper = db.query(PaperTicket.id).join(PaperTicketBatch, PaperTicketBatch.id == PaperTicket.batch_id).filter(PaperTicketBatch.event_id == event.id, PaperTicketBatch.seller_id.in_(seller_ids), PaperTicket.status.in_(['allocated', 'released', 'offline_used'])).count()
        if unrecorded_paper:
            notes.append(f'{unrecorded_paper} paper ticket(s) have no recorded sale and are excluded until reconciled.')
        result.append({'provisional':bool(notes), 'event_id':event.id, 'event_name':event.name, 'event_date':event.event_date,
                       **{k:row[k] for k in fields}, 'own_direct_cost_cents':row['total_fighter_cost_cents'], 'opponent_direct_cost_cents':opponent_cost, 'combined_bout_cost_cents':combined_cost, 'combined_bout_contribution_cents':contribution, 'combined_bout_outcome':'needs_allocation' if contribution is None else 'above_direct_costs' if contribution > 0 else 'below_direct_costs' if contribution < 0 else 'break_even', 'outcome':'above_direct_costs' if row['ticket_contribution_cents']>0 else 'below_direct_costs' if row['ticket_contribution_cents']<0 else 'break_even',
                       'notes':notes})
    response.headers['Cache-Control'] = 'private, no-store'
    return {'fighter_id':fighter_id, 'events':result, 'total':events.count(), 'limit':limit, 'offset':offset,
            'cost_scope':'both_corners', 'ticket_sales_scope':'this_fighter', 'basis':'Paid tickets credited to this fighter minus their own recorded purse, travel/per diem and commission cost, before shared expenses.', 'combined_bout_basis':'Recorded paid tickets credited to this fighter minus the combined direct costs of both red and blue corners (purses, travel/per diem and ticket commissions). Ticket sales remain specific to this fighter; the same combined cost appears on each participant’s profile and must not be added together across profiles. Event recap accounting still counts each fighter once. Costs use recorded obligations or higher recorded payments. Before venue, officials, insurance, state assessment and separately recorded vendor expenses. This is a direct-cost contribution estimate, not final event profit.',
            'roster_scope':'current_bout_card'}
