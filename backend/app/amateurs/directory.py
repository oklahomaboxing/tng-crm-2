"""Private amateur club/contact directory with source provenance and conservative identity merges."""
import csv,io,json,re,hashlib
from html.parser import HTMLParser
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Response,Query
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import Column,Integer,String,Text,JSON,Boolean,DateTime,UniqueConstraint,text
from app.database import Base,get_db
from app.models import SecurityLog
from app.ticketing.delivery import normalize_ticket_phone
from .rosters import access
router=APIRouter(prefix='/api/amateurs/directory',tags=['Amateur contacts'])
ROLES=['official_in_charge','referee','judge','timekeeper','ringside_physician','clerk','other']
CLUB_HEADERS=['ClubName','Phone','ClubEmail','ClubContact_FName','ClubContact_LName','ClubContact_Email','ClubContact_Phone','ClubRep','ClubRep_Email','Club_Address','Club_Address2','Club_City','Club_State','Club_Zip']
MEMBER_HEADERS=['Member ID','Last Name','First Name','Address','Address2','City','State','Zip','Country','Email','Phone','DOB','Mbr Type','Mbr Status','Club Name','LBC Name']
class DirectoryContact(Base):
 __tablename__='amateur_directory_contacts'
 id=Column(Integer,primary_key=True)
 identity_key=Column(String(64),unique=True,nullable=False)
 kind=Column(String(12),nullable=False,index=True)
 name=Column(String(200),nullable=False)
 emails=Column(JSON,default=list,nullable=False)
 phones=Column(JSON,default=list,nullable=False)
 details=Column(JSON,default=dict,nullable=False)
 observations=Column(JSON,default=list,nullable=False)
 roles=Column(JSON,default=list,nullable=False)
 role_verified=Column(Boolean,default=False,nullable=False)
 sms_consent=Column(Boolean,default=False,nullable=False)
 consent_note=Column(String(500),default='',nullable=False)
 consent_at=Column(DateTime,nullable=True)
 active=Column(Boolean,default=True,nullable=False)
 issues=Column(JSON,default=list,nullable=False)
 version=Column(Integer,default=1,nullable=False)
class DirectoryImport(Base):
 __tablename__='amateur_directory_imports'
 id=Column(Integer,primary_key=True)
 digest=Column(String(64),unique=True,nullable=False)
 filenames=Column(JSON,nullable=False)
 source_text=Column(Text,nullable=False)
 result=Column(JSON,nullable=False)
 created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def key(value):return hashlib.sha256(value.encode()).hexdigest()
def words(value):return re.sub(r'[^a-z0-9]','',value.casefold())
def lock(db):
 if db.get_bind().dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(8426202602)'))
