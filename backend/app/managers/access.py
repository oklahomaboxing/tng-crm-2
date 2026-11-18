"""Revalidate active representation on every delegated fighter request."""
from types import SimpleNamespace
from fastapi import HTTPException
from app.matchmaker.models import BoxingManagerAccount,BoxingManagerFighter

def manager_for(db,user,lock=False):
    if user.role!='manager':raise HTTPException(403,'Manager login required')
    q=db.query(BoxingManagerAccount).filter_by(user_id=user.id,active=True)
    manager=q.with_for_update().first() if lock else q.first()
    if not manager or not manager.active:raise HTTPException(403,'An active manager profile is required')
    return manager

def represented_fighter(db,user,fid):
    manager=manager_for(db,user)
    if not db.query(BoxingManagerFighter).filter_by(manager_account_id=manager.id,fighter_id=fid,active=True).first():raise HTTPException(403,'This boxer is not on your active roster')
    return manager

def delegated_account(db,user):
    context=db.info.get('manager_fighter_context')
    if not context or context.get('actor_id')!=user.id:raise HTTPException(403,'Select a boxer in the manager workspace first')
    represented_fighter(db,user,context['fighter_id'])
    return SimpleNamespace(fighter_id=context['fighter_id'],user_id=user.id,id=None)

def authorize_workspace_request(db,user,payload,request):
    raw=payload.get('managed_fighter_id')
    if raw is None:return
    if user.role!='manager' or not isinstance(raw,int) or isinstance(raw,bool) or raw<=0:raise HTTPException(403,'Invalid manager workspace authorization')
    represented_fighter(db,user,raw)
    path=request.url.path
    own_report=path in (f'/api/events/fighters/{raw}/contribution',f'/api/events/fighters/{raw}/results') and request.method=='GET'
    portal=path=='/api/fighter/me' or path.startswith('/api/fighter/me/')
    if not portal and not own_report:raise HTTPException(403,'This workspace token is restricted to the selected boxer')
    if portal and any(part in path for part in ('/esign','/docusign-signing-url','/adobe-signing-url')):raise HTTPException(403,'The boxer must provide their own personal signature')
    db.info['manager_fighter_context']={'actor_id':user.id,'fighter_id':raw}
