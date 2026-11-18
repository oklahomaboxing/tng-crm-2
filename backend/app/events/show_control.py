"""Assigned announcer/DJ event preparation. No audio playback or external sends."""
import io,json,re,uuid
from datetime import datetime
from typing import Literal
from xml.sax.saxutils import escape
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import Column,Integer,String,Text,Boolean,ForeignKey,DateTime
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import User,SecurityLog
from app.matchmaker.models import BoxingEvent,BoxingBout,BoxingFighter
from .partners import PartnerProfile
router=APIRouter(prefix='/api/show-control',tags=['Announcer and DJ'])
class ShowAssignment(Base):
 __tablename__='event_show_assignments'
 event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
 user_id=Column(Integer,ForeignKey('users.id'),primary_key=True)
class ShowSong(Base):
 __tablename__='event_show_walkout_songs'
 event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
 fighter_id=Column(Integer,ForeignKey('boxing_fighters.id'),primary_key=True)
 title=Column(String(160),default='',nullable=False)
 artist=Column(String(160),default='',nullable=False)
 source_url=Column(String(1000),default='',nullable=False)
 start_seconds=Column(Integer,default=0,nullable=False)
 clean_version=Column(Boolean,default=False,nullable=False)
 confirmed=Column(Boolean,default=False,nullable=False)
 notes=Column(Text,default='',nullable=False)
 version=Column(Integer,default=0,nullable=False)
class ShowCue(Base):
 __tablename__='event_show_cues'
 id=Column(Integer,primary_key=True)
 event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
 request_key=Column(String(100),unique=True,nullable=False)
 title=Column(String(160),nullable=False)
 script=Column(Text,default='',nullable=False)
 time_label=Column(String(80),default='',nullable=False)
 kind=Column(String(40),nullable=False)
 owner=Column(String(20),default='both',nullable=False)
 position=Column(Integer,default=0,nullable=False)
 approved=Column(Boolean,default=False,nullable=False)
 status=Column(String(20),default='draft',nullable=False)
 version=Column(Integer,default=1,nullable=False)
 completed_at=Column(DateTime,nullable=True)
class SongBody(BaseModel):
 title:str=Field(default='',max_length=160)
 artist:str=Field(default='',max_length=160)
 source_url:str=Field(default='',max_length=1000)
 start_seconds:int=Field(default=0,ge=0,le=7200)
 clean_version:bool=False
 confirmed:bool=False
 notes:str=Field(default='',max_length=2000)
 version:int=Field(ge=0)
 @field_validator('source_url')
 @classmethod
 def valid_link(cls,v):
  if v and (not re.match(r'^https?://[^/\s]+',v) or any(x in v for x in ('\r','\n'))):raise ValueError('Use a complete http or https song reference link')
  return v.strip()
class CueBody(BaseModel):
 title:str=Field(min_length=1,max_length=160)
 script:str=Field(default='',max_length=6000)
 time_label:str=Field(default='',max_length=80)
 kind:Literal['welcome','sponsor','concessions','bar','walkout','bout','result','break','safety','closing','custom']='custom'
 owner:Literal['announcer','dj','both']='both'
 position:int=Field(default=0,ge=0,le=9999)
 approved:bool=False
 version:int=Field(default=0,ge=0)
 request_key:uuid.UUID
class GrantBody(BaseModel):
 user_id:int
 enabled:bool=True
class ProfileBody(BaseModel):
 title:str=Field(max_length=160)
 phone:str=Field(default='',max_length=40)
class VersionBody(BaseModel):
 version:int=Field(ge=1)

def is_staff(u):return u.role in ('admin','staff')
def access(db,eid,u,lock=False):
 if not is_staff(u) and (u.role not in ('announcer','dj') or not db.get(ShowAssignment,(eid,u.id))):raise HTTPException(403,'This event is not assigned to your show account')
 q=db.query(BoxingEvent).filter_by(id=eid);e=q.with_for_update().first() if lock else q.first()
 if not e:raise HTTPException(404,'Event not found')
 return e

