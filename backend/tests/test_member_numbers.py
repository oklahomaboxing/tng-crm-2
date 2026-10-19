import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.database import Base
from app.models import Member
from app.services.member_numbers import find_checkin_member

class MemberNumberTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Member.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.db.add(Member(first_name='Test', last_name='Member', member_number='TNG-000042', barcode='TNG000042', qr_code='member:TNG-000042'))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_short_full_and_existing_qr_resolve_same_member(self):
        for code in ['42', '000042', 'TNG-000042', 'TNG000042', 'member:TNG-000042', '  member:tng-000042  ']:
            with self.subTest(code=code):
                self.assertEqual(find_checkin_member(self.db, code).member_number, 'TNG-000042')

    def test_unknown_does_not_check_in_another_member(self):
        self.assertIsNone(find_checkin_member(self.db, '43'))
        self.assertIsNone(find_checkin_member(self.db, 'OTHER42'))

    def test_collision_requires_staff_verification(self):
        self.db.add(Member(first_name='Other', last_name='Member', member_number='42'))
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            find_checkin_member(self.db, '42')
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(find_checkin_member(self.db, 'TNG-000042').first_name, 'Test')

    def test_oversized_code_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            find_checkin_member(self.db, '9' * 300)
        self.assertEqual(caught.exception.status_code, 400)

    def test_empty_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            find_checkin_member(self.db, '')
        self.assertEqual(caught.exception.status_code, 400)

if __name__ == '__main__':
    unittest.main()
