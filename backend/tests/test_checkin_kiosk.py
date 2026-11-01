"""Device boundary, privacy, attendance reuse and duplicate regression coverage."""
import unittest
from datetime import datetime, timedelta
import test_stabilization as support
from app.models import Attendance, Member
from app.kiosk.models import KioskDevice, KioskAttempt
from app.kiosk.routes import digest

class KioskTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers

    def enroll(self, name='InBody test'):
        response = self.client.post('/api/kiosk/devices', headers=self.headers(), json={'name': name})
        self.assertEqual(response.status_code, 201, response.text)
        identity = response.json()['id']
        code = self.client.post(f'/api/kiosk/devices/{identity}/pairing', headers=self.headers()).json()['code']
        pair = self.client.post('/api/kiosk/pair', json={'code': code})
        self.assertEqual(pair.status_code, 200, pair.text)
        return identity, code, pair.json()['credential']

    def enter(self, token, number='000001'):
        return self.client.post('/api/kiosk/checkin', headers={'Authorization': f'Bearer {token}'}, json={'member_number': number})

    def test_enrollment_single_use_credential_hashed_and_staff_boundary(self):
        identity, code, token = self.enroll()
        self.assertEqual(self.db.get(KioskDevice, identity).credential_hash, digest(token))
        self.assertEqual(self.client.post('/api/kiosk/pair', json={'code': code}).status_code,401)
        for path in ('/api/kiosk/devices','/api/members','/api/operations/overview'):
            self.assertEqual(self.client.get(path,headers={'Authorization':f'Bearer {token}'}).status_code,401)
        for role in ('rep','member','fighter'):
            self.assertEqual(self.client.get('/api/kiosk/devices',headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.get('/api/kiosk/devices',headers=self.headers('staff')).status_code,200)
        self.assertEqual(self.enter(self.headers()['Authorization'].split(' ',1)[1]).status_code,401)

    def test_leading_zero_number_records_existing_attendance_minimal_response(self):
        identity, _, token = self.enroll()
        r = self.enter(token)
        self.assertEqual(r.status_code,200,r.text); data=r.json()
        self.assertTrue(data['recorded']); self.assertEqual(data['first_name'],'Test')
        self.assertEqual(data['confirmation_seconds'],8); self.assertIn('no-store',r.headers['cache-control'])
        self.assertFalse(any(key in data for key in ('email','phone','member_number','member_id','last_name','billing','membership_end','token')))
        attendance=self.db.query(Attendance).one()
        self.assertEqual(attendance.member_id,self.member.id)
        self.assertEqual(attendance.method,'kiosk_number'); self.assertIn(f'#{identity}',attendance.location)
        self.db.refresh(self.member); self.assertEqual(self.member.total_checkins,1)
        attempt=self.db.query(KioskAttempt).one();self.assertEqual(attempt.attendance_id,attendance.id)

    def test_same_and_other_device_and_front_desk_do_not_duplicate(self):
        _, _, one=self.enroll(); _, _, two=self.enroll('Second kiosk')
        self.assertTrue(self.enter(one).json()['recorded'])
        self.assertTrue(self.enter(one).json()['duplicate']);self.assertTrue(self.enter(two).json()['duplicate'])
        r=self.client.post('/api/checkin',headers=self.headers('staff'),json={'code':'000001'})
        self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['duplicate'])
        self.assertEqual(self.db.query(Attendance).count(),1)
        self.db.refresh(self.member);self.assertEqual(self.member.total_checkins,1)

    def test_front_desk_then_kiosk_do_not_duplicate(self):
        _, _, token=self.enroll()
        self.client.post('/api/checkin',headers=self.headers(),json={'code':'000001'})
        self.assertTrue(self.enter(token).json()['duplicate'])
        self.assertEqual(self.db.query(Attendance).count(),1)

    def test_invalid_inactive_expired_and_ambiguous_do_not_record(self):
        identity, _, token=self.enroll()
        invalid = self.enter(token,'999999').json()
        self.assertFalse(invalid['success']); self.assertNotEqual(invalid['code'], 'membership_inactive')
        self.member.membership_end=datetime.utcnow()-timedelta(days=1);self.db.commit()
        r=self.enter(token);self.assertFalse(r.json()['success']);self.assertEqual(r.json()['reset_seconds'],5)
        self.assertEqual(r.json()['code'],'membership_inactive')
        self.assertEqual(r.json()['message'],'Membership inactive. Please visit the front desk.')
        self.member.membership_end=datetime.utcnow()+timedelta(days=1);self.member.membership_status='pending';self.db.commit()
        pending=self.enter(token).json()
        self.assertFalse(pending['success']);self.assertNotEqual(pending['code'],'membership_inactive')
        self.member.membership_status='inactive';self.db.commit()
        self.assertEqual(self.enter(token).json()['code'],'membership_inactive')
        self.db.add(Member(first_name='Other',last_name='Person',member_number='000001'));self.db.commit()
        self.assertFalse(self.enter(token).json()['success'])
        outcomes=[a.outcome for a in self.db.query(KioskAttempt).all()]
        self.assertEqual(outcomes,['invalid','inactive','ineligible','inactive','ambiguous'])
        self.assertEqual(self.db.query(Attendance).count(),0)

    def test_disable_revoke_expiry_rotation_and_config(self):
        identity, _, token=self.enroll()
        payload={'name':'Entrance','enabled':False,'confirmation_seconds':12,'duplicate_seconds':300}
        self.assertEqual(self.client.put(f'/api/kiosk/devices/{identity}',headers=self.headers(),json=payload).status_code,200)
        self.assertEqual(self.enter(token).status_code,403)
        ping=self.client.post('/api/kiosk/heartbeat',headers={'Authorization':f'Bearer {token}'})
        self.assertFalse(ping.json()['enabled']);self.assertEqual(ping.json()['confirmation_seconds'],12)
        payload['enabled']=True
        self.client.put(f'/api/kiosk/devices/{identity}',headers=self.headers(),json=payload)
        code=self.client.post(f'/api/kiosk/devices/{identity}/pairing',headers=self.headers()).json()['code']
        # Existing session remains until staff pairs a new one; pairing is one-use.
        new=self.client.post('/api/kiosk/pair',json={'code':code}).json()['credential']
        self.assertEqual(self.enter(token).status_code,401)
        self.assertEqual(self.enter(new).json()['confirmation_seconds'],12)
        self.client.post(f'/api/kiosk/devices/{identity}/revoke',headers=self.headers())
        self.assertEqual(self.enter(new).status_code,401)
        code=self.client.post(f'/api/kiosk/devices/{identity}/pairing',headers=self.headers()).json()['code']
        self.db.expire_all();device=self.db.get(KioskDevice,identity);device.pairing_expires=datetime.utcnow()-timedelta(seconds=1);self.db.commit()
        self.assertEqual(self.client.post('/api/kiosk/pair',json={'code':code}).status_code,401)

    def test_configured_duplicate_window_can_expire(self):
        identity, _, token=self.enroll()
        self.enter(token)
        a=self.db.query(Attendance).one();a.checkin_time=datetime.utcnow()-timedelta(seconds=61);self.db.commit()
        self.assertTrue(self.enter(token).json()['duplicate'])
        self.client.put(f'/api/kiosk/devices/{identity}',headers=self.headers(),json={'name':'Entrance','duplicate_seconds':30})
        self.assertTrue(self.enter(token).json()['recorded']);self.assertEqual(self.db.query(Attendance).count(),2)

    def test_rate_limits_persist_and_do_not_write_attendance(self):
        identity, _, token=self.enroll()
        for _ in range(30):self.assertEqual(self.enter(token,'999999').status_code,200)
        r=self.enter(token,'999999');self.assertEqual(r.status_code,429);self.assertEqual(r.headers['retry-after'],'60')
        self.assertEqual(self.db.query(Attendance).count(),0)
        self.assertEqual(self.db.query(KioskAttempt).filter_by(outcome='rate_limited').count(),1)
        for _ in range(9):self.assertEqual(self.client.post('/api/kiosk/pair',json={'code':'BADCODE123'}).status_code,401)
        self.assertEqual(self.client.post('/api/kiosk/pair',json={'code':'BADCODE123'}).status_code,429)

    def test_numeric_string_validation_and_settings_limits(self):
        _, _, token=self.enroll()
        for number in ('-1','abc','1'*33,1,None):
            r=self.client.post('/api/kiosk/checkin',headers={'Authorization':f'Bearer {token}'},json={'member_number':number})
            self.assertEqual(r.status_code,422)
        r=self.client.post('/api/kiosk/devices',headers=self.headers(),json={'name':'Bad','confirmation_seconds':0})
        self.assertEqual(r.status_code,422)
        self.assertEqual(self.db.query(Attendance).count(),0)

    def test_monitoring_staff_only_and_online_status(self):
        _,_,token=self.enroll();self.enter(token);self.enter(token);self.enter(token,'999999')
        r=self.client.get('/api/kiosk/devices',headers=self.headers('staff'))
        self.assertEqual(r.status_code,200,r.text);self.assertIn('no-store',r.headers['cache-control'])
        device=r.json()['devices'][0];self.assertTrue(device['online'])
        self.assertEqual(device['today']['recorded'],1);self.assertEqual(device['today']['duplicate'],1);self.assertEqual(device['today']['invalid'],1)
        self.assertNotIn(token,r.text);self.assertNotIn('credential_hash',r.text);self.assertNotIn('pairing_hash',r.text)

    @unittest.skipUnless(support.TEST_DATABASE_URL, 'Requires isolated local PostgreSQL')
    def test_concurrent_kiosks_and_front_desk_record_exactly_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        _,_,one=self.enroll();_,_,two=self.enroll('Other kiosk')
        gate=Barrier(6)
        # Construct staff headers before threads access the fixture session.
        original=self.headers('staff')
        def concurrent(i):
            gate.wait()
            if i % 3 == 0:
                return self.client.post('/api/checkin',headers=original,json={'code':'000001'})
            return self.enter(one if i % 3 == 1 else two)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(concurrent,range(6)))
        self.assertTrue(all(r.status_code == 200 for r in results),[r.status_code for r in results])
        self.assertEqual(sum(not r.json().get('duplicate',False) for r in results),1)
        self.db.expire_all()
        self.assertEqual(self.db.query(Attendance).count(),1)
        self.db.refresh(self.member);self.assertEqual(self.member.total_checkins,1)

    @unittest.skipUnless(support.TEST_DATABASE_URL, 'Requires isolated local PostgreSQL foreign keys')
    def test_audit_does_not_block_existing_attendance_or_profile_deletion(self):
        _,_,token=self.enroll()
        member=Member(first_name='Temporary',last_name='Fixture',member_number='000002',
            member_type='MEMBER',membership_status='active',status='active',
            membership_end=datetime.utcnow()+timedelta(days=1))
        self.db.add(member);self.db.commit();identity=member.id
        self.assertTrue(self.enter(token,'000002').json()['recorded'])
        self.db.query(Attendance).filter_by(member_id=identity).delete(synchronize_session=False)
        self.db.query(Member).filter_by(id=identity).delete(synchronize_session=False);self.db.commit()
        attempt=self.db.query(KioskAttempt).one()
        self.assertIsNone(attempt.member_id);self.assertIsNone(attempt.attendance_id)
