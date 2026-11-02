import unittest,json
from datetime import datetime,timedelta
import test_stabilization as support
from app.models import Member,Sale,Attendance,SecurityLog,User
from app.member_portal.models import MemberAccount,MemberInvite,InBodyScan,MemberProfilePhoto
from app.services.contact_consolidation import ConsolidatedContact,MergedMemberLogin,MergedRecordSnapshot,confirmed_plan,merge_profiles
from app.services.member_reporting import membership_report,membership_totals
from app.services.member_profiles import import_customer

class RosterConsolidationTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers

    def source(self, **changes):
        values=dict(first_name='Test',last_name='Member',email='member@example.com',phone='+14055550100',
            member_type='CUSTOMER',membership_status='pending',member_number='TNG-000900',barcode='TNG000900',qr_code='member:TNG-000900',clover_customer_id='duplicate-clover')
        values.update(changes);source=Member(**values);self.db.add(source)
        self.member.phone='4055550100';self.member.clover_customer_id='primary-clover';self.db.commit()
        return source

    def test_confirmed_contact_consolidation_preserves_member_and_old_identifiers(self):
        source=self.source();identity=source.id
        old_end=self.member.membership_end;old_number=self.member.member_number
        response=self.client.post('/api/duplicates/contacts/consolidate',headers=self.headers())
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['merged'],1)
        self.db.expire_all();self.assertIsNone(self.db.get(Member,identity))
        archive=self.db.query(ConsolidatedContact).one();self.assertEqual(archive.member_id,self.member.id)
        self.assertEqual(json.loads(archive.source_snapshot)['clover_customer_id'],'duplicate-clover')
        self.assertEqual(self.member.membership_end,old_end);self.assertEqual(self.member.member_number,old_number)
        self.assertEqual(self.db.query(Sale).count(),1);self.assertEqual(self.db.query(MemberAccount).count(),1)
        self.assertEqual(self.client.get(f'/api/members/{identity}',headers=self.headers()).json()['id'],self.member.id)
        result=self.client.post('/api/checkin',headers=self.headers(),json={'code':'000900'})
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['member']['id'],self.member.id)
        self.assertEqual(self.client.post('/api/duplicates/contacts/consolidate',headers=self.headers()).json()['merged'],0)

    def test_import_after_merge_resolves_clover_alias_without_recreating_contact(self):
        self.source();self.client.post('/api/duplicates/contacts/consolidate',headers=self.headers())
        result,member=import_customer(self.db,{'id':'duplicate-clover','firstName':'Test','lastName':'Member',
            'emailAddresses':{'elements':[{'emailAddress':'member@example.com'}]},'phoneNumbers':{'elements':[{'phoneNumber':'4055550100'}]}})
        self.db.commit();self.assertEqual(member.id,self.member.id);self.assertEqual(self.db.query(Member).count(),1)
        self.assertEqual(member.clover_customer_id,'primary-clover')
        result,member=import_customer(self.db,{'id':'duplicate-clover','firstName':'Updated name','lastName':'Member',
            'emailAddresses':{'elements':[{'emailAddress':'updated@example.com'}]},'phoneNumbers':{'elements':[{'phoneNumber':'4055550100'}]}})
        self.db.commit();self.assertEqual(self.db.query(Member).count(),1)
        self.assertEqual(member.first_name,'Test');self.assertEqual(member.email,'member@example.com')


    def test_shared_family_contacts_conflicting_emails_and_linked_profiles_not_auto_merged(self):
        source=self.source(first_name='Other')
        self.assertEqual(confirmed_plan(self.db),[])
        source.first_name='Test';source.email='different@example.com';self.db.commit()
        self.assertEqual(confirmed_plan(self.db),[])
        source.email='member@example.com';self.db.add(MemberInvite(member_id=source.id,token_hash='invite',expires_at=datetime.utcnow()+timedelta(days=1)));self.db.commit()
        self.assertEqual(confirmed_plan(self.db),[])
        source.member_type='MEMBER';self.db.commit();self.assertEqual(confirmed_plan(self.db),[])

    def test_name_and_phone_with_missing_target_email_can_link_without_guessing(self):
        self.source();self.member.email='';self.db.commit()
        self.assertEqual(len(confirmed_plan(self.db)),1)

    def test_manual_merge_moves_history_invites_and_preserves_portal_and_term(self):
        source=self.source(member_type='MEMBER',membership_status='active',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=90),membership_type='Monthly')
        self.db.add(Sale(member_id=source.id,product_id=self.product.id,sales_rep_id=self.rep.id,amount=150,payment_status='paid'))
        self.db.add(Attendance(member_id=source.id));self.db.add(MemberInvite(member_id=source.id,token_hash='pending-invite',expires_at=datetime.utcnow()+timedelta(days=2)))
        self.db.commit();account=self.db.query(MemberAccount).one();account_id=account.id;source_id=source.id
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source_id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(Sale).count(),2);self.assertTrue(all(s.member_id==self.member.id for s in self.db.query(Sale)))
        self.assertEqual(self.db.query(Attendance).one().member_id,self.member.id)
        self.assertEqual(self.db.query(MemberInvite).one().member_id,self.member.id)
        self.assertEqual(self.db.query(MemberAccount).one().id,account_id)
        self.assertGreater(self.member.membership_end,datetime.utcnow()+timedelta(days=89))
        self.assertTrue(json.loads(self.db.query(ConsolidatedContact).one().moved_records)['sales.member_id'])

    def test_reviewed_merge_preserves_both_logins_and_passwords(self):
        source=self.source()
        user=User(name='Other portal',email='other-portal@example.com',role='member',active=True,password_hash='fixture')
        self.db.add(user);self.db.flush();self.db.add(MemberAccount(member_id=source.id,user_id=user.id));self.db.commit();source_id=source.id
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(MemberAccount).count(),1);self.assertEqual(self.db.query(Member).count(),1)
        self.assertEqual(self.db.query(MergedMemberLogin).one().user_id,user.id)
        self.assertEqual(self.db.get(User,user.id).password_hash,'fixture')
        from app.auth import create_token
        secondary={'Authorization':'Bearer '+create_token({'sub':str(user.id)})}
        self.assertEqual(self.client.get('/api/member/me',headers=secondary).status_code,200)
        self.assertEqual(self.client.get('/api/member/me',headers=self.headers('member')).status_code,200)
        self.users['member'].active=False;self.db.commit()
        self.assertEqual(self.client.get('/api/member/me',headers=secondary).status_code,403)
        self.users['member'].active=True;self.db.commit()
        self.assertEqual(self.client.get('/api/member/me',headers=secondary).status_code,200)
        repeat=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source_id})
        self.assertEqual(repeat.status_code,200,repeat.text)
        self.assertEqual(self.db.query(ConsolidatedContact).count(),1)

    def test_classification_excludes_contacts_and_expiring_is_subset_of_active(self):
        now=datetime(2026,11,1,12)
        identity=dict(first_name='Gym',last_name='Member',email='gym@example.com')
        active=Member(id=1,**identity,member_type='MEMBER',membership_status='active',membership_start=now-timedelta(days=30),membership_end=now+timedelta(days=20))
        soon=Member(id=2,**identity,member_type='MEMBER',membership_status='active',membership_end=now+timedelta(days=3))
        expired=Member(id=3,**identity,member_type='MEMBER',membership_status='active',membership_end=now-timedelta(seconds=1))
        pending=Member(id=4,**identity,member_type='CUSTOMER',membership_status='pending')
        bare=Member(id=5,**identity,member_type='MEMBER',membership_status='active')
        totals=membership_totals([active,soon,expired,pending,bare],{1,2,3},now)
        self.assertEqual({k:totals[k] for k in ('active','expiring','expired','contact','members')},{'active':2,'expiring':1,'expired':1,'contact':2,'members':3})
        self.assertEqual(membership_report(expired,{3},now)['membership_days_remaining'],-1)
        self.assertEqual(membership_report(soon,{2},soon.membership_end)['membership_category'],'expired')
        soon.membership_status='inactive'
        self.assertEqual(membership_report(soon,{2},now)['membership_category'],'inactive')

    def test_api_dashboard_and_roster_count_same_current_and_expired_members(self):
        source=self.source();r=self.client.get('/api/members',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text);rows=r.json()
        self.assertEqual(sum(row['is_current_member'] for row in rows),1)
        self.assertEqual(next(row for row in rows if row['id']==source.id)['membership_category'],'contact')
        dash=self.client.get('/api/dashboard',headers=self.headers()).json();self.assertEqual(dash['active_members'],1)
        self.member.membership_end=datetime.utcnow()-timedelta(seconds=1);self.db.commit()
        dash=self.client.get('/api/dashboard',headers=self.headers()).json();self.assertEqual(dash['active_members'],0);self.assertEqual(dash['expired_members'],1)

    def test_only_admin_can_consolidate_and_staff_can_read_roster(self):
        self.source()
        for role in ('staff','member','rep'):
            self.assertEqual(self.client.post('/api/duplicates/contacts/consolidate',headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.post('/api/duplicates/contacts/consolidate').status_code,401)
        self.assertEqual(self.client.get('/api/members',headers=self.headers('staff')).status_code,200)

    def test_source_portal_account_and_loaded_sales_move_without_changing_login(self):
        source=self.member;source.phone='4055550100'
        target=Member(first_name=source.first_name,last_name=source.last_name,email=source.email,phone=source.phone,
            member_number='TNG-000901',member_type='MEMBER',membership_status='pending')
        self.db.add(target);self.db.commit();source_id=source.id;target_id=target.id
        account=self.db.query(MemberAccount).one();account_id=account.id;user_id=account.user_id
        password=self.db.get(User,user_id).password_hash
        list(source.sales)
        merge_profiles(self.db,self.users['admin'],target.id,source.id,allow_linked=True);self.db.commit();self.db.expire_all()
        self.assertEqual(self.db.query(MemberAccount).one().member_id,target_id)
        self.assertEqual(self.db.query(MemberAccount).one().id,account_id)
        self.assertEqual(self.db.get(User,user_id).password_hash,password)
        self.assertEqual(self.db.query(Sale).one().member_id,target_id)
        self.assertIsNone(self.db.get(Member,source_id))

    def test_conflicting_photos_are_retained_in_merge_archive(self):
        source=self.source()
        for member,data in [(self.member,b'target'),(source,b'source')]:
            self.db.add(MemberProfilePhoto(member_id=member.id,file_name='fixture.png',content_type='image/png',file_size=len(data),file_data=data))
        self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(MemberProfilePhoto).one().file_data,b'target')
        archived=json.loads(self.db.query(MergedRecordSnapshot).filter_by(table_name='member_profile_photos').one().record_json)
        import base64
        self.assertEqual(base64.b64decode(archived['file_data']['base64']),b'source')
        self.assertEqual(self.db.query(Member).count(),1)

    def test_reviewed_matching_contact_can_merge_without_correcting_birthdates(self):
        source=self.source(date_of_birth=datetime(2000,1,1))
        self.member.date_of_birth=datetime(1999,1,1);self.db.commit()
        self.assertEqual(confirmed_plan(self.db),[])
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.db.query(Member).count(),1)

    def test_same_phone_formatted_differently_allows_different_names_and_emails(self):
        source=self.source(first_name='Misspelled',email='other@example.com',phone='(405) 555-0100')
        pairs=self.client.get('/api/duplicates/members',headers=self.headers()).json()
        self.assertIn('Same phone',pairs[0]['reasons']);self.assertTrue(pairs[0]['contact_match'])
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text)
        self.db.expire_all();self.assertEqual(self.member.email,'member@example.com')
        self.assertEqual(json.loads(self.db.query(ConsolidatedContact).one().source_snapshot)['email'],'other@example.com')

    def test_latest_membership_retains_its_assigned_rate_and_source_invites_expire(self):
        from app.services.assigned_memberships import assign_membership
        from app.member_portal.models import AssignedMembership
        source=self.source(member_type='MEMBER',membership_status='active',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=90),membership_type='Custom')
        assign_membership(self.db,self.member,'Monthly',125,1,activate=False,user_id=self.users['admin'].id)
        assign_membership(self.db,source,'Custom',225,1,activate=False,user_id=self.users['admin'].id)
        self.db.add(MemberInvite(member_id=source.id,token_hash='source-invite',expires_at=datetime.utcnow()+timedelta(days=1)))
        self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(AssignedMembership).one().rate,225)
        self.assertEqual(self.member.monthly_rate,225)
        self.assertIsNotNone(self.db.query(MemberInvite).one().used_at)
        self.assertEqual(self.db.query(Sale).count(),1)

    def test_member_cannot_merge_and_unrelated_profiles_still_require_match(self):
        source=self.source(first_name='Other',phone='5055550101',email='other@example.com')
        for role in ('staff','member','rep'):
            self.assertEqual(self.client.post('/api/duplicates/members/merge',headers=self.headers(role),json={'keep_id':self.member.id,'merge_id':source.id}).status_code,403)
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.db.query(Member).count(),2)
        self.assertEqual(self.db.query(ConsolidatedContact).count(),0)

    def test_later_standard_term_does_not_inherit_older_discount_assignment(self):
        from app.services.assigned_memberships import assign_membership
        from app.member_portal.models import AssignedMembership
        source=self.source(member_type='MEMBER',membership_status='active',membership_type='Monthly',monthly_rate=150,billing_cycle='30_day',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=90))
        assign_membership(self.db,self.member,'Monthly',125,1,activate=False,user_id=self.users['admin'].id);self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.member.monthly_rate,150);self.assertEqual(self.db.query(AssignedMembership).count(),0)
        self.assertEqual(json.loads(self.db.query(MergedRecordSnapshot).one().record_json)['rate'],125)

    def test_prepared_source_account_keeps_secondary_login_without_claiming_primary(self):
        from app.member_portal.models import PortalAccountSetup
        from app.services.portal_accounts import fingerprint
        source=self.source(email='secondary@example.com')
        second=User(name='Secondary',email=source.email,role='member',active=True,password_hash='source-password')
        self.db.add(second);self.db.flush()
        self.db.add(MemberAccount(member_id=source.id,user_id=second.id))
        for member,user in [(source,second),(self.member,self.users['member'])]:
            self.db.add(PortalAccountSetup(member_id=member.id,user_id=user.id,password_fingerprint=fingerprint(user)))
        self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(PortalAccountSetup).one().user_id,self.users['member'].id)
        self.assertEqual(self.db.query(MergedMemberLogin).one().user_id,second.id)
        self.assertEqual(self.db.get(User,second.id).password_hash,'source-password')

    def test_kept_standard_term_does_not_inherit_source_discount_assignment(self):
        from app.services.assigned_memberships import assign_membership
        from app.member_portal.models import AssignedMembership
        source=self.source(member_type='MEMBER',membership_status='active',membership_type='Discount',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=5))
        assign_membership(self.db,source,'Discount',125,1,activate=False,user_id=self.users['admin'].id);self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.db.query(AssignedMembership).count(),0)
        self.assertEqual(json.loads(self.db.query(MergedRecordSnapshot).one().record_json)['rate'],125)


    def test_membership_purchase_promotes_customer_but_retail_purchase_does_not(self):
        from app.services.memberships import apply_membership
        from app.models import MembershipProduct
        customer=self.source()
        retail=MembershipProduct(name='Gloves',category='retail',is_membership=False,price=50)
        apply_membership(customer,retail)
        self.assertEqual(customer.member_type,'CUSTOMER')
        apply_membership(customer,self.product)
        self.assertEqual(customer.member_type,'MEMBER')
        self.assertEqual(customer.membership_status,'active')

    def test_customer_generic_order_without_receipt_or_term_is_not_membership_evidence(self):
        from app.services.member_reporting import membership_evidence
        customer=self.source()
        self.db.add(Sale(member_id=customer.id,product_id=self.product.id,sales_rep_id=self.rep.id,
            amount=434.4,payment_status='paid',payment_method='clover',clover_order_id='generic-order'))
        self.db.commit()
        evidence=membership_evidence(self.db)
        self.assertNotIn(customer.id,evidence)
        self.assertEqual(membership_report(customer,evidence)['membership_category'],'contact')

    def test_missing_name_or_email_excluded_even_with_saved_active_term(self):
        for name,email in [('', 'valid@example.com'),('Named',''),('Named','invalid'),('Clover Customer','valid@example.com')]:
            member=Member(id=99,first_name=name,email=email,member_type='MEMBER',membership_status='active',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=30))
            report=membership_report(member,{99})
            self.assertEqual(report['membership_category'],'contact');self.assertFalse(report['is_current_member'])

    def test_fight_tickets_never_activate_gym_even_if_product_mistagged(self):
        from app.services.memberships import is_membership_product,apply_membership
        from app.models import MembershipProduct
        for name in ('Fall Brawl Fight Ticket','General Admission','Table Seat','Ringside'):
            ticket=MembershipProduct(name=name,price=150,category='membership',is_membership=True)
            member=Member(first_name='Ticket',email='ticket@example.com',member_type='CUSTOMER',membership_status='pending')
            self.assertFalse(is_membership_product(ticket));apply_membership(member,ticket)
            self.assertEqual(member.member_type,'CUSTOMER');self.assertIsNone(member.membership_end)

    def test_merging_ticket_profile_cannot_extend_gym_term(self):
        source=self.source(member_type='MEMBER',membership_type='Fight Ticket',membership_start=datetime.utcnow(),membership_end=datetime.utcnow()+timedelta(days=365))
        expected=self.member.membership_end
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.member.membership_end,expected);self.assertEqual(self.member.membership_type,'Monthly')

    def test_merge_fills_missing_identity_and_prepares_account_in_one_action(self):
        source=self.source(first_name='Complete',last_name='Identity',email='fresh@example.com')
        self.db.query(MemberAccount).delete();self.member.first_name='';self.member.last_name='';self.member.email='';self.db.commit()
        r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source.id})
        self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
        self.assertEqual(self.member.first_name,'Complete');self.assertEqual(self.member.email,'fresh@example.com')
        account=self.db.query(MemberAccount).one();self.assertEqual(account.member_id,self.member.id)
        self.assertTrue(self.db.get(User,account.user_id).active)
        self.assertEqual(self.db.query(Sale).count(),1)