def audit(db,u,eid,action):db.add(SecurityLog(user_id=u.id,action='SHOW_'+action,description=f'Event {eid} announcer/DJ preparation',success=True))
def cue_dict(c):return {k:getattr(c,k)for k in ['id','title','script','time_label','kind','owner','position','approved','status','version']}
def card(db,eid):
 rows=[]
 for b in db.query(BoxingBout).filter_by(event_id=eid).order_by(BoxingBout.bout_order,BoxingBout.id):
  if str(b.status or '').lower() in ('cancelled','canceled','withdrawn','deleted','void'):continue
  corners={}
  for corner,fid in [('red',b.red_fighter_id),('blue',b.blue_fighter_id)]:
   f=db.get(BoxingFighter,fid)
   if not f:continue
   song=db.get(ShowSong,(eid,fid));corners[corner]={'id':f.id,'name':f.legal_name,'nickname':getattr(f,'nickname',''),'gym':f.gym,'city':f.city,'state':f.state,'record':f.pro_record if b.bout_type=='pro' else f.amateur_record,'song':{k:getattr(song,k)for k in SongBody.model_fields} if song else {'version':0,'title':'','artist':'','source_url':'','start_seconds':0,'clean_version':False,'confirmed':False,'notes':''}}
  rows.append({'bout_id':b.id,'order':b.bout_order,'rounds':b.rounds,'weight':b.weight_agreed,'type':b.bout_type,**corners})
 return rows

def templates(db,e):
 from .concessions import ConcessionsPlan
 from app.revenue.models import EventRevenueProspect,RevenueOrganization
 plan=db.get(ConcessionsPlan,e.id);published=json.loads(plan.published_json)if plan and plan.published_json else None
 offers=', '.join(f'{m["name"]} ${m["price_cents"]/100:.2f}'for m in (published or {}).get('items',[])[:4])
 sponsor_ids={p.organization_id for p in db.query(EventRevenueProspect).filter_by(event_id=e.id,prospect_type='SPONSOR') if str(p.status).upper() in ('COMMITTED','PAID')};sponsors=[o.business_name for o in db.query(RevenueOrganization).filter(RevenueOrganization.id.in_(sponsor_ids))]if sponsor_ids else []
 cues=[{'title':'Welcome to '+e.name,'kind':'welcome','owner':'announcer','script':f'Welcome to {e.name}, presented by TNG Promotions! Thank you for supporting our fighters. Let’s bring the energy tonight!','time_label':'Doors / opening'}, {'title':'Concessions sales reminder','kind':'concessions','owner':'announcer','script':'Keep your energy up! Visit concessions for food and refreshments between bouts. '+('Tonight’s published menu includes '+offers+'. 'if offers else '')+'Thank you for supporting TNG Boxing.','time_label':'Between bouts'}, {'title':'Bar reminder','kind':'bar','owner':'announcer','script':'Guests 21 and over, visit the bar between bouts for available drinks. Please have your ID ready and enjoy the event responsibly.','time_label':'Between bouts'}, {'title':'Music & backstage reminder','kind':'safety','owner':'both','script':'No loud music in shared preparation areas. Please use headphones for personal music and keep clear for event staff.','time_label':'Fighter check-in'}, {'title':'Closing & next event','kind':'closing','owner':'announcer','script':'Thank you to our fighters, teams, sponsors and fans for supporting TNG Promotions. Follow TNG Boxing for the next event, training and membership information. Travel home safely!','time_label':'After final decision'}]
 for name in sponsors:cues.append({'title':'Sponsor recognition · '+name,'kind':'sponsor','owner':'announcer','script':f'A special thank-you to {name} for supporting this event and our fighters. Please show your support for our event sponsors!','time_label':'Between bouts'})
 return cues,sponsors

@router.get('')
def home(response:Response,db=Depends(get_db),user=Depends(current_user)):
 if user.role not in ('admin','staff','announcer','dj'):raise HTTPException(403,'Show team access required')
 response.headers['Cache-Control']='private, no-store';q=db.query(BoxingEvent)
 if not is_staff(user):q=q.join(ShowAssignment,ShowAssignment.event_id==BoxingEvent.id).filter(ShowAssignment.user_id==user.id)
 users=[]
 if user.role=='admin':
  for u in db.query(User).filter(User.role.in_(['announcer','dj'])):
   p=db.get(PartnerProfile,u.id);users.append({'id':u.id,'name':u.name,'role':u.role,'active':u.active,'title':p.title if p else '', 'phone':p.phone if p else ''})
 return {'role':user.role,'user_id':user.id,'name':user.name,'events':[{'id':e.id,'name':e.name,'date':e.event_date}for e in q.order_by(BoxingEvent.event_date.desc())],'users':users}
