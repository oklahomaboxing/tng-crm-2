"""Saved Clover descriptions only; never cache customer/payment credentials."""
import json,os
from datetime import datetime,timedelta
import requests
from sqlalchemy import Column,Integer,String,DateTime,Text,ForeignKey
from app.database import Base
from app.models import Sale

class CloverPurchaseDetail(Base):
    __tablename__='member_clover_purchase_details'
    id=Column(Integer,primary_key=True)
    member_id=Column(Integer,ForeignKey('members.id',ondelete='CASCADE'),nullable=False,index=True)
    order_id=Column(String,unique=True,nullable=False)
    items_json=Column(Text,nullable=False)
    status=Column(String,default='ready',nullable=False)
    fetched_at=Column(DateTime,default=datetime.utcnow)


def save_details(db,member_id,order):
    order_id=str(order.get('id') or '')
    if not order_id:return False
    owners={identity for (identity,) in db.query(Sale.member_id).filter_by(clover_order_id=order_id).distinct().all()}
    if owners and owners!={member_id}:return False
    items=[]
    for row in (order.get('lineItems') or {}).get('elements',[]):
        name=str(row.get('name') or (row.get('item') or {}).get('name') or 'Custom Clover item — no description supplied')[:300]
        qty=row.get('unitQty')
        quantity=qty/1000 if isinstance(qty,(int,float)) and qty>0 else 1
        items.append({'name':name,'quantity':quantity,'unit_price_cents':row.get('price'),'item_id':(row.get('item') or {}).get('id')})
    if not items:return False
    detail=db.query(CloverPurchaseDetail).filter_by(order_id=order_id).first()
    if detail and detail.member_id!=member_id:return False
    if not detail:detail=CloverPurchaseDetail(order_id=order_id,member_id=member_id);db.add(detail)
    detail.items_json=json.dumps(items);detail.status='ready';detail.fetched_at=datetime.utcnow()
    return True


def purchase_details(db,sale):
    row=db.query(CloverPurchaseDetail).filter_by(order_id=sale.clover_order_id,member_id=sale.member_id,status='ready').first() if sale.clover_order_id else None
    items=json.loads(row.items_json) if row else [{'name':sale.product.name if sale.product else 'Purchase details unavailable','quantity':sale.quantity or 1}]
    if row and db.query(Sale).filter_by(clover_order_id=sale.clover_order_id,member_id=sale.member_id).count()>1:
        item_id=getattr(sale.product,'clover_item_id',None) if sale.product else None
        matched=[item for item in items if (item_id and item.get('item_id')==item_id) or (sale.product and item['name'].strip().casefold()==sale.product.name.strip().casefold())]
        if matched:items=matched
        else:
            row=None;items=[{'name':sale.product.name if sale.product else 'Purchase details unavailable','quantity':sale.quantity or 1}]
    description='; '.join(f"{item['name']}"+(f" × {item['quantity']:g}" if item['quantity']!=1 else '') for item in items)
    return {'items':items,'purchase_description':description,'purchase_source':'clover' if row else 'tngos','refund_amount':float(sale.refund_amount or 0),'refunded':bool(sale.refunded)}


def sync_purchase_details(db,limit=20):
    token=os.getenv('CLOVER_API_TOKEN','');merchant=os.getenv('CLOVER_MERCHANT_ID','')
    if not token or not merchant:return {'updated':0,'failed':0}
    cached={row.order_id for row in db.query(CloverPurchaseDetail).all() if row.status=='ready' or row.fetched_at>datetime.utcnow()-timedelta(hours=24)}
    orders={}
    for sale in db.query(Sale).filter(Sale.clover_order_id.isnot(None)).order_by(Sale.sale_date.desc()):
        if sale.clover_order_id and sale.clover_order_id not in cached:orders.setdefault(sale.clover_order_id,sale.member_id)
    base='https://api.clover.com' if os.getenv('CLOVER_ENV','production')=='production' else 'https://apisandbox.dev.clover.com'
    updated=failed=0
    for order_id,member_id in list(orders.items())[:limit]:
        try:
            response=requests.get(f'{base}/v3/merchants/{merchant}/orders/{order_id}',headers={'Authorization':'Bearer '+token},params={'expand':'lineItems,lineItems.item'},timeout=10)
            saved=response.ok and save_details(db,member_id,response.json())
            if saved:updated+=1
            else:
                failed+=1
                row=db.query(CloverPurchaseDetail).filter_by(order_id=order_id).first()
                if not row:row=CloverPurchaseDetail(order_id=order_id,member_id=member_id,items_json='[]');db.add(row)
                row.status='retry';row.fetched_at=datetime.utcnow()
            db.commit()
        except (requests.RequestException,ValueError):failed+=1;db.rollback()
    return {'updated':updated,'failed':failed}
