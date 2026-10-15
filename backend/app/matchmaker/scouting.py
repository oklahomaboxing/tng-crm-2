"""Separate prospect catalogue; research never changes the active fight roster."""
import hashlib
import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import Base, get_db
from app.core.dependencies import current_user
from app.core.permissions import require_matchmaker_access
from .discovery import public_url, SearchRequest, search_public_web

US_STATES = dict(zip('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(),
['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','District of Columbia','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']))
# Standard weight labels are research filters, not a certification of a boxer's division.
DIVISIONS = [('atomweight',102),('minimumweight',105),('light_flyweight',108),('flyweight',112),('super_flyweight',115),('bantamweight',118),('super_bantamweight',122),('featherweight',126),('super_featherweight',130),('lightweight',135),('super_lightweight',140),('welterweight',147),('super_welterweight',154),('middleweight',160),('super_middleweight',168),('light_heavyweight',175),('cruiserweight',200),('bridgerweight',224),('heavyweight',None)]
DIVISION_KEYS = {x[0] for x in DIVISIONS} | {'unknown'}
router = APIRouter(prefix='/api/boxing/scouting', tags=['boxer-scouting'])


class BoxerProspect(Base):
    __tablename__ = 'boxing_scouting_prospects'
    id = Column(Integer, primary_key=True)
    identity = Column(String(64), nullable=False, unique=True)
    name = Column(String(180), nullable=False, index=True)
    city = Column(String(120), default='')
    state = Column(String(2), nullable=False, index=True)
    division = Column(String(40), default='unknown', nullable=False, index=True)
    weight = Column(String(150), default='')
    record = Column(String(100), default='')
    gym_or_manager = Column(String(200), default='')
    business_phone = Column(String(60), default='')
    business_email = Column(String(180), default='')
    source_url = Column(String(2000), nullable=False)
    evidence = Column(Text, default='')
    last_activity = Column(String(300), default='')
    status = Column(String(24), default='new', nullable=False, index=True)
    availability = Column(String(24), default='unknown', nullable=False)
    notes = Column(Text, default='')
    updated_by = Column(Integer, nullable=False)
    researched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProspectCreate(BaseModel):
    name: str = Field(min_length=1,max_length=180)
    city: str = Field(default='',max_length=120)
    state: str
    division: str = 'unknown'
    weight: str = Field(default='',max_length=150)
    record: str = Field(default='',max_length=100)
    gym_or_manager: str = Field(default='',max_length=200)
    business_phone: str = Field(default='',max_length=60)
    business_email: str = Field(default='',max_length=180)
    source_url: str = Field(max_length=2000)
    evidence: str = Field(default='',max_length=1200)
    last_activity: str = Field(default='',max_length=300)

    @field_validator('name')
    @classmethod
    def nonblank(cls,v):
        if not v.strip():raise ValueError('Name is required')
        return v.strip()
    @field_validator('state')
    @classmethod
    def state_valid(cls,v):
        value=v.strip().upper()
        if value not in US_STATES:raise ValueError('Choose a US state')
        return value
    @field_validator('division')
    @classmethod
    def division_valid(cls,v):
        if v not in DIVISION_KEYS:raise ValueError('Choose a supported weight class')
        return v
    @field_validator('source_url')
    @classmethod
    def source_valid(cls,v):
        if not public_url(v):raise ValueError('A public HTTPS source is required')
        return v


def row_dict(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns if c.name not in ('identity','updated_by')}


def store_prospect(body, db, user):
    # Same name + state + source person is deduplicated across weight-class searches.
    # Different sources are not automatically merged: common names need human review.
    from .discovery import citation_key
    identity=hashlib.sha256((re.sub(r'\W+','',body.name.casefold())+'|'+body.state+'|'+citation_key(body.source_url)).encode()).hexdigest()
    row=db.query(BoxerProspect).filter_by(identity=identity).first()
    if row:return row,False
    data=body.model_dump()
    for key in ('business_phone','business_email'):
        if data[key] and data[key].casefold() not in body.evidence.casefold():data[key]=''
    row=BoxerProspect(identity=identity,updated_by=user.id,**data)
    db.add(row)
    try:db.commit();db.refresh(row)
    except IntegrityError:
        db.rollback();row=db.query(BoxerProspect).filter_by(identity=identity).first()
        if row is None:raise
        return row,False
    return row,True


@router.get('/options')
def options(user=Depends(current_user)):
    require_matchmaker_access(user)
    return {'states':US_STATES,'divisions':[{'key':k,'label':k.replace('_',' ').title(),'limit_lb':n} for k,n in DIVISIONS]}


