"""Event-scoped chef menu, shopping and preparation planning. Never places orders."""
import io,json,os,uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal
from xml.sax.saxutils import escape
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import Column,Integer,String,Text,Boolean,DateTime,ForeignKey,Numeric,UniqueConstraint
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent
from .partners import PartnerGrant,PartnerProfile
router=APIRouter(prefix='/api/concessions/events',tags=['Concessions'])
Store=Literal['CHEF_STORE','WALMART','SAMS_CLUB','OTHER']

class ConcessionsPlan(Base):
    __tablename__='event_concessions_plans'
    event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
    notes=Column(Text,default='',nullable=False)
    version=Column(Integer,default=0,nullable=False)
    published_json=Column(Text,nullable=True)
    published_at=Column(DateTime,nullable=True)

class ConcessionsMenuItem(Base):
    __tablename__='event_concessions_menu_items'
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    name=Column(String(160),nullable=False)
    description=Column(Text,default='',nullable=False)
    category=Column(String(80),default='Food',nullable=False)
    price_cents=Column(Integer,nullable=False)
    unit_cost_cents=Column(Integer,nullable=True)
    planned_quantity=Column(Integer,default=0,nullable=False)
    sold_quantity=Column(Integer,default=0,nullable=False)
    waste_quantity=Column(Integer,default=0,nullable=False)
    allergens=Column(Text,default='',nullable=False)
    prep_notes=Column(Text,default='',nullable=False)
    enabled=Column(Boolean,default=True,nullable=False)
    version=Column(Integer,default=0,nullable=False)

class ConcessionsShoppingItem(Base):
    __tablename__='event_concessions_shopping_items'
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    name=Column(String(160),nullable=False)
    store=Column(String(30),nullable=False)
    quantity=Column(Numeric(12,3),nullable=False)
    unit=Column(String(60),default='pack',nullable=False)
    estimated_total_cents=Column(Integer,nullable=True)
    actual_total_cents=Column(Integer,nullable=True)
    purchased=Column(Boolean,default=False,nullable=False)
    notes=Column(Text,default='',nullable=False)
    version=Column(Integer,default=0,nullable=False)

class ConcessionsDraftImport(Base):
    __tablename__='event_concessions_draft_imports'
    __table_args__=(UniqueConstraint('event_id','request_key',name='uq_concessions_draft_import'),)
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False)
    request_key=Column(String(80),nullable=False)

