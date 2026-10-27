"""Signed downloads use immutable evidence, never current contract terms."""
import hashlib
import json
import unittest
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.models import BoxingContract, BoxingContractSignature, BoxingSignedContractDocument, BoxingFighter
from app.fighter_portal.models import FighterAccount

class SignedDownloadTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers

    def fixture(self):
        fighter = BoxingFighter(legal_name='Test Signer')
        self.db.add(fighter); self.db.flush()
        c = BoxingContract(event_id=1, bout_id=1, fighter_id=fighter.id, opponent_id=2, corner='red', signature_provider='tng', status='signed')
        self.db.add(c); self.db.flush()
        raw=json.dumps({'contract_id':c.id,'fighter_id':fighter.id,'gross_purse':1000,'boxer_name':'Original Signer'})
        sig=BoxingContractSignature(contract_id=c.id,fighter_id=fighter.id,signer_user_id=self.users['fighter'].id,typed_legal_name='Original Signer',agreed=True,contract_snapshot=raw,snapshot_sha256=hashlib.sha256(raw.encode()).hexdigest(),template_version='v1')
        self.db.add_all([sig,FighterAccount(fighter_id=fighter.id,user_id=self.users['fighter'].id)])
        self.db.commit()
        return c,sig

    def test_both_routes_download_without_provider_calls_and_keep_ownership(self):
        c,sig=self.fixture()
        with patch('requests.post') as post:
            for path,role in [(f'/api/boxing/contracts/{c.id}/signed-file','admin'),(f'/api/fighter/me/contracts/{c.id}/signed-file','fighter')]:
                r=self.client.get(path,headers=self.headers(role))
                self.assertEqual(r.status_code,200,r.text[:100]);self.assertTrue(r.content.startswith(b'%PDF-'));self.assertIn('no-store',r.headers['cache-control'])
            post.assert_not_called()
        self.assertEqual(self.client.get(f'/api/boxing/contracts/{c.id}/signed-file').status_code,401)
        self.assertEqual(self.client.get(f'/api/boxing/contracts/{c.id}/signed-file',headers=self.headers('rep')).status_code,403)
        c.fighter_id=999;self.db.commit()
        self.assertEqual(self.client.get(f'/api/fighter/me/contracts/{c.id}/signed-file',headers=self.headers('fighter')).status_code,404)

    def test_invalid_signature_never_generates_signed_pdf(self):
        c,sig=self.fixture()
        for field,value in [('snapshot_sha256','bad'),('agreed',False),('fighter_id',999)]:
            old=getattr(sig,field);setattr(sig,field,value);self.db.commit()
            r=self.client.get(f'/api/boxing/contracts/{c.id}/signed-file',headers=self.headers())
            self.assertEqual(r.status_code,409,r.text)
            setattr(sig,field,old);self.db.commit()

    def test_existing_original_preserved_and_unsigned_not_generated(self):
        c,sig=self.fixture(); original=b'%PDF-1.4\noriginal-provider-bytes'
        self.db.add(BoxingSignedContractDocument(contract_id=c.id,file_name='original.pdf',file_data=original,file_size=len(original),source='docusign'));self.db.commit()
        r=self.client.get(f'/api/boxing/contracts/{c.id}/signed-file',headers=self.headers())
        self.assertEqual(r.content,original)
        self.db.query(BoxingSignedContractDocument).delete();self.db.delete(sig);self.db.commit()
        self.assertEqual(self.client.get(f'/api/boxing/contracts/{c.id}/signed-file',headers=self.headers()).status_code,404)

    def test_render_uses_saved_terms_after_current_contract_changes(self):
        c,sig=self.fixture();c.gross_purse=9000;c.boxer_name='Changed name';self.db.commit()
        from app.matchmaker.signed_download import signed_contract_response
        with patch('app.matchmaker.signed_download.SimpleDocTemplate') as pdf:
            signed_contract_response(self.db,c)
            text=' '.join(getattr(p,'text','') for p in pdf.return_value.build.call_args.args[0])
            self.assertIn('Original Signer',text);self.assertIn('1000',text);self.assertNotIn('Changed name',text);self.assertNotIn('9000',text)

if __name__=='__main__':unittest.main()
