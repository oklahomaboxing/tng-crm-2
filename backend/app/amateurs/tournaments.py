"""Private draft tournament brackets and two-day capacity planning, not an official draw."""
import csv,io,hashlib,json
from datetime import date,datetime,time,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import Column,Integer,String,Date,DateTime,JSON,ForeignKey
from app.database import Base,get_db
from app.models import SecurityLog
from app.events.venue import utc_local
from .rosters import access,roster_for,AmateurEntry
router=APIRouter(prefix='/api/amateurs/tournaments',tags=['Amateur tournaments'])
SESSION_KEYS=['sat_am','sat_pm','sun_am','sun_pm']
LABELS={'sat_am':'Saturday AM','sat_pm':'Saturday PM','sun_am':'Sunday AM','sun_pm':'Sunday PM'}
DEFAULT_SESSIONS={k:{'start':v,'capacity':20} for k,v in [('sat_am','09:00'),('sat_pm','17:00'),('sun_am','09:00'),('sun_pm','15:00')]}
NOTICE='Draft tournament plan, not an official draw or eligibility approval. Division classification, seed order, event Fact Sheet and the public draw require the Official in Charge. Local matched-bout Appendix F proposals are not used to certify tournament divisions. Daily weigh-ins, medical clearance and restrictions must be checked before every bout.'
POLICY='TNG planning defaults: at most one bout per boxer per day and 12 hours between potential bouts. These conservative planning settings are not represented as universal USA Boxing rules. Extra sessions add capacity, not permission to box more often. Brackets needing more competition days remain visibly unscheduled.'
class TournamentPlan(Base):
 __tablename__='amateur_tournament_plans'
 id=Column(Integer,primary_key=True)
 roster_id=Column(Integer,ForeignKey('amateur_rosters.id'),nullable=False,index=True)
 request_key=Column(String(100),unique=True,nullable=False)
 name=Column(String(160),nullable=False)
 saturday=Column(Date,nullable=False)
 sessions=Column(JSON,nullable=False)
 sunday_am=Column(String(10),default='auto',nullable=False)
 slot_minutes=Column(Integer,default=15,nullable=False)
 schedule=Column(JSON,nullable=True)
 version=Column(Integer,default=1,nullable=False)
 created_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
class TournamentDivision(Base):
 __tablename__='amateur_tournament_divisions'
 id=Column(Integer,primary_key=True)
 plan_id=Column(Integer,ForeignKey('amateur_tournament_plans.id'),nullable=False,index=True)
 name=Column(String(160),nullable=False)
 entry_ids=Column(JSON,nullable=False)
 entry_versions=Column(JSON,nullable=False)
 winners=Column(JSON,default=dict,nullable=False)
 version=Column(Integer,default=1,nullable=False)
class SessionConfig(BaseModel):
 model_config=ConfigDict(extra='forbid')
 start:time
 capacity:int=Field(default=20,ge=1,le=200)
class PlanBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 roster_id:int
 request_key:str|None=Field(default=None,min_length=16,max_length=80)
 name:str=Field(min_length=2,max_length=160)
 saturday:date
 sessions:dict[str,SessionConfig]
 sunday_am:Literal['auto','on','off']='auto'
 slot_minutes:int=Field(default=15,ge=15,le=60)
 @model_validator(mode='after')
 def validate_sessions(self):
  if not 2000<=self.saturday.year<=2100:raise ValueError('Choose a supported tournament year')
  if self.saturday.weekday()!=5:raise ValueError('Choose a Saturday; Sunday is the following day')
  if not self.name.strip():raise ValueError('Enter a tournament name')
  if set(self.sessions)!=set(SESSION_KEYS):raise ValueError('Configure all four potential sessions')
  ranges={}
  for k,s in self.sessions.items():
   if s.start.tzinfo or s.start.second or s.start.microsecond:raise ValueError('Use local Oklahoma City times to the minute')
   if (k.endswith('am') and s.start.hour>=12) or (k.endswith('pm') and s.start.hour<12):raise ValueError('AM sessions must start before noon and PM sessions at/after noon')
   start=s.start.hour*60+s.start.minute;end=start+s.capacity*self.slot_minutes
   if end>1440:raise ValueError('Session capacity extends past midnight; adjust time or capacity')
   utc_local(datetime.combine(self.saturday+timedelta(days=int(k.startswith('sun'))),s.start))
   ranges[k]=(start,end)
  for day in ('sat','sun'):
   if day=='sun' and self.sunday_am=='off':continue
   if ranges[day+'_am'][1]>ranges[day+'_pm'][0]:raise ValueError('AM and PM session windows overlap; adjust capacity or start times')
  return self
