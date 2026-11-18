"""Event POS snapshots and source-linked operating expenses; no Clover writes."""
import csv,io,json,os,re,time,uuid
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_HALF_UP,InvalidOperation
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
import requests
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from typing import Literal
from sqlalchemy import Column,Integer,Text,DateTime,ForeignKey,text
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent,BoxingEventFee
router=APIRouter(prefix='/api/concessions/events',tags=['Event concessions financials'])
CT=ZoneInfo('America/Chicago')
Channel=Literal['concessions','bar','event','review','exclude']
class EventPosSnapshot(Base):
 __tablename__='event_pos_financial_snapshots'
 event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
 source_json=Column(Text,default='{}',nullable=False)
 settings_json=Column(Text,default='{}',nullable=False)
 version=Column(Integer,default=0,nullable=False)
 imported_at=Column(DateTime,nullable=True)
class SyncBody(BaseModel):
 start_local:str=Field(max_length=30)
 end_local:str=Field(max_length=30)
 version:int=Field(ge=0)
class SettingsBody(BaseModel):
 items:dict[str,Channel]=Field(default_factory=dict,max_length=1000)
 expenses:dict[str,Channel]=Field(default_factory=dict,max_length=1000)
 costs_complete:dict[str,bool]=Field(default_factory=dict,max_length=2)
 version:int=Field(ge=0)
class ExpenseBody(BaseModel):
 name:str=Field(min_length=1,max_length=160)
 amount_cents:int=Field(ge=0,le=100000000)
 channel:Channel='event'
 paid:bool=False
 request_key:uuid.UUID

def staff(user=Depends(current_user)):
 if user.role not in ('admin','staff'):raise HTTPException(403,'Staff financial access required')
 return user

def event_for(db,eid,lock=False):
 q=db.query(BoxingEvent).filter_by(id=eid);e=q.with_for_update().first() if lock else q.first()
 if not e:raise HTTPException(404,'Event not found')
 return e

def suggest(name,categories=()):
 n=re.sub(r'[^a-z0-9]+',' ',str(name).lower()).strip()
 if re.search(r'\b(beer|wine|shot|shots|cocktail|alcohol|liquor|mixed drink)\b',n):return 'bar'
 if re.search(r'\b(chips|gatorade|soda|water|juice|nacho|nachos|wings|hot dog|chilli dog|tacos|red bull)\b',n):return 'concessions'
 if re.search(r'\b(ticket|admission|reserved|membership|registration|ga)\b',n) or any('membership' in c.lower() for c in categories):return 'exclude'
 if any(c.lower() in ('concessions','food','beverage','non alcoholic beverages') for c in categories):return 'concessions'
 return 'review'

