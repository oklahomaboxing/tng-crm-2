"""Explicit investor business grants and private aggregate management reporting."""
import json,math
from datetime import datetime,date,timezone
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,String,Text,Date,DateTime,Boolean,ForeignKey
from app.database import Base,get_db
from app.models import User,SecurityLog,Member,Sale,MembershipProduct,MerchandiseCheckout
from app.matchmaker.models import BoxingEvent,BoxingBout
from app.ticketing.models import TicketOrder,EventSeller
from app.revenue.models import EventRevenuePayment
from app.services.member_reporting import membership_evidence,membership_totals,membership_report
from app.services.memberships import is_membership_product,is_ticket_purchase_name
from .recap import recap,CANCELLED
from app.core.dependencies import current_user
router=APIRouter(prefix='/api/partners/business-admin',tags=['Investor business access'])
CT=ZoneInfo('America/Chicago')
CATEGORIES=['gym_rent','utilities','staffing','marketing','equipment','apparel_cost','concessions_cost','insurance','other_expense','other_income']
class InvestorBusinessAccess(Base):
 __tablename__='investor_business_access'
 user_id=Column(Integer,ForeignKey('users.id'),primary_key=True)
 enabled=Column(Boolean,default=False,nullable=False)
 version=Column(Integer,default=1,nullable=False)
 updated_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)
class BusinessLedgerEntry(Base):
 __tablename__='investor_business_ledger'
 id=Column(Integer,primary_key=True)
 request_key=Column(String(100),unique=True,nullable=False)
 kind=Column(String(10),nullable=False)
 category=Column(String(40),nullable=False)
 title=Column(String(160),nullable=False)
 amount_cents=Column(Integer,nullable=False)
 occurred_on=Column(Date,nullable=False)
 basis=Column(String(20),default='paid',nullable=False)
 source_reference=Column(String(120),unique=True,nullable=True)
 private_note=Column(Text,default='',nullable=False)
 active=Column(Boolean,default=True,nullable=False)
 version=Column(Integer,default=1,nullable=False)
 updated_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)
class InvestorUpdate(Base):
 __tablename__='investor_business_updates'
 id=Column(Integer,primary_key=True)
 title=Column(String(160),nullable=False)
 body=Column(Text,nullable=False)
 published=Column(Boolean,default=False,nullable=False)
 version=Column(Integer,default=1,nullable=False)
 updated_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def admin(user=Depends(current_user)):
 if user.role!='admin':raise HTTPException(403,'Administrator access required')
 return user