class PlanUpdate(PlanBody):version:int=Field(ge=1)
class DivisionBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 name:str=Field(min_length=2,max_length=160)
 entry_ids:list[int]=Field(min_length=1,max_length=16)
 version:int=Field(ge=1)
class VersionBody(BaseModel):version:int=Field(ge=1)
class WinnerBody(VersionBody):
 winner_id:int
 official_result_confirmed:bool

def plan_for(db,pid,lock=False):
 q=db.query(TournamentPlan).filter_by(id=pid);p=q.with_for_update().first() if lock else q.first()
 if not p:raise HTTPException(404,'Tournament plan not found')
 return p

def divisions(db,p):return db.query(TournamentDivision).filter_by(plan_id=p.id).order_by(TournamentDivision.id).all()
def audit(db,u,p,action):db.add(SecurityLog(user_id=u.id,action='AMATEUR_TOURNAMENT_'+action,description=f'Tournament plan {p.id} updated'))
def name_of(entries,eid):
 d=entries[eid].data;return d.get('first_name','')+' '+d.get('last_name','')
def bracket(d,entries):
 ids=d.entry_ids;n=len(ids)
 if n==1:return []
 size=1
 while size<n:size*=2
 seeds=[1,2]
 while len(seeds)<size:
  total=len(seeds)*2+1;seeds=[s for x in seeds for s in (x,total-x)]
 previous=[];nodes=[];round_no=1
 for i in range(0,size,2):
  a=ids[seeds[i]-1] if seeds[i]<=n else None;b=ids[seeds[i+1]-1] if seeds[i+1]<=n else None
  previous.append({'key':f'd{d.id}-r1-b{i//2+1}','round':1,'red_entry_id':a,'blue_entry_id':b,'red_source':None,'blue_source':None,'potential_ids':[x for x in (a,b) if x],'bye':not a or not b})
 while previous:
  for node in previous:
   node['winner_id']=(node['red_entry_id'] or node['blue_entry_id']) if node['bye'] else (d.winners or {}).get(node['key'])
   node['division_id']=d.id;node['division_name']=d.name
   node['red_label']=name_of(entries,node['red_entry_id']) if node['red_entry_id'] else 'Winner of '+str(node['red_source'])
   node['blue_label']=name_of(entries,node['blue_entry_id']) if node['blue_entry_id'] else 'Winner of '+str(node['blue_source'])
  nodes.extend(previous)
  if len(previous)==1:break
  current=[];round_no+=1
  for i in range(0,len(previous),2):
   a,b=previous[i:i+2];current.append({'key':f'd{d.id}-r{round_no}-b{i//2+1}','round':round_no,'red_entry_id':a['winner_id'],'blue_entry_id':b['winner_id'],'red_source':a['key'],'blue_source':b['key'],'potential_ids':a['potential_ids']+b['potential_ids'],'bye':False})
  previous=current
 return nodes

def snapshot(p,ds,entries):return hashlib.sha256(json.dumps({'date':p.saturday.isoformat(),'sessions':p.sessions,'sunday_am':p.sunday_am,'slot':p.slot_minutes,'divisions':[(d.id,d.name,d.entry_ids,[(i,entries[i].version) for i in d.entry_ids]) for d in ds]},sort_keys=True).encode()).hexdigest()
def session_list(p,include_am):
 result=[]
 for k in SESSION_KEYS:
  cfg=p.sessions[k];day=p.saturday+timedelta(days=int(k.startswith('sun')));start=datetime.combine(day,time.fromisoformat(cfg['start']));end=start+timedelta(minutes=p.slot_minutes*cfg['capacity'])
  result.append({'key':k,'label':LABELS[k],'date':day.isoformat(),'start_local':start.isoformat(timespec='minutes'),'end_local':end.isoformat(timespec='minutes'),'starts_at':utc_local(start).isoformat()+'Z','ends_at':utc_local(end).isoformat()+'Z','capacity':cfg['capacity'],'enabled':k!='sun_am' or include_am})
 return result

