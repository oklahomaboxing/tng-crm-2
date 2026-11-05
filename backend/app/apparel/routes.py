"""Public apparel catalog; Clover pays, the existing merchandise ledger records sales."""
import hashlib,hmac,json,os,re,secrets
from datetime import datetime,timezone,date,timedelta
from zoneinfo import ZoneInfo
import requests
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Response
from pydantic import BaseModel,Field,EmailStr
from sqlalchemy import Column,Integer,String,Boolean,Text,LargeBinary,ForeignKey,DateTime,UniqueConstraint
from sqlalchemy.exc import IntegrityError
from app.database import Base,get_db
from app.models import MembershipProduct,MerchandiseCheckout,SalesRep,SecurityLog
from app.core.dependencies import current_user
from app.core.permissions import require_admin

router=APIRouter(prefix='/api/apparel',tags=['TNG Apparel'])
CT=ZoneInfo('America/Chicago')
class ApparelProduct(Base):
 __tablename__='apparel_products'
 id=Column(Integer,primary_key=True)
 slug=Column(String(90),unique=True,nullable=False)
 title=Column(String(120),nullable=False)
 description=Column(Text,default='')
 presale_cents=Column(Integer,nullable=False,default=2000)
 event_cents=Column(Integer,nullable=False,default=2500)
 event_date=Column(String(10),nullable=True)
 fulfillment=Column(String(500),nullable=False,default='')
 published=Column(Boolean,nullable=False,default=False)
 ever_published=Column(Boolean,nullable=False,default=False)
 image=Column(LargeBinary,nullable=True)
 image_type=Column(String(30),nullable=True)
class ApparelVariant(Base):
 __tablename__='apparel_variants'
 __table_args__=(UniqueConstraint('apparel_id','size',name='uq_apparel_size'),)
 id=Column(Integer,primary_key=True)
 apparel_id=Column(Integer,ForeignKey('apparel_products.id'),nullable=False)
 size=Column(String(15),nullable=False)
 product_id=Column(Integer,ForeignKey('membership_products.id'),nullable=False,unique=True)
 clover_presale_id=Column(String(30),nullable=True)
 clover_event_id=Column(String(30),nullable=True)
class ApparelOrder(Base):
 __tablename__='apparel_orders'
 id=Column(Integer,primary_key=True)
 checkout_id=Column(Integer,ForeignKey('merchandise_checkouts.id'),unique=True,nullable=False)
 request_key=Column(String(64),unique=True,nullable=False)
 fingerprint=Column(String(64),nullable=False)
 token_hash=Column(String(64),unique=True,nullable=False)
 items_json=Column(Text,nullable=False)
 fulfillment=Column(String(500),nullable=False)
 collection_status=Column(String(30),nullable=False,default='awaiting_payment')
 checkout_url=Column(Text,nullable=True)
 created_at=Column(DateTime,default=datetime.utcnow)

def price(product,now=None):
 today=(now or datetime.now(timezone.utc)).astimezone(CT).date()
 return product.event_cents if product.event_date and today>=date.fromisoformat(product.event_date) else product.presale_cents

def product_json(db,p):
 amount=price(p)
 return {'id':p.id,'slug':p.slug,'title':p.title,'description':p.description,'presale_cents':p.presale_cents,'event_cents':p.event_cents,'price_cents':amount,'event_date':p.event_date,'phase':'event' if amount==p.event_cents else 'presale','fulfillment':p.fulfillment,'published':p.published,'image_url':f'/api/apparel/{p.id}/image' if p.image else None,'variants':[{'id':v.id,'size':v.size,'clover_synced':bool(v.clover_presale_id and v.clover_event_id)} for v in db.query(ApparelVariant).filter_by(apparel_id=p.id).order_by(ApparelVariant.id)]}
