"""Deterministic proposals using reviewed paired limits; never an eligibility clearance."""
import hashlib,json
from datetime import date
from fastapi import HTTPException
from .rosters import AmateurEntry,AmateurRulebook,AmateurMatchRun,audit,DEFAULT_PREFERENCES
from .rules_2026 import compatible,DOCUMENT_SHA256,IMPLEMENTATION

def roster_fingerprint(roster,rulebook,entries):
    snapshot={'roster_version':roster.version,'date':roster.competition_date.isoformat(),'rule_id':rulebook.id,'rule_hash':rulebook.document_sha256,'config':rulebook.config,'preferences':{**DEFAULT_PREFERENCES,**(roster.preferences or {})},'entries':[(e.id,e.version,e.excluded,e.data,e.issues) for e in entries]}
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest()

def generate(db,roster,user):
    rulebook=db.query(AmateurRulebook).filter_by(year=roster.competition_date.year,enabled=True).first()
    if not rulebook:raise HTTPException(409,'Official rules for this competition year are not verified')
    if rulebook.document_sha256!=DOCUMENT_SHA256 or rulebook.config.get('implementation')!=IMPLEMENTATION:raise HTTPException(409,'The reviewed rule configuration needs correction before matching')
    prefs={**DEFAULT_PREFERENCES,**(roster.preferences or {})}
    entries=db.query(AmateurEntry).filter_by(roster_id=roster.id).order_by(AmateurEntry.id).all()
    eligible=[e for e in entries if not e.excluded and not e.issues]
    if len(eligible)>200:raise HTTPException(422,'Generate proposals with up to 200 available boxers at a time; exclude others or split the roster')
    fingerprint=roster_fingerprint(roster,rulebook,entries)
    prior=db.query(AmateurMatchRun).filter_by(roster_id=roster.id,roster_fingerprint=fingerprint).first()
    if prior:return {'run_id':prior.id,**prior.result,'existing':True}
    candidates=[]
    for i,a in enumerate(eligible):
        for j in range(i+1,len(eligible)):
            b=eligible[j];rule=compatible(a.data,b.data,roster.competition_date,prefs)
            if rule:
                gap=abs(a.data['weight_lb']-b.data['weight_lb']);bouts=abs(a.data['bouts']-b.data['bouts']);dobgap=abs((date.fromisoformat(a.data['dob'])-date.fromisoformat(b.data['dob'])).days)
                candidates.append((i,j,rule,int(round(gap*1000+bouts*100+dobgap/36.525))))
    pairs=[];used=set();optimal=True
    if candidates:
        import numpy as np
        from scipy.optimize import milp,Bounds,LinearConstraint
        from scipy.sparse import coo_matrix
        n=len(candidates);row=[];col=[]
        for k,(i,j,_,_) in enumerate(candidates):row.extend([i,j]);col.extend([k,k])
        matrix=coo_matrix((np.ones(2*n),(row,col)),shape=(len(eligible),n)).tocsc()
        priority=(max(c[3] for c in candidates)+1)*(len(eligible)+1)
        solution=milp(c=np.array([-priority+c[3] for c in candidates],dtype=float),integrality=np.ones(n),bounds=Bounds(0,1),constraints=LinearConstraint(matrix,np.zeros(len(eligible)),np.ones(len(eligible))),options={'time_limit':10})
        if solution.x is None:raise HTTPException(409,'The proposal solver could not finish. Reduce the available roster and retry')
        optimal=solution.status==0
        for k,value in enumerate(solution.x):
            if value<0.5:continue
            i,j,rule,_=candidates[k];a,b=eligible[i],eligible[j]
            if a.id in used or b.id in used:raise HTTPException(500,'Conflicting proposals were rejected')
            used.update([a.id,b.id]);pairs.append({'red_entry_id':a.id,'blue_entry_id':b.id,'division':rule['division'],'rule_reference':rule['reference'],'rounds':rule['rounds'],'max_round_minutes':rule['max_round_minutes'],'weight_limits_lb':rule['weight_limits_lb'],'experience_review_required':True,'winning_percentages_missing':rule['winning_percentages_missing'],'win_percentages':rule['win_percentages'],'coed':rule['coed'],'masters':rule['masters'],'weight_gap_lb':round(abs(a.data['weight_lb']-b.data['weight_lb']),3),'bout_gap':abs(a.data['bouts']-b.data['bouts'])})
    unmatched=[{'entry_id':e.id,'reason':'Excluded by staff' if e.excluded else 'Roster data needs review' if e.issues else 'No opponent fits the age/weight limits and selected TNG preferences; ages 35–40 also need registered age classification' if not any(e.id in (eligible[i].id,eligible[j].id) for i,j,_,_ in candidates) else 'Unmatched to keep one bout per boxer'} for e in entries if e.id not in used]
    result={'proposals':pairs,'unmatched':unmatched,'candidate_pairs':len(candidates),'solver_optimal':optimal,'rulebook_title':rulebook.title,'reference_year':2026,'source_url':rulebook.source_url,'age_basis':'birthday','preferences':prefs,'notice':'Preliminary age/weight proposals only. Total bouts are reported; winning percentages, all combat-sport experience, current membership, actual weigh-in weights and medical clearance still require review. Both coaches and the Official in Charge must approve. TNG bout-gap, same-club and unlimited-weight preferences are not USA Boxing rules. No offers, contracts or card changes were sent.'}
    run=AmateurMatchRun(roster_id=roster.id,rulebook_id=rulebook.id,competition_date=roster.competition_date,roster_fingerprint=fingerprint,result=result,created_by=user.id);db.add(run);audit(db,user,'MATCH_PROPOSALS_GENERATED',roster.id);db.commit();return {'run_id':run.id,**result,'existing':False}