def allocate(p,nodes,include_am):
 sessions=session_list(p,include_am);lookup={s['key']:s for s in sessions};used={k:0 for k in SESSION_KEYS};assigned={};daily={};last={};pending=[]
 depths={d:max(n['round'] for n in nodes if n['division_id']==d) for d in {n['division_id'] for n in nodes}}
 ordered=sorted([n for n in nodes if not n['bye']],key=lambda n:(depths[n['division_id']]==1,n['round'],n['division_id'],n['key']))
 for node in ordered:
  predecessors=[n for n in nodes if n['division_id']==node['division_id'] and n['round']<node['round'] and not n['bye']]
  if any(n['key'] not in assigned for n in predecessors):pending.append({'bout_key':node['key'],'reason':'An earlier bracket round could not be scheduled'});continue
  final=node['round']==depths[node['division_id']]
  order=['sun_pm','sun_am','sat_pm','sat_am'] if final else ['sat_am','sat_pm','sun_am','sun_pm']
  placed=False
  for key in order:
   session=lookup[key]
   if not session['enabled'] or used[key]>=session['capacity']:continue
   start=datetime.fromisoformat(session['start_local'])+timedelta(minutes=used[key]*p.slot_minutes);end=start+timedelta(minutes=p.slot_minutes)
   if any(assigned[n['key']]['end']>start for n in predecessors):continue
   if any(daily.get((eid,start.date())) or (eid in last and start-last[eid]<timedelta(hours=12)) for eid in node['potential_ids']):continue
   assigned[node['key']]={'session':key,'start':start,'end':end};used[key]+=1
   for eid in node['potential_ids']:daily[(eid,start.date())]=1;last[eid]=end
   placed=True;break
  if not placed:pending.append({'bout_key':node['key'],'reason':'No remaining session slot satisfies capacity, bracket order and TNG one-bout/day/rest planning limits. Adjust capacity or allow more competition days'})
 rows=[{'bout_key':k,'session_key':v['session'],'start_local':v['start'].isoformat(timespec='minutes'),'end_local':v['end'].isoformat(timespec='minutes')} for k,v in assigned.items()]
 rows.sort(key=lambda x:(x['start_local'],x['bout_key']))
 for s in sessions:s['used']=used[s['key']]
 return {'sessions':sessions,'bouts':rows,'unscheduled':pending,'sunday_am_enabled':include_am,'policy':POLICY,'notice':NOTICE}

def view(db,p):
 ds=divisions(db,p);entries={e.id:e for e in db.query(AmateurEntry).filter_by(roster_id=p.roster_id)};nodes=[n for d in ds for n in bracket(d,entries)];fingerprint=snapshot(p,ds,entries)
 return {'id':p.id,'roster_id':p.roster_id,'name':p.name,'saturday':p.saturday.isoformat(),'sunday':(p.saturday+timedelta(days=1)).isoformat(),'sessions':p.sessions,'sunday_am':p.sunday_am,'slot_minutes':p.slot_minutes,'version':p.version,'divisions':[{'id':d.id,'name':d.name,'entry_ids':d.entry_ids,'version':d.version,'unopposed':len(d.entry_ids)==1,'stale':any(str(eid) not in d.entry_versions or d.entry_versions[str(eid)]!=entries[eid].version for eid in d.entry_ids),'recorded_results':len(d.winners or {})} for d in ds],'nodes':nodes,'schedule':p.schedule,'schedule_stale':bool(p.schedule and p.schedule.get('fingerprint')!=fingerprint),'notice':NOTICE,'policy':POLICY}