class ProductInput(BaseModel):
 slug:str=Field(pattern=r'^[a-z0-9-]{3,90}$')
 title:str=Field(min_length=3,max_length=120)
 description:str=Field(default='',max_length=2000)
 presale_cents:int=Field(default=2000,ge=100,le=100000)
 event_cents:int=Field(default=2500,ge=100,le=100000)
 event_date:date|None=None
 fulfillment:str=Field(default='',max_length=500)
 sizes:list[str]=Field(default_factory=list,max_length=15)
 published:bool=False

@router.get('/catalog')
def catalog(response:Response,db=Depends(get_db)):
 response.headers['Cache-Control']='no-store'
 return [product_json(db,p) for p in db.query(ApparelProduct).filter_by(published=True).order_by(ApparelProduct.id)]
@router.get('/admin')
def admin_catalog(db=Depends(get_db),user=Depends(current_user)):
 require_admin(user)
 orders=[]
 for order,checkout in db.query(ApparelOrder,MerchandiseCheckout).join(MerchandiseCheckout,MerchandiseCheckout.id==ApparelOrder.checkout_id).order_by(ApparelOrder.id.desc()).limit(100):
  orders.append({'id':order.id,'customer_name':checkout.customer_name,'customer_email':checkout.customer_email,'customer_phone':checkout.customer_phone,'clover_checkout_id':checkout.clover_checkout_id,'items':json.loads(order.items_json),'total_cents':round(checkout.total_amount*100),'payment_status':checkout.status,'collection_status':order.collection_status,'fulfillment':order.fulfillment,'created_at':order.created_at})
 return {'products':[product_json(db,p) for p in db.query(ApparelProduct).order_by(ApparelProduct.id)],'orders':orders}
@router.put('/admin/{product_id}')
def save_product(product_id:int,data:ProductInput,db=Depends(get_db),user=Depends(current_user)):
 require_admin(user)
 p=db.query(ApparelProduct).filter_by(id=product_id).with_for_update().first() if product_id else ApparelProduct()
 if p is None:raise HTTPException(404,'Apparel product not found')
 if p.ever_published and data.slug!=p.slug:raise HTTPException(409,'Published product links are permanent; create a new product for another link')
 sizes=list(dict.fromkeys(x.strip().upper() for x in data.sizes if x.strip()))
 if any(not re.fullmatch(r'[A-Z0-9 -]{1,15}',x) for x in sizes):raise HTTPException(400,'Use short sizes such as S, M, L or 2XL')
 existing=db.query(ApparelProduct).filter(ApparelProduct.slug==data.slug,ApparelProduct.id!=product_id).first()
 if existing:raise HTTPException(409,'Choose a unique product link')
 if data.published and (not sizes or not data.fulfillment.strip() or not p.image or not data.event_date):raise HTTPException(400,'Add the shirt image, sizes, fulfillment instructions and event date before publishing')
 variants=db.query(ApparelVariant).filter_by(apparel_id=product_id).order_by(ApparelVariant.id).all() if product_id else []
 if data.published and (not variants or not all(v.clover_presale_id and v.clover_event_id for v in variants)):raise HTTPException(400,'Create or match Clover POS items before publishing')
 # Keep catalog variants stable so saved purchases and Clover links retain their identity.
 if variants and sizes!=[v.size for v in variants]:raise HTTPException(409,'Sizes are locked after creation; create another product to offer different sizes')
 if variants and any(v.clover_presale_id or v.clover_event_id for v in variants) and (data.title!=p.title or data.presale_cents!=p.presale_cents or data.event_cents!=p.event_cents):raise HTTPException(409,'Clover items already exist. Keep their names/prices or create a new product version')
 for key,value in data.model_dump(exclude={'sizes','event_date'}).items():setattr(p,key,value)
 p.event_date=data.event_date.isoformat() if data.event_date else None
 if data.published:p.ever_published=True
 db.add(p);db.flush()
 if not variants:
  for size in sizes:
   item=MembershipProduct(name=f'{p.title} / {size}',price=p.presale_cents/100,category='merchandise',is_membership=False,active=False,track_inventory=False,sku=f'TNG-APP-{p.id}-{size}')
   db.add(item);db.flush();db.add(ApparelVariant(apparel_id=p.id,size=size,product_id=item.id))
 db.add(SecurityLog(user_id=user.id,action='APPAREL_PRODUCT_SAVED',description=f'Apparel #{p.id}'))
 db.commit();return product_json(db,p)
