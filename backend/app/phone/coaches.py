"""Signed keypad coach directory, using the existing transfer/callback flow."""
from fastapi import APIRouter,Depends,Request
from sqlalchemy.orm import Session
from app.database import get_db
from .routes import verified,config,get_call,gather,transfer_for
router=APIRouter(prefix='/api/phone/coaches',tags=['Coach phone directory'])

def offer_coaches(db,call,cfg):
    if not cfg.enabled:return transfer_for(db,call,cfg)
    coaches=[c for c in cfg.coaches if c.enabled]
    if not coaches:
        db.commit();return gather('No coach lines are currently available. Press 0 for the front desk.','menu',cfg=cfg)
    call.stage='coach_menu';call.empty_attempts=0;db.commit()
    prompt='Choose your coach. '+' '.join(f'Press {c.digit} for {c.name}.' for c in coaches)+' Press 0 for the front desk, or 9 for the main menu.'
    # Nine remains a coach digit only when explicitly configured as such.
    if any(c.digit=='9' for c in coaches):prompt=prompt.replace(', or 9 for the main menu','')
    return gather(prompt,'coaches/choose',cfg=cfg)

@router.post('/choose')
async def choose(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    if not cfg.enabled or form.get('Digits')=='0':return transfer_for(db,call,cfg)
    if call.stage!='coach_menu':return offer_coaches(db,call,cfg)
    digit=str(form.get('Digits') or '')
    coaches=[c for c in cfg.coaches if c.enabled]
    if digit=='9' and not any(c.digit=='9' for c in coaches):
        from .routes import MENU
        call.stage='menu';db.commit();return gather(MENU,'menu',cfg=cfg)
    matches=[c for c in coaches if digit==c.digit]
    if len(matches)==1:return transfer_for(db,call,cfg,'coach_'+matches[0].digit)
    call.empty_attempts+=1
    if call.empty_attempts>=3:return transfer_for(db,call,cfg)
    # Preserve the invalid-choice count while repeating the directory.
    attempts=call.empty_attempts;result=offer_coaches(db,call,cfg);call.empty_attempts=attempts;db.commit();return result