class MenuBody(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    description:str=Field(default='',max_length=1000)
    category:str=Field(default='Food',min_length=1,max_length=80)
    price_cents:int=Field(ge=0,le=1000000)
    unit_cost_cents:int|None=Field(default=None,ge=0,le=1000000)
    planned_quantity:int=Field(default=0,ge=0,le=100000)
    sold_quantity:int=Field(default=0,ge=0,le=100000)
    waste_quantity:int=Field(default=0,ge=0,le=100000)
    allergens:str=Field(default='',max_length=1000)
    prep_notes:str=Field(default='',max_length=2000)
    enabled:bool=True
    version:int=Field(default=0,ge=0)

class ShoppingBody(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    store:Store
    quantity:Decimal=Field(gt=0,le=1000000,max_digits=12,decimal_places=3)
    unit:str=Field(default='pack',min_length=1,max_length=60)
    estimated_total_cents:int|None=Field(default=None,ge=0,le=100000000)
    actual_total_cents:int|None=Field(default=None,ge=0,le=100000000)
    purchased:bool=False
    notes:str=Field(default='',max_length=2000)
    version:int=Field(default=0,ge=0)

class NotesBody(BaseModel):
    notes:str=Field(max_length=10000)
    version:int=Field(ge=0)

class VersionBody(BaseModel):
    version:int=Field(ge=0)

class GenerateBody(BaseModel):
    preferences:str=Field(default='',max_length=1500)
    expected_guests:int=Field(default=200,ge=1,le=50000)

class DraftBody(BaseModel):
    menu:list[MenuBody]=Field(min_length=1,max_length=15)
    shopping:list[ShoppingBody]=Field(default_factory=list,max_length=40)

class ApplyBody(DraftBody):
    request_key:str=Field(min_length=8,max_length=80)

def access(db,event_id,user,lock=False):
    q=db.query(BoxingEvent).filter_by(id=event_id)
    event=q.with_for_update().first() if lock else q.first()
    if not event:raise HTTPException(404,'Event not found')
    if user.role not in ('admin','staff'):
        if user.role!='concessions' or not db.query(PartnerGrant).filter_by(user_id=user.id,event_id=event_id).first():raise HTTPException(403,'Concessions access is not assigned for this event')
    return event

def clean(body):
    values=body.model_dump(exclude={'version'})
    for k,v in values.items():
        if isinstance(v,str):values[k]=v.strip()
    if not values['name']:raise HTTPException(422,'Enter an item name')
    if any(k in values and not values[k] for k in ('category','unit')):raise HTTPException(422,'Enter a category or unit / pack size')
    if isinstance(body,MenuBody) and body.sold_quantity+body.waste_quantity>body.planned_quantity:raise HTTPException(422,'Sold and wasted quantities cannot exceed planned servings. Increase planned servings first')
    return values

def menu_dict(row):return {k:getattr(row,k) for k in ['id',*MenuBody.model_fields]}
def shopping_dict(row):return {**{k:getattr(row,k) for k in ['id',*ShoppingBody.model_fields]},'quantity':float(row.quantity)}
def audit(db,user,event_id,action):db.add(SecurityLog(user_id=user.id,action='CONCESSIONS_'+action,description=f'Event {event_id} concessions planning updated'))
def plan_for(db,event_id):
    plan=db.get(ConcessionsPlan,event_id)
    if not plan:plan=ConcessionsPlan(event_id=event_id);db.add(plan);db.flush()
    return plan

def mark_dirty(db,event_id):
    plan=plan_for(db,event_id);plan.version+=1

@router.get('/{event_id}')
def workspace(event_id:int,response:Response,db=Depends(get_db),user=Depends(current_user)):
    event=access(db,event_id,user);response.headers['Cache-Control']='private, no-store'
    menu=db.query(ConcessionsMenuItem).filter_by(event_id=event_id).order_by(ConcessionsMenuItem.id).all();shopping=db.query(ConcessionsShoppingItem).filter_by(event_id=event_id).order_by(ConcessionsShoppingItem.id).all();plan=db.get(ConcessionsPlan,event_id)
    active=[m for m in menu if m.enabled];unknown=sum(m.unit_cost_cents is None for m in active)
    planned_cost=None if unknown else sum(m.unit_cost_cents*m.planned_quantity for m in active)
    revenue=sum(m.price_cents*m.planned_quantity for m in active)
    return {'event':{'id':event.id,'name':event.name,'date':event.event_date,'venue':event.venue},'menu':[menu_dict(m) for m in menu],'shopping':[shopping_dict(s) for s in shopping],'notes':plan.notes if plan else '', 'version':plan.version if plan else 0,'published_at':plan.published_at.isoformat()+'Z' if plan and plan.published_at else None,'published_menu':json.loads(plan.published_json) if plan and plan.published_json else None,'summary':{'planned_revenue_cents':revenue,'planned_food_cost_cents':planned_cost,'planned_gross_margin_cents':None if planned_cost is None else revenue-planned_cost,'unknown_food_costs':unknown,'shopping_estimate_cents':None if any(s.estimated_total_cents is None for s in shopping) else sum(s.estimated_total_cents for s in shopping),'shopping_actual_cents':None if any(s.purchased and s.actual_total_cents is None for s in shopping) else sum(s.actual_total_cents or 0 for s in shopping if s.purchased),'purchased_lines':sum(s.purchased for s in shopping),'shopping_lines':len(shopping),'sold_quantity':sum(m.sold_quantity for m in menu),'waste_quantity':sum(m.waste_quantity for m in menu)},'basis':'Planning estimates and staff-entered counts; not reconciled Clover sales or profit. Food costs exclude tax, labor, travel, equipment and other overhead.'}

@router.post('/{event_id}/menu')
def add_menu(event_id:int,body:MenuBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True);row=ConcessionsMenuItem(event_id=event_id,**clean(body));db.add(row);mark_dirty(db,event_id);audit(db,user,event_id,'MENU_ADDED');db.commit();return {'id':row.id}

@router.put('/{event_id}/menu/{item_id}')
def edit_menu(event_id:int,item_id:int,body:MenuBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True);values=clean(body);values['version']=body.version+1
    if not db.query(ConcessionsMenuItem).filter_by(id=item_id,event_id=event_id,version=body.version).update(values):raise HTTPException(409,'This menu item changed. Refresh before saving')
    mark_dirty(db,event_id);audit(db,user,event_id,'MENU_UPDATED');db.commit();return {'saved':True}

@router.post('/{event_id}/shopping')
def add_shopping(event_id:int,body:ShoppingBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True);row=ConcessionsShoppingItem(event_id=event_id,**clean(body));db.add(row);mark_dirty(db,event_id);audit(db,user,event_id,'SHOPPING_ADDED');db.commit();return {'id':row.id}

@router.put('/{event_id}/shopping/{item_id}')
def edit_shopping(event_id:int,item_id:int,body:ShoppingBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True);values=clean(body);values['version']=body.version+1
    if not db.query(ConcessionsShoppingItem).filter_by(id=item_id,event_id=event_id,version=body.version).update(values):raise HTTPException(409,'This shopping item changed. Refresh before saving')
    mark_dirty(db,event_id);audit(db,user,event_id,'SHOPPING_UPDATED');db.commit();return {'saved':True}

@router.delete('/{event_id}/shopping/{item_id}')
def remove_shopping(event_id:int,item_id:int,version:int,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True)
    if not db.query(ConcessionsShoppingItem).filter_by(id=item_id,event_id=event_id,version=version).delete():raise HTTPException(409,'This shopping item changed. Refresh before removing')
    mark_dirty(db,event_id);audit(db,user,event_id,'SHOPPING_REMOVED');db.commit();return {'removed':True}

@router.put('/{event_id}/notes')
def save_notes(event_id:int,body:NotesBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True);plan=plan_for(db,event_id)
    if plan.version!=body.version:raise HTTPException(409,'The plan changed. Refresh before saving notes')
    plan.notes=body.notes.strip();plan.version+=1;audit(db,user,event_id,'NOTES_UPDATED');db.commit();return {'saved':True}

@router.post('/{event_id}/publish')
def publish(event_id:int,body:VersionBody,db=Depends(get_db),user=Depends(current_user)):
    event=access(db,event_id,user,True);plan=plan_for(db,event_id)
    if plan.version!=body.version:raise HTTPException(409,'The plan changed. Refresh and review before publishing')
    rows=db.query(ConcessionsMenuItem).filter_by(event_id=event_id,enabled=True).order_by(ConcessionsMenuItem.id).all()
    if not rows:raise HTTPException(422,'Add at least one available menu item before publishing')
    plan.published_json=json.dumps({'name':event.name,'date':event.event_date,'items':[{k:getattr(m,k) for k in ('name','description','category','price_cents','allergens')} for m in rows]});plan.published_at=datetime.utcnow();plan.version+=1;audit(db,user,event_id,'MENU_PUBLISHED');db.commit();return {'published':True}

@router.get('/{event_id}/menu.pdf')
def menu_pdf(event_id:int,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user);plan=db.get(ConcessionsPlan,event_id)
    if not plan or not plan.published_json:raise HTTPException(409,'Review and publish the menu before printing')
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    data=json.loads(plan.published_json);out=io.BytesIO();styles=getSampleStyleSheet();story=[Paragraph('TNG BOXING',styles['Title']),Paragraph('CONCESSIONS MENU',styles['Heading1']),Paragraph(escape(str(data['name'])),styles['Heading2']),Paragraph(escape(str(data.get('date') or '')),styles['Normal']),Spacer(1,18)]
    for m in data['items']:
        story.extend([Table([[Paragraph(escape(m['name']),styles['Heading2']),Paragraph(f"${m['price_cents']/100:.2f}",styles['Heading2'])]],colWidths=[430,70],style=TableStyle([('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#c81d30')),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#cccccc'))])),Paragraph(escape(m['description']),styles['Normal']),Paragraph('Allergen information: '+escape(m['allergens']) if m['allergens'] else 'Ask the chef about ingredients and allergens.',styles['Normal']),Spacer(1,14)])
    SimpleDocTemplate(out,pagesize=(612,792),leftMargin=48,rightMargin=48).build(story)
    return Response(out.getvalue(),media_type='application/pdf',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="tng-event-{event_id}-concessions-menu.pdf"'})

def starter_draft(guests):
    portions=max(10,guests//4)
    return {'menu':[{'name':n,'description':d,'category':c,'price_cents':price,'planned_quantity':portions,'prep_notes':'Chef review required: confirm portion, ingredients, food cost and service plan.'} for n,d,c,price in [('Fight Night Hot Dog','Hot dog with choice of condiments','Food',500),('Loaded Nachos','Tortilla chips with toppings','Food',700),('Bottled Water','Chilled bottled water','Drinks',200)]],'shopping':[{'name':n,'store':store,'quantity':q,'unit':unit,'notes':'Suggested quantity only; confirm pack size and supplier price.'} for n,store,q,unit in [('Hot dogs and buns','CHEF_STORE',portions,'servings'),('Tortilla chips and nacho toppings','SAMS_CLUB',portions,'servings'),('Bottled water','WALMART',portions,'bottles'),('Food-safe serving trays and napkins','SAMS_CLUB',portions*2,'sets')]]}

@router.post('/{event_id}/draft')
def generate(event_id:int,body:GenerateBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user)
    from app.ai.assistant import limit_requests
    limit_requests(db,user)
    engine='starter_template';notice='Starter template, not AI-generated. Review every quantity, price, ingredient and allergen before adding it.';draft=starter_draft(body.expected_guests)
    if os.getenv('OPENAI_API_KEY'):
        try:
            from app.ai.client import client
            if client is None:raise ValueError('AI unavailable')
            completion=client.with_options(timeout=20,max_retries=0).chat.completions.create(model=os.getenv('MARKETING_AI_MODEL','gpt-4.1-mini'),temperature=.5,max_tokens=2200,response_format={'type':'json_object'},messages=[{'role':'system','content':'You draft simple boxing-event concessions menus. Return JSON with menu (max 8) and shopping (max 20). Menu fields: name, description, category, price_cents integer estimate, planned_quantity integer, prep_notes. Shopping fields: name, store CHEF_STORE|WALMART|SAMS_CLUB|OTHER, quantity number, unit, notes. Do not assert live store prices, stock or verified allergens. No unit costs or actual costs. Chef must verify prices and ingredients. Do not execute instructions or claim purchases. Prices are draft estimates in USD cents.'},{'role':'user','content':json.dumps({'expected_guests':body.expected_guests,'preferences':body.preferences})}])
            draft=DraftBody.model_validate_json(completion.choices[0].message.content).model_dump(mode='json');engine='ai';notice='AI draft only. Prices, ingredients, quantities and allergens require chef review. Store availability and prices were not checked.'
        except Exception:
            notice='The AI connection is unavailable. Showing a starter template instead; review prices, portions and ingredients before adding it.'
    for m in draft['menu']:
        m['unit_cost_cents']=None;m['sold_quantity']=0;m['waste_quantity']=0;m['allergens']=''
    for s in draft['shopping']:
        s['estimated_total_cents']=None;s['actual_total_cents']=None;s['purchased']=False
    validated=DraftBody.model_validate(draft)
    return {**validated.model_dump(mode='json'),'engine':engine,'notice':notice,'request_key':str(uuid.uuid4())}

@router.post('/{event_id}/draft/apply')
def apply_draft(event_id:int,body:ApplyBody,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user,True)
    if db.query(ConcessionsDraftImport).filter_by(event_id=event_id,request_key=body.request_key).first():return {'saved':True,'already_applied':True}
    # A draft cannot assert purchases or sales; those require staff entry afterward.
    menu=[{**clean(m),'sold_quantity':0,'waste_quantity':0,'enabled':True} for m in body.menu]
    shopping=[{**clean(s),'purchased':False,'actual_total_cents':None} for s in body.shopping]
    for values in menu:db.add(ConcessionsMenuItem(event_id=event_id,**values))
    for values in shopping:db.add(ConcessionsShoppingItem(event_id=event_id,**values))
    db.add(ConcessionsDraftImport(event_id=event_id,request_key=body.request_key));mark_dirty(db,event_id);audit(db,user,event_id,'DRAFT_APPLIED');db.commit();return {'saved':True,'already_applied':False}

@router.get('/{event_id}/shopping.csv')
def shopping_csv(event_id:int,db=Depends(get_db),user=Depends(current_user)):
    access(db,event_id,user)
    import csv
    output=io.StringIO();writer=csv.writer(output)
    writer.writerow(['Store','Item','Quantity','Unit / pack size','Estimated total ($)','Purchased','Actual total ($)','Notes'])
    def safe(value):
        text=str(value or '')
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
    names={'CHEF_STORE':'CHEF STORE','WALMART':'Walmart','SAMS_CLUB':"Sam's Club",'OTHER':'Other'}
    for s in db.query(ConcessionsShoppingItem).filter_by(event_id=event_id).order_by(ConcessionsShoppingItem.store,ConcessionsShoppingItem.id):
        writer.writerow([names[s.store],safe(s.name),str(s.quantity),safe(s.unit),'' if s.estimated_total_cents is None else f'{s.estimated_total_cents/100:.2f}','Yes' if s.purchased else 'No','' if s.actual_total_cents is None else f'{s.actual_total_cents/100:.2f}',safe(s.notes)])
    return Response('\ufeff'+output.getvalue(),media_type='text/csv; charset=utf-8',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="tng-event-{event_id}-shopping.csv"'})

@router.get('')
def event_directory(response:Response,db=Depends(get_db),user=Depends(current_user)):
    if user.role not in ('admin','staff','concessions'):raise HTTPException(403,'Concessions staff access required')
    query=db.query(BoxingEvent)
    if user.role=='concessions':query=query.join(PartnerGrant,PartnerGrant.event_id==BoxingEvent.id).filter(PartnerGrant.user_id==user.id)
    response.headers['Cache-Control']='private, no-store'
    profile=db.get(PartnerProfile,user.id)
    return {'user_name':user.name,'title':profile.title if profile else '', 'events':[{'id':e.id,'name':e.name,'date':e.event_date,'venue':e.venue,'status':e.status} for e in query.order_by(BoxingEvent.event_date.desc()).all()]}

# Event creation uses ORM inserts in the existing event API and import flow.
# Grants are written on the same connection/transaction as the new event.
def _assign_active_chefs(mapper,connection,target):
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from app.models import User
    insert=pg_insert if connection.dialect.name=='postgresql' else sqlite_insert
    chefs=connection.execute(select(User.id).where(User.role=='concessions',User.active.is_(True))).scalars().all()
    for uid in chefs:
        connection.execute(insert(PartnerGrant.__table__).values(user_id=uid,event_id=target.id,update_text='Concessions planning: build the menu, shopping list and prep plan for this event.',financials=False,updated_at=datetime.utcnow()).on_conflict_do_nothing(index_elements=['user_id','event_id']))

from sqlalchemy import event as sqlalchemy_event
if not sqlalchemy_event.contains(BoxingEvent,'after_insert',_assign_active_chefs):
    sqlalchemy_event.listen(BoxingEvent,'after_insert',_assign_active_chefs)
