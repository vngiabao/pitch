import json,unittest
from pathlib import Path
import test_application_pilot as fixtures
from founder_os.application_review import ApplicationReview
from founder_os.connector_outbox import ConnectorOutbox,OWNER
from founder_os.materials_library import MaterialsLibrary
from founder_os.report_email import DailyReporter
from founder_os.store import digest,js,now,PolicyError

class ReviewTests(unittest.TestCase):
    setUp=fixtures.AutonomyTests.setUp
    tearDown=fixtures.AutonomyTests.tearDown
    facts=fixtures.AutonomyTests.facts
    def enable(self):
        old=self.p.authorization('daily_email_report');self.p.revoke(old['id']);self.p.authorize('daily_email_report',{'recipient':OWNER,'question_answer_attachments':True},'Owner explicitly requests questions and filled answers in private text attachments')
        self.s.db.execute("INSERT INTO hunter_settings VALUES('mail_delivery',?)",(js({'mode':'gmail_connector'}),));return ConnectorOutbox(self.s)
    def test_unknown_official_questions_are_explicit_and_not_filled(self):
        p=self.p.build(self.oid);r=ApplicationReview(self.s);info=r.plan(p['id']);self.assertEqual(info['questions'],[])
        text=r.text(p['id']);self.assertIn('OFFICIAL QUESTIONS UNKNOWN',text);self.assertIn('No answers have been filled for this form.',text)
        self.assertEqual(self.s.one('SELECT count(*) n FROM application_attempts')['n'],0)
    def test_real_labels_paired_with_values_and_blank_required_field(self):
        self.facts();t=fixtures.FormsTransport();t.form['fields'].append({'name':'revenue','type':'text','required':True,'label':'Revenue last year?','maxlength':20,'disabled':False})
        p=self.p.inspect(self.oid,t);r=ApplicationReview(self.s);rows=r.plan(p['id'])['questions'];self.assertEqual(rows[0]['question'],'Company name');self.assertEqual(rows[0]['answer'],'A Story');self.assertEqual(rows[-1]['state'],'UNFILLED');self.assertIsNone(rows[-1]['answer'])
        self.assertIn('NOT SUBMITTED',r.text(p['id']));self.assertEqual(t.calls,0)
    def test_saved_draft_retains_source_and_never_becomes_live_form_answer(self):
        f=Path(self.tmp.name)/'essay.txt';f.write_text('Historical question and draft');v=self.s.import_source(f,'text','KEEP');aid=self.h.start_application(self.oid)
        q=self.s.add_question(aid,1,'Describe your past traction',v,'paragraph 2');self.s.add_answer(q,'Old unconfirmed traction',[v],[],['Verify traction'])
        text=ApplicationReview(self.s).text();self.assertIn('Old unconfirmed traction',text);self.assertIn('SAVED DRAFT — NOT LIVE FORM',text);self.assertIn(str(f),text)
    def test_daily_attachment_is_hashed_frozen_and_sent_once(self):
        o=self.enable();self.facts();self.p.inspect(self.oid,fixtures.FormsTransport());r=DailyReporter(self.s).prepare();claim=o.claim('report',r['id']);attachment=claim['message']['attachments'][0]
        self.assertEqual(digest(attachment['content'].encode()),attachment['sha256']);self.assertIn('question-and-answer text preview is attached',r['body'])
        self.assertIn('Company name',attachment['content']);self.assertIn('A Story',attachment['content']);self.assertEqual(o.complete('report',r['id'],claim['message_sha256'],'fixture',OWNER)['state'],'SENT')
        self.assertEqual(DailyReporter(self.s).prepare()['body'],r['body'])
        with self.assertRaises(PolicyError):o.claim('report',r['id'])
    def test_supplement_does_not_change_daily_report_or_approve_submission(self):
        o=self.enable();report=DailyReporter(self.s).prepare();c=o.claim('report',report['id']);o.complete('report',report['id'],c['message_sha256'],'fixture',OWNER)
        key=o.review.supplement();c=o.claim('supplement',key);o.complete('supplement',key,c['message_sha256'],'fixture-supplement',OWNER)
        self.assertEqual(self.s.one('SELECT body FROM daily_reports')['body'],report['body']);self.assertEqual(self.s.one('SELECT count(*) n FROM application_confirmations')['n'],0)
        with self.assertRaises(PolicyError):o.claim('supplement',key)
    def test_text_preview_permission_revoked_blocks_email(self):
        o=self.enable();key=o.review.supplement();self.p.revoke(self.p.authorization('daily_email_report')['id'])
        with self.assertRaises(PolicyError):o.claim('supplement',key)
    def test_library_search_duplicate_group_and_changed_original(self):
        lib=MaterialsLibrary(self.s);root=Path(self.tmp.name);file=root/'deck.txt';file.write_text('A Story deck');stat=file.stat()
        self.s.db.execute('INSERT INTO material_library VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('mat',str(file),'deck.txt',str(root),'document','KEEP',stat.st_size,digest(file.read_bytes()),stat.st_mtime_ns,None,'Founder pitch','text',None,now()))
        self.assertEqual(lib.search('Founder')['total'],1);self.assertEqual(lib.search('%')['total'],0);self.assertEqual(lib.original('mat'),file)
        file.write_text('changed original');
        with self.assertRaises(PolicyError):lib.original('mat')
    def test_emailed_submission_preview_attaches_actual_questions(self):
        o=self.enable();self.facts();p=self.p.inspect(self.oid,fixtures.FormsTransport());c=self.p.preview(p['id']);m=json.loads(c['email_json'])
        self.assertIn('Question: Company name',m['body']);self.assertIn('Company name',m['attachments'][0]['content']);self.assertEqual(c['decision'],'PENDING')

if __name__=='__main__':unittest.main()
