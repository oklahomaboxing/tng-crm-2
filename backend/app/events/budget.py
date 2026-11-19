"""Separate event planning assumptions; never creates actual income or expenses."""
import io,json,math
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from xml.sax.saxutils import escape
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import Column,Integer,Text,DateTime,ForeignKey
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent,BoxingEventFee
from .recap import recap
router=APIRouter(prefix='/api/events',tags=['Event budget and forecast'])
class EventBudget(Base):
 __tablename__='event_budget_forecasts'
 event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
 assumptions_json=Column(Text,nullable=False)
 version=Column(Integer,default=1,nullable=False)
 updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)
class CostLine(BaseModel):
 name:str=Field(min_length=1,max_length=160)
 amount_cents:int|None=Field(default=None,ge=0,le=100000000)
 basis:str=Field(default='Manual planning estimate',max_length=200)
class BudgetBody(BaseModel):
 baseline_event_id:int|None=None
 expected_paid_tickets:int=Field(ge=0,le=100000)
 average_ticket_cents:int|None=Field(default=None,ge=0,le=1000000)
 concessions_per_ticket_cents:int|None=Field(default=None,ge=0,le=1000000)
 bar_per_ticket_cents:int|None=Field(default=None,ge=0,le=1000000)
 sponsor_vendor_cents:int|None=Field(default=None,ge=0,le=100000000)
 purse_allowance_cents:int|None=Field(default=None,ge=0,le=100000000)
 commission_percent:Decimal=Field(default=0,ge=0,le=100,max_digits=5,decimal_places=2)
 assessment_percent:Decimal=Field(default=5,ge=0,le=100,max_digits=5,decimal_places=2)
 assessment_minimum_cents:int=Field(default=45000,ge=0,le=100000000)
 processing_fee_percent:Decimal|None=Field(default=None,ge=0,le=100)
 @field_validator("processing_fee_percent")
 @classmethod
 def precision(cls,v):
  if v is not None and v.as_tuple().exponent < -2:raise ValueError("Use at most two decimal places for processing percentage")
  return v
 operating_costs:list[CostLine]=Field(default_factory=list,max_length=150)
 notes:str=Field(default='',max_length=4000)
 version:int=Field(default=0,ge=0)

def staff(user=Depends(current_user)):
 if user.role not in ('admin','staff'):raise HTTPException(403,'Event finance staff access required')
 return user

def event_for(db,eid,lock=False):
 q=db.query(BoxingEvent).filter_by(id=eid);e=q.with_for_update().first()if lock else q.first()
 if not e:raise HTTPException(404,'Event not found')
 return e