class TableReader(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=='tr':self.row=[]
  if tag in ('td','th'):self.cell=''
 def handle_data(self,value):
  if self.cell is not None:self.cell+=value
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.cell is not None:
   if self.row is not None:self.row.append(self.cell.strip())
   self.cell=None
  if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None

def parse_export(content,filename):
 try:s=content.decode('utf-8-sig')
 except UnicodeDecodeError:raise HTTPException(422,'Export as UTF-8 CSV/TXT or an HTML Excel export')
 if '<html' in s[:200].lower():
  parser=TableReader();parser.feed(s);rows=parser.rows
 elif '\n' in s or '\r' in s:
  rows=list(csv.reader(io.StringIO(s),delimiter='\t' if '\t' in s.splitlines()[0] else ','))
 else:
  a=s.split('\t')
  if s.startswith('ClubName\t'):
   headers=CLUB_HEADERS;step=13;current=a[13].removeprefix('Club_Zip');rows=[headers]
   if (len(a)-14)%13:raise HTTPException(422,'Flattened club export has an incomplete record. Use the Excel export')
   for j in range(13,len(a)-1,step):
    tail=a[j+step];m=re.match(r'^(\d{5}(?:-\d{4})?)(.*)$',tail)
    if not m:raise HTTPException(422,'A flattened club ZIP/record boundary is ambiguous. Use the Excel export')
    rows.append([current]+a[j+1:j+step]+[m[1]]);current=m[2]
   if current:raise HTTPException(422,'Flattened export has an unfinished final club')
  elif s.startswith('Member ID\t'):
   headers=MEMBER_HEADERS;step=15;current=a[15].removeprefix('LBC Name');rows=[headers]
   if (len(a)-16)%15:raise HTTPException(422,'Flattened membership export has an incomplete record')
   for j in range(15,len(a)-1,step):
    tail=a[j+step];m=re.fullmatch(r'(.*?)(\d+)',tail) if j+step<len(a)-1 else None
    if not current.isdigit():raise HTTPException(422,'Member ID/record boundary needs review. Export CSV with line breaks')
    rows.append([current]+a[j+1:j+step]+[m[1] if m else tail]);current=m[2] if m else ''
   if current:raise HTTPException(422,'Flattened membership export has an unfinished final record')
  else:raise HTTPException(422,'Unrecognized contact export headers')
 rows=[r for r in rows if any(str(x).strip() for x in r)]
 if len(rows)<2 or len(rows)>5001:raise HTTPException(422,'Use an export with 1–5,000 contacts')
 headers=[x.strip() for x in rows[0]];kind='club' if headers==CLUB_HEADERS else 'person' if headers==MEMBER_HEADERS else None
 if not kind:raise HTTPException(422,'Use the supplied USA Boxing club or membership export columns')
 if any(len(r)!=len(headers) for r in rows):raise HTTPException(422,'Some rows have inconsistent column counts')
 return kind,[{k:str(v).strip() for k,v in zip(headers,r)} for r in rows[1:]]

def normalize(kind,row):
 issues=[]
 if kind=='club':
  name=row['ClubName'];identity='club:'+words(name)+'|'+words(row['Club_City'])+'|'+words(row['Club_State']);emails=[row[k] for k in ('ClubEmail','ClubContact_Email','ClubRep_Email')];phones=[row[k] for k in ('Phone','ClubContact_Phone')]
  detail={'city':row['Club_City'],'state':row['Club_State'],'club':name,'contact_name':(row['ClubContact_FName']+' '+row['ClubContact_LName']).strip(),'representative':row['ClubRep'],'address':row['Club_Address'],'address2':row['Club_Address2'],'zip':row['Club_Zip'],'categories':['club']}
 else:
  name=(row['First Name']+' '+row['Last Name']).strip();identity='person:usab:'+row['Member ID'];emails=[row['Email']];phones=[row['Phone']];detail={'member_id':row['Member ID'],'city':row['City'],'state':row['State'],'club':row['Club Name'],'lbc':row['LBC Name'],'categories':['non_athlete' if row['Mbr Type']=='Non-Athlete' else 'athlete' if row['Mbr Type']=='Athlete' else 'fitness'],'source_statuses':[row['Mbr Status']]}
  if row['Mbr Type']=='Non-Athlete':issues.append('Non-Athlete membership does not establish official/coach role or certification')
  if row['Mbr Status']!='Current':issues.append('Source membership status: '+row['Mbr Status']+'; verify current eligibility separately')
 if not name:raise HTTPException(422,'A source row has no name')
 good_emails=[]
 for value in emails:
  if not value:continue
  if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):good_emails.append(value.casefold())
  else:issues.append('Source email needs correction')
 good_phones=[]
 for value in phones:
  if not value:continue
  try:good_phones.append(normalize_ticket_phone(value))
  except ValueError:issues.append('Source phone needs correction')
 return identity,name,list(dict.fromkeys(good_emails)),list(dict.fromkeys(good_phones)),detail,issues