def round_cents(v):return int(Decimal(str(v)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def line_weight(l):
 if l.get('refunded') or l.get('exchanged') or l.get('isOrderFee'):raise ValueError('review_line')
 quantity=Decimal(str(l.get('unitQty',1000)))/1000
 if quantity<=0:raise ValueError('review_quantity')
 price=int(l.get('price',0))+sum(int(m.get('amount',0)) for m in l.get('modifications',{}).get('elements',[]))
 total=round_cents(Decimal(price)*quantity)
 for discount in l.get('discounts',{}).get('elements',[]):
  if discount.get('amount') is not None:total-=abs(int(discount['amount']))
  elif discount.get('percentage') is not None:total-=round_cents(Decimal(total)*Decimal(str(discount['percentage']))/100)
  else:raise ValueError('unknown_discount')
 if total<0:raise ValueError('negative_line')
 return total

def allocate(total,weights):
 denominator=sum(weights)
 if denominator<=0:raise ValueError('empty_basket')
 values=[total*w//denominator for w in weights];remainder=total-sum(values)
 ranking=sorted(range(len(weights)),key=lambda i:(total*weights[i]%denominator,-i),reverse=True)
 for i in ranking[:remainder]:values[i]+=1
 return values

def normalize_orders(orders,catalog):
 rows=[];issues=defaultdict(int);seen=set()
 for o in orders:
  oid=o.get('id')
  if not oid or oid in seen:issues['duplicate_orders']+=1;continue
  seen.add(oid)
  if o.get('paymentState')!='PAID':issues['unpaid_or_refunded_orders']+=1;continue
  try:
   payments=o.get('payments',{}).get('elements',[]);lines=o.get('lineItems',{}).get('elements',[])
   if not payments or not lines or len(lines)>=100 or len(payments)>=100:raise ValueError('missing_or_truncated_details')
   if o.get('serviceCharge') or o.get('testMode'):raise ValueError('service_charge_or_test_order')
   if any(p.get('result')!='SUCCESS' or p.get('refunds',{}).get('elements') or p.get('voided') for p in payments):raise ValueError('payment_requires_review')
   if any('taxAmount' not in p or 'amount' not in p or int(p.get('cashbackAmount',0)) for p in payments):raise ValueError('tax_or_cashback_requires_review')
   paid=sum(int(p['amount']) for p in payments);tax=sum(int(p['taxAmount']) for p in payments)
   if paid!=int(o.get('total',-1)) or tax<0 or tax>paid:raise ValueError('payment_mismatch')
   weights=[line_weight(l) for l in lines];net=paid-tax
   if net>sum(weights)+2 or (abs(net-sum(weights))>2 and not o.get('discounts',{}).get('elements')):raise ValueError('unexplained_total_adjustment')
   amounts=allocate(net,weights)
   for line_index,(line,amount) in enumerate(zip(lines,amounts)):
    identity=line.get('item',{}).get('id');item=catalog.get(identity,{})
    cats=[c.get('name','') for c in item.get('categories',{}).get('elements',[])]
    if line.get('isRevenue') is False:issues['clover_nonrevenue_lines']+=1
    name=str(line.get('name') or item.get('name') or 'Unnamed item')[:160];key=str(identity or ('order:'+oid+':'+str(line.get('id',line_index)) if name.casefold() in ('custom item','manual transaction') else 'name:'+name.casefold()))[:200]
    rows.append({'key':key,'name':name,'categories':cats,'net_cents':amount,'quantity':float(Decimal(str(line.get('unitQty',1000)))/1000),'order_id':oid,'order_reference':oid if key.startswith('order:') else '', 'payment_ids':[p['id'] for p in payments if p.get('id')]})
  except (ValueError,TypeError,KeyError,ArithmeticError) as e:issues[str(e) if isinstance(e,ValueError) else 'malformed_order']+=1
 return {'rows':rows,'review_counts':dict(issues),'orders_scanned':len(seen)}

def fetch_clover(start,end):
 token=os.getenv('CLOVER_API_TOKEN');merchant=os.getenv('CLOVER_MERCHANT_ID')
 if not token or not merchant:raise HTTPException(503,'Clover connection is not configured')
 base='https://api.clover.com' if os.getenv('CLOVER_ENV','production')=='production' else 'https://apisandbox.dev.clover.com'
 root=base+'/v3/merchants/'+merchant;headers={'Authorization':'Bearer '+token};began=time.monotonic()
 def pages(path,params=()):
  collected=[]
  for offset in range(0,3000,100):
   if time.monotonic()-began>55:raise HTTPException(503,'Clover read timed out. Previous report preserved; try a shorter window')
   try:
    r=requests.get(root+path,headers=headers,params=[*params,('limit','100'),('offset',str(offset))],timeout=12);r.raise_for_status();batch=r.json()['elements']
   except (requests.RequestException,ValueError,KeyError):raise HTTPException(502,'Clover could not supply complete records. Previous report preserved; retry later')
   collected.extend(batch)
   if len(batch)<100:return collected
  raise HTTPException(422,'Too many records. Choose a shorter reporting window')
 catalog={i['id']:i for i in pages('/items',[('expand','categories')])}
 orders=pages('/orders',[('filter','createdTime>='+str(int(start.timestamp()*1000))),('filter','createdTime<'+str(int(end.timestamp()*1000))),('expand','lineItems.discounts,lineItems.modifications,payments.refunds,discounts,serviceCharge')])
 return normalize_orders(orders,catalog)

def defaults(e):
 try:start=datetime.fromisoformat(str(e.event_date)[:10]).replace(tzinfo=CT)
 except (ValueError,TypeError):return {'start_local':'','end_local':''}
 return {'start_local':start.strftime('%Y-%m-%dT%H:%M'),'end_local':(start+timedelta(days=1,hours=6)).strftime('%Y-%m-%dT%H:%M')}

def report_data(db,eid):
 e=event_for(db,eid);snapshot=db.get(EventPosSnapshot,eid);source=json.loads(snapshot.source_json) if snapshot else {};settings=json.loads(snapshot.settings_json) if snapshot else {};groups={};totals={'concessions':0,'bar':0,'review':0,'exclude':0}
 for row in source.get('rows',[]):
  item=groups.setdefault(row['key'],{'key':row['key'],'name':row['name'],'categories':row['categories'],'order_reference':row.get('order_reference',''),'quantity':0,'net_cents':0,'channel':settings.get('items',{}).get(row['key'],suggest(row['name'],row['categories']))});item['quantity']+=row['quantity'];item['net_cents']+=row['net_cents']
 for item in groups.values():totals[item['channel'] if item['channel'] in totals else 'review']+=item['net_cents']
 from .recap import RecapFeeTreatment,default_treatment
 mappings={x.fee_id:x.treatment for x in db.query(RecapFeeTreatment).join(BoxingEventFee,BoxingEventFee.id==RecapFeeTreatment.fee_id).filter(BoxingEventFee.event_id==eid)}
 expenses=[];costs={'concessions':0,'bar':0,'event':0,'review':0,'exclude':0}
 for f in db.query(BoxingEventFee).filter_by(event_id=eid).order_by(BoxingEventFee.id):
  treatment=mappings.get(f.id,default_treatment(f));default='bar' if f.fee_key in ('owner_operating_beer','owner_operating_alcohol') else 'event';channel=settings.get('expenses',{}).get(str(f.id),default)
  if treatment in ('exclude','fighter_pay','ticket_commission'):channel='exclude'
  try:
   amount=None if f.actual_amount is None else round_cents(Decimal(str(f.actual_amount))*100)
   if amount is not None and amount<0:amount=None
  except (InvalidOperation,ValueError,TypeError):amount=None
  if amount is not None:costs[channel]+=amount
  expenses.append({'id':f.id,'name':f.name,'amount_cents':amount,'paid':bool(f.paid),'channel':channel,'treatment':treatment})
 sections={}
 for channel in ('concessions','bar'):
  complete=bool(settings.get('costs_complete',{}).get(channel)) and not any(x['channel']==channel and x['amount_cents'] is None for x in expenses)
  profit_ready=complete and not totals['review'] and not any(v for k,v in source.get('review_counts',{}).items() if k not in ('unpaid_or_refunded_orders','duplicate_orders','clover_nonrevenue_lines'))
  sections[channel]={'revenue_cents':totals[channel] if snapshot and snapshot.imported_at else None,'cost_cents':costs[channel],'contribution_cents':totals[channel]-costs[channel] if snapshot and snapshot.imported_at else None,'profit_cents':totals[channel]-costs[channel] if profit_ready and snapshot and snapshot.imported_at else None,'costs_complete':complete}
 return {'event':{'id':e.id,'name':e.name,'date':e.event_date},'version':snapshot.version if snapshot else 0,'imported_at':snapshot.imported_at.isoformat()+'Z' if snapshot and snapshot.imported_at else None,'window':source.get('window',defaults(e)),'items':list(groups.values()),'expenses':expenses,'sections':sections,'totals':totals,'cost_totals':costs,'review_counts':source.get('review_counts',{}),'orders_scanned':source.get('orders_scanned',0),'basis':'Clover paid orders created in the displayed Oklahoma City time window. Sales exclude tax and tips; basket-level discounts are allocated proportionally after known line discounts. Unpaid/refunded, incomplete or unreconciled orders are excluded and flagged. Paid food/drink lines marked non-revenue in Clover are counted from collected amounts and flagged for classification review. Custom items require classification. Revenue is recorded sales, not bank deposits; card-processing fees are not supplied by this read. Profit remains unconfirmed until staff verifies complete allocated costs. Shared event costs, unpaid costs and excluded lines are itemized separately. Purchase costs are used as recorded; remaining stock is not valued automatically. Shopping estimates and planned menu counts are not actual sales or expenses. Operating sheet excludes fighter compensation; see event recap for full event costs.'}

def pos_revenue(db,eid):
 s=db.get(EventPosSnapshot,eid)
 if not s or not s.imported_at:return {'concessions':0,'bar':0}
 data=report_data(db,eid);return {k:data['totals'][k] for k in ('concessions','bar')}

def pos_references(db,eid,fully_covered=False):
 s=db.get(EventPosSnapshot,eid)
 if not s or not s.imported_at:return set()
 settings=json.loads(s.settings_json);orders=defaultdict(list)
 for r in json.loads(s.source_json).get('rows',[]):orders[r['order_id']].append(settings.get('items',{}).get(r['key'],suggest(r['name'],r['categories'])))
 return {oid for oid,channels in orders.items() if any(c in ('concessions','bar') for c in channels) and (not fully_covered or all(c in ('concessions','bar') for c in channels))}

@router.get('/{event_id}/financials')
def get_report(event_id:int,response:Response,db=Depends(get_db),user=Depends(staff)):
 response.headers['Cache-Control']='private, no-store';return report_data(db,event_id)
@router.post('/{event_id}/financials/sync')
def sync(event_id:int,body:SyncBody,db=Depends(get_db),user=Depends(staff)):
 event_for(db,event_id)
 try:
  start=datetime.fromisoformat(body.start_local);end=datetime.fromisoformat(body.end_local)
  if start.tzinfo or end.tzinfo:raise ValueError()
  start=start.replace(tzinfo=CT);end=end.replace(tzinfo=CT)
  if not timedelta(0)<end-start<=timedelta(days=3):raise ValueError()
 except ValueError:raise HTTPException(422,'Choose a valid local-time window of at most three days')
 source=fetch_clover(start,end);source['window']={'start_local':body.start_local,'end_local':body.end_local}
 if db.bind.dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(90437812)'))
 event_for(db,event_id,True);row=db.get(EventPosSnapshot,event_id)
 order_ids={r['order_id'] for r in source['rows']}
 for other in db.query(EventPosSnapshot).filter(EventPosSnapshot.event_id!=event_id):
  if order_ids.intersection(r['order_id'] for r in json.loads(other.source_json).get('rows',[])):raise HTTPException(409,'This window overlaps Clover orders already attributed to another event. Correct the reporting window first')
 if (row.version if row else 0)!=body.version:raise HTTPException(409,'Report changed. Refresh before importing')
 if not row:row=EventPosSnapshot(event_id=event_id,settings_json='{}');db.add(row)
 row.source_json=json.dumps(source);row.imported_at=datetime.utcnow();row.version=body.version+1;db.add(SecurityLog(user_id=user.id,action='EVENT_POS_REPORT_IMPORTED',description=f'Event {event_id}; {len(source["rows"])} item rows; Clover read only',success=True));db.commit();return {'saved':True}
@router.put('/{event_id}/financials/settings')
def save_settings(event_id:int,body:SettingsBody,db=Depends(get_db),user=Depends(staff)):
 event_for(db,event_id,True);row=db.get(EventPosSnapshot,event_id)
 if (row.version if row else 0)!=body.version:raise HTTPException(409,'Report changed. Refresh before saving')
 if any(v=='event' for v in body.items.values()) or any(k not in ('concessions','bar') for k in body.costs_complete):raise HTTPException(422,'Choose food/bar, excluded or review for sales')
 if not row:row=EventPosSnapshot(event_id=event_id,source_json='{}');db.add(row)
 row.settings_json=json.dumps(body.model_dump(exclude={'version'}));row.version=body.version+1;db.add(SecurityLog(user_id=user.id,action='EVENT_POS_ALLOCATION_UPDATED',description=f'Event {event_id}; classifications and cost completeness reviewed',success=True));db.commit();return {'saved':True}
@router.post('/{event_id}/financials/expenses')
def add_expense(event_id:int,body:ExpenseBody,db=Depends(get_db),user=Depends(staff)):
 event_for(db,event_id,True);key='operating_receipt_'+str(body.request_key);old=db.query(BoxingEventFee).filter_by(event_id=event_id,fee_key=key).first()
 if old:
  if old.name!=body.name.strip() or round_cents(Decimal(str(old.actual_amount))*100)!=body.amount_cents or bool(old.paid)!=body.paid:raise HTTPException(409,'This receipt key already belongs to another expense')
  return {'saved':True,'existing':True}
 if not body.name.strip():raise HTTPException(422,'Enter an expense name')
 fee=BoxingEventFee(event_id=event_id,fee_key=key,name=body.name.strip(),actual_amount=body.amount_cents/100,paid=body.paid);db.add(fee);db.flush();row=db.get(EventPosSnapshot,event_id)
 if not row:row=EventPosSnapshot(event_id=event_id,source_json='{}',settings_json='{}',version=0);db.add(row)
 settings=json.loads(row.settings_json);settings.setdefault('expenses',{})[str(fee.id)]=body.channel;settings['costs_complete']={};row.settings_json=json.dumps(settings);row.version+=1;db.add(SecurityLog(user_id=user.id,action='EVENT_OPERATING_EXPENSE_ADDED',description=f'Event {event_id}; fee {fee.id}; {body.amount_cents} cents; channel {body.channel}',success=True));db.commit();return {'saved':True}

@router.get('/{event_id}/financials.csv')
def expense_csv(event_id:int,db=Depends(get_db),user=Depends(staff)):
 d=report_data(db,event_id);out=io.StringIO();w=csv.writer(out)
 safe=lambda x:"'"+str(x) if str(x).lstrip().startswith(('=','+','-','@')) else str(x)
 w.writerow(['Event',safe(d['event']['name'])]);w.writerow(['Expense','Section','Actual USD','Marked paid','Accounting treatment'])
 for e in d['expenses']:w.writerow([safe(e['name']),e['channel'],'' if e['amount_cents'] is None else f'{e["amount_cents"]/100:.2f}',e['paid'],e['treatment']])
 return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="event-{event_id}-itemized-expenses.csv"'})
@router.get('/{event_id}/financials.pdf')
def finance_pdf(event_id:int,view:Literal['profit','expenses']='profit',db=Depends(get_db),user=Depends(staff)):
 from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
 from reportlab.lib.styles import getSampleStyleSheet
 from reportlab.lib import colors
 d=report_data(db,event_id);styles=getSampleStyleSheet();out=io.BytesIO();money=lambda v:'NOT RECORDED' if v is None else f'${v/100:,.2f}'
 story=[Paragraph('TNG BOXING | '+('ITEMIZED EXPENSE SHEET' if view=='expenses' else 'CONCESSIONS & BAR RESULTS'),styles['Title']),Paragraph(escape(d['event']['name']),styles['Heading2']),Paragraph(escape(str(d['event']['date'] or 'Date not recorded')),styles['Normal']),Paragraph(escape(d['basis']),styles['Normal']),Spacer(1,12)]
 def table(head,rows,widths):
  values=[[Paragraph(escape(str(v)),styles['Normal'])for v in row] for row in [head,*rows]];t=Table(values,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8e8ed')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#c62039')),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.extend([t,Spacer(1,14)])
 if view=='profit':
  story.append(Paragraph('Reporting window (America/Chicago): '+escape(d['window']['start_local']+' to '+d['window']['end_local']),styles['Normal']))
  table(['Section','Net sales','Recorded costs','Contribution','Confirmed profit/loss'],[[k.title(),money(v['revenue_cents']),money(v['cost_cents']),money(v['contribution_cents']),money(v['profit_cents'])]for k,v in d['sections'].items()],[78,100,100,100,142])
  table(['Sold item / Clover category','Section','Quantity','Net sales'],[[i['name']+(' | Order '+i['order_reference'] if i.get('order_reference') else '')+' / '+', '.join(i['categories']),i['channel'],i['quantity'],money(i['net_cents'])]for i in d['items']],[260,100,70,90])
  story.append(Paragraph('Unclassified sales: '+money(d['totals']['review'])+'; source review counts: '+escape(json.dumps(d['review_counts'])),styles['Normal']))
 table(['Expense','Section','Actual amount','Marked paid','Treatment'],[[e['name'],e['channel'],money(e['amount_cents']),'Yes' if e['paid'] else 'Not confirmed',e['treatment']]for e in d['expenses']],[185,80,100,75,80])
 story.append(Paragraph('Total included operating expenses: '+money(sum(e['amount_cents'] or 0 for e in d['expenses'] if e['channel']!='exclude'))+'. Missing amounts and excluded duplicate/treatment lines are not counted. Fighter compensation is in the full event recap.',styles['Normal']))
 SimpleDocTemplate(out,pagesize=(612,792),leftMargin=46,rightMargin=46,topMargin=42,bottomMargin=42).build(story)
 return Response(out.getvalue(),media_type='application/pdf',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="event-{event_id}-{view}.pdf"'})