def cents(n):return int(Decimal(str(n)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def previous(db,event):
 rows=[];today=datetime.now(timezone.utc).date().isoformat()
 for e in db.query(BoxingEvent).order_by(BoxingEvent.event_date.desc(),BoxingEvent.id.desc()):
  if e.id==event.id or not e.event_date or e.event_date[:10]>=today or (event.event_date and e.event_date[:10]>=event.event_date[:10]):continue
  d=recap(db,e.id)
  if d['summary']['paid_ticket_quantity']<=0:continue
  rows.append({'id':e.id,'name':e.name,'date':e.event_date,'summary':d['summary'],'provisional':d['provisional'],'warnings':d['warnings']})
 return rows

def defaults(db,event,baseline_id=None):
 options=previous(db,event);baseline=next((e for e in options if e['id']==baseline_id),None) if baseline_id else (options[0]if options else None)
 if baseline_id and not baseline:raise HTTPException(422,'Choose a prior completed-date event with recorded paid ticket sales')
 current=recap(db,event.id);s=baseline['summary'] if baseline else {};q=s.get('paid_ticket_quantity',0);current_s=current['summary'];prior_expenses=recap(db,baseline['id'])['expenses']if baseline else [];costs=[];keys=set()
 # Current recorded operating amounts take priority; otherwise use prior actual amounts.
 source_fees={f.id:f for f in db.query(BoxingEventFee).filter_by(event_id=event.id)}
 for fee in current['expenses']:
  if fee['treatment']!='other':continue
  source=source_fees[fee['id']]
  if fee['actual_cents'] is not None:costs.append({'name':fee['name'],'amount_cents':fee['actual_cents'],'basis':'Current event recorded expense'});keys.add(source.fee_key)
 baseline_fees={f.id:f for f in db.query(BoxingEventFee).filter_by(event_id=baseline['id'])}if baseline else {}
 for fee in prior_expenses:
  if fee['treatment']!='other':continue
  source=baseline_fees[fee['id']]
  if source.fee_key in keys:continue
  costs.append({'name':fee['name'],'amount_cents':fee['actual_cents'],'basis':'Prior event actual reference; review for this event'});keys.add(source.fee_key)
 for fee in current['expenses']:
  source=source_fees[fee['id']]
  if fee['treatment']=='other' and source.fee_key not in keys:costs.append({'name':fee['name'],'amount_cents':None,'basis':'Current event cost not recorded'});keys.add(source.fee_key)
 if not any(any(word in c['name'].lower()for word in ('food','concession','ingredient'))for c in costs):costs.append({'name':'Concessions food purchases','amount_cents':None,'basis':'Food stock cost is not recorded in the prior/current expense sheet'})
 if not any(any(word in c['name'].lower()for word in ('beer','alcohol','bar','beverage'))for c in costs):costs.append({'name':'Bar beverage purchases','amount_cents':None,'basis':'Bar inventory cost is not recorded in the prior/current expense sheet'})
 if not any('venue' in c['name'].lower()or'rent' in c['name'].lower()for c in costs):costs.append({'name':'Venue / rent allocation','amount_cents':None,'basis':'Enter actual agreement or explicit zero if none'})
 if not any('insurance' in c['name'].lower()for c in costs):costs.append({'name':'Event insurance','amount_cents':None,'basis':'Confirm actual event coverage cost; excluded placeholders are not estimates'})
 from .concessions_finance import EventPosSnapshot
 has_pos=bool(baseline and (p:=db.get(EventPosSnapshot,baseline['id'])) and p.imported_at)
 body={'baseline_event_id':baseline['id']if baseline else None,'expected_paid_tickets':max(q,current_s['paid_ticket_quantity']),'average_ticket_cents':cents(s['ticket_sales_cents']/q)if q else None,'concessions_per_ticket_cents':cents(s.get('concessions_sales_cents',0)/q)if q and has_pos else None,'bar_per_ticket_cents':cents(s.get('bar_sales_cents',0)/q)if q and has_pos else None,'sponsor_vendor_cents':max(0,s.get('other_income_cents',0)-s.get('concessions_sales_cents',0)-s.get('bar_sales_cents',0))if baseline else None,'purse_allowance_cents':current_s['purse_cost_cents']if current_s['current_card_fighters'] else (s.get('purse_cost_cents')if baseline else None),'commission_percent':min(100,cents(Decimal(s.get('commission_cost_cents',0))*10000/Decimal(s['ticket_sales_cents']))/100) if s.get('ticket_sales_cents') else 0,'assessment_percent':5,'assessment_minimum_cents':45000,'processing_fee_percent':None,'operating_costs':costs,'notes':'Planning assumptions only. Prior costs, revenue per paid ticket and sponsorship are references, not booked commitments. Ticket price excludes customer fees. Enter missing costs and confirm any commission minimum. Do not reuse prior purses as booked current-card contracts.','version':0}
 return BudgetBody(**body),options,current

def attach_reference(forecast,options,baseline_id):
 reference=next((r for r in options if r['id']==baseline_id),None)
 if reference and reference['provisional']:
  forecast['missing_or_review'].append('Prior event reference has incomplete records; historical results may change')
  forecast['provisional']=True
 return forecast

def calculate(body,current):
 missing=[k.replace('_',' ')for k in ('average_ticket_cents','concessions_per_ticket_cents','bar_per_ticket_cents','sponsor_vendor_cents','purse_allowance_cents','processing_fee_percent')if getattr(body,k)is None]+[c.name for c in body.operating_costs if c.amount_cents is None]
 if not current['summary']['current_card_fighters']:missing.append('No fighters booked on the current card; purse reference is not a current contract')
 if body.expected_paid_tickets<current['summary']['paid_ticket_quantity']:missing.append('Expected ticket count is below already recorded paid tickets')
 numeric_missing=any(getattr(body,k)is None for k in ('average_ticket_cents','concessions_per_ticket_cents','bar_per_ticket_cents','sponsor_vendor_cents','purse_allowance_cents','processing_fee_percent')) or any(c.amount_cents is None for c in body.operating_costs)
 fixed=sum(c.amount_cents or 0 for c in body.operating_costs)+(body.purse_allowance_cents or 0);sponsors=body.sponsor_vendor_cents or 0;scenarios=[]
 def scenario(name,quantity):
  ticket=quantity*(body.average_ticket_cents or 0);food=quantity*(body.concessions_per_ticket_cents or 0);bar=quantity*(body.bar_per_ticket_cents or 0);commission=max(current['summary']['commission_cost_cents'],cents(Decimal(ticket)*body.commission_percent/100));assessment=max(45000,body.assessment_minimum_cents,cents(Decimal(ticket)*body.assessment_percent/100));fees=cents(Decimal(ticket+food+bar+sponsors)*(body.processing_fee_percent or 0)/100);income=ticket+food+bar+sponsors;cost=fixed+commission+assessment+fees
  return {'name':name,'paid_tickets':quantity,'ticket_revenue_cents':ticket,'concessions_revenue_cents':food,'bar_revenue_cents':bar,'sponsor_vendor_revenue_cents':sponsors,'income_cents':income,'fixed_costs_cents':fixed,'commission_cents':commission,'assessment_cents':assessment,'processing_fees_cents':fees,'cost_cents':cost,'projected_result_cents':income-cost}
 for name,factor in [('Lower sales',Decimal('.8')),('Planning case',Decimal('1')),('Higher sales',Decimal('1.2'))]:scenarios.append(scenario(name,cents(body.expected_paid_tickets*factor)))
 # Monotone search includes assessment minima, recorded commission obligations and all fee assumptions.
 limit=100000;break_even=0 if scenario('',0)['projected_result_cents']>=0 else None
 if break_even is None and scenario('',limit)['projected_result_cents']>=0:
  lo,hi=0,limit
  while lo<hi:
   mid=(lo+hi)//2
   if scenario('',mid)['projected_result_cents']>=0:hi=mid
   else:lo=mid+1
  break_even=lo
 return {'scenarios':scenarios,'break_even_status':'missing_inputs'if numeric_missing else'calculated'if break_even is not None else'unreachable','break_even_paid_tickets':None if numeric_missing else break_even,'missing_or_review':missing,'provisional':bool(missing),'purse_basis':('Current card recorded obligations'if body.purse_allowance_cents==current['summary'].get('purse_cost_cents')else'Staff planning amount; review against current card obligations')if current['summary']['current_card_fighters']else'Planning purse reference; current card not booked','basis':'Estimate only, not actual income, profit or guaranteed demand. Paid-ticket count is a planning proxy, not verified attendance. Prior food/bar revenue is divided by recorded paid tickets and scaled to expected tickets. Inventory carryover and unsold stock are not valued automatically; review required new purchases. Operating costs are fixed planning amounts; earned commissions, ticket assessment and processor percentages vary with forecast receipts. Recorded current commission obligations are a floor. Processing percentage applies to all forecast receipts as a planning approximation. Unrecorded costs contribute zero to scenario arithmetic but remain explicitly missing; do not treat incomplete projections as complete profit. 80%/100%/120% sales scenarios are assumptions, not statistical probabilities.'}

@router.get('/{event_id}/budget')
def get_budget(event_id:int,response:Response,baseline_event_id:int|None=None,db=Depends(get_db),user=Depends(staff)):
 e=event_for(db,event_id);response.headers['Cache-Control']='private, no-store';body,options,current=defaults(db,e,baseline_event_id);saved=db.get(EventBudget,event_id)
 if saved and baseline_event_id is None:body=BudgetBody(**{**json.loads(saved.assumptions_json),'assessment_minimum_cents':max(45000,json.loads(saved.assumptions_json).get('assessment_minimum_cents',0))},version=saved.version)
 return {'event':{'id':e.id,'name':e.name,'date':e.event_date},'assumptions':body.model_dump(mode='json'),'prior_events':options,'forecast':attach_reference(calculate(body,current),options,body.baseline_event_id),'version':saved.version if saved else 0,'current_recorded_summary':current['summary']}
@router.post('/{event_id}/budget/preview')
def preview(event_id:int,body:BudgetBody,db=Depends(get_db),user=Depends(staff)):
 e=event_for(db,event_id)
 _,options,_=defaults(db,e,body.baseline_event_id)
 return attach_reference(calculate(body,recap(db,event_id)),options,body.baseline_event_id)
@router.put('/{event_id}/budget')
def save(event_id:int,body:BudgetBody,db=Depends(get_db),user=Depends(staff)):
 e=event_for(db,event_id,True)
 if body.baseline_event_id:defaults(db,e,body.baseline_event_id)
 row=db.get(EventBudget,event_id)
 if (row.version if row else 0)!=body.version:raise HTTPException(409,'Budget changed. Refresh before saving')
 if not row:row=EventBudget(event_id=event_id);db.add(row)
 body.assessment_minimum_cents=max(45000,body.assessment_minimum_cents)
 row.assumptions_json=json.dumps(body.model_dump(mode='json',exclude={'version'}));row.version=body.version+1;row.updated_at=datetime.utcnow();db.add(SecurityLog(user_id=user.id,action='EVENT_BUDGET_SAVED',description=f'Event {event_id}; baseline {body.baseline_event_id}; version {row.version}; planning only',success=True));db.commit();return {'saved':True}
@router.get('/{event_id}/budget.pdf')
def pdf(event_id:int,db=Depends(get_db),user=Depends(staff)):
 from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
 from reportlab.lib.styles import getSampleStyleSheet
 from reportlab.lib import colors
 if not db.get(EventBudget,event_id):raise HTTPException(409,'Save and review the planning budget before downloading')
 d=get_budget(event_id,Response(),None,db,user);a=d['assumptions'];f=d['forecast'];styles=getSampleStyleSheet();out=io.BytesIO();money=lambda x:'NOT ENTERED'if x is None else f'${x/100:,.2f}';story=[Paragraph('TNG BOXING | EVENT BUDGET & FORECAST',styles['Title']),Paragraph(escape(d['event']['name']),styles['Heading2']),Paragraph(escape(f['basis']),styles['Normal']),Spacer(1,12)]
 rows=[['Sales scenario','Paid tickets','Projected income','Projected costs','Projected result']]+[[s['name'],str(s['paid_tickets']),money(s['income_cents']),money(s['cost_cents']),money(s['projected_result_cents'])]for s in f['scenarios']]
 table=Table([[Paragraph(escape(str(c)),styles['Normal'])for c in r]for r in rows],colWidths=[105,65,115,115,120],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8e8ed')),('VALIGN',(0,0),(-1,-1),'TOP')]));story.extend([table,Spacer(1,12),Paragraph('Break-even paid tickets: '+str('Enter missing inputs first'if f['break_even_status']=='missing_inputs'else f['break_even_paid_tickets']if f['break_even_paid_tickets']is not None else'Not achievable within 100,000 tickets under these assumptions'),styles['Heading2'])])
 story.append(Paragraph('Purses / allowances: '+money(a['purse_allowance_cents'])+' | '+escape(f['purse_basis']),styles['Normal']))
 for c in a['operating_costs']:story.append(Paragraph(escape(c['name'])+': '+money(c['amount_cents'])+' | '+escape(c['basis']),styles['Normal']))
 story.append(Paragraph('Missing / review: '+escape('; '.join(f['missing_or_review'])or'No missing inputs; assumptions still require staff review.'),styles['Normal']));story.append(Paragraph(escape(a['notes']),styles['Normal']));SimpleDocTemplate(out,pagesize=(612,792),leftMargin=46,rightMargin=46).build(story)
 return Response(out.getvalue(),media_type='application/pdf',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="event-{event_id}-budget-forecast.pdf"'})
