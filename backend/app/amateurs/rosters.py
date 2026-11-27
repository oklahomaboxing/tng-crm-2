"""Private, lossless amateur roster intake. No eligibility inferred from an upload."""
import calendar,csv,hashlib,io,json,re,zipfile
from datetime import date,datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Response
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import Column,Integer,String,Text,Date,DateTime,JSON,Boolean,ForeignKey,UniqueConstraint,text
from sqlalchemy.exc import IntegrityError
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent
from .experience import experience_class,POLICY as EXPERIENCE_POLICY
router=APIRouter(prefix='/api/amateurs',tags=['Amateur matchmaking'])
DEFAULT_PREFERENCES={'max_bout_gap':5,'allow_same_club':False,'allow_coed_peewee':False,'max_unlimited_weight_gap_lb':20,'allow_novice_open_consideration':True}
SOURCE='https://assets.contentstack.io/v3/assets/blteb7d012fc7ebef7f/blt5ff28f6e78e9624d/695ed2d8b45570d8a64b74b9/USA_Boxing_Rule_Book_Revisions_-_1.1.2026.pdf'

class AmateurRoster(Base):
    __tablename__='amateur_rosters'
    id=Column(Integer,primary_key=True)
    name=Column(String(160),nullable=False)
    file_name=Column(String(180),nullable=False)
    file_hash=Column(String(64),unique=True,nullable=False)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=True)
    competition_date=Column(Date,nullable=True)
    created_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
    version=Column(Integer,default=1,nullable=False)
    preferences=Column(JSON,default=lambda:dict(DEFAULT_PREFERENCES),nullable=False)

class AmateurEntry(Base):
    __tablename__='amateur_roster_entries'
    __table_args__=(UniqueConstraint('roster_id','row_number',name='uq_amateur_roster_row'),)
    id=Column(Integer,primary_key=True)
    roster_id=Column(Integer,ForeignKey('amateur_rosters.id'),nullable=False,index=True)
    row_number=Column(Integer,nullable=False)
    data=Column(JSON,nullable=False)
    issues=Column(JSON,nullable=False)
    excluded=Column(Boolean,default=False,nullable=False)
    version=Column(Integer,default=1,nullable=False)

class AmateurRulebook(Base):
    __tablename__='amateur_verified_rulebooks'
    id=Column(Integer,primary_key=True)
    year=Column(Integer,unique=True,nullable=False)
    title=Column(String(200),nullable=False)
    source_url=Column(String(1000),nullable=False)
    document_sha256=Column(String(64),nullable=False)
    appendix_text=Column(Text,nullable=False)
    # Typed matching constraints are installed only after official-source review.
    config=Column(JSON,nullable=False)
    verified_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    verified_at=Column(DateTime,default=datetime.utcnow,nullable=False)
    enabled=Column(Boolean,default=False,nullable=False)

class AmateurMatchRun(Base):
    __tablename__='amateur_match_runs'
    id=Column(Integer,primary_key=True)
    roster_id=Column(Integer,ForeignKey('amateur_rosters.id'),nullable=False,index=True)
    rulebook_id=Column(Integer,ForeignKey('amateur_verified_rulebooks.id'),nullable=False)
    competition_date=Column(Date,nullable=False)
    roster_fingerprint=Column(String(64),nullable=False)
    result=Column(JSON,nullable=False)
    created_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def access(user=Depends(current_user)):
    if user.role not in ('admin','staff','matchmaker'):raise HTTPException(403,'Amateur matchmaker or event staff access required')
    return user

def audit(db,user,action,roster_id):db.add(SecurityLog(user_id=user.id,action='AMATEUR_'+action,description=f'Amateur roster {roster_id} updated'))
def normal_header(s):return re.sub(r'[^a-z0-9]','',str(s or '').strip().lower())
HEADERS={'memberid':'member_id','firstname':'first_name','lastname':'last_name','dateofbirth':'dob','dob':'dob','age':'reported_age','sex':'sex','gender':'sex','weight':'declared_weight','numberofbouts':'bouts','bouts':'bouts','coachfirstname':'coach_first_name','coachlastname':'coach_last_name','lbc':'lbc','city':'city','state':'state','boxingclubname':'club','club':'club','gym':'club','wins':'wins','ageclassification':'masters_class'}
REQUIRED={'member_id','first_name','last_name','dob','sex','declared_weight','bouts','club'}

def parse_dob(v):
    if isinstance(v,(date,datetime)):return v.date() if isinstance(v,datetime) else v
    for fmt in ('%m/%d/%Y','%Y-%m-%d','%m/%d/%y'):
        try:return datetime.strptime(str(v).strip(),fmt).date()
        except ValueError:pass
    raise ValueError('Birth date must be MM/DD/YYYY or YYYY-MM-DD')

