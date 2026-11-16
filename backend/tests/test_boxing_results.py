import io,unittest
from openpyxl import Workbook
import test_stabilization as support
import test_ticketing as tickets
import test_event_recap as recaps
from app.events.results import BoxingBoutResult,BoxingResultSource,parse_workbook
from app.matchmaker.models import BoxingFighter
from app.fighter_portal.models import FighterAccount
class BoxingResultsTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    order=tickets.TicketingTests.order
    fixture=recaps.RecapTests.fixture
    def setup_event(self):
        self.fixture();self.event.event_date='2026-11-14';self.a.boxrec_id='111';self.b.boxrec_id='222';self.db.commit()
        self.url=f'/api/events/{self.event.id}/results'
    def workbook(self,method='UD',blue_wins=False,bad=False):
        book=Workbook();s=book.active;s['A1']='OKLAHOMA STATE ATHLETIC COMMISSION';s['A9']='11.14.26'
        for i,name in [(6,'Kyle English'),(7,'Don Hayes'),(8,'Tim Tallchief')]:s[f'L{i}']=name
        ids=['222','111']if blue_wins else ['111','222']
        for row,ident,outcome in [(14,ids[0],'WON'),(15,ids[1],'LOST'if method=='UD'else 'LOST BY '+method)]:
            s.cell(row,1,1);s.cell(row,3,'Source '+ident);s.cell(row,6,'ID: '+ident);s.cell(row,8,4 if row==14 else None);s.cell(row,10,'0-0');s.cell(row,11,outcome)
        s['L14']='Kyle, Don, Tim 30-40'if bad else 'Kyle, Don, Tim 40-33'if method=='UD'else 'RD 1 - 2:25'
        s['L15']='Suspended 30 DAYS'
        raw=io.BytesIO();book.save(raw);return raw.getvalue()
    def upload(self,raw,role='admin'):
        return self.client.post(self.url+'/import',headers=self.headers(role),files={'file':('results.xlsx',raw,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    def test_blue_corner_winner_scores_and_review_only_records(self):
        self.setup_event();before=(self.a.pro_record,self.b.pro_record)
        r=self.upload(self.workbook(blue_wins=True));self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['imported'],1)
        self.db.refresh(self.a);self.db.refresh(self.b);self.assertEqual((self.a.pro_record,self.b.pro_record),before)
        result=self.client.get(self.url,headers=self.headers()).json()['results'][0]
        self.assertEqual(result['winner_id'],self.b.id);self.assertEqual(result['judges'][0]['red_total'],33);self.assertEqual(result['judges'][0]['blue_total'],40)
        self.assertEqual(len(result['judges']),3);self.assertTrue(any(f['career_review_required']for f in result['record_review']))
        self.db.refresh(self.bout);self.assertEqual(self.bout.status,'completed');self.assertEqual(self.bout.bout_order,1)
        self.assertIn('round-by-round',result['score_detail'])
    def test_replay_is_idempotent_and_changed_source_needs_review(self):
        self.setup_event();raw=self.workbook();self.assertEqual(self.upload(raw).status_code,200)
        replay=self.upload(raw);self.assertEqual(replay.status_code,200);self.assertTrue(replay.json()['already_imported'])
        self.assertEqual(self.db.query(BoxingBoutResult).count(),1);self.assertEqual(self.db.query(BoxingResultSource).count(),1)
        self.assertEqual(self.upload(self.workbook(method='TKO')).status_code,409)
    def test_invalid_scores_and_wrong_event_do_not_change_any_record(self):
        self.setup_event();self.assertEqual(self.upload(self.workbook(bad=True)).status_code,422)
        self.event.event_date='2026-11-15';self.db.commit();self.assertEqual(self.upload(self.workbook()).status_code,409)
        self.assertEqual(self.db.query(BoxingBoutResult).count(),0);self.assertEqual(self.db.query(BoxingResultSource).count(),0);self.db.refresh(self.bout);self.assertEqual(self.bout.status,'draft')
    def test_stoppage_has_no_fabricated_scorecards_and_history_is_frozen(self):
        self.setup_event();r=self.upload(self.workbook(method='TKO'));self.assertEqual(r.status_code,200,r.text)
        other=BoxingFighter(legal_name='Replacement');self.db.add(other);self.db.flush();self.bout.red_fighter_id=other.id;self.db.commit()
        result=self.client.get(self.url,headers=self.headers()).json()['results'][0]
        self.assertEqual(result['red']['id'],self.a.id);self.assertEqual(result['winner_name'],'Red Fighter');self.assertEqual(result['judges'],[]);self.assertEqual(result['elapsed'],'2:25')
    def test_fighter_sees_only_own_record_notes_and_not_entire_workbook(self):
        self.setup_event();self.db.add(FighterAccount(user_id=self.users['fighter'].id,fighter_id=self.a.id));self.db.commit();self.upload(self.workbook())
        path=f'/api/events/fighters/{self.a.id}/results';r=self.client.get(path,headers=self.headers('fighter'));self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()['results'][0]['record_review']),1)
        self.assertEqual(r.json()['results'][0]['record_review'][0]['fighter_id'],self.a.id)
        self.assertEqual(self.client.get(f'/api/events/fighters/{self.b.id}/results',headers=self.headers('fighter')).status_code,403)
        self.assertEqual(self.client.get(self.url+'/source.xlsx',headers=self.headers('fighter')).status_code,403)
        self.assertEqual(self.upload(self.workbook(),'fighter').status_code,403)
        self.assertEqual(self.client.get(self.url).status_code,401)
    def test_parser_supports_decision_tko_and_ko_without_invented_round_scores(self):
        for method in ['UD','TKO','KO']:
            date,rows=parse_workbook(self.workbook(method=method))
            self.assertEqual(date,'2026-11-14');self.assertEqual(rows[0]['method'],method)
            self.assertEqual(len(rows[0]['scores']),3 if method=='UD'else 0)
            self.assertEqual(rows[0]['elapsed'],None if method=='UD'else '2:25')

    def test_unknown_source_identity_blocks_import_atomically(self):
        self.setup_event();self.a.boxrec_id='999';self.db.commit()
        r=self.upload(self.workbook());self.assertEqual(r.status_code,409,r.text)
        self.assertEqual(self.db.query(BoxingResultSource).count(),0)
        self.assertEqual(self.db.query(BoxingBoutResult).count(),0)
        self.db.refresh(self.bout);self.assertEqual(self.bout.status,'draft')