@router.get('/prospects')
def list_prospects(q: str=Query('',max_length=150), state: str='', division: str='', status: str='', contact_only: bool=False,
                   page: int=Query(1,ge=1), page_size: int=Query(30,ge=1,le=100), db: Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user)
    query=db.query(BoxerProspect)
    if q.strip():
        value='%'+q.strip().replace('%','\\%').replace('_','\\_')+'%'
        query=query.filter(or_(BoxerProspect.name.ilike(value,escape='\\'),BoxerProspect.record.ilike(value,escape='\\'),BoxerProspect.city.ilike(value,escape='\\'),BoxerProspect.gym_or_manager.ilike(value,escape='\\')))
    if state:query=query.filter(BoxerProspect.state==state.upper())
    if division:query=query.filter(BoxerProspect.division==division)
    if status:query=query.filter(BoxerProspect.status==status)
    if contact_only:query=query.filter(or_(BoxerProspect.business_phone!='',BoxerProspect.business_email!=''))
    total=query.count()
    rows=query.order_by(BoxerProspect.updated_at.desc(),BoxerProspect.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'items':[row_dict(r) for r in rows],'total':total,'page':page,'page_size':page_size,
        'database_total':db.query(BoxerProspect).count(),'shortlisted':db.query(BoxerProspect).filter_by(status='shortlisted').count()}


@router.post('/prospects')
def create_prospect(body:ProspectCreate,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user)
    row,created=store_prospect(body,db,user)
    return {'prospect':row_dict(row),'created':created}


class ProspectUpdate(BaseModel):
    status:str
    availability:str='unknown'
    notes:str=Field(default='',max_length=4000)


@router.patch('/prospects/{pid}')
def update_prospect(pid:int,body:ProspectUpdate,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user)
    if body.status not in ('new','reviewing','shortlisted','contacted','passed') or body.availability not in ('unknown','available','unavailable'):
        raise HTTPException(400,'Invalid prospect status')
    row=db.get(BoxerProspect,pid)
    if not row:raise HTTPException(404,'Prospect not found')
    row.status=body.status;row.availability=body.availability;row.notes=body.notes.strip();row.updated_by=user.id
    db.commit();db.refresh(row)
    return row_dict(row)


class DiscoveryBatch(BaseModel):
    division:str
    states:list[str]=Field(default_factory=lambda:list(US_STATES),min_length=1,max_length=51)
    query:str=Field(default='',max_length=200)
    @field_validator('division')
    @classmethod
    def division_valid(cls,v):
        if v not in DIVISION_KEYS or v=='unknown':raise ValueError('Choose a weight class')
        return v
    @field_validator('states')
    @classmethod
    def state_valid(cls,v):
        if any(x not in US_STATES for x in v):raise ValueError('Choose US states')
        return list(dict.fromkeys(v))


@router.post('/discover')
def discover_batch(body:DiscoveryBatch,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user)
    index=next(i for i,x in enumerate(DIVISIONS) if x[0]==body.division)
    upper=DIVISIONS[index][1]
    lower=DIVISIONS[index-1][1] if index else 50
    # Heavyweight has no upper research limit; bridgerweight inclusion is source-specific.
    if body.division=='heavyweight':lower=200
    request=SearchRequest(kind='fighter',states=body.states,weight_min=lower,weight_max=upper,
        query=(f'Find currently competing professional boxers based in the USA in {body.division.replace("_"," ")}. Prefer approachable developing fighters, but include any properly sourced professional. Exclude amateurs-only, MMA, bare-knuckle, retired boxers. '+body.query)[:300])
    results=search_public_web(request)
    inserted=0;found=[]
    for lead in results['leads']:
        numbers=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',lead.get('weight',''))]
        if len(numbers)==1 and (numbers[0] < lower or (upper is not None and numbers[0] > upper)):
            continue
        # Combat-sport records from these sources do not establish a pro boxing record.
        if any(domain in lead['source_url'].split('/')[2].lower() for domain in ('bkfc.com','ufc.com','sherdog.com')):
            continue
        data={k:v for k,v in lead.items() if k in ProspectCreate.model_fields}
        data['division']=body.division if lead.get('weight') else 'unknown'
        # This is the searched weight group, not a verified sanctioning classification.
        row,created=store_prospect(ProspectCreate(**data),db,user)
        inserted+=int(created);found.append(row_dict(row))
    return {'division':body.division,'found':len(found),'inserted':inserted,'prospects':found}