@router.get('/events/{event_id}')
def workspace(event_id:int,response:Response,db=Depends(get_db),user=Depends(current_user)):
 e=access(db,event_id,user);response.headers['Cache-Control']='private, no-store';cues=db.query(ShowCue).filter_by(event_id=event_id).order_by(ShowCue.position,ShowCue.id).all();drafts,sponsors=templates(db,e)
 from app.matchmaker.models import BoxingEventPublication
 pub=db.query(BoxingEventPublication).filter_by(event_id=event_id).first()
 team=[]
 for grant in db.query(ShowAssignment).filter_by(event_id=event_id):
  u=db.get(User,grant.user_id)
  if u and u.active and u.role in ('announcer','dj'):
   p=db.get(PartnerProfile,u.id);team.append({'id':u.id,'name':u.name,'role':u.role,'title':p.title if p else '', 'phone':p.phone if p else ''})
 return {'event':{'id':e.id,'name':e.name,'date':e.event_date,'venue':e.venue,'address':e.venue_address,'doors_time':pub.doors_time if pub else '', 'first_bout_time':pub.first_bout_time if pub else ''},'role':user.role,'card':card(db,event_id),'cues':[cue_dict(c)for c in cues],'templates':drafts,'sponsors':sponsors,'team':team,'notice':'Draft scripts and song references require review. Run-of-show times are planning cues; bout order and official instructions control. No audio is played or announcement sent automatically.'}
@router.put('/events/{event_id}/assignment')
def grant(event_id:int,body:GrantBody,db=Depends(get_db),user=Depends(current_user)):
 if user.role!='admin':raise HTTPException(403,'Admin access required')
 access(db,event_id,user,True);target=db.get(User,body.user_id)
 if not target or target.role not in ('announcer','dj'):raise HTTPException(422,'Select an Announcer or DJ account')
 row=db.get(ShowAssignment,(event_id,body.user_id))
 if body.enabled and not row:db.add(ShowAssignment(event_id=event_id,user_id=body.user_id))
 elif not body.enabled and row:db.delete(row)
 audit(db,user,event_id,'ACCESS_UPDATED');db.commit();return {'saved':True}
@router.put('/profiles/{user_id}')
def profile(user_id:int,body:ProfileBody,db=Depends(get_db),user=Depends(current_user)):
 if user.role!='admin' and (user.id!=user_id or user.role not in ('announcer','dj')):raise HTTPException(403,'Your own show profile only')
 target=db.get(User,user_id)
 if not target or target.role not in ('announcer','dj'):raise HTTPException(422,'Select a show team account')
 row=db.get(PartnerProfile,user_id)
 if not row:row=PartnerProfile(user_id=user_id);db.add(row)
 row.title=body.title.strip();row.phone=body.phone.strip();db.add(SecurityLog(user_id=user.id,action='SHOW_PROFILE_UPDATED',description=f'Show profile {user_id}',success=True));db.commit();return {'saved':True}
@router.put('/events/{event_id}/songs/{fighter_id}')
def save_song(event_id:int,fighter_id:int,body:SongBody,db=Depends(get_db),user=Depends(current_user)):
 access(db,event_id,user,True)
 if user.role not in ('admin','staff','dj'):raise HTTPException(403,'DJ or staff music editing required')
 if body.confirmed and not body.title.strip():raise HTTPException(422,'Enter a track title before confirming music')
 if fighter_id not in {b[c]['id']for b in card(db,event_id)for c in ('red','blue')if c in b}:raise HTTPException(409,'Fighter is not on the current event card')
 row=db.get(ShowSong,(event_id,fighter_id))
 if (row.version if row else 0)!=body.version:raise HTTPException(409,'Song changed. Refresh before saving')
 if not row:row=ShowSong(event_id=event_id,fighter_id=fighter_id);db.add(row)
 for k,v in body.model_dump(exclude={'version'}).items():setattr(row,k,v)
 row.version=body.version+1;audit(db,user,event_id,'SONG_UPDATED');db.commit();return {'saved':True}
@router.post('/events/{event_id}/cues')
def add_cue(event_id:int,body:CueBody,db=Depends(get_db),user=Depends(current_user)):
 access(db,event_id,user,True);key=f'{event_id}:{body.request_key}';old=db.query(ShowCue).filter_by(request_key=key).first()
 if old:
  if any(getattr(old,k)!=v for k,v in body.model_dump(exclude={'version','request_key'}).items()):raise HTTPException(409,'This request key already belongs to another cue version')
  return {'saved':True,'id':old.id,'existing':True}
 if body.approved and not is_staff(user):raise HTTPException(403,'Staff approval required')
 if not body.title.strip():raise HTTPException(422,'Enter a cue title')
 values=body.model_dump(exclude={'version','request_key'});row=ShowCue(event_id=event_id,request_key=key,**values,status='ready'if body.approved else 'draft');db.add(row);db.flush();audit(db,user,event_id,'CUE_ADDED');db.commit();return {'saved':True,'id':row.id}