def normalize_row(raw):
    d={k:str(v if v is not None else '').strip() for k,v in raw.items()};issues=[]
    for k in ('member_id','first_name','last_name','club'):
        if not d.get(k):issues.append(k.replace('_',' ')+' is missing')
        elif len(d[k])>160:issues.append(k.replace('_',' ')+' is too long')
    if d.get('member_id') and not re.fullmatch(r'[0-9A-Za-z-]{1,40}',d['member_id']):issues.append('Member ID contains unsupported characters')
    try:
        dob=parse_dob(raw.get('dob',''))
        if dob>=date.today() or date.today().year-dob.year>100:raise ValueError('Birth date is outside the supported range')
        d['dob']=dob.isoformat()
    except ValueError as e:issues.append(str(e))
    sex=d.get('sex','').upper();sex={'M':'MALE','F':'FEMALE'}.get(sex,sex);d['sex']=sex
    if sex not in ('MALE','FEMALE'):issues.append('Sex category requires review before matching')
    weight=d.get('declared_weight','');match=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)?(?:\s*\([^)]*\))?\s*',weight,re.I)
    kg=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*kg\s*',weight,re.I)
    try:
        value=float(match[1]) if match else float(kg[1])*2.2046226218 if kg else None
        if value is None or not 20<=value<=600:raise ValueError()
        d['weight_lb']=round(value,3)
    except (ValueError,TypeError):d['weight_lb']=None;issues.append('Declared weight is missing or invalid')
    try:
        val=d.get('bouts','')
        if not re.fullmatch(r'\d{1,4}',val):raise ValueError()
        d['bouts']=int(val)
        if d['bouts']>1000:raise ValueError()
    except ValueError:d['bouts']=None;issues.append('Number of bouts must be a whole number from 0 to 1000')
    wins=d.get('wins','')
    if wins:
        if not wins.isdigit() or d['bouts'] is None or int(wins)>d['bouts']:issues.append('Reported wins must not exceed total bouts')
        else:d['wins']=int(wins)
    else:d['wins']=None
    d['masters_class']=d.get('masters_class','').lower()
    if d['masters_class'] not in ('','elite','masters','both'):issues.append('Registered age classification must be elite, masters or both')
    d['coach']=' '.join(d.get(k,'') for k in ('coach_first_name','coach_last_name')).strip()
    return d,issues

def read_rows(content,filename):
    if filename.lower().endswith('.csv'):
        try:source=content.decode('utf-8-sig')
        except UnicodeDecodeError:raise HTTPException(422,'Save the CSV with UTF-8 encoding')
        try:rows=list(csv.reader(io.StringIO(source),strict=True))
        except csv.Error:raise HTTPException(422,'This CSV could not be read. Check its quoting and column structure')
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if len(z.infolist())>500 or sum(x.file_size for x in z.infolist())>20*1024*1024:raise ValueError()
            from openpyxl import load_workbook
            book=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
            try:
                sheet=book.active
                if sheet.max_row and sheet.max_row>1001:raise ValueError()
                rows=list(sheet.iter_rows(values_only=True))
            finally:book.close()
        except Exception:raise HTTPException(422,'This XLSX could not be read or exceeds the 1,000-boxer / 20 MB expanded limit')
    else:raise HTTPException(422,'Upload a CSV or XLSX roster')
    rows=[r for r in rows if any(str(x or '').strip() for x in r)]
    if len(rows)<2 or len(rows)>1001:raise HTTPException(422,'Upload a header and 1–1,000 boxer rows')
    if len(rows[0])>50:raise HTTPException(422,'Too many columns')
    headers=[HEADERS.get(normal_header(c)) for c in rows[0]]
    if len([h for h in headers if h])!=len(set(h for h in headers if h)):raise HTTPException(422,'Duplicate roster columns')
    if not REQUIRED.issubset(headers):raise HTTPException(422,'Missing columns: '+', '.join(sorted(REQUIRED-set(headers))))
    result=[];seen={}
    for number,row in enumerate(rows[1:],2):
        raw={k:(row[i] if i<len(row) else '') for i,k in enumerate(headers) if k};d,issues=normalize_row(raw)
        if len(row)>len(headers) and any(str(x or '').strip() for x in row[len(headers):]):issues.append('Row contains extra columns')
        member=d.get('member_id','')
        if member and member in seen:
            issues.append('Duplicate USA Boxing member ID in this roster')
            result[seen[member]][2].append('Duplicate USA Boxing member ID in this roster')
        elif member:seen[member]=len(result)
        result.append([number,d,issues])
    return result

