"""Recorded event profitability and separate purse/commission payment records."""
import csv, io, json
from datetime import datetime, date, time, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base, get_db
from app.core.dependencies import staff_user
from app.models import SecurityLog, User
from app.matchmaker.models import BoxingEvent, BoxingBout, BoxingFighter, BoxingContract, BoxingContractSignature, BoxingSignedContractDocument, BoxingEventFee
from app.matchmaker.deductions import ContractDeductions
from app.ticketing.models import TicketOrder, IssuedTicket, EventSeller, SellerPayout
from app.ticketing.sales_reports import commission_summary, quantity
from app.revenue.models import EventRevenuePayment
router = APIRouter(prefix='/api/events', tags=['Event recap'])
CT = ZoneInfo('America/Chicago')
CANCELLED = {'cancelled', 'canceled', 'void', 'withdrawn', 'declined', 'rejected', 'removed', 'deleted'}
TREATMENTS = Literal['other', 'fighter_pay', 'ticket_commission', 'state_assessment', 'exclude']

class EventPursePayment(Base):
    __tablename__ = 'event_purse_payment_records'
    __table_args__ = (UniqueConstraint('event_id', 'fighter_id', name='uq_event_purse_fighter'),)
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('boxing_events.id'), nullable=False, index=True)
    fighter_id = Column(Integer, ForeignKey('boxing_fighters.id'), nullable=False)
    amount_paid_cents = Column(Integer, nullable=False)
    paid_date = Column(String(10), nullable=True)
    notes = Column(Text, nullable=False, default='')
    version = Column(Integer, nullable=False, default=1)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class EventPurseHold(Base):
    __tablename__ = 'event_purse_holds'
    __table_args__ = (UniqueConstraint('event_id','fighter_id',name='uq_event_purse_hold'),)
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    fighter_id=Column(Integer,ForeignKey('boxing_fighters.id'),nullable=False)
    active=Column(Integer,default=0,nullable=False)
    reason=Column(Text,default='',nullable=False)
    version=Column(Integer,default=1,nullable=False)
    updated_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class EventPaymentChange(Base):
    __tablename__ = 'event_payment_changes'
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    kind=Column(String(20),nullable=False)
    target_id=Column(Integer,nullable=False)
    source_id=Column(Integer,nullable=True)
    amount_paid_cents=Column(Integer,nullable=True)
    paid_date=Column(String(10),nullable=True)
    notes=Column(Text,default='',nullable=False)
    hold_active=Column(Integer,nullable=True)
    baseline=Column(Integer,default=0,nullable=False)
    recorded_by=Column(Integer,ForeignKey('users.id'),nullable=True)
    recorded_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def payment_status(due,paid,hold=False):
    if hold and (paid is None or paid<due or due==0):return 'on_hold'
    if paid is None:return 'not_recorded' if due else 'nothing_due'
    if paid>due:return 'overpaid'
    if not due:return 'nothing_due'
    if paid==due:return 'paid'
    return 'partial' if paid else 'unpaid'

