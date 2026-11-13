"""Itemized contract deductions and payout statements; signed terms remain immutable."""
import io,json
from datetime import datetime
from decimal import Decimal,InvalidOperation
from html import escape
from fastapi import APIRouter,Depends,HTTPException,Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import Column,Integer,Text,DateTime,ForeignKey
from sqlalchemy.orm import Session
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.core.permissions import require_matchmaker_access
from app.models import SecurityLog
from .models import BoxingContract,BoxingContractSignature,BoxingSignedContractDocument
router=APIRouter(prefix='/api/boxing/contracts',tags=['Contract deductions'])
class ContractDeductions(Base):
    __tablename__='boxing_contract_deductions'
    contract_id=Column(Integer,ForeignKey('boxing_contracts.id'),primary_key=True)
    base_deductions_cents=Column(Integer,nullable=False,default=0)
    items_json=Column(Text,nullable=False,default='[]')
    version=Column(Integer,nullable=False,default=0)
    updated_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class DeductionItem(BaseModel):
    label:str=Field(min_length=1,max_length=120)
    amount:Decimal=Field(gt=0,max_digits=9,decimal_places=2)
    @field_validator('label')
    @classmethod
    def clean(cls,value):
        value=value.strip()
        if not value:raise ValueError('Enter a deduction description')
        return value
class SaveDeductions(BaseModel):
    version:int=Field(ge=0)
    items:list[DeductionItem]=Field(max_length=50)

def cents(value):
    try:
        d=Decimal(str(value or 0))
        if not d.is_finite() or d<0:raise ValueError()
        return int(d.quantize(Decimal('.01'))*100)
    except (InvalidOperation,ValueError,TypeError):raise HTTPException(400,'Contract money fields need review')
def locked(db,c):
    return bool(str(c.status or '').lower() in ('signed','sent','completed','executed') or str(c.docusign_status or '').lower() in ('sent','delivered','completed') or str(c.adobe_status or '').lower() in ('out_for_signature','signed','completed') or db.query(BoxingContractSignature.id).filter_by(contract_id=c.id).first() or db.query(BoxingSignedContractDocument.id).filter_by(contract_id=c.id).first())
def contract(db,cid,write=False):
    q=db.query(BoxingContract).filter_by(id=cid)
    if write:q=q.with_for_update()
    c=q.one_or_none()
    if not c:raise HTTPException(404,'Contract not found')
    return c

def view(db,c):
    row=db.get(ContractDeductions,c.id);items=json.loads(row.items_json) if row else []
    base=row.base_deductions_cents if row else cents(c.deductions)
    extra=sum(i['amount_cents'] for i in items);gross=cents(c.gross_purse);travel=cents(c.travel_expense);per_diem=cents(c.per_diem_total)
    return {'contract_id':c.id,'fighter_id':c.fighter_id,'fighter_name':c.boxer_name,'event_name':c.event_name,'contract_status':c.status,'signed_terms_locked':locked(db,c),'version':row.version if row else 0,'items':items,'gross_purse_cents':gross,'travel_cents':travel,'per_diem_cents':per_diem,'base_deductions_cents':base,'added_deductions_cents':extra,'total_deductions_cents':base+extra,'net_payout_cents':gross+travel+per_diem-base-extra,'updated_at':row.updated_at.isoformat()+'Z' if row else None,'basis':'Gross purse + travel allowance + recorded per diem − deductions. Ticket commissions are separate.'}

@router.get('/{contract_id}/deductions')
def get_deductions(contract_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user)
    return JSONResponse(view(db,contract(db,contract_id)),headers={'Cache-Control':'private, no-store'})

@router.put('/{contract_id}/deductions')
def save_deductions(contract_id:int,body:SaveDeductions,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user);c=contract(db,contract_id,True);row=db.get(ContractDeductions,c.id)
    version=row.version if row else 0
    if body.version!=version:raise HTTPException(409,'Deductions changed elsewhere. Reload before saving again.')
    before=view(db,c);base=row.base_deductions_cents if row else cents(c.deductions)
    items=[{'label':i.label,'amount_cents':int(i.amount*100)} for i in body.items]
    total=base+sum(i['amount_cents'] for i in items)
    if total>cents(c.gross_purse)+cents(c.travel_expense)+cents(c.per_diem_total):raise HTTPException(400,'Deductions exceed the purse and travel allowance. Review the amounts.')
    if not row:row=ContractDeductions(contract_id=c.id,base_deductions_cents=base,updated_by=user.id);db.add(row)
    row.items_json=json.dumps(items);row.version=version+1;row.updated_by=user.id;row.updated_at=datetime.utcnow()
    # Draft contracts receive the same totals used by their existing PDF generator.
    # Sent/signed contracts retain their original fields and signature snapshots.
    if not before['signed_terms_locked']:
        c.deductions=total/100;c.boxer_paid=(cents(c.gross_purse)+cents(c.travel_expense)+cents(c.per_diem_total)-total)/100
    db.flush();after=view(db,c)
    db.add(SecurityLog(user_id=user.id,action='CONTRACT_DEDUCTIONS_UPDATED',endpoint=f'/api/boxing/contracts/{c.id}/deductions',description=json.dumps({'contract_id':c.id,'before':before,'after':after}),success=True));db.commit()
    return JSONResponse(after,headers={'Cache-Control':'private, no-store'})

@router.get('/{contract_id}/deductions.pdf')
def statement(contract_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    require_matchmaker_access(user);data=view(db,contract(db,contract_id))
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    output=io.BytesIO();styles=getSampleStyleSheet();story=[]
    for text,style in [('TNG BOXING','Title'),('Payout deduction statement','Heading2'),(f"{data['fighter_name']} · {data['event_name']} · Contract #{contract_id}",'Normal')]:story.extend([Paragraph(escape(text),styles[style]),Spacer(1,10)])
    money=lambda value:f'${value/100:,.2f}'
    rows=[['Description','Amount'],['Gross purse',money(data['gross_purse_cents'])],['Travel allowance',money(data['travel_cents'])],['Recorded per diem',money(data['per_diem_cents'])],['Existing contract deductions',money(data['base_deductions_cents'])]]
    rows.extend([[Paragraph(escape(i['label']),styles['Normal']),'-'+money(i['amount_cents'])] for i in data['items']])
    rows.extend([['Total deductions',money(data['total_deductions_cents'])],['Projected net payout',money(data['net_payout_cents'])]])
    table=Table(rows,colWidths=[370,110]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#171717')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#f7e8ea')),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('ALIGN',(1,0),(1,-1),'RIGHT'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.3,colors.lightgrey)]));story.extend([table,Spacer(1,16),Paragraph(escape(data['basis']),styles['Normal']),Spacer(1,10),Paragraph('This payout statement does not alter a signed agreement or confirm that payment has been made.',styles['Normal'])])
    SimpleDocTemplate(output,pagesize=(612,792),leftMargin=48,rightMargin=48).build(story)
    return Response(output.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="TNG_contract_{contract_id}_deductions.pdf"','Cache-Control':'private, no-store'})


def recorded_total(db,c):
    if not c.id:return None
    row=db.get(ContractDeductions,c.id)
    return (row.base_deductions_cents+sum(i['amount_cents'] for i in json.loads(row.items_json)))/100 if row else None


def pdf_deductions(db,c,for_signing=False):
    if not c.id or not db.get(ContractDeductions,c.id):return None
    if for_signing and locked(db,c):return None
    return view(db,c)