def roster_for(db,rid):
    r=db.get(AmateurRoster,rid)
    if not r:raise HTTPException(404,'Amateur roster not found')
    return r

def entry_dict(row,event_date=None):
    d=dict(row.data);age=None;calendar_age=None
    try:
        dob=date.fromisoformat(d['dob'])
        if event_date:age=event_date.year-dob.year-((event_date.month,event_date.day)<(dob.month,dob.day));calendar_age=event_date.year-dob.year
    except (ValueError,KeyError):pass
    return {'id':row.id,'row_number':row.row_number,'data':d,'issues':row.issues,'excluded':row.excluded,'version':row.version,'experience_class':experience_class(d.get('bouts')),'birthday_age_at_event':age,'calendar_year_age':calendar_age}

def rule_status(db,year):
    rule=db.query(AmateurRulebook).filter_by(year=year,enabled=True).first()
    from .rules_2026 import DOCUMENT_SHA256,IMPLEMENTATION
    ready=bool(rule and rule.appendix_text.strip() and rule.document_sha256==DOCUMENT_SHA256 and rule.config.get('implementation')==IMPLEMENTATION)
    return {'year':year,'reference_year':rule.config.get('reference_year') if ready else 2026,'verified':ready,'title':rule.title if ready else '2026 USA Boxing Appendix F source review pending','source_url':rule.source_url if ready else SOURCE,'message':'The 2026 reference was reviewed for local matched-bout proposals. It is the current requested reference, not a 2027 edition. Both coaches and the Official in Charge must review every proposal.' if ready else 'Automatic matching is disabled until the 2026 Appendix F document is reviewed and its limits are installed for this event year. The 2026 edition is the requested reference; it is not represented as a 2027 rulebook.'}

@router.get('/rosters')
def list_rosters(response:Response,db=Depends(get_db),user=Depends(access)):
    response.headers['Cache-Control']='private, no-store'
    rows=db.query(AmateurRoster).order_by(AmateurRoster.id.desc()).all()
    return [{'id':r.id,'name':r.name,'file_name':r.file_name,'competition_date':r.competition_date.isoformat() if r.competition_date else None,'event_id':r.event_id} for r in rows]

@router.post('/rosters/import')
async def import_roster(file:UploadFile=File(...),db=Depends(get_db),user=Depends(access)):
    content=await file.read(5*1024*1024+1)
    if len(content)>5*1024*1024:raise HTTPException(413,'Roster exceeds the 5 MB upload limit')
    filename=(file.filename or 'roster.csv').replace('\\','/').split('/')[-1][:180];digest=hashlib.sha256(content).hexdigest()
    if db.get_bind().dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':int.from_bytes(bytes.fromhex(digest)[:8],'big',signed=True)})
    prior=db.query(AmateurRoster).filter_by(file_hash=digest).first()
    if prior:return {'roster_id':prior.id,'existing':True,'rows':db.query(AmateurEntry).filter_by(roster_id=prior.id).count()}
    rows=read_rows(content,filename);r=AmateurRoster(name=filename.rsplit('.',1)[0][:160],file_name=filename,file_hash=digest,created_by=user.id);db.add(r);db.flush()
    for number,data,issues in rows:db.add(AmateurEntry(roster_id=r.id,row_number=number,data=data,issues=issues,excluded=False))
    audit(db,user,'ROSTER_IMPORTED',r.id)
    try:db.commit()
    except IntegrityError:
        db.rollback();prior=db.query(AmateurRoster).filter_by(file_hash=digest).first()
        if prior:return {'roster_id':prior.id,'existing':True,'rows':db.query(AmateurEntry).filter_by(roster_id=prior.id).count()}
        raise
    return {'roster_id':r.id,'existing':False,'rows':len(rows),'needs_review':sum(bool(x[2]) for x in rows)}