@router.post('/admin/{product_id}/image')
async def image_upload(product_id:int,file:UploadFile=File(...),db=Depends(get_db),user=Depends(current_user)):
 require_admin(user);p=db.get(ApparelProduct,product_id)
 if not p:raise HTTPException(404,'Apparel product not found')
 raw=await file.read(5*1024*1024+1)
 if len(raw)>5*1024*1024:raise HTTPException(400,'Use an image under 5 MB')
 import io
 from PIL import Image
 try:
  with Image.open(io.BytesIO(raw)) as image:
   if image.width*image.height>20000000 or image.format not in ('JPEG','PNG','WEBP'):raise ValueError()
   image.verify()
   kind={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[image.format]
 except Exception:raise HTTPException(400,'Upload a valid JPG, PNG or WebP image')
 p.image=raw;p.image_type=kind;db.commit();return {'saved':True}
@router.get('/{product_id}/image')
def image_get(product_id:int,db=Depends(get_db)):
 p=db.get(ApparelProduct,product_id)
 if not p or not p.image:raise HTTPException(404,'Image not found')
 return Response(p.image,media_type=p.image_type,headers={'X-Content-Type-Options':'nosniff','Cache-Control':'public, max-age=300'})

def clover():
 token=os.getenv('CLOVER_API_TOKEN');merchant=os.getenv('CLOVER_MERCHANT_ID')
 if not token or not merchant:raise HTTPException(503,'Clover is not configured')
 base='https://api.clover.com' if os.getenv('CLOVER_ENV','production')=='production' else 'https://apisandbox.dev.clover.com'
 return base,merchant,{'Authorization':f'Bearer {token}','X-Clover-Merchant-Id':merchant,'Content-Type':'application/json'}
@router.post('/admin/{product_id}/clover')
def sync_clover(product_id:int,db=Depends(get_db),user=Depends(current_user)):
 require_admin(user);p=db.query(ApparelProduct).filter_by(id=product_id).with_for_update().first()
 if not p:raise HTTPException(404,'Apparel product not found')
 base,merchant,headers=clover()
 # Match deterministic SKU before creating so a timeout cannot cause duplicate POS items.
 try:
  response=requests.get(f'{base}/v3/merchants/{merchant}/items',headers=headers,params={'limit':1000},timeout=15);response.raise_for_status();items=response.json().get('elements',[])
  if len(items)>=1000:raise HTTPException(409,'Clover catalog needs a paginated review before synchronizing apparel')
  for v in db.query(ApparelVariant).filter_by(apparel_id=p.id):
   for phase,amount,attr in [('PRESALE',p.presale_cents,'clover_presale_id'),('EVENT',p.event_cents,'clover_event_id')]:
    sku=f'TNG-APP-{p.id}-{v.size}-{phase}';matches=[i for i in items if i.get('sku')==sku]
    if len(matches)>1:raise HTTPException(409,'Duplicate Clover apparel SKU needs review')
    if getattr(v,attr):continue
    if matches:
     if matches[0].get('price')!=amount:raise HTTPException(409,'Existing Clover price differs; review before linking')
     identity=matches[0]['id']
    else:
     r=requests.post(f'{base}/v3/merchants/{merchant}/items',headers=headers,json={'name':f'{p.title} / {v.size} / {phase}','price':amount,'priceType':'FIXED','sku':sku,'isRevenue':True},timeout=15);r.raise_for_status();identity=r.json()['id']
    setattr(v,attr,identity);db.flush()
  db.commit()
  return {'synced':True,'notice':'Separate presale and event-day items are available on Clover POS. Select the correct phase at the register.'}
 except HTTPException:raise
 except Exception:db.rollback();raise HTTPException(503,'Clover synchronization could not finish. Retry safely to match existing SKUs; do not create duplicate items manually.')

class CheckoutInput(BaseModel):
 request_key:str=Field(pattern=r'^[a-f0-9-]{32,64}$')
 name:str=Field(min_length=2,max_length=100)
 email:EmailStr
 phone:str=Field(default='',max_length=25)
 variant_id:int
 quantity:int=Field(default=1,ge=1,le=10)
 expected_price_cents:int=Field(ge=100,le=100000)

def public_token(key):return hmac.new(os.environ['SECRET_KEY'].encode(),('apparel:'+key).encode(),hashlib.sha256).hexdigest()
@router.post('/checkout')
def create_checkout(data:CheckoutInput,db=Depends(get_db)):
 variant=db.get(ApparelVariant,data.variant_id);p=db.get(ApparelProduct,variant.apparel_id) if variant else None
 if not p or not p.published:raise HTTPException(404,'This item is not available')
 if not p.fulfillment:raise HTTPException(409,'Fulfillment needs configuration')
 token=public_token(data.request_key);fingerprint=hashlib.sha256(json.dumps(data.model_dump(),sort_keys=True).encode()).hexdigest()
 previous=db.query(ApparelOrder).filter_by(request_key=data.request_key).first()
 if previous:
  if previous.fingerprint!=fingerprint:raise HTTPException(409,'Checkout details changed; start a new checkout')
  if not previous.checkout_url:raise HTTPException(409,'Checkout creation is uncertain. Check your email or contact the gym before trying another payment.')
  return {'checkout_url':previous.checkout_url,'order_token':token}
 now=datetime.utcnow()
 if db.query(ApparelOrder).filter(ApparelOrder.created_at>=now-timedelta(minutes=1)).count()>=30 or db.query(MerchandiseCheckout).filter(MerchandiseCheckout.customer_email==str(data.email).lower(),MerchandiseCheckout.created_at>=now-timedelta(minutes=10)).count()>=3:raise HTTPException(429,'Too many checkouts. Wait a few minutes before trying again.')
 rep=db.query(SalesRep).first()
 if not rep:raise HTTPException(503,'Store checkout needs a sales ledger account')
 amount=price(p)
 if data.expected_price_cents!=amount:raise HTTPException(409,'The price changed. Refresh the product page and review the new price before paying.')
 base,merchant,headers=clover();total=amount*data.quantity
 cart=[{'product_id':variant.product_id,'quantity':data.quantity,'unit_price_cents':amount}]
 checkout=MerchandiseCheckout(sales_rep_id=rep.id,customer_name=data.name.strip(),customer_email=str(data.email).lower(),customer_phone=data.phone,cart_json=json.dumps(cart),total_amount=total/100,status='creating')
 db.add(checkout);db.flush()
 order=ApparelOrder(checkout_id=checkout.id,request_key=data.request_key,fingerprint=fingerprint,token_hash=hashlib.sha256(token.encode()).hexdigest(),items_json=json.dumps([{'title':p.title,'size':variant.size,'quantity':data.quantity,'unit_price_cents':amount}]),fulfillment=p.fulfillment)
 db.add(order)
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'Checkout is already being created; retry the same request')
 app=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')
 payload={'customer':{'firstName':data.name.strip(),'email':str(data.email)},'redirectUrls':{'success':f'{app}/apparel?order={token}','failure':f'{app}/apparel?order={token}'},'shoppingCart':{'lineItems':[{'name':f'{p.title} / {variant.size}','price':amount,'unitQty':data.quantity}]}}
 try:
  r=requests.post(f'{base}/invoicingcheckoutservice/v1/checkouts',headers=headers,json=payload,timeout=25);r.raise_for_status();result=r.json();url=result.get('href') or result.get('url');identity=result.get('checkoutSessionId') or result.get('id')
  if identity:checkout.clover_checkout_id=str(identity);db.commit()
  from urllib.parse import urlparse
  parsed=urlparse(url or '')
  if not identity or parsed.scheme!='https' or not (parsed.hostname=='clover.com' or (parsed.hostname or '').endswith('.clover.com')):raise ValueError()
  checkout.clover_checkout_id=str(identity);checkout.status='pending';order.checkout_url=url;db.commit()
 except Exception:
  checkout.status='creation_uncertain';db.commit();raise HTTPException(503,'Payment page could not be confirmed. Contact the gym before starting another checkout.')
 return {'checkout_url':url,'order_token':token}