@router.get('')
def list_plans(roster_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
 roster_for(db,roster_id);response.headers['Cache-Control']='private, no-store'
 return [{'id':p.id,'name':p.name,'saturday':p.saturday.isoformat()} for p in db.query(TournamentPlan).filter_by(roster_id=roster_id).order_by(TournamentPlan.id.desc())]
@router.post('')
def create(body:PlanBody,db=Depends(get_db),user=Depends(access)):
 roster_for(db,body.roster_id)
 if not body.request_key:raise HTTPException(422,'A create request key is required')
 request_key=str(user.id)+':'+body.request_key
 if db.get_bind().dialect.name=='postgresql':
  from sqlalchemy import text
  db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':int.from_bytes(hashlib.sha256(request_key.encode()).digest()[:8],'big',signed=True)})
 values=body.model_dump(exclude={'sessions','request_key'});values['name']=body.name.strip();values['sessions']={k:{'start':s.start.strftime('%H:%M'),'capacity':s.capacity} for k,s in body.sessions.items()}
 prior=db.query(TournamentPlan).filter_by(request_key=request_key).first()
 if prior:
  if any(getattr(prior,k)!=v for k,v in values.items()):raise HTTPException(409,'This create key was already used. Open the existing plan or start a new plan')
  return view(db,prior)
 p=TournamentPlan(**values,request_key=request_key,created_by=user.id);db.add(p);db.flush();audit(db,user,p,'CREATED');db.commit();return view(db,p)
@router.get('/{plan_id}')
def get(plan_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
 response.headers['Cache-Control']='private, no-store';return view(db,plan_for(db,plan_id))
@router.put('/{plan_id}')
def update(plan_id:int,body:PlanUpdate,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=body.version:raise HTTPException(409,'Plan changed. Refresh before saving')
 if p.roster_id!=body.roster_id:raise HTTPException(422,'A tournament cannot move to a different roster')
 if any(d.winners for d in divisions(db,p)):raise HTTPException(409,'Results are recorded; preserve this tournament and create a new plan for a different schedule')
 p.name=body.name.strip();p.saturday=body.saturday;p.sessions={k:{'start':s.start.strftime('%H:%M'),'capacity':s.capacity} for k,s in body.sessions.items()};p.sunday_am=body.sunday_am;p.slot_minutes=body.slot_minutes;p.version+=1;audit(db,user,p,'SETTINGS');db.commit();return view(db,p)
@router.post('/{plan_id}/divisions')
def add_division(plan_id:int,body:DivisionBody,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=body.version:raise HTTPException(409,'Plan changed. Refresh before adding a division')
 if not body.name.strip() or len(set(body.entry_ids))!=len(body.entry_ids):raise HTTPException(422,'Enter a division name and unique boxer entries')
 rows=db.query(AmateurEntry).filter(AmateurEntry.roster_id==p.roster_id,AmateurEntry.id.in_(body.entry_ids)).all();entries={r.id:r for r in rows}
 if len(entries)!=len(body.entry_ids) or any(r.excluded or r.issues for r in rows):raise HTTPException(422,'Select available, unflagged boxers from this roster')
 if len({r.data['sex'] for r in rows})>1:raise HTTPException(422,'Tournament divisions require a single sex category; local Pee Wee matched-bout exceptions are not assumed')
 assigned={eid for d in divisions(db,p) for eid in d.entry_ids}
 if assigned.intersection(body.entry_ids):raise HTTPException(409,'A boxer is already assigned to another division in this tournament')
 db.add(TournamentDivision(plan_id=p.id,name=body.name.strip(),entry_ids=body.entry_ids,entry_versions={str(i):entries[i].version for i in body.entry_ids},winners={}));p.version+=1;audit(db,user,p,'DIVISION_ADDED');db.commit();return view(db,p)
@router.delete('/{plan_id}/divisions/{division_id}')
def remove_division(plan_id:int,division_id:int,version:int,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=version:raise HTTPException(409,'Plan changed. Refresh before removing a division')
 d=db.query(TournamentDivision).filter_by(id=division_id,plan_id=p.id).first()
 if not d:raise HTTPException(404,'Division not found')
 if d.winners:raise HTTPException(409,'Clear recorded results before removing this division')
 db.delete(d);p.version+=1;audit(db,user,p,'DIVISION_REMOVED');db.commit();return view(db,p)
@router.post('/{plan_id}/schedule')
def generate_schedule(plan_id:int,body:VersionBody,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=body.version:raise HTTPException(409,'Plan changed. Refresh before scheduling')
 d=view(db,p)
 if not d['divisions']:raise HTTPException(422,'Add at least one division first')
 if any(x['stale'] for x in d['divisions']):raise HTTPException(409,'Roster details changed. Recreate the affected draft division after reviewing its classification')
 if any(x['recorded_results'] for x in d['divisions']):raise HTTPException(409,'Results are recorded; preserve the existing schedule')
 result=allocate(p,d['nodes'],p.sunday_am=='on')
 if p.sunday_am=='auto' and result['unscheduled']:
  extra=allocate(p,d['nodes'],True)
  if len(extra['unscheduled'])<len(result['unscheduled']):result=extra
 result['fingerprint']=snapshot(p,divisions(db,p),{e.id:e for e in db.query(AmateurEntry).filter_by(roster_id=p.roster_id)});p.schedule=result;p.version+=1;audit(db,user,p,'SCHEDULE_GENERATED');db.commit();return view(db,p)
@router.post('/{plan_id}/results/{bout_key}')
def record_result(plan_id:int,bout_key:str,body:WinnerBody,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=body.version:raise HTTPException(409,'Plan changed. Refresh before recording a result')
 if not body.official_result_confirmed:raise HTTPException(422,'Confirm the official result before recording it')
 v=view(db,p);node=next((n for n in v['nodes'] if n['key']==bout_key),None)
 if not node or node['bye']:raise HTTPException(422,'Choose a contested bracket bout')
 if any(d['stale'] for d in v['divisions']):raise HTTPException(409,'Roster changed; review the draw before recording results')
 if not node['red_entry_id'] or not node['blue_entry_id']:raise HTTPException(409,'Record the earlier-round results first')
 if body.winner_id not in (node['red_entry_id'],node['blue_entry_id']):raise HTTPException(422,'Winner must be a boxer in this bout')
 if node['winner_id'] and node['winner_id']!=body.winner_id:raise HTTPException(409,'Clear this result before changing its winner')
 d=db.get(TournamentDivision,node['division_id']);d.winners={**(d.winners or {}),bout_key:body.winner_id};d.version+=1;p.version+=1;audit(db,user,p,'RESULT_RECORDED');db.commit();return view(db,p)
@router.delete('/{plan_id}/results/{bout_key}')
def clear_result(plan_id:int,bout_key:str,version:int,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id,True)
 if p.version!=version:raise HTTPException(409,'Plan changed. Refresh before clearing a result')
 v=view(db,p);node=next((n for n in v['nodes'] if n['key']==bout_key),None)
 if not node:raise HTTPException(404,'Bout not found')
 if any(n['division_id']==node['division_id'] and n['round']>node['round'] and n['winner_id'] for n in v['nodes']):raise HTTPException(409,'Clear later-round results first')
 d=db.get(TournamentDivision,node['division_id']);d.winners={k:x for k,x in (d.winners or {}).items() if k!=bout_key};d.version+=1;p.version+=1;audit(db,user,p,'RESULT_CLEARED');db.commit();return view(db,p)
@router.get('/{plan_id}/schedule.csv')
def export(plan_id:int,db=Depends(get_db),user=Depends(access)):
 p=plan_for(db,plan_id);v=view(db,p)
 if not p.schedule or v['schedule_stale']:raise HTTPException(409,'Generate a current schedule before exporting')
 out=io.StringIO();writer=csv.writer(out);writer.writerow(['Session','OKC start','Division','Round','Red','Blue','Status']);nodes={n['key']:n for n in v['nodes']}
 def cell(x):
  s=str(x or '');return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
 for b in p.schedule['bouts']:
  n=nodes[b['bout_key']];writer.writerow([LABELS[b['session_key']],b['start_local'],cell(n['division_name']),n['round'],cell(n['red_label']),cell(n['blue_label']),'Draft; OIC approval required'])
 for b in p.schedule['unscheduled']:
  n=nodes[b['bout_key']];writer.writerow(['UNSCHEDULED','',cell(n['division_name']),n['round'],cell(n['red_label']),cell(n['blue_label']),b['reason']])
 return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="tng-tournament-{p.id}-draft-schedule.csv"'})