@router.get('/rosters/{roster_id}')
def get_roster(roster_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
    response.headers['Cache-Control']='private, no-store';r=roster_for(db,roster_id);rows=db.query(AmateurEntry).filter_by(roster_id=r.id).order_by(AmateurEntry.row_number).all()
    latest=db.query(AmateurMatchRun).filter_by(roster_id=r.id).order_by(AmateurMatchRun.id.desc()).first()
    last_match=None
    if latest:
        from .matching import roster_fingerprint
        rule=db.get(AmateurRulebook,latest.rulebook_id)
        stale=not r.competition_date or not rule or not rule.enabled or latest.competition_date!=r.competition_date or latest.roster_fingerprint!=roster_fingerprint(r,rule,rows)
        last_match={'run_id':latest.id,**latest.result,'stale':bool(stale)}
    return {'id':r.id,'name':r.name,'file_name':r.file_name,'competition_date':r.competition_date.isoformat() if r.competition_date else None,'event_id':r.event_id,'version':r.version,'last_match':last_match,'experience_policy':EXPERIENCE_POLICY,'preferences':{**DEFAULT_PREFERENCES,**(r.preferences or {})},'entries':[entry_dict(x,r.competition_date) for x in rows],'rules':rule_status(db,r.competition_date.year if r.competition_date else 2027),'notice':'Roster weights and bout counts are declared values, not weigh-in results or verified competition history. Upload does not verify USA Boxing membership, medical clearance or eligibility.'}

class MatchPreferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    allow_novice_open_consideration:bool=True
    max_bout_gap:int=Field(default=5,ge=0,le=1000)
    allow_same_club:bool=False
    allow_coed_peewee:bool=False
    max_unlimited_weight_gap_lb:float=Field(default=20,ge=0,le=1000)

class RosterSettings(BaseModel):
    name:str=Field(min_length=2,max_length=160)
    competition_date:date
    event_id:int|None=None
    version:int=Field(ge=1)
    preferences:MatchPreferences=Field(default_factory=MatchPreferences)

@router.put('/rosters/{roster_id}/settings')
def update_roster(roster_id:int,body:RosterSettings,db=Depends(get_db),user=Depends(access)):
    r=db.query(AmateurRoster).filter_by(id=roster_id).with_for_update().first()
    if not r:raise HTTPException(404,'Roster not found')
    if r.version!=body.version:raise HTTPException(409,'Roster settings changed. Refresh before saving')
    if body.event_id:
        event=db.get(BoxingEvent,body.event_id)
        if not event:raise HTTPException(404,'Event not found')
        if (event.event_date or '')[:10]!=body.competition_date.isoformat():raise HTTPException(422,'Competition date must match the selected TNG event date')
    r.name=body.name.strip();r.competition_date=body.competition_date;r.event_id=body.event_id;r.preferences=body.preferences.model_dump();r.version+=1;audit(db,user,'ROSTER_SETTINGS',r.id);db.commit();return {'saved':True}

class EntryUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    data:dict
    excluded:bool=False
    version:int=Field(ge=1)

@router.put('/rosters/{roster_id}/entries/{entry_id}')
def update_entry(roster_id:int,entry_id:int,body:EntryUpdate,db=Depends(get_db),user=Depends(access)):
    db.query(AmateurRoster).filter_by(id=roster_id).with_for_update().first();roster_for(db,roster_id);row=db.query(AmateurEntry).filter_by(id=entry_id,roster_id=roster_id).with_for_update().first()
    if not row:raise HTTPException(404,'Roster boxer not found')
    if row.version!=body.version:raise HTTPException(409,'Boxer details changed. Refresh before saving')
    if len(json.dumps(body.data))>10000:raise HTTPException(422,'Boxer details are too large')
    allowed=set(HEADERS.values());raw={k:v for k,v in body.data.items() if k in allowed};data,issues=normalize_row(raw)
    for other in db.query(AmateurEntry).filter(AmateurEntry.roster_id==roster_id,AmateurEntry.id!=row.id):
        if data.get('member_id') and other.data.get('member_id')==data['member_id']:raise HTTPException(409,'Another roster entry has this member ID. Keep both flagged for review or correct the duplicate ID')
    row.data=data;row.issues=issues;row.excluded=body.excluded;row.version+=1;audit(db,user,'BOXER_UPDATED',roster_id);db.commit();return entry_dict(row)

@router.post('/rosters/{roster_id}/auto-match')
def auto_match(roster_id:int,db=Depends(get_db),user=Depends(access)):
    r=db.query(AmateurRoster).filter_by(id=roster_id).with_for_update().first()
    if not r:raise HTTPException(404,'Roster not found')
    if not r.competition_date:raise HTTPException(409,'Set the competition date before generating match proposals')
    status=rule_status(db,r.competition_date.year)
    if not status['verified']:raise HTTPException(409,status['message'])
    from .matching import generate
    return generate(db,r,user)

@router.get('/rosters/{roster_id}/matches')
def match_history(roster_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
    roster_for(db,roster_id);response.headers['Cache-Control']='private, no-store'
    rows=db.query(AmateurMatchRun).filter_by(roster_id=roster_id).order_by(AmateurMatchRun.id.desc()).limit(10).all()
    return [{'id':r.id,'competition_date':r.competition_date.isoformat(),'created_at':r.created_at.isoformat()+'Z','result':r.result} for r in rows]