@router.get('/order/{token}')
def order_status(token:str,response:Response,db=Depends(get_db)):
 response.headers['Cache-Control']='no-store'
 order=db.query(ApparelOrder).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
 if not order:raise HTTPException(404,'Order not found')
 checkout=db.get(MerchandiseCheckout,order.checkout_id)
 return {'status':checkout.status,'items':json.loads(order.items_json),'total_cents':round(checkout.total_amount*100),'fulfillment':order.fulfillment,'collection_status':order.collection_status,'paid':checkout.status=='paid'}
class CollectionInput(BaseModel):
 status:str=Field(pattern='^(ready|collected)$')
@router.put('/admin/orders/{order_id}')
def collection(order_id:int,data:CollectionInput,db=Depends(get_db),user=Depends(current_user)):
 require_admin(user);order=db.query(ApparelOrder).filter_by(id=order_id).with_for_update().first()
 if not order:raise HTTPException(404,'Order not found')
 if db.get(MerchandiseCheckout,order.checkout_id).status!='paid':raise HTTPException(409,'Verify Clover payment before fulfilling an order')
 order.collection_status=data.status;db.commit();return {'saved':True}

@router.get('/share/{slug}')
def share_page(slug:str,db=Depends(get_db)):
 from html import escape
 from fastapi.responses import HTMLResponse
 p=db.query(ApparelProduct).filter_by(slug=slug,published=True).first()
 if not p:raise HTTPException(404,'Apparel is not published')
 frontend=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')
 backend=os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
 title=escape(p.title);description=escape(p.description,quote=True);image=backend+f'/api/apparel/{p.id}/image';url=frontend+'/apparel?product='+p.slug
 return HTMLResponse(f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | TNG Apparel</title><meta property="og:type" content="product"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:image" content="{image}"><meta name="twitter:card" content="summary_large_image"><meta property="og:url" content="{backend}/api/apparel/share/{p.slug}"></head><body style="margin:0;background:#08090c;color:white;font:18px Arial;text-align:center"><main style="max-width:650px;margin:40px auto;padding:24px"><p>TNG APPAREL · THE NEXT GENERATION</p><img src="{image}" alt="{title}" style="width:100%;border-radius:20px"><h1>{title}</h1><p>{description}</p><h2>${price(p)/100:.2f}</h2><p>{escape(p.fulfillment)}</p><a href="{url}" style="display:inline-block;padding:20px 40px;background:#d31b35;color:white;text-decoration:none;border-radius:12px">Choose size &amp; buy with Clover</a></main></body></html>''',headers={'Cache-Control':'no-store'})

@router.get('/admin/export/catalog.csv')
def catalog_export(db=Depends(get_db),user=Depends(current_user)):
 require_admin(user)
 import csv,io
 output=io.StringIO();writer=csv.writer(output);writer.writerow(['sku','title','description','size','price_usd','product_link','image_link','brand','fulfillment'])
 frontend=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/');backend=os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
 def cell(value):
  value=str(value or '')
  return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
 for p in db.query(ApparelProduct).filter_by(published=True):
  for v in db.query(ApparelVariant).filter_by(apparel_id=p.id):writer.writerow([cell('TNG-APP-'+str(p.id)+'-'+v.size),cell(p.title),cell(p.description),cell(v.size),f'{price(p)/100:.2f}',frontend+'/apparel?product='+p.slug,backend+f'/api/apparel/{p.id}/image','TNG Apparel',cell(p.fulfillment)])
 return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="tng-apparel-catalog.csv"','Cache-Control':'no-store'})