def money(value,review):
 try:
  d=Decimal(str(value or 0))
  if not d.is_finite() or d<0:raise ValueError()
  return int((d*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
 except (InvalidOperation,ValueError,TypeError):review['invalid_amounts']+=1;return 0

def day(value):
 if isinstance(value,datetime):return value.replace(tzinfo=timezone.utc).astimezone(CT).date() if value.tzinfo is None else value.astimezone(CT).date()
 if isinstance(value,date):return value
 try:return date.fromisoformat((value or '')[:10])
 except (ValueError,TypeError):return None

def allowed_date(d,period,now):return period=='all' or bool(d and d.year==now.year and (period=='year' or d.month==now.month))

def safe_event(db,event):
 r=recap(db,event.id);fields=['pos_snapshot_imported','pos_snapshot_imported_at','ticket_sales_cents','concessions_sales_cents','bar_sales_cents','paid_ticket_quantity','total_recorded_income_cents','other_income_cents','purse_cost_cents','commission_cost_cents','state_assessment_cents','state_assessment_required_cents','state_assessment_recorded_cents','other_expenses_cents','total_cost_cents','recorded_result_cents','purse_payments_recorded_cents','commission_payments_recorded_cents','unconfirmed_orders','paid_orders','assessment_basis']
 fighter_fields=['fighter_id','name','ticket_quantity','ticket_sales_cents','gross_purse_cents','travel_cents','per_diem_cents','deductions_cents','net_obligation_cents','purse_cost_cents','purse_paid_cents','purse_status','commission_earned_cents','commission_cost_cents','commission_paid_cents','commission_status','total_fighter_cost_cents','ticket_contribution_cents']
 fighters=[{k:f[k] for k in fighter_fields} for f in r['fighters']];by_id={f['fighter_id']:f for f in fighters};sellers=[]
 source_sellers={s.id:s for s in db.query(EventSeller).filter_by(event_id=event.id)}
 for s in r['sellers']:
  source=source_sellers.get(s['seller_id'])
  sellers.append({k:s[k] for k in ('name','ticket_quantity','ticket_sales_cents','commission_earned_cents','commission_paid_cents','commission_status')}|{'fighter_id':source.seller_ref_id if source and source.seller_type=='fighter' else None,'on_current_card':bool(source and source.seller_type=='fighter' and source.seller_ref_id in by_id)})
 bouts=db.query(BoxingBout).filter_by(event_id=event.id).order_by(BoxingBout.bout_order,BoxingBout.id).all();bouts=[b for b in bouts if str(b.status or '').lower() not in CANCELLED];counts={}
 for b in bouts:
  for fid in (b.red_fighter_id,b.blue_fighter_id):counts[fid]=counts.get(fid,0)+1
 bout_rows=[]
 for b in bouts:
  red,blue=by_id.get(b.red_fighter_id),by_id.get(b.blue_fighter_id);complete=bool(red and blue and counts[b.red_fighter_id]==1 and counts[b.blue_fighter_id]==1);cost=(red['total_fighter_cost_cents']+blue['total_fighter_cost_cents']) if complete else None;sales=sum(f['ticket_sales_cents'] for f in (red,blue) if f)
  bout_rows.append({'bout_id':b.id,'bout_order':b.bout_order,'red_name':red['name'] if red else 'Not recorded','blue_name':blue['name'] if blue else 'Not recorded','red_direct_cost_cents':red['total_fighter_cost_cents'] if complete else None,'blue_direct_cost_cents':blue['total_fighter_cost_cents'] if complete else None,'combined_bout_cost_cents':cost,'combined_ticket_sales_cents':sales,'bout_contribution_cents':sales-cost if cost is not None else None,'needs_allocation':not complete})
 return {'id':event.id,'name':event.name,'date':event.event_date,'status':event.status,'venue':event.venue,'summary':{k:r['summary'][k] for k in fields},'fighters':fighters,'sellers':sellers,'bouts':bout_rows,'expenses':[{'name':f['name'],'actual_cents':f['actual_cents'],'paid':f['paid'],'treatment':f['treatment']} for f in r['expenses']],'provisional':r['provisional'],'review_notice':'Costs include recorded purse/allowance obligations or higher recorded payments, earned ticket commissions, state assessment and actual shared event expenses. Missing costs or unsigned terms can change the result.','bout_basis':'Both red and blue corners’ direct costs, before shared venue, officials, insurance and other event overhead. Shared-fighter costs across multiple bouts require allocation; they are not counted twice.'}

def overview(db,period='all',now=None):
 now=now or datetime.now(timezone.utc);today=now.astimezone(CT).date();review={k:0 for k in ('invalid_amounts','duplicate_ledger_rows','cross_source_sales_excluded','partial_refunds','pending_ticket_orders','unlinked_pos_ticket_sales','unknown_sale_refunds','missing_event_dates','event_costs_need_review','merchandise_receipts_without_ledger','overhead_entries_missing')}
 members=db.query(Member).all();evidence=membership_evidence(db);counts=membership_totals(members,evidence,now.replace(tzinfo=None));plans={}
 for m in members:
  if membership_report(m,evidence,now.replace(tzinfo=None))['is_current_member']:
   name=m.membership_type or 'Membership plan';plans[name]=plans.get(name,0)+1
 events=db.query(BoxingEvent).order_by(BoxingEvent.event_date.desc(),BoxingEvent.id.desc()).all();selected=[e for e in events if allowed_date(day(e.event_date),period,today)];selected_ids={e.id for e in selected};event_details=[safe_event(db,e) for e in selected];categories={k:0 for k in ('memberships','registration','retail_apparel','concessions','bar','other_pos','event_tickets','sponsor_vendor','other_recorded')};timeline={};membership_sales={};seen=set();membership_transactions=0
 def add(category,value,d,expense=False):
  if not expense:categories[category]+=value
  if d:
   key=d.strftime('%Y-%m');bucket=timeline.setdefault(key,{'income_cents':0,'cost_cents':0});bucket['cost_cents' if expense else 'income_cents']+=value
 all_tickets=db.query(TicketOrder).all();ticket_payrefs={o.payment_id for o in all_tickets if o.payment_id and o.payment_status in ('paid','refunded','partial_refund')};ticket_checkouts={o.clover_checkout_id for o in all_tickets if o.clover_checkout_id and o.payment_status in ('paid','refunded','partial_refund')};event_dates={e.id:day(e.event_date) for e in events}
 for o in all_tickets:
  if o.event_id not in selected_ids:continue
  if o.payment_status in ('pending','failed'):review['pending_ticket_orders']+=1
  if o.payment_status=='partial_refund':review['partial_refunds']+=1
  if o.payment_status!='paid':continue
  reference=o.payment_id or ''
  if reference and reference in seen:review['duplicate_ledger_rows']+=1;continue
  if reference:seen.add(reference)
  add('event_tickets',max(0,int(o.subtotal_cents or 0)),event_dates.get(o.event_id))
 revenue=db.query(EventRevenuePayment).all();rev_refs={p.provider_payment_id for p in revenue if p.provider_payment_id and str(p.status).upper() in ('PAID','PARTIAL','REFUNDED')}
 for p in revenue:
  if p.event_id not in selected_ids or str(p.status).upper()!='PAID':continue
  ref=p.provider_payment_id or ''
  if ref and (ref in ticket_payrefs or ref in seen):review['duplicate_ledger_rows']+=1;continue
  if ref:seen.add(ref)
  add('sponsor_vendor',money(p.amount,review),event_dates.get(p.event_id))
 from .concessions_finance import pos_revenue,pos_references,suggest
 pos_order_refs=set();fully_covered_pos_orders=set()
 for e in events:
  pos_order_refs.update(pos_references(db,e.id));fully_covered_pos_orders.update(pos_references(db,e.id,True))
  if e.id in selected_ids:
   for category,value in pos_revenue(db,e.id).items():add(category,value,event_dates.get(e.id))
 products={p.id:p for p in db.query(MembershipProduct)};sale_refs=set();merch={m.clover_checkout_id:m for m in db.query(MerchandiseCheckout) if m.clover_checkout_id}
 for sale in db.query(Sale).order_by(Sale.id):
  d=day(sale.sale_date)
  product=products.get(sale.product_id)
  if sale.clover_order_id in fully_covered_pos_orders or (sale.clover_order_id in pos_order_refs and product and (suggest(product.name) in ('concessions','bar') or str(product.category or '').lower() in ('concessions','food','bar','beverage','alcohol'))):review['cross_source_sales_excluded']+=1;continue
  if not allowed_date(d,period,today) or sale.payment_status!='paid':continue
  if (sale.clover_payment_id and (sale.clover_payment_id in ticket_payrefs or sale.clover_payment_id in rev_refs)) or (sale.clover_checkout_id and sale.clover_checkout_id in ticket_checkouts):review['cross_source_sales_excluded']+=1;continue
  parent=merch.get(sale.clover_checkout_id)
  if parent and parent.status!='paid':review['unknown_sale_refunds']+=1;continue
  amount=money(sale.amount,review);refund=money(sale.refund_amount,review)
  if (sale.refunded or str(sale.transaction_status).lower() in ('refunded','partial_refund')) and not refund:review['unknown_sale_refunds']+=1;continue
  amount=max(0,amount-refund)
  if not amount:continue
  signature=(sale.clover_payment_id,sale.product_id,money(sale.amount,review),sale.quantity)
  if sale.clover_payment_id and signature in sale_refs:review['duplicate_ledger_rows']+=1;continue
  if sale.clover_payment_id:sale_refs.add(signature)
  product=products.get(sale.product_id);category=(product.category or '').casefold() if product else '';name=product.name if product else ''
  if is_membership_product(product):
   category='memberships';membership_transactions+=1;membership_sales[name]=membership_sales.get(name,0)+amount
  elif is_ticket_purchase_name(name) or category in ('event','tickets','ticket'):
   category='event_tickets';review['unlinked_pos_ticket_sales']+=1
  elif category=='registration' or sale.sale_type=='registration':category='registration'
  elif category in ('merchandise','apparel','retail'):category='retail_apparel'
  elif category in ('concessions','food','beverage'):category='concessions'
  else:category='other_pos'
  add(category,amount,d)
 # Paid merchandise callbacks normally create Sale rows. Count a receipt fallback only
 # when no paid ledger row exists anywhere, so checkout mirrors are not counted twice.
 paid_sales=db.query(Sale).filter_by(payment_status='paid').all()
 for checkout in merch.values():
  d=day(checkout.paid_at or checkout.created_at)
  if checkout.status!='paid' or not allowed_date(d,period,today):continue
  if checkout.clover_payment_id in ticket_payrefs or checkout.clover_payment_id in rev_refs:continue
  if any(s.clover_checkout_id==checkout.clover_checkout_id or (checkout.clover_payment_id and s.clover_payment_id==checkout.clover_payment_id) for s in paid_sales):continue
  ref=checkout.clover_payment_id or ''
  if ref and ref in seen:review['duplicate_ledger_rows']+=1;continue
  if ref:seen.add(ref)
  review['merchandise_receipts_without_ledger']+=1;add('retail_apparel',money(checkout.total_amount,review),d)
 event_cost=sum(e['summary']['total_cost_cents'] for e in event_details)
 for e in event_details:
  if e['provisional']:review['event_costs_need_review']+=1
  d=day(e['date'])
  if not d:review['missing_event_dates']+=1
  add('',e['summary']['total_cost_cents'],d,True)
 ledger_rows=[];overhead=0
 for row in db.query(BusinessLedgerEntry).filter_by(active=True).order_by(BusinessLedgerEntry.occurred_on.desc(),BusinessLedgerEntry.id.desc()):
  if not allowed_date(row.occurred_on,period,today):continue
  if row.kind=='income':add('other_recorded',row.amount_cents,row.occurred_on)
  else:overhead+=row.amount_cents;add('',row.amount_cents,row.occurred_on,True)
  ledger_rows.append({'id':row.id,'kind':row.kind,'title':row.title,'category':row.category,'amount_cents':row.amount_cents,'date':row.occurred_on.isoformat(),'basis':row.basis})
 review['overhead_entries_missing']=int(not any(r['kind']=='expense' for r in ledger_rows))
 total=sum(categories.values());cost=event_cost+overhead;updates=[{'id':u.id,'title':u.title,'body':u.body,'updated_at':u.updated_at.isoformat()+'Z'} for u in db.query(InvestorUpdate).filter_by(published=True).order_by(InvestorUpdate.updated_at.desc()).limit(20)]
 return {'period':period,'generated_at':now.isoformat(),'as_of':today.isoformat(),'membership_counts':{k:counts[k] for k in ('members','active','expiring','expired','inactive','review')},'membership_plans':[{'name':k,'active_members':v} for k,v in sorted(plans.items())],'membership_sales':[{'name':k,'income_cents':v} for k,v in sorted(membership_sales.items())],'membership_transactions':membership_transactions,'income_categories':categories,'summary':{'recorded_income_cents':total,'recorded_event_costs_cents':event_cost,'recorded_overhead_cents':overhead,'total_costs_and_obligations_cents':cost,'recorded_contribution_cents':total-cost},'events':event_details,'other_ledger':ledger_rows,'timeline':[{'month':k,**v} for k,v in sorted(timeline.items())][-12:],'updates':updates,'review_counts':review,'provisional':any(review.values()),'basis':'Management view, not a bank balance, audited profit or investment return. Event income/costs are assigned to event dates; gym/retail sales to sale dates; other entries to their recorded dates. Membership counts are current as of today. Only recorded paid income is counted. Pending orders, customer ticket fees and unresolved partial refunds are excluded. Event costs include obligations and estimated assessment where actual amounts are missing. Identical payment/product/amount/quantity ledger rows and cross-source payment references are de-duplicated; mixed orders may need review. No unrecorded rent, payroll, food stock, tax, processor fees or other costs are invented.'}

class AccessBody(BaseModel):enabled:bool;version:int=Field(ge=0)
class LedgerBody(BaseModel):
 kind:Literal['income','expense']
 category:str=Field(min_length=2,max_length=40)
 title:str=Field(min_length=2,max_length=160)
 amount_cents:int=Field(gt=0,le=100000000000)
 occurred_on:date
 basis:Literal['paid','obligation']='paid'
 source_reference:str=Field(default='',max_length=120)
 private_note:str=Field(default='',max_length=4000)
 request_key:str=Field(min_length=16,max_length=80)
 active:bool=True
 version:int|None=None
class UpdateBody(BaseModel):title:str=Field(min_length=2,max_length=160);body:str=Field(min_length=2,max_length=8000);published:bool=False;version:int|None=None

def ledger_dict(r):return {k:getattr(r,k) for k in ('id','kind','category','title','amount_cents','basis','source_reference','private_note','active','version')}|{'occurred_on':r.occurred_on.isoformat()}
def audit(db,u,action,description):db.add(SecurityLog(user_id=u.id,action='INVESTOR_'+action,description=description))
@router.get('')
def admin_view(response:Response,db=Depends(get_db),user=Depends(admin)):
 response.headers['Cache-Control']='private, no-store';grants={g.user_id:g for g in db.query(InvestorBusinessAccess)}
 return {'investors':[{'id':u.id,'name':u.name,'active':u.active,'enabled':grants[u.id].enabled if u.id in grants else False,'version':grants[u.id].version if u.id in grants else 0} for u in db.query(User).filter_by(role='investor').order_by(User.name)],'ledger':[ledger_dict(r) for r in db.query(BusinessLedgerEntry).order_by(BusinessLedgerEntry.occurred_on.desc()).limit(200)],'updates':[{'id':u.id,'title':u.title,'body':u.body,'published':u.published,'version':u.version} for u in db.query(InvestorUpdate).order_by(InvestorUpdate.id.desc()).limit(100)],'categories':CATEGORIES}
@router.get('/overview')
def preview_overview(response:Response,period:Literal['all','month','year']='all',db=Depends(get_db),user=Depends(admin)):
 response.headers['Cache-Control']='private, no-store';return overview(db,period)
@router.put('/access/{investor_id}')
def grant(investor_id:int,body:AccessBody,db=Depends(get_db),user=Depends(admin)):
 target=db.query(User).filter_by(id=investor_id).with_for_update().first()
 if not target or target.role!='investor':raise HTTPException(422,'Choose an investor account')
 row=db.get(InvestorBusinessAccess,investor_id)
 if (row.version if row else 0)!=body.version:raise HTTPException(409,'Access changed. Refresh before saving')
 if not row:row=InvestorBusinessAccess(user_id=investor_id,version=0,updated_by=user.id);db.add(row)
 row.enabled=body.enabled;row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow();audit(db,user,'BUSINESS_ACCESS_UPDATED',f'Investor {investor_id}; full aggregate business access {row.enabled}');db.commit();return {'saved':True}
@router.post('/ledger')
def record_ledger(body:LedgerBody,db=Depends(get_db),user=Depends(admin)):
 if body.category not in CATEGORIES or (body.kind=='expense' and body.category=='other_income') or (body.kind=='income' and body.category!='other_income') or (body.kind=='income' and body.basis!='paid'):raise HTTPException(422,'Use paid Other income for money not already in sales, or a recorded expense category')
 request_key=str(user.id)+':'+body.request_key
 # Admin row serializes idempotency and reference checks across workers.
 db.query(User).filter_by(id=user.id).with_for_update().first();old=db.query(BusinessLedgerEntry).filter_by(request_key=request_key).first();values=body.model_dump(exclude={'request_key','version'});values['title']=body.title.strip();values['source_reference']=body.source_reference.strip() or None
 if old:
  if any(getattr(old,k)!=v for k,v in values.items()):raise HTTPException(409,'This save key belongs to another entry')
  return {'saved':True,'id':old.id,'existing':True}
 if body.kind=='income' and values['source_reference'] and (db.query(Sale).filter_by(clover_payment_id=values['source_reference']).first() or db.query(TicketOrder).filter_by(payment_id=values['source_reference']).first() or db.query(EventRevenuePayment).filter_by(provider_payment_id=values['source_reference']).first()):raise HTTPException(409,'That payment reference already appears in a revenue source. Do not record the same income twice')
 if values['source_reference'] and db.query(BusinessLedgerEntry).filter_by(source_reference=values['source_reference']).first():raise HTTPException(409,'That source reference is already recorded. Review the existing entry')
 row=BusinessLedgerEntry(**values,request_key=request_key,updated_by=user.id);db.add(row);db.flush();audit(db,user,'LEDGER_RECORDED',f'Entry {row.id}; {row.kind}; {row.amount_cents} cents; {row.occurred_on}');db.commit();return {'saved':True,'id':row.id}
@router.put('/ledger/{entry_id}')
def edit_ledger(entry_id:int,body:LedgerBody,db=Depends(get_db),user=Depends(admin)):
 row=db.query(BusinessLedgerEntry).filter_by(id=entry_id).with_for_update().first()
 if not row:raise HTTPException(404,'Entry not found')
 if row.version!=body.version:raise HTTPException(409,'Entry changed. Refresh before saving')
 if body.category not in CATEGORIES or (body.kind=='expense' and body.category=='other_income') or (body.kind=='income' and (body.category!='other_income' or body.basis!='paid')):raise HTTPException(422,'Choose a recorded expense or paid Other income')
 reference=body.source_reference.strip() or None
 if body.kind=='income' and reference and (db.query(Sale).filter_by(clover_payment_id=reference).first() or db.query(TicketOrder).filter_by(payment_id=reference).first() or db.query(EventRevenuePayment).filter_by(provider_payment_id=reference).first()):raise HTTPException(409,'That payment reference already appears in a revenue source. Do not record the same income twice')
 if reference and db.query(BusinessLedgerEntry).filter(BusinessLedgerEntry.source_reference==reference,BusinessLedgerEntry.id!=row.id).first():raise HTTPException(409,'That source reference already exists')
 before=row.amount_cents
 for k,v in body.model_dump(exclude={'request_key','version'}).items():setattr(row,k,v)
 row.title=row.title.strip();row.source_reference=reference;row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow();audit(db,user,'LEDGER_UPDATED',f'Entry {row.id}; {before} to {row.amount_cents} cents; active {row.active}');db.commit();return {'saved':True}
@router.delete('/ledger/{entry_id}')
def remove_ledger(entry_id:int,version:int,db=Depends(get_db),user=Depends(admin)):
 row=db.query(BusinessLedgerEntry).filter_by(id=entry_id).with_for_update().first()
 if not row:raise HTTPException(404,'Entry not found')
 if row.version!=version:raise HTTPException(409,'Entry changed. Refresh before removing')
 row.active=False;row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow();audit(db,user,'LEDGER_REMOVED',f'Entry {row.id}; prior {row.amount_cents} cents; history retained');db.commit();return {'saved':True}
@router.post('/updates')
def publish(body:UpdateBody,db=Depends(get_db),user=Depends(admin)):
 if not body.title.strip() or not body.body.strip():raise HTTPException(422,'Enter an update title and message')
 row=InvestorUpdate(title=body.title.strip(),body=body.body.strip(),published=body.published,updated_by=user.id);db.add(row);db.flush();audit(db,user,'UPDATE_PUBLISHED' if body.published else 'UPDATE_DRAFTED',f'Business update {row.id}');db.commit();return {'saved':True,'id':row.id}
@router.put('/updates/{update_id}')
def edit_update(update_id:int,body:UpdateBody,db=Depends(get_db),user=Depends(admin)):
 row=db.query(InvestorUpdate).filter_by(id=update_id).with_for_update().first()
 if not row:raise HTTPException(404,'Update not found')
 if row.version!=body.version:raise HTTPException(409,'Update changed. Refresh before saving')
 row.title=body.title.strip();row.body=body.body.strip();row.published=body.published;row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow();audit(db,user,'UPDATE_EDITED',f'Business update {row.id}; published {row.published}');db.commit();return {'saved':True}
