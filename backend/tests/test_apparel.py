import os,unittest,io,json
from datetime import datetime,timezone
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import Member,MembershipProduct,MerchandiseCheckout,Sale
from app.apparel.routes import ApparelProduct,ApparelVariant,ApparelOrder,price
from app import main

class ApparelTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def make_product(self):
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':'earned-not-given','title':'TNG Earned Not Given','sizes':['S','M'],'fulfillment':'Pickup at event merch table','event_date':'2026-11-14'});self.assertEqual(r.status_code,200,r.text)
  self.identity=r.json()['id'];p=self.db.get(ApparelProduct,self.identity);p.image=b'fixture';p.image_type='image/png';p.published=True;self.db.commit();self.variant=self.db.query(ApparelVariant).filter_by(apparel_id=p.id).first();return p
 def checkout(self,key='a'*32):
  body={'request_key':key,'expected_price_cents':2000,'name':'Shirt Buyer','email':'buyer@example.com','phone':'4055550100','variant_id':self.variant.id,'quantity':2}
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.apparel.routes.price',return_value=2000),patch('app.apparel.routes.requests.post',return_value=Mock(status_code=200,json=lambda:{'id':'test-checkout','href':'https://www.clover.com/checkout/test'})) as post:
   r=self.client.post('/api/apparel/checkout',json=body)
  self.assertEqual(r.status_code,200,r.text);return r.json(),post,body
 def test_prices_switch_at_central_midnight(self):
  p=ApparelProduct(presale_cents=2000,event_cents=2500,event_date='2026-11-14')
  self.assertEqual(price(p,datetime(2026,11,14,5,59,tzinfo=timezone.utc)),2000)
  self.assertEqual(price(p,datetime(2026,11,14,6,0,tzinfo=timezone.utc)),2500)
 def test_public_catalog_only_published_and_admin_mutations_restricted(self):
  self.make_product();self.assertEqual(len(self.client.get('/api/apparel/catalog').json()),1)
  self.assertEqual(self.client.get('/api/apparel/admin').status_code,401)
  self.assertEqual(self.client.get('/api/apparel/admin',headers=self.headers('member')).status_code,403)
  p=self.db.get(ApparelProduct,self.identity);p.published=False;self.db.commit();self.assertEqual(self.client.get('/api/apparel/catalog').json(),[])
 def test_checkout_freezes_price_and_same_request_does_not_create_second_payment(self):
  self.make_product();before=self.db.query(Sale).count();data,post,body=self.checkout();self.assertEqual(post.call_args.kwargs['json']['shoppingCart']['lineItems'][0]['price'],2000)
  with patch('app.apparel.routes.requests.post') as second:
   repeat=self.client.post('/api/apparel/checkout',json=body);self.assertEqual(repeat.status_code,200);second.assert_not_called()
  checkout=self.db.query(MerchandiseCheckout).filter_by(clover_checkout_id='test-checkout').one();self.assertEqual(checkout.total_amount,40)
  self.assertEqual(json.loads(checkout.cart_json)[0]['unit_price_cents'],2000);self.assertEqual(self.db.query(Sale).count(),before)
  self.assertEqual(self.client.get('/api/apparel/order/'+data['order_token']).json()['paid'],False)
 def test_payment_records_frozen_price_once_without_gym_membership(self):
  self.make_product();data,post,body=self.checkout();checkout=self.db.query(MerchandiseCheckout).filter_by(clover_checkout_id='test-checkout').one();mp=self.db.get(MembershipProduct,self.variant.product_id);mp.price=25;self.db.commit()
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.main.requests.get',return_value=Mock(json=lambda:{'amount':4000,'result':'SUCCESS'})):
   main.finalize_merchandise_checkout(checkout,'paid-id','order-id',self.db);main.finalize_merchandise_checkout(checkout,'paid-id','order-id',self.db)
  sales=self.db.query(Sale).filter_by(clover_checkout_id='test-checkout').all();self.assertEqual(len(sales),1);self.assertEqual(sales[0].amount,40)
  member=self.db.get(Member,sales[0].member_id);self.assertEqual(member.member_type,'CUSTOMER');self.assertIsNone(member.membership_end)
  self.assertTrue(self.client.get('/api/apparel/order/'+data['order_token']).json()['paid'])
 def test_wrong_amount_cannot_mark_paid_or_fulfill(self):
  self.make_product();data,_,_=self.checkout();checkout=self.db.query(MerchandiseCheckout).filter_by(clover_checkout_id='test-checkout').one()
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.main.requests.get',return_value=Mock(json=lambda:{'amount':1,'result':'SUCCESS'})):
   with self.assertRaises(Exception):main.finalize_merchandise_checkout(checkout,'payment','order',self.db)
  self.db.rollback();order=self.db.query(ApparelOrder).one();self.assertEqual(self.client.put('/api/apparel/admin/orders/'+str(order.id),headers=self.headers(),json={'status':'collected'}).status_code,409)
 def test_unknown_checkout_not_replayed_and_order_status_has_no_contact_information(self):
  self.make_product();body={'request_key':'b'*32,'expected_price_cents':2000,'name':'Buyer','email':'buyer@example.com','variant_id':self.variant.id}
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.apparel.routes.requests.post',side_effect=TimeoutError()),patch('app.apparel.routes.price',return_value=2000):
   self.assertEqual(self.client.post('/api/apparel/checkout',json=body).status_code,503)
  with patch('app.apparel.routes.requests.post') as post:
   self.assertEqual(self.client.post('/api/apparel/checkout',json=body).status_code,409);post.assert_not_called()
  self.assertEqual(self.client.get('/api/apparel/order/not-a-token').status_code,404)
 def test_draft_cannot_publish_without_required_details_or_checkout(self):
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':'draft-shirt','title':'Draft shirt','published':True});self.assertEqual(r.status_code,400)
 def test_image_rejects_non_image(self):
  self.make_product();r=self.client.post(f'/api/apparel/admin/{self.identity}/image',headers=self.headers(),files={'file':('evil.svg',b'<script>bad</script>','image/svg+xml')});self.assertEqual(r.status_code,400)
 def test_clover_pos_sync_is_repeatable_and_creates_two_prices_per_size(self):
  self.make_product();items=[]
  def create(url,**kwargs):
   item={**kwargs['json'],'id':'item-'+str(len(items)+1)};items.append(item);return Mock(json=lambda:item)
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.apparel.routes.requests.get',side_effect=lambda *a,**k:Mock(json=lambda:{'elements':list(items)})),patch('app.apparel.routes.requests.post',side_effect=create) as post:
   a=self.client.post(f'/api/apparel/admin/{self.identity}/clover',headers=self.headers());self.assertEqual(a.status_code,200,a.text)
   self.assertEqual(post.call_count,4)
   b=self.client.post(f'/api/apparel/admin/{self.identity}/clover',headers=self.headers());self.assertEqual(b.status_code,200,b.text);self.assertEqual(post.call_count,4)
  self.assertEqual({i['price'] for i in items},{2000,2500});self.assertEqual(len(set(i['sku'] for i in items)),4)
 def test_social_preview_has_original_image_and_public_status_omits_contacts(self):
  self.make_product();r=self.client.get('/api/apparel/share/earned-not-given');self.assertEqual(r.status_code,200);self.assertIn('og:image',r.text)
  data,_,_=self.checkout();status=self.client.get('/api/apparel/order/'+data['order_token']);self.assertNotIn('buyer@example.com',status.text);self.assertNotIn('customer_name',status.text)
 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_concurrent_payment_callbacks_record_one_sale(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.database import SessionLocal
  self.make_product();self.checkout();checkout=self.db.query(MerchandiseCheckout).filter_by(clover_checkout_id='test-checkout').one();identity=checkout.id;self.db.commit();gate=Barrier(2)
  def run(_):
   with SessionLocal() as db:
    item=db.get(MerchandiseCheckout,identity);gate.wait();main.finalize_merchandise_checkout(item,'same-paid-id','order-id',db)
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.main.requests.get',return_value=Mock(json=lambda:{'amount':4000,'result':'SUCCESS'})):
   with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,range(2)))
  self.assertEqual(self.db.query(Sale).filter_by(clover_checkout_id='test-checkout').count(),1)

 def test_price_change_requires_customer_to_review_before_checkout(self):
  self.make_product()
  with patch('app.apparel.routes.price',return_value=2500),patch('app.apparel.routes.requests.post') as post:
   r=self.client.post('/api/apparel/checkout',json={'request_key':'c'*32,'expected_price_cents':2000,'name':'Buyer','email':'buyer@example.com','variant_id':self.variant.id})
  self.assertEqual(r.status_code,409,r.text);post.assert_not_called();self.assertEqual(self.db.query(ApparelOrder).count(),0)

 def test_event_shirt_is_merchandise_not_a_fight_ticket(self):
  self.assertEqual(main.categorize_clover_product('TNG Earned Not Given Tee / S / EVENT'),'merchandise')
  self.assertEqual(main.categorize_clover_product('General Admission Event Ticket'),'event_ticket')

 def test_saving_seeded_draft_reuses_same_link_without_second_product(self):
  body={'slug':'first-shirt','title':'TNG First Shirt','sizes':[],'published':False}
  first=self.client.put('/api/apparel/admin/0',headers=self.headers(),json=body);self.assertEqual(first.status_code,200,first.text)
  second=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={**body,'description':'Updated presale draft','sizes':['S','M']});self.assertEqual(second.status_code,200,second.text)
  self.assertEqual(first.json()['id'],second.json()['id']);self.assertEqual(self.db.query(ApparelProduct).count(),1)
 def test_new_product_cannot_overwrite_published_link(self):
  p=self.make_product()
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':p.slug,'title':'Another shirt'});self.assertEqual(r.status_code,409,r.text)

 def test_sync_with_no_saved_sizes_cannot_claim_success(self):
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':'empty-tee','title':'Empty tee'});identity=r.json()['id']
  with patch('app.apparel.routes.requests.get') as get,patch('app.apparel.routes.requests.post') as post:
   r=self.client.post(f'/api/apparel/admin/{identity}/clover',headers=self.headers())
  self.assertEqual(r.status_code,409,r.text);get.assert_not_called();post.assert_not_called()
 def test_publish_saves_sizes_syncs_actual_items_and_then_publishes(self):
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':'ready-tee','title':'Ready Tee'});identity=r.json()['id'];p=self.db.get(ApparelProduct,identity);p.image=b'fixture';p.image_type='image/png';self.db.commit();items=[]
  def create(url,**kwargs):
   item={**kwargs['json'],'id':'id-'+str(len(items)+1)};items.append(item);return Mock(json=lambda:item)
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.apparel.routes.requests.get',return_value=Mock(json=lambda:{'elements':[]})),patch('app.apparel.routes.requests.post',side_effect=create):
   r=self.client.put(f'/api/apparel/admin/{identity}',headers=self.headers(),json={'slug':'ready-tee','title':'Ready Tee','sizes':['M','L'],'fulfillment':'Pickup at the gym','event_date':'2026-11-14','published':True})
  self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['published']);self.assertEqual(len(items),4);self.assertTrue(all(v['clover_synced'] for v in r.json()['variants']))
 def test_failed_auto_sync_keeps_saved_sizes_in_draft(self):
  r=self.client.put('/api/apparel/admin/0',headers=self.headers(),json={'slug':'failed-tee','title':'Failed Tee'});identity=r.json()['id'];p=self.db.get(ApparelProduct,identity);p.image=b'fixture';p.image_type='image/png';self.db.commit()
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'test','CLOVER_MERCHANT_ID':'test'}),patch('app.apparel.routes.requests.get',side_effect=TimeoutError()):
   r=self.client.put(f'/api/apparel/admin/{identity}',headers=self.headers(),json={'slug':'failed-tee','title':'Failed Tee','sizes':['M'],'fulfillment':'Pickup at the gym','event_date':'2026-11-14','published':True})
  self.assertEqual(r.status_code,503,r.text);self.db.expire_all();self.assertFalse(self.db.get(ApparelProduct,identity).published);self.assertEqual(self.db.query(ApparelVariant).filter_by(apparel_id=identity).count(),1)