@router.put('/events/{event_id}/cues/{cue_id}')
def edit_cue(event_id:int,cue_id:int,body:CueBody,db=Depends(get_db),user=Depends(current_user)):
 access(db,event_id,user,True);row=db.query(ShowCue).filter_by(id=cue_id,event_id=event_id).first()
 if not row:raise HTTPException(404,'Cue not found')
 if row.version!=body.version:raise HTTPException(409,'Cue changed. Refresh before saving')
 if body.approved and not is_staff(user):raise HTTPException(403,'Staff approval required')
 if not body.title.strip():raise HTTPException(422,'Enter a cue title')
 for k,v in body.model_dump(exclude={'request_key','version'}).items():setattr(row,k,v)
 row.status='ready'if body.approved else 'draft';row.completed_at=None;row.version+=1;audit(db,user,event_id,'CUE_UPDATED');db.commit();return {'saved':True}
@router.post('/events/{event_id}/cues/{cue_id}/done')
def done(event_id:int,cue_id:int,body:VersionBody,db=Depends(get_db),user=Depends(current_user)):
 access(db,event_id,user,True);row=db.query(ShowCue).filter_by(id=cue_id,event_id=event_id).first()
 if not row:raise HTTPException(404,'Cue not found')
 if row.version!=body.version:raise HTTPException(409,'Cue status changed. Refresh')
 if not row.approved:raise HTTPException(409,'Staff must approve this cue first')
 if not is_staff(user) and row.owner not in ('both',user.role):raise HTTPException(403,'This cue belongs to another show role')
 row.status='done';row.completed_at=datetime.utcnow();row.version+=1;audit(db,user,event_id,'CUE_COMPLETED');db.commit();return {'saved':True}
@router.delete('/events/{event_id}/cues/{cue_id}')
def delete(event_id:int,cue_id:int,version:int,db=Depends(get_db),user=Depends(current_user)):
 access(db,event_id,user,True)
 if not is_staff(user):raise HTTPException(403,'Staff cue removal required')
 row=db.query(ShowCue).filter_by(id=cue_id,event_id=event_id).first()
 if not row:raise HTTPException(404,'Cue not found')
 if row.version!=version:raise HTTPException(409,'Cue changed. Refresh')
 db.delete(row);audit(db,user,event_id,'CUE_REMOVED');db.commit();return {'saved':True}
@router.get('/events/{event_id}/run-of-show.pdf')
def pdf(event_id:int,db=Depends(get_db),user=Depends(current_user)):
 from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
 from reportlab.lib.styles import getSampleStyleSheet
 from reportlab.lib import colors
 d=workspace(event_id,Response(),db,user);styles=getSampleStyleSheet();out=io.BytesIO();story=[Paragraph('TNG BOXING | RUN OF SHOW',styles['Title']),Paragraph(escape(d['event']['name']),styles['Heading2']),Paragraph(escape(str(d['event']['date'])+' | '+str(d['event']['venue'])),styles['Normal']),Paragraph(escape(d['notice']),styles['Normal']),Spacer(1,14)]
 for c in d['cues']:
  story.extend([Paragraph(escape(f'{c["position"]} · {c["time_label"]} · {c["title"]}'),styles['Heading2']),Paragraph(escape(f'{c["owner"]} | {c["status"]} | '+('STAFF APPROVED'if c['approved']else'DRAFT - REVIEW REQUIRED')),styles['Normal']),Paragraph(escape(c['script']).replace('\n','<br/>'),styles['Normal']),Spacer(1,10)])
 story.append(Paragraph('FIGHT CARD & WALKOUT MUSIC',styles['Heading1']))
 for b in d['card']:
  story.append(Paragraph(escape(f'Bout {b["order"]} | {b["rounds"]} rounds | '+str(b['weight']or'Weight TBC')),styles['Heading2']))
  for corner in ('red','blue'):
   if corner not in b:continue
   f=b[corner];s=f['song'];text=f'{corner.upper()}: {f["name"]} | {f["record"] or "Record TBC"} | {f["gym"] or "Gym TBC"}\nSong: {s["title"] or "NOT SUPPLIED"} / {s["artist"]} | start {s["start_seconds"]} sec | '+('Confirmed'if s['confirmed']else'Needs confirmation')+f'\nReference: {s["source_url"]}\nDJ notes: {s["notes"]}';story.extend([Paragraph(escape(text).replace('\n','<br/>'),styles['Normal']),Spacer(1,8)])
 SimpleDocTemplate(out,pagesize=(612,792),leftMargin=46,rightMargin=46).build(story)
 return Response(out.getvalue(),media_type='application/pdf',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="event-{event_id}-run-of-show.pdf"'})
