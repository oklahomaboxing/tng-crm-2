"""Event-wide signed agreement index; files stay behind existing staff-only downloads."""
import hashlib,hmac,json
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,Response,HTTPException
from app.database import get_db
from app.core.dependencies import current_user
from app.core.permissions import require_matchmaker_access
from .models import BoxingContract,BoxingContractSignature,BoxingSignedContractDocument,BoxingEvent,BoxingFighter
router=APIRouter(prefix='/api/boxing',tags=['Signed contracts'])
def library(event_id,response,db,user):
 require_matchmaker_access(user);response.headers['Cache-Control']='private, no-store'
 if event_id is not None and not db.get(BoxingEvent,event_id):raise HTTPException(404,'Event not found')
 rows=[]
 fighter_names={f.id:f.legal_name for f in db.query(BoxingFighter.id,BoxingFighter.legal_name)}
 event_names={e.id:e.name for e in db.query(BoxingEvent.id,BoxingEvent.name)}
 docs={d.contract_id:d for d in db.query(BoxingSignedContractDocument.id,BoxingSignedContractDocument.contract_id,BoxingSignedContractDocument.file_name,BoxingSignedContractDocument.uploaded_at).join(BoxingContract,BoxingContract.id==BoxingSignedContractDocument.contract_id).filter(True if event_id is None else BoxingContract.event_id==event_id)}
 signatures={s.contract_id:s for s in db.query(BoxingContractSignature).join(BoxingContract,BoxingContract.id==BoxingContractSignature.contract_id).filter(True if event_id is None else BoxingContract.event_id==event_id)}
 for contract in db.query(BoxingContract).filter(True if event_id is None else BoxingContract.event_id==event_id).order_by(BoxingContract.id.desc()):
  document=docs.get(contract.id);signature=signatures.get(contract.id);valid=False
  if signature:
   try:
    raw=signature.contract_snapshot or '';snapshot=json.loads(raw)
    valid=bool(signature.agreed and signature.typed_legal_name.strip() and snapshot.get('contract_id')==contract.id and snapshot.get('fighter_id')==signature.fighter_id==contract.fighter_id and hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(),signature.snapshot_sha256 or ''))
   except (ValueError,AttributeError,TypeError):pass
  completed=str(contract.docusign_status or '').lower()=='completed' or str(contract.adobe_status or '').lower() in ('signed','completed') or str(contract.status or '').lower()=='signed'
  if not (document or valid or completed or (signature and signature.agreed)):continue
  signed_at=signature.signed_at if valid else contract.docusign_signed_at or contract.adobe_signed_at or (document.uploaded_at if document else None)
  if isinstance(signed_at,datetime):signed_at=(signed_at.replace(tzinfo=timezone.utc) if signed_at.tzinfo is None else signed_at).isoformat()
  rows.append({'id':contract.id,'event_id':contract.event_id,'event_name':contract.event_name or event_names.get(contract.event_id,''),'bout_id':contract.bout_id,'fighter_name':contract.boxer_name or (signature.typed_legal_name if valid else fighter_names.get(contract.fighter_id,'')),'opponent_name':contract.opponent_name or fighter_names.get(contract.opponent_id,''),'corner':contract.corner,'contract_status':contract.status,'source':'signed_pdf' if document else 'electronic_signature_record' if valid else 'needs_sync_or_review','download_available':bool(document or valid),'signed_at':signed_at,'provider':contract.signature_provider,'filename':document.file_name if document else None})
 return {'event_id':event_id,'contracts':rows}

@router.get('/events/{event_id}/signed-contracts')
def event_library(event_id:int,response:Response,db=Depends(get_db),user=Depends(current_user)):
 return library(event_id,response,db,user)
@router.get('/signed-contracts')
def all_library(response:Response,db=Depends(get_db),user=Depends(current_user)):
 return library(None,response,db,user)
