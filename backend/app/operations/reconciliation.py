"""Read-only review of recorded payments and the access they should fulfill."""
from datetime import datetime
from fastapi import APIRouter,Depends,Response
from sqlalchemy import func
from app.database import get_db
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.models import Member
from app.member_portal.models import MemberAccount
from app.services.memberships import is_ticket_purchase_name
from app.services.member_reporting import membership_evidence,has_member_identity
from app.services.portal_accounts import eligible
from app.ticketing.models import TicketOrder,IssuedTicket,TicketDelivery
from app.operations.overview import expected_quantity

router=APIRouter(prefix='/api/operations',tags=['Payment reconciliation'])

@router.get('/reconciliation')
def reconciliation(response:Response,db=Depends(get_db),user=Depends(current_user)):
    require_admin(user);response.headers['Cache-Control']='private, no-store'
    counts=dict(db.query(IssuedTicket.order_id,func.count(IssuedTicket.id)).filter(IssuedTicket.status.in_(['valid','used'])).group_by(IssuedTicket.order_id).all())
    failures={i for (i,) in db.query(TicketDelivery.order_id).filter(TicketDelivery.status.in_(['failed','undelivered'])).distinct().all()}
    paid=db.query(TicketOrder).filter_by(payment_status='paid').order_by(TicketOrder.id.desc()).all()
    issues=[]
    for order in paid:
        expected=expected_quantity(order.items_json);issued=counts.get(order.id,0)
        if expected is None or issued<expected:
            issues.append({'key':f'issuance-{order.id}','kind':'ticket_issuance','severity':'error','title':'Paid order needs ticket review','reference':order.receipt_number or f'Order #{order.id}',
                'detail':f'{issued} valid/used tickets; '+(f'{expected} purchased.' if expected is not None else 'purchased quantity needs review.'),'page':'TNG BOXING EVENTS','target':{'eventId':order.event_id}})
        if order.id in failures:
            issues.append({'key':f'delivery-{order.id}','kind':'ticket_delivery','severity':'warning','title':'Paid ticket delivery failed','reference':order.receipt_number or f'Order #{order.id}',
                'detail':'Review delivery history and contact details before resending.','page':'TNG BOXING EVENTS','target':{'eventId':order.event_id}})
    paid_members=membership_evidence(db);accounts={a.member_id for a in db.query(MemberAccount).all()}
    for member in db.query(Member).order_by(Member.id).all():
        recorded=member.id in paid_members or bool(member.member_type=='MEMBER' and member.membership_start and member.membership_end and not is_ticket_purchase_name(member.membership_type))
        if recorded and not has_member_identity(member):
            issues.append({'key':f'identity-{member.id}','kind':'member_identity','severity':'warning','title':'Gym record needs a name and email','reference':f'Profile #{member.id}',
                'detail':'Excluded from gym membership totals until its identity is complete. Existing records are retained.','page':'Members','target':{'memberId':member.id}})
        elif member.id in paid_members and (not member.membership_start or not member.membership_end):
            issues.append({'key':f'term-{member.id}','kind':'membership_term','severity':'warning','title':'Recorded membership payment needs term review','reference':f'Profile #{member.id}',
                'detail':'Review the actual product and payment before assigning dates. No membership time is added here.','page':'Members','target':{'memberId':member.id}})
        if recorded and eligible(member) and member.id not in accounts:
            issues.append({'key':f'access-{member.id}','kind':'portal_access','severity':'info','title':'Gym profile has no linked portal account','reference':f'Profile #{member.id}',
                'detail':'Review matching accounts or use Connect Customer Accounts. No invitation is sent here.','page':'Members','target':{'memberId':member.id}})
    issues.sort(key=lambda i:({'error':0,'warning':1,'info':2}[i['severity']],i['key']))
    return {'generated_at':datetime.utcnow().isoformat()+'Z','read_only':True,'provider_checks_performed':False,
        'summary':{'paid_ticket_orders':len(paid),'pending_checkouts':db.query(TicketOrder).filter_by(payment_status='pending').count(),'review_items':len(issues),
            'urgent_items':sum(i['severity']=='error' for i in issues),'membership_items':sum(i['kind'] in ('member_identity','membership_term','portal_access') for i in issues)},
        'issues':issues[:150],'total_issues':len(issues),'limit':150}