class RecapFeeTreatment(Base):
    __tablename__ = 'event_recap_fee_treatments'
    fee_id = Column(Integer, ForeignKey('boxing_event_fees.id'), primary_key=True)
    treatment = Column(String(30), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

def event_for(db, eid, lock=False):
    q = db.query(BoxingEvent).filter_by(id=eid)
    row = (q.with_for_update() if lock else q).first()
    if not row:
        raise HTTPException(404, 'Event not found')
    return row

def cents(value, issues, label):
    try:
        d = Decimal(str(value or 0))
        if not d.is_finite() or d < 0:
            raise ValueError()
        return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        issues.add(f'{label}: invalid amount excluded; review the source record.')
        return 0

def default_treatment(fee):
    key = str(fee.fee_key or '').lower().replace('-', '_').replace(' ', '_')
    if key in {'assessment', 'state_assessment', 'osac_assessment'}:
        return 'state_assessment'
    if key in {'purse', 'purses', 'fighter_pay', 'fighter_purse', 'fighter_purses'}:
        return 'fighter_pay'
    if key in {'ticket_commission', 'ticket_commissions', 'seller_commissions'}:
        return 'ticket_commission'
    return 'other'

def recap(db, eid):
    event = event_for(db, eid)
    issues = set()
    orders = db.query(TicketOrder).filter_by(event_id=eid).order_by(TicketOrder.id).all()
    paid = {o.id: o for o in orders if o.payment_status == 'paid'}
    gross = sum((int(o.subtotal_cents or 0) for o in paid.values()))
    fees_collected = sum((int(o.fee_cents or 0) for o in paid.values()))
    health = commission_summary(db, eid, orders)
    for key, label in [('unreconciled_paper_tickets', 'paper tickets await sales reconciliation'), ('partial_refund_orders', 'partially refunded orders need net-refund reconciliation'), ('paid_orders_missing_tickets', 'paid orders have a ticket issuance mismatch')]:
        if health[key]:
            issues.add(f'{health[key]} {label}.')
    bouts = db.query(BoxingBout).filter_by(event_id=eid).order_by(BoxingBout.id).all()
    active = [b for b in bouts if str(b.status or '').strip().lower() not in CANCELLED]
    contracts = db.query(BoxingContract).filter_by(event_id=eid).order_by(BoxingContract.id.desc()).all()
    cids = [c.id for c in contracts]
    signed = {x[0] for x in db.query(BoxingContractSignature.contract_id).filter(BoxingContractSignature.contract_id.in_(cids))} | {x[0] for x in db.query(BoxingSignedContractDocument.contract_id).filter(BoxingSignedContractDocument.contract_id.in_(cids))}
    deductions = {r.contract_id: r for r in db.query(ContractDeductions).filter(ContractDeductions.contract_id.in_(cids))}
    holds = {r.fighter_id:r for r in db.query(EventPurseHold).filter_by(event_id=eid)}
    purse_records = {r.fighter_id: r for r in db.query(EventPursePayment).filter_by(event_id=eid)}
    participant_ids = {f for b in active for f in [b.red_fighter_id, b.blue_fighter_id]}
    fighters = {f.id: f for f in db.query(BoxingFighter).filter(BoxingFighter.id.in_(participant_ids))}
    rows = {}

    def row(fid):
        if fid not in rows:
            f = fighters.get(fid)
            p = purse_records.get(fid)
            rows[fid] = {'fighter_id': fid, 'name': f.legal_name if f else f'Fighter #{fid}', 'contract_ids': [], 'basis': [], 'gross_purse_cents': 0, 'travel_cents': 0, 'per_diem_cents': 0, 'deductions_cents': 0, 'net_obligation_cents': 0, 'ticket_quantity': 0, 'ticket_sales_cents': 0, 'commission_earned_cents': 0, 'commission_cost_cents': 0, 'purse_paid_cents': p.amount_paid_cents if p else None, 'purse_paid_date': p.paid_date if p else None, 'purse_notes': p.notes if p else '', 'purse_version': p.version if p else 0}
        return rows[fid]

    def executed(c):
        return c.id in signed or str(c.status or '').lower() in {'signed', 'completed', 'executed'} or str(c.docusign_status or '').lower() == 'completed' or (str(c.adobe_status or '').lower() in {'signed', 'completed'})
    seen = set()
    active_ids = set()
    for b in active:
        for fid, side in [(b.red_fighter_id, 'red'), (b.blue_fighter_id, 'blue')]:
            if (b.id, fid) in seen:
                continue
            seen.add((b.id, fid))
            active_ids.add(fid)
            r = row(fid)
            options = [c for c in contracts if c.bout_id == b.id and c.fighter_id == fid and (str(c.status or '').lower() not in CANCELLED)]
            effective = [c for c in options if executed(c)]
            c = effective[0] if effective else options[0] if options else None
            if c:
                r['contract_ids'].append(c.id)
                g = cents(c.gross_purse, issues, f'Contract {c.id} purse')
                t = cents(c.travel_expense, issues, f'Contract {c.id} travel')
                p = cents(c.per_diem_total, issues, f'Contract {c.id} per diem')
                d = deductions.get(c.id)
                if d:
                    try:
                        ded = int(d.base_deductions_cents or 0) + sum((int(i['amount_cents']) for i in json.loads(d.items_json or '[]')))
                    except (ValueError, TypeError, KeyError):
                        ded = 0
                        issues.add(f'Contract {c.id}: deduction ledger needs review.')
                else:
                    ded = cents(c.deductions, issues, f'Contract {c.id} deductions')
                if ded < 0 or ded > g + t + p:
                    issues.add(f'Contract {c.id}: deductions exceed the recorded allowance or are invalid.')
                    ded = max(0, min(ded, g + t + p))
                r['basis'].append(f'Contract #{c.id}' + (' · signed' if executed(c) else ' · not fully signed'))
                if not executed(c):
                    issues.add(f"{r['name']}: purse is based on an unsigned contract.")
                if effective and options[0].id != c.id:
                    issues.add(f"{r['name']}: a newer unsigned revision exists; the signed contract is used.")
            else:
                g = cents(getattr(b, side + '_purse'), issues, f'Bout {b.id} {side} purse')
                t = p = ded = 0
                r['basis'].append(f'Bout #{b.id} recorded purse only')
                issues.add(f"{r['name']}: no current contract; travel and final purse terms need review.")
            r['gross_purse_cents'] += g
            r['travel_cents'] += t
            r['per_diem_cents'] += p
            r['deductions_cents'] += ded
            r['net_obligation_cents'] += g + t + p - ded
    if not active:
        issues.add('No active bout purse costs are recorded; the event result may be incomplete.')
    excluded_purses = [p for fid, p in purse_records.items() if fid not in active_ids]
    excluded_paid_cents = sum(int(p.amount_paid_cents or 0) for p in excluded_purses)
    if excluded_purses:
        issues.add(f'{len(excluded_purses)} off-card purse payment record(s), totaling ${excluded_paid_cents / 100:,.2f}, are excluded from this current-card recap. Saved payment history is retained.')
    sellers = db.query(EventSeller).filter_by(event_id=eid).order_by(EventSeller.id).all()
    seller_map = {s.id: s for s in sellers}
    sales = {}
    earned = {}
    counts = {}
    for o in paid.values():
        sales[o.seller_id] = sales.get(o.seller_id, 0) + int(o.subtotal_cents or 0)
        counts[o.seller_id] = counts.get(o.seller_id, 0) + quantity(o)
    for t in db.query(IssuedTicket).filter_by(event_id=eid):
        if t.order_id in paid and t.status in ('valid', 'used'):
            earned[t.seller_id] = earned.get(t.seller_id, 0) + int(t.commission_cents or 0)
    snapshots = {}
    for p in db.query(SellerPayout).filter_by(event_id=eid).order_by(SellerPayout.created_at.desc(), SellerPayout.id.desc()):
        snapshots.setdefault(p.seller_id, p)
    seller_rows = []
    for sid in sorted(set(sales) | set(earned) | set(snapshots) | set(seller_map), key=lambda x: (x is None, x or 0)):
        s = seller_map.get(sid)
        snap = snapshots.get(sid)
        commission = earned.get(sid, 0)
        paid_comm = max(0, int(snap.amount_paid_cents or 0)) if snap else None
        cost = max(commission, paid_comm or 0)
        sr = {'seller_id': sid, 'name': s.display_name if s else 'Direct / unattributed', 'fighter_id': s.seller_ref_id if s and s.seller_type == 'fighter' and (s.seller_ref_id in active_ids) else None, 'ticket_quantity': counts.get(sid, 0), 'ticket_sales_cents': sales.get(sid, 0), 'commission_earned_cents': commission, 'commission_paid_cents': paid_comm, 'commission_cost_cents': cost, 'remaining_cents': max(0, commission - (paid_comm or 0)), 'commission_status':payment_status(commission,paid_comm),'previous_payout_id': snap.id if snap else None, 'notes': snap.notes or '' if snap else '', 'paid_date': snap.paid_at.replace(tzinfo=timezone.utc).astimezone(CT).date().isoformat() if snap and snap.paid_at else None}
        seller_rows.append(sr)
        if paid_comm is not None and paid_comm > commission:
            issues.add(f"{sr['name']}: recorded commission payments exceed current earned commission; the higher paid cost is included.")
        if sr['fighter_id'] is not None:
            r = row(sr['fighter_id'])
            r['ticket_quantity'] += sr['ticket_quantity']
            r['ticket_sales_cents'] += sr['ticket_sales_cents']
            r['commission_earned_cents'] += commission
            r['commission_cost_cents'] += cost
    for r in rows.values():
        actual = r['purse_paid_cents']
        r['purse_cost_cents'] = max(r['net_obligation_cents'], actual or 0)
        r['total_fighter_cost_cents'] = r['purse_cost_cents'] + r['commission_cost_cents']
        r['ticket_contribution_cents'] = r['ticket_sales_cents'] - r['total_fighter_cost_cents']
        r['remaining_purse_cents'] = max(0, r['net_obligation_cents'] - (actual or 0))
        hold=holds.get(r['fighter_id'])
        r.update({'purse_on_hold':bool(hold and hold.active),'purse_hold_reason':hold.reason if hold else '', 'purse_hold_version':hold.version if hold else 0})
        r['purse_status']=payment_status(r['net_obligation_cents'],actual,r['purse_on_hold'])
        linked=[seller for seller in seller_rows if seller['fighter_id']==r['fighter_id']]
        known=sum(seller['commission_paid_cents'] or 0 for seller in linked)
        missing=any(seller['commission_paid_cents'] is None and seller['commission_earned_cents']>0 for seller in linked)
        r['commission_paid_cents']=None if missing else known
        r['commission_known_paid_cents']=known
        r['commission_remaining_cents']=sum(seller['remaining_cents'] for seller in linked)
        r['commission_status']='partly_recorded' if missing and known else payment_status(r['commission_earned_cents'],r['commission_paid_cents'])
        if r['purse_on_hold'] and actual is not None and actual>=r['net_obligation_cents'] and actual>0:
            issues.add(f"{r['name']}: purse is fully recorded as paid but a hold is still active; review the hold without changing payment history.")

        if actual is not None and actual > r['net_obligation_cents']:
            issues.add(f"{r['name']}: recorded purse payments exceed current net obligation; the higher paid cost is included.")
    if sum((r['deductions_cents'] for r in rows.values())):
        issues.add('Deductions reduce net fighter payouts. Record related hotel, medical or other vendor costs separately once; deductions alone do not prove those expenses were paid.')
    fee_mappings = {r.fee_id: r for r in db.query(RecapFeeTreatment).join(BoxingEventFee, BoxingEventFee.id == RecapFeeTreatment.fee_id).filter(BoxingEventFee.event_id == eid)}
    fee_rows = []
    other_cost = 0
    assessment_values = []
    source_fees = db.query(BoxingEventFee).filter_by(event_id=eid).order_by(BoxingEventFee.id).all()
    if not source_fees:
        issues.add('No event expense amounts are recorded; add actual venue, officials, insurance and other costs in Expenses.')
    for f in source_fees:
        mapping = fee_mappings.get(f.id)
        kind = mapping.treatment if mapping else default_treatment(f)
        amount = cents(f.actual_amount, issues, f'Expense {f.id}') if f.actual_amount is not None else None
        if kind in ('other', 'state_assessment') and amount is None:
            issues.add(f'{f.name}: actual expense amount is not recorded; text estimates are not treated as actual costs.')
        if kind == 'other' and amount is not None:
            other_cost += amount
        if kind == 'state_assessment' and amount is not None:
            assessment_values.append(amount)
        fee_rows.append({'id': f.id, 'name': f.name, 'estimate': f.estimate, 'actual_cents': amount, 'paid': bool(f.paid), 'treatment': kind, 'version': mapping.version if mapping else 0, 'included_cents': amount or 0 if kind in ('other', 'state_assessment') else 0})
    recorded_assessment=sum(assessment_values) if assessment_values else None
    assessment=max(recorded_assessment or 0,health['state_commission_cents'])
    if recorded_assessment is not None and recorded_assessment<health['state_commission_cents']:issues.add('Recorded assessment is below the required 5% / $450 minimum. Review the remaining liability.')
    if not assessment_values:
        issues.add('State assessment uses the greater of 5% of paid tickets or $450 minimum until an actual assessment is recorded.')
    other_income = 0
    income_rows = []
    seen_refs = set()
    ticket_refs = {o.payment_id for o in paid.values() if o.payment_id}
    for p in db.query(EventRevenuePayment).filter_by(event_id=eid).order_by(EventRevenuePayment.id):
        if str(p.status or '').upper() != 'PAID':
            if str(p.status or '').upper() == 'PARTIAL':
                issues.add('Partial sponsor/vendor payments need reconciliation; only PAID entries are included.')
            continue
        ref = (str(p.provider or '').upper(), p.provider_payment_id)
        if p.provider_payment_id and (ref in seen_refs or p.provider_payment_id in ticket_refs):
            issues.add(f'Other revenue payment #{p.id}: duplicate payment reference excluded from other income.')
            continue
        if p.provider_payment_id:
            seen_refs.add(ref)
        value = cents(p.amount, issues, f'Other revenue payment {p.id}')
        other_income += value
        income_rows.append({'id': p.id, 'provider': p.provider, 'amount_cents': value})
    fighter_rows = sorted(rows.values(), key=lambda r: r['name'].casefold())
    purse_cost = sum((r['purse_cost_cents'] for r in fighter_rows))
    comm_cost = sum((r['commission_cost_cents'] for r in seller_rows))
    total_cost = purse_cost + comm_cost + assessment + other_cost
    from .concessions_finance import pos_revenue,report_data,EventPosSnapshot
    pos=pos_revenue(db,eid)
    pos_snapshot=db.get(EventPosSnapshot,eid)
    other_income+=pos['concessions']+pos['bar']
    if pos['concessions'] or pos['bar']:
        pos_report=report_data(db,eid)
        if pos_report['totals']['review'] or any(pos_report['review_counts'].values()):issues.add('Concessions/bar POS report has unclassified or excluded source orders; review Sales & profit.')
    summary = {'pos_snapshot_imported':bool(pos_snapshot and pos_snapshot.imported_at),'pos_snapshot_imported_at':pos_snapshot.imported_at.isoformat()+'Z' if pos_snapshot and pos_snapshot.imported_at else None,'concessions_sales_cents':pos['concessions'],'bar_sales_cents':pos['bar'],'excluded_off_card_purse_records': len(excluded_purses), 'excluded_off_card_purse_paid_cents': excluded_paid_cents, 'current_card_fighters': len(fighter_rows), 'ticket_sales_cents': gross, 'customer_fees_cents': fees_collected, 'paid_ticket_quantity': sum((quantity(o) for o in paid.values())), 'paid_orders':len(paid), 'unconfirmed_orders': sum((o.payment_status in ('pending', 'failed') for o in orders)), 'refunded_orders': sum((o.payment_status == 'refunded' for o in orders)), 'gross_purse_cents': sum((r['gross_purse_cents'] for r in fighter_rows)), 'travel_cents': sum((r['travel_cents'] for r in fighter_rows)), 'per_diem_cents': sum((r['per_diem_cents'] for r in fighter_rows)), 'deductions_cents': sum((r['deductions_cents'] for r in fighter_rows)), 'net_purse_obligation_cents': sum((r['net_obligation_cents'] for r in fighter_rows)), 'purse_cost_cents': purse_cost, 'commission_cost_cents': comm_cost, 'fighter_and_seller_cost_cents': purse_cost + comm_cost, 'ticket_contribution_cents': gross - purse_cost - comm_cost, 'state_assessment_cents': assessment, 'state_assessment_required_cents':health['state_commission_cents'],'state_assessment_recorded_cents':recorded_assessment,'assessment_basis': 'recorded_actual' if assessment_values and recorded_assessment>=health['state_commission_cents'] else 'required_exceeds_recorded' if assessment_values else 'estimated_5_percent_minimum_450', 'other_expenses_cents': other_cost, 'other_income_cents': other_income, 'total_recorded_income_cents': gross + other_income, 'total_cost_cents': total_cost, 'recorded_result_cents': gross + other_income - total_cost, 'purse_payments_recorded_cents': sum((r['purse_paid_cents'] or 0 for r in fighter_rows)), 'purse_payment_status_unknown': sum((r['purse_paid_cents'] is None for r in fighter_rows)), 'remaining_recorded_purses_cents': sum((r['remaining_purse_cents'] for r in fighter_rows if r['purse_paid_cents'] is not None)), 'unreconciled_purse_obligations_cents': sum((r['net_obligation_cents'] for r in fighter_rows if r['purse_paid_cents'] is None)), 'commission_payments_recorded_cents': sum((r['commission_paid_cents'] or 0 for r in seller_rows)), 'remaining_commissions_cents': sum((r['remaining_cents'] for r in seller_rows)), 'commission_payment_status_unknown': sum((r['commission_paid_cents'] is None and r['commission_earned_cents'] > 0 for r in seller_rows))}
    summary['purses_on_hold']=sum(r['purse_status']=='on_hold' for r in fighter_rows)
    summary['purses_fully_paid']=sum(r['purse_status'] in ('paid','overpaid') for r in fighter_rows)
    summary['commissions_fully_paid']=sum(r['commission_status'] in ('paid','overpaid') for r in seller_rows)
    return {'roster_scope': 'current_bout_card', 'current_bout_ids': [b.id for b in active], 'event': {'id': event.id, 'name': event.name, 'date': event.event_date, 'status': event.status}, 'summary': summary, 'fighters': fighter_rows, 'sellers': seller_rows, 'expenses': fee_rows, 'other_income': income_rows, 'warnings': sorted(issues), 'provisional': bool(issues), 'generated_at': datetime.now(timezone.utc).isoformat(), 'basis': 'Fighter breakdown and purse totals use only fighters on the current bout card. Off-card purse records are excluded and retained in payment history. Ticket revenue, seller commissions and other event costs remain event-wide. Recorded paid ticket subtotals + PAID sponsor/vendor receipts + attributed Clover concessions/bar sales − net purse/allowance obligations (or higher recorded payments) − earned seller commissions (or higher recorded payments) − state assessment − other actual expenses. Pending sales, customer fees, textual estimates and unreconciled partial refunds are not included. This is not a bank balance or proof that an unrecorded payment is unpaid.'}

@router.get('/{event_id}/recap')
def get_recap(event_id: int, response: Response, db=Depends(get_db), user=Depends(staff_user)):
    response.headers['Cache-Control'] = 'private, no-store'
    return recap(db, event_id)

@router.get('/recaps')
def event_recaps(response: Response, limit: int=Query(20, ge=1, le=50), offset: int=Query(0, ge=0), db=Depends(get_db), user=Depends(staff_user)):
    response.headers['Cache-Control'] = 'private, no-store'
    events = db.query(BoxingEvent).order_by(BoxingEvent.event_date.desc(), BoxingEvent.id.desc())
    total = events.count()
    data = []
    for e in events.offset(offset).limit(limit):
        d = recap(db, e.id)
        data.append({'event': d['event'], 'summary': d['summary'], 'provisional': d['provisional']})
    return {'events': data, 'total': total, 'limit': limit, 'offset': offset}

class PaymentBody(BaseModel):
    amount_paid: Decimal = Field(ge=0, max_digits=9, decimal_places=2)
    paid_date: date | None = None
    notes: str = Field(default='', max_length=1000)

    @field_validator('paid_date')
    @classmethod
    def not_future(cls, v):
        if v and v > datetime.now(CT).date():
            raise ValueError('Record only payments already made; paid date cannot be in the future')
        return v

class PurseBody(PaymentBody):
    version: int = Field(default=0, ge=0)

class CommissionBody(PaymentBody):
    previous_id: int | None = Field(default=None, ge=1)

@router.put('/{event_id}/recap/purses/{fighter_id}')
def record_purse(event_id: int, fighter_id: int, body: PurseBody, db=Depends(get_db), user=Depends(staff_user)):
    event_for(db, event_id, True)
    participants = {f for b in db.query(BoxingBout).filter_by(event_id=event_id) if str(b.status or '').strip().lower() not in CANCELLED for f in [b.red_fighter_id, b.blue_fighter_id]}
    row = db.query(EventPursePayment).filter_by(event_id=event_id, fighter_id=fighter_id).first()
    if fighter_id not in participants:
        raise HTTPException(409, 'Fighter is not on the current bout card. Saved payment history is retained; refresh the recap.')
    version = row.version if row else 0
    if body.version != version:
        raise HTTPException(409, 'Purse payment record changed. Refresh before saving.')
    before = row.amount_paid_cents if row else None
    if row and not db.query(EventPaymentChange).filter_by(event_id=event_id,kind='purse',target_id=fighter_id).first():
        db.add(EventPaymentChange(event_id=event_id,kind='purse',target_id=fighter_id,source_id=row.id,amount_paid_cents=row.amount_paid_cents,paid_date=row.paid_date,notes=row.notes,baseline=1,recorded_by=row.updated_by,recorded_at=row.updated_at))

    if not row:
        row = EventPursePayment(event_id=event_id, fighter_id=fighter_id, updated_by=user.id)
        db.add(row)
    row.amount_paid_cents = int(body.amount_paid * 100)
    row.paid_date = body.paid_date.isoformat() if body.paid_date else None
    row.notes = body.notes.strip()
    row.version = version + 1
    row.updated_by = user.id
    row.updated_at = datetime.utcnow()
    db.add(EventPaymentChange(event_id=event_id,kind='purse',target_id=fighter_id,amount_paid_cents=row.amount_paid_cents,paid_date=row.paid_date,notes=row.notes,recorded_by=user.id))
    db.add(SecurityLog(user_id=user.id, action='EVENT_PURSE_PAYMENT_RECORDED', description=json.dumps({'event_id': event_id, 'fighter_id': fighter_id, 'previous_cents': before, 'paid_to_date_cents': row.amount_paid_cents, 'no_money_transferred': True}), success=True))
    db.commit()
    return {'version': row.version, 'no_money_transferred': True}

@router.put('/{event_id}/recap/commissions/{seller_id}')
def record_commission(event_id: int, seller_id: int, body: CommissionBody, db=Depends(get_db), user=Depends(staff_user)):
    event_for(db, event_id, True)
    seller = db.query(EventSeller).filter_by(id=seller_id, event_id=event_id).first()
    if not seller:
        raise HTTPException(404, 'Seller not found for this event')
    latest = db.query(SellerPayout).filter_by(event_id=event_id, seller_id=seller_id).order_by(SellerPayout.created_at.desc(), SellerPayout.id.desc()).first()
    if body.previous_id != (latest.id if latest else None):
        raise HTTPException(409, 'Commission payment record changed. Refresh before saving.')
    data = recap(db, event_id)
    totals = next((r for r in data['sellers'] if r['seller_id'] == seller_id))
    amount = int(body.amount_paid * 100)
    paid_at = datetime.combine(body.paid_date, time.min, CT).astimezone(timezone.utc).replace(tzinfo=None) if body.paid_date else None
    row = SellerPayout(event_id=event_id, seller_id=seller_id, gross_sales_cents=totals['ticket_sales_cents'], commission_earned_cents=totals['commission_earned_cents'], amount_paid_cents=amount, status='paid' if amount >= totals['commission_earned_cents'] else 'partial' if amount else 'unpaid', paid_at=paid_at, notes=body.notes.strip())
    db.add(row)
    db.flush()
    db.add(EventPaymentChange(event_id=event_id,kind='commission',target_id=seller_id,source_id=row.id,amount_paid_cents=amount,paid_date=body.paid_date.isoformat() if body.paid_date else None,notes=row.notes,recorded_by=user.id))
    db.add(SecurityLog(user_id=user.id, action='EVENT_COMMISSION_PAYMENT_RECORDED', description=json.dumps({'event_id': event_id, 'seller_id': seller_id, 'previous_snapshot_id': body.previous_id, 'snapshot_id': row.id, 'paid_to_date_cents': amount, 'no_money_transferred': True}), success=True))
    db.commit()
    return {'payout_id': row.id, 'no_money_transferred': True}

class HoldBody(BaseModel):
    active: bool
    reason: str=Field(default='',max_length=1000)
    version: int=Field(default=0,ge=0)

@router.put('/{event_id}/recap/purses/{fighter_id}/hold')
def set_purse_hold(event_id:int,fighter_id:int,body:HoldBody,db=Depends(get_db),user=Depends(staff_user)):
    event_for(db,event_id,True)
    participants={fid for b in db.query(BoxingBout).filter_by(event_id=event_id) if str(b.status or '').strip().lower() not in CANCELLED for fid in (b.red_fighter_id,b.blue_fighter_id)}
    if fighter_id not in participants:raise HTTPException(409,'Fighter is not on the current bout card')
    if body.active and not body.reason.strip():raise HTTPException(422,'Enter the reason this purse is being held')
    row=db.query(EventPurseHold).filter_by(event_id=event_id,fighter_id=fighter_id).first()
    if body.version!=(row.version if row else 0):raise HTTPException(409,'Hold changed. Refresh before saving')
    if not row:row=EventPurseHold(event_id=event_id,fighter_id=fighter_id,updated_by=user.id,version=0);db.add(row)
    row.active=int(body.active);row.reason=body.reason.strip();row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow()
    db.add(EventPaymentChange(event_id=event_id,kind='hold',target_id=fighter_id,hold_active=int(body.active),notes=row.reason,recorded_by=user.id))
    db.add(SecurityLog(user_id=user.id,action='EVENT_PURSE_HOLD_UPDATED',description=json.dumps({'event_id':event_id,'fighter_id':fighter_id,'active':body.active,'reason':row.reason,'no_money_transferred':True}),success=True));db.commit()
    return {'version':row.version,'no_money_transferred':True}

@router.get('/{event_id}/recap/payment-history')
def payment_history(event_id:int,response:Response,kind:Literal['purse','commission'],target_id:int=Query(gt=0),db=Depends(get_db),user=Depends(staff_user)):
    event_for(db,event_id);response.headers['Cache-Control']='private, no-store'
    kinds=['purse','hold'] if kind=='purse' else ['commission']
    changes=db.query(EventPaymentChange).filter(EventPaymentChange.event_id==event_id,EventPaymentChange.target_id==target_id,EventPaymentChange.kind.in_(kinds)).order_by(EventPaymentChange.recorded_at.desc(),EventPaymentChange.id.desc()).limit(50).all()
    names={u.id:u.name for u in db.query(User).filter(User.id.in_([c.recorded_by for c in changes if c.recorded_by]))}
    rows=[]
    if kind=='commission':
        bysource={c.source_id:c for c in changes}
        for snap in db.query(SellerPayout).filter_by(event_id=event_id,seller_id=target_id).order_by(SellerPayout.created_at.desc(),SellerPayout.id.desc()).limit(50):
            c=bysource.get(snap.id);rows.append({'kind':'commission','paid_to_date_cents':snap.amount_paid_cents,'paid_date':snap.paid_at.replace(tzinfo=timezone.utc).astimezone(CT).date().isoformat() if snap.paid_at else None,'notes':snap.notes or '', 'recorded_at':snap.created_at.isoformat()+'Z','recorded_by':names.get(c.recorded_by) if c else None,'baseline':not bool(c)})
    else:
        for c in changes:
            rows.append({'kind':c.kind,'paid_to_date_cents':c.amount_paid_cents,'paid_date':c.paid_date,'notes':c.notes,'hold_active':bool(c.hold_active) if c.hold_active is not None else None,'recorded_at':c.recorded_at.isoformat()+'Z','recorded_by':names.get(c.recorded_by),'baseline':bool(c.baseline)})
        if not any(c.kind=='purse' for c in changes):
            legacy=db.query(EventPursePayment).filter_by(event_id=event_id,fighter_id=target_id).first()
            if legacy:rows.append({'kind':'purse','paid_to_date_cents':legacy.amount_paid_cents,'paid_date':legacy.paid_date,'notes':legacy.notes,'recorded_at':legacy.updated_at.isoformat()+'Z','recorded_by':None,'baseline':True})
        rows.sort(key=lambda r:r['recorded_at'],reverse=True)
    return {'records':rows[:50],'basis':'Cumulative payment record revisions, not separate transfers. Do not add these totals together. Recorded-on time is not the actual payment date.'}

class FeeBody(BaseModel):
    treatment: TREATMENTS
    version: int = Field(default=0, ge=0)

@router.put('/{event_id}/recap/expenses/{fee_id}')
def classify_fee(event_id: int, fee_id: int, body: FeeBody, db=Depends(get_db), user=Depends(staff_user)):
    event_for(db, event_id, True)
    if not db.query(BoxingEventFee.id).filter_by(id=fee_id, event_id=event_id).first():
        raise HTTPException(404, 'Expense not found')
    row = db.get(RecapFeeTreatment, fee_id)
    version = row.version if row else 0
    if body.version != version:
        raise HTTPException(409, 'Expense treatment changed. Refresh before saving.')
    if not row:
        row = RecapFeeTreatment(fee_id=fee_id, updated_by=user.id)
        db.add(row)
    row.treatment = body.treatment
    row.version = version + 1
    row.updated_by = user.id
    row.updated_at = datetime.utcnow()
    db.add(SecurityLog(user_id=user.id, action='EVENT_RECAP_EXPENSE_CLASSIFIED', description=f'Event {event_id}; expense {fee_id}; treatment {body.treatment}; original amount unchanged', success=True))
    db.commit()
    return {'version': row.version}

def export_sections(d):
    sections = [('Summary', ['Metric', 'USD / value'], [[k.removesuffix('_cents').replace('_', ' ').title(), ('' if v is None else format(v / 100, '.2f')) if k.endswith('_cents') else ('Not recorded' if v is None else str(v).replace('_', ' '))] for k, v in d['summary'].items()]), ('Fighters', ['Fighter', 'Ticket sales', 'Purse', 'Travel', 'Per diem', 'Deductions', 'Net obligation', 'Purse cost', 'Ticket commission cost', 'Contribution', 'Purse paid to date', 'Payment status'], [[r['name'], *[r[k] / 100 for k in ['ticket_sales_cents', 'gross_purse_cents', 'travel_cents', 'per_diem_cents', 'deductions_cents', 'net_obligation_cents', 'purse_cost_cents', 'commission_cost_cents', 'ticket_contribution_cents']], r['purse_paid_cents'] / 100 if r['purse_paid_cents'] is not None else '', 'Not recorded' if r['purse_paid_cents'] is None else 'Recorded'] for r in d['fighters']]), ('Ticket commissions', ['Seller', 'Sales', 'Earned', 'Paid to date', 'Remaining / unrecorded', 'Note'], [[r['name'], r['ticket_sales_cents'] / 100, r['commission_earned_cents'] / 100, r['commission_paid_cents'] / 100 if r['commission_paid_cents'] is not None else '', r['remaining_cents'] / 100, r['notes']] for r in d['sellers']]), ('Expenses', ['Name', 'Actual USD', 'Treatment', 'Marked paid'], [[r['name'], r['actual_cents'] / 100 if r['actual_cents'] is not None else '', r['treatment'], r['paid']] for r in d['expenses']]), ('Review notes', ['Notice'], [[w] for w in d['warnings']])]

    sections.append(('Payment status', ['Fighter','Purse status','Purse owed','Purse paid','Purse payment date','Hold reason','Commission status','Commission paid'], [[r['name'],r['purse_status'].replace('_',' '),format(r['net_obligation_cents']/100,'.2f'),'' if r['purse_paid_cents'] is None else format(r['purse_paid_cents']/100,'.2f'),r['purse_paid_date'] or '',r['purse_hold_reason'] if r['purse_on_hold'] else '',r['commission_status'].replace('_',' '),'' if r['commission_paid_cents'] is None else format(r['commission_paid_cents']/100,'.2f')] for r in d['fighters']]))
    return sections

@router.get('/{event_id}/recap.csv')
def export_csv(event_id: int, db=Depends(get_db), user=Depends(staff_user)):
    d = recap(db, event_id)
    out = io.StringIO()
    w = csv.writer(out)

    def safe(v):
        text = str(v)
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
    w.writerow([safe(v) for v in ['Event', d['event']['name'], 'Date', d['event']['date'], 'Generated UTC', d['generated_at']]])
    w.writerow(['Basis', d['basis']])
    w.writerow([])
    for title, head, rows in export_sections(d):
        w.writerow([title])
        w.writerow(head)
        w.writerows([[safe(v) for v in row] for row in rows])
        w.writerow([])
    return Response('\ufeff' + out.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="tng_event_{event_id}_recap.csv"', 'Cache-Control': 'private, no-store'})

@router.get('/{event_id}/recap.pdf')
def export_pdf(event_id: int, db=Depends(get_db), user=Depends(staff_user)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from html import escape
    d = recap(db, event_id)
    out = io.BytesIO()
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 8
    styles['BodyText'].leading = 11
    p = lambda text: Paragraph(escape(str(text)), styles['BodyText'])
    story = [Paragraph('TNG PROMOTIONS — EVENT RECAP', styles['Title']), p(d['event']['name'] + ' · ' + d['event']['date']), p('Recorded result: $' + format(d['summary']['recorded_result_cents'] / 100, ',.2f') + (' · PROVISIONAL / REVIEW REQUIRED' if d['provisional'] else ' · based on recorded amounts')), Spacer(1, 10), p(d['basis']), Spacer(1, 12)]
    sections = export_sections(d)
    fighters = [['Fighter', 'Sales', 'Net purse', 'Commission cost', 'Purse paid', 'Contribution']] + [[r['name'], *['$' + format(r[k] / 100, ',.2f') for k in ['ticket_sales_cents', 'net_obligation_cents', 'commission_cost_cents']], '$' + format(r['purse_paid_cents'] / 100, ',.2f') if r['purse_paid_cents'] is not None else 'Not recorded', '$' + format(r['ticket_contribution_cents'] / 100, ',.2f')] for r in d['fighters']]
    for title, head, rows in sections:
        raw = fighters if title == 'Fighters' else [head] + rows
        if not rows and title != 'Fighters':
            continue
        story.extend([Paragraph(title, styles['Heading2']), Spacer(1, 5)])
        table = Table([[p(v) for v in row] for row in raw], colWidths=[720 / len(raw[0])] * len(raw[0]), repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6e8ee')), ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#ccd0d7')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        story.extend([table, Spacer(1, 12)])
    SimpleDocTemplate(out, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=28, bottomMargin=28).build(story)
    return Response(out.getvalue(), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="tng_event_{event_id}_recap.pdf"', 'Cache-Control': 'private, no-store'})