def serialize(c):return {k:getattr(c,k) for k in ('id','kind','name','emails','phones','details','roles','role_verified','sms_consent','consent_note','active','issues','version')}
@router.get('')
def list_contacts(response:Response,kind:str='person',category:str='all',q:str=Query('',max_length=160),page:int=Query(1,ge=1),state:str=Query('',max_length=100),db=Depends(get_db),user=Depends(access)):
 response.headers['Cache-Control']='private, no-store';rows=db.query(DirectoryContact).filter_by(kind=kind).order_by(DirectoryContact.name).all()
 if category=='official':rows=[c for c in rows if c.role_verified and c.roles]
 elif category!='all':rows=[c for c in rows if category in c.details.get('categories',[])]
 if state.strip():
  selected=state.strip().casefold();states={'ok','oklahoma'} if selected in {'ok','oklahoma'} else {selected}
  rows=[c for c in rows if str(c.details.get('state','')).strip().casefold() in states]
 if q.strip():rows=[c for c in rows if q.casefold() in json.dumps([c.name,c.emails,c.phones,c.details],ensure_ascii=False).casefold()]
 return {'total':len(rows),'page_size':25,'contacts':[serialize(c) for c in rows[(page-1)*25:page*25]],'roles':ROLES}
@router.get('/imports')
def imports(response:Response,db=Depends(get_db),user=Depends(access)):
 response.headers['Cache-Control']='private, no-store';return [{'id':r.id,'files':r.filenames,**r.result} for r in db.query(DirectoryImport).order_by(DirectoryImport.id.desc()).limit(100)]
@router.post('/import')
async def import_contacts(file:UploadFile=File(...),db=Depends(get_db),user=Depends(access)):
 content=await file.read(5*1024*1024+1)
 if len(content)>5*1024*1024:raise HTTPException(413,'Contact export exceeds 5 MB')
 digest=hashlib.sha256(content).hexdigest();filename=(file.filename or 'contacts').replace('\\','/').split('/')[-1][:180];lock(db);prior=db.query(DirectoryImport).filter_by(digest=digest).first()
 if prior and not prior.result.get('needs_review'):
  prior.filenames=list(dict.fromkeys(prior.filenames+[filename]));db.commit();return {**prior.result,'existing':True,'added':0,'merged':0}
 recovered=False
 try:kind,rows=parse_export(content,filename)
 except HTTPException as exc:
  kind=None
  try:raw=content.decode('utf-8-sig')
  except UnicodeDecodeError:raise exc
  for reference in db.query(DirectoryImport).order_by(DirectoryImport.id.desc()).limit(100):
   if reference.result.get('kind')!='club' or '<html' not in reference.source_text[:200].lower():continue
   _,candidates=parse_export(reference.source_text.encode(),reference.filenames[0]);canonical=''.join(CLUB_HEADERS)+''.join(''.join(r[k] for k in CLUB_HEADERS) for r in candidates)
   if re.sub(r'\s','',raw)==re.sub(r'\s','',canonical):kind='club';rows=candidates;recovered=True;break
  if kind is None:
   result={'kind':'review','rows':0,'added':0,'merged':0,'needs_review':True,'notice':exc.detail}
   if prior:prior.result=result;prior.filenames=list(dict.fromkeys(prior.filenames+[filename]))
   else:db.add(DirectoryImport(digest=digest,filenames=[filename],source_text=raw,result=result))
   db.commit();return result
 added=merged=0
 for ordinal,row in enumerate(rows,2):
  identity,name,emails,phones,detail,issues=normalize(kind,row);c=db.query(DirectoryContact).filter_by(identity_key=key(identity)).first()
  observation={'file':filename,'row':ordinal,'values':row,'recovered_from_equivalent_excel':recovered}
  if not c:
   c=DirectoryContact(identity_key=key(identity),kind=kind,name=name,emails=emails,phones=phones,details=detail,observations=[observation],issues=issues);db.add(c);db.flush();added+=1
  else:
   if kind=='person' and words(c.name)!=words(name):issues.append('Conflicting names share a source member ID; review observations before using this contact')
   c.emails=list(dict.fromkeys(c.emails+emails));c.phones=list(dict.fromkeys(c.phones+phones));d=dict(c.details)
   for k,v in detail.items():
    if isinstance(v,list):d[k]=list(dict.fromkeys(d.get(k,[])+v))
    elif not d.get(k):d[k]=v
   c.details=d;c.issues=list(dict.fromkeys(c.issues+issues));c.observations=c.observations+[observation];c.version+=1;merged+=1
 result={'kind':kind,'rows':len(rows),'added':added,'merged':merged,'existing':False,'recovered_from_equivalent_excel':recovered}
 if prior:prior.result=result;prior.filenames=list(dict.fromkeys(prior.filenames+[filename]))
 else:db.add(DirectoryImport(digest=digest,filenames=[filename],source_text=content.decode('utf-8-sig'),result=result))
 db.add(SecurityLog(user_id=user.id,action='AMATEUR_DIRECTORY_IMPORTED',description=f'{kind} export; rows {len(rows)}, added {added}, merged {merged}; no consent or availability inferred'));db.commit();return result
class ContactBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 kind:Literal['person','club']='person'
 name:str=Field(min_length=2,max_length=200)
 email:str=Field(default='',max_length=254)
 phone:str=Field(default='',max_length=40)
 roles:list[str]=Field(default_factory=list,max_length=8)
 role_verified:bool=False
 sms_consent:bool=False
 consent_note:str=Field(default='',max_length=500)
 active:bool=True
 version:int|None=None
 city:str=Field(default='',max_length=120)
 state:str=Field(default='',max_length=100)
 club:str=Field(default='',max_length=200)
 contact_name:str=Field(default='',max_length=160)
 address:str=Field(default='',max_length=300)
 @model_validator(mode='after')
 def validate_contact(self):
  self.name=self.name.strip()
  if len(self.name)<2:raise ValueError('Enter a contact name')
  if self.email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',self.email):raise ValueError('Enter a valid email')
  if self.phone:self.phone=normalize_ticket_phone(self.phone)
  if set(self.roles)-set(ROLES):raise ValueError('Unsupported official role')
  if self.sms_consent and (not self.phone or len(self.consent_note.strip())<10):raise ValueError('Record the official’s permission and its source before enabling texts')
  return self
@router.post('')
def create_contact(body:ContactBody,db=Depends(get_db),user=Depends(access)):
 if not body.email and not body.phone:raise HTTPException(422,'Provide email or phone')
 identity=f'manual:{body.kind}:{words(body.name)}:{body.email.casefold() or body.phone}';lock(db)
 if db.query(DirectoryContact).filter_by(identity_key=key(identity)).first():raise HTTPException(409,'This contact already exists')
 c=DirectoryContact(identity_key=key(identity),kind=body.kind,name=body.name,emails=[body.email.casefold()] if body.email else [],phones=[body.phone] if body.phone else [],details={'categories':['manual']},observations=[],issues=[]);db.add(c);return save_contact(db,c,body,user)
def save_contact(db,c,body,user):
 c.details={**c.details,**{k:getattr(body,k).strip() for k in ('city','state','club','contact_name','address') if getattr(body,k).strip() or (k=='contact_name' and k in body.model_fields_set)}}
 c.name=body.name;c.emails=list(dict.fromkeys(([body.email.casefold()] if body.email else [])+c.emails));c.phones=list(dict.fromkeys(([body.phone] if body.phone else [])+c.phones));c.roles=list(dict.fromkeys(body.roles));c.role_verified=body.role_verified;c.sms_consent=body.sms_consent;c.consent_note=body.consent_note.strip();c.consent_at=datetime.utcnow() if body.sms_consent else None;c.active=body.active;c.version=(c.version or 0)+1;db.flush();db.add(SecurityLog(user_id=user.id,action='AMATEUR_DIRECTORY_UPDATED',description=f'Directory contact {c.id}; role verification {c.role_verified}; SMS permission {c.sms_consent}'));db.commit();return serialize(c)
@router.put('/{contact_id}')
def update_contact(contact_id:int,body:ContactBody,db=Depends(get_db),user=Depends(access)):
 lock(db);c=db.query(DirectoryContact).filter_by(id=contact_id).with_for_update().first()
 if not c:raise HTTPException(404,'Contact not found')
 if c.version!=body.version:raise HTTPException(409,'Contact changed. Refresh before saving')
 if c.kind!=body.kind:raise HTTPException(422,'A contact cannot change directory type')
 return save_contact(db,c,body,user)
@router.get('/{contact_id}/sources')
def sources(contact_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
 c=db.get(DirectoryContact,contact_id)
 if not c:raise HTTPException(404,'Contact not found')
 response.headers['Cache-Control']='private, no-store';return {'observations':c.observations}
