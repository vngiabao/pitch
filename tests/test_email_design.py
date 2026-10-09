import sqlite3,unittest
from unittest.mock import patch
import test_application_pilot as fixtures
from test_opportunity_curation import brief
from founder_os.store import js,digest,PolicyError
from founder_os.report_email import DailyReporter,GmailTransport
from founder_os.connector_outbox import ConnectorOutbox,OWNER
from founder_os.email_design import link

class EmailDesignTests(unittest.TestCase):
    setUp=fixtures.AutonomyTests.setUp
    tearDown=fixtures.AutonomyTests.tearDown
    def setup_report(self):
        old=self.p.authorization('daily_email_report');self.p.revoke(old['id'])
        self.p.authorize('daily_email_report',{'recipient':OWNER,'question_answer_attachments':True},'Private report authorization')
        self.s.db.execute("INSERT INTO hunter_settings VALUES('mail_delivery',?)",(js({'mode':'gmail_connector'}),))
        r=self.record.copy();r['founder_brief']=brief(r['official_url']);r['founder_brief']['how_it_helps']='Could reduce costs <script>alert(1)</script> & improve interviews.'
        self.h.upsert(r)
        return DailyReporter(self.s)
    def test_escaped_shared_html_and_frozen_claim(self):
        r=self.setup_report();html=r.render()['body_html']
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        self.assertIn('Agent is handling:',html);self.assertIn('Your action:',html)
        daily=r.prepare();out=ConnectorOutbox(self.s);c=out.claim('report',daily['id'])
        self.assertEqual(c['message']['body_html'],html)
        self.assertEqual(c['message']['body_html_sha256'],digest(html.encode('utf-8')))
        for sql in ('UPDATE report_presentations SET body_html=? WHERE report_id=?','DELETE FROM report_presentations WHERE report_id=?'):
            with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute(sql,('changed',daily['id']) if sql.startswith('UPDATE') else (daily['id'],))
        out.complete('report',daily['id'],c['message_sha256'],'test-gmail-id',OWNER)
        self.assertEqual(r.prepare()['body'],daily['body'])
        sample=r.prepare_sample();claimed=out.claim('supplement',sample)
        self.assertIn('DESIGN SAMPLE',claimed['message']['body_html'])
        self.assertEqual(self.s.one('SELECT count(*) n FROM submissions')['n'],0)
    def test_html_tamper_blocked_and_unsafe_links(self):
        r=self.setup_report();key=r.prepare_sample()
        m=self.s.one('SELECT message_json FROM report_supplements WHERE id=?',(key,))
        import json
        changed=json.loads(m['message_json']);changed['body_html']+='changed'
        with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute('UPDATE report_supplements SET message_json=? WHERE id=?',(js(changed),key))
        self.s.db.execute("INSERT INTO report_supplements VALUES('corrupt',?,'PENDING','test',NULL,NULL)",(js(changed),))
        with self.assertRaisesRegex(PolicyError,'HTML integrity'):ConnectorOutbox(self.s).claim('supplement','corrupt')
        self.assertEqual(link('javascript:alert(1)','Source'),'Source')
    def test_smtp_has_html_alternative_and_exact_attachment(self):
        r=self.setup_report();rendered=r.render();report={'id':'test','recipient':OWNER,'subject':'test',**rendered,'attachments':[r.review.snapshot()]}
        with patch('founder_os.report_email.read_credential',return_value='test-only'),patch('founder_os.report_email.smtplib.SMTP_SSL') as smtp:
            smtp.return_value.__enter__.return_value.send_message.return_value={}
            GmailTransport().send(report)
            message=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        html=message.get_body(preferencelist=('html',)).get_content()
        self.assertEqual(html.rstrip('\n'),rendered['body_html'].rstrip('\n'))
        self.assertEqual(list(message.iter_attachments())[0].get_filename(),report['attachments'][0]['filename'])

if __name__=='__main__':unittest.main()
