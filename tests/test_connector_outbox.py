import json,unittest
from datetime import datetime,timedelta,timezone
import test_application_pilot as fixtures
from founder_os.store import js,PolicyError
from founder_os.connector_outbox import ConnectorOutbox,OWNER
from founder_os.report_email import DailyReporter

class ConnectorTests(unittest.TestCase):
    setUp=fixtures.AutonomyTests.setUp
    tearDown=fixtures.AutonomyTests.tearDown
    facts=fixtures.AutonomyTests.facts
    def configure(self):
        self.s.db.execute("INSERT INTO hunter_settings VALUES('mail_delivery',?)",(js({'mode':'gmail_connector','account':OWNER}),));return ConnectorOutbox(self.s)
    def test_connector_report_claim_receipt_and_no_duplicate(self):
        o=self.configure();reporter=DailyReporter(self.s);r=reporter.prepare();self.assertEqual(reporter.send(r['id'])['state'],'CONNECTOR_PENDING')
        c=o.claim('report',r['id'])
        with self.assertRaises(PolicyError):o.claim('report',r['id'])
        result=o.complete('report',r['id'],c['message_sha256'],'fixture-gmail-message',OWNER);self.assertEqual(result['state'],'SENT')
        self.assertEqual(reporter.prepare()['state'],'SENT')
        with self.assertRaises(PolicyError):o.claim('report',r['id'])
    def test_report_scope_revocation_and_wrong_receipt_block(self):
        o=self.configure();r=DailyReporter(self.s).prepare();c=o.claim('report',r['id'])
        for sha,account in [('changed',OWNER),(c['message_sha256'],'different@example.org')]:
            with self.assertRaises(PolicyError):o.complete('report',r['id'],sha,'fixture',account)
        self.p.revoke(self.p.authorization('daily_email_report')['id'])
        # Retain the real outcome of an already-started send despite revocation.
        self.assertEqual(o.complete('report',r['id'],c['message_sha256'],'fixture',OWNER)['state'],'SENT')
        with self.assertRaises(PolicyError):DailyReporter(self.s).prepare()
    def test_uncertain_connector_send_cannot_retry(self):
        o=self.configure();r=DailyReporter(self.s).prepare();o.claim('report',r['id']);o.uncertain('report',r['id'])
        with self.assertRaises(PolicyError):o.claim('report',r['id'])
        self.assertEqual(DailyReporter(self.s).prepare()['state'],'DELIVERY_UNKNOWN')
    def test_connected_preview_still_requires_individual_confirmation(self):
        from test_application_pilot import FormsTransport
        o=self.configure();self.facts();t=FormsTransport();p=self.p.inspect(self.oid,t);c=self.p.preview(p['id'])
        self.assertEqual(self.p.send_preview(c['id'])['email_state'],'CONNECTOR_PENDING')
        with self.assertRaises(PolicyError):self.p.confirm(c['id'],'APPROVED',True)
        claim=o.claim('preview',c['id']);o.complete('preview',c['id'],claim['message_sha256'],'fixture',OWNER)
        self.assertEqual(self.p.execute(p['id'],t)['state'],'AWAITING_CONFIRMATION');self.assertEqual(t.calls,0)
        self.p.confirm(c['id'],'APPROVED',True);self.assertEqual(self.p.execute(p['id'],t)['state'],'SUBMITTED')
    def test_stale_preview_never_emailed_by_connector(self):
        from test_application_pilot import FormsTransport
        o=self.configure();self.facts();p=self.p.inspect(self.oid,FormsTransport());c=self.p.preview(p['id'])
        self.h.decide(self.oid,'SKIP','Owner declined program')
        with self.assertRaises(PolicyError):o.claim('preview',c['id'])
    def test_connector_cannot_send_yesterdays_backlog(self):
        o=self.configure();r=DailyReporter(self.s).prepare(datetime.now(timezone.utc)-timedelta(days=1))
        with self.assertRaises(PolicyError):o.claim('report',r['id'])

if __name__=='__main__':unittest.main()
