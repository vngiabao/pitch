import json,smtplib,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo
import test_application_pilot as fixtures
from founder_os.store import js,PolicyError
from founder_os.connector_outbox import ConnectorOutbox,OWNER
from founder_os.report_email import DailyReporter,MailNotSent
from test_application_pilot import MailTransport

class ConnectorTests(unittest.TestCase):
    setUp=fixtures.AutonomyTests.setUp
    tearDown=fixtures.AutonomyTests.tearDown
    facts=fixtures.AutonomyTests.facts
    def configure(self,fallback=None):
        mail={'mode':'gmail_connector','account':OWNER}
        if fallback is not None:mail['smtp_fallback']=fallback
        self.s.db.execute("INSERT INTO hunter_settings VALUES('mail_delivery',?)",(js(mail),));return ConnectorOutbox(self.s)
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

class RaisingTransport(MailTransport):
    def __init__(self,error):super().__init__();self.error=error
    def send(self,r):self.calls+=1;raise self.error

class FallbackTests(unittest.TestCase):
    setUp=fixtures.AutonomyTests.setUp
    tearDown=fixtures.AutonomyTests.tearDown
    configure=ConnectorTests.configure
    def at(self,hour,minute):
        local=datetime.now(timezone.utc).astimezone(ZoneInfo('America/New_York'))
        return local.replace(hour=hour,minute=minute,second=0,microsecond=0).astimezone(timezone.utc)
    def poll(self,t,hour=9,minute=30):
        with patch('founder_os.report_email.GmailTransport',return_value=t):return DailyReporter(self.s).poll(self.at(hour,minute))
    def test_fallback_waits_for_grace_then_sends_once(self):
        o=self.configure({'enabled':True,'after_minutes':30});t=MailTransport()
        self.assertEqual(self.poll(t,9,29)['state'],'CONNECTOR_PENDING');self.assertEqual(t.calls,0)
        self.assertEqual(self.poll(t)['state'],'SENT');self.poll(t,10,0);self.assertEqual(t.calls,1)
        with self.assertRaises(PolicyError):o.claim('report',DailyReporter(self.s).prepare(self.at(9,30))['id'])
    def test_fallback_is_off_unless_owner_enabled(self):
        self.configure();t=MailTransport()
        self.assertEqual(self.poll(t,12,0)['state'],'CONNECTOR_PENDING');self.assertEqual(t.calls,0)
    def test_fallback_never_touches_a_claimed_or_uncertain_report(self):
        o=self.configure({'enabled':True});t=MailTransport()
        r=self.poll(t,9,5);o.claim('report',r['id'])
        self.assertEqual(self.poll(t)['state'],'SENDING');o.uncertain('report',r['id'])
        self.assertEqual(self.poll(t,11,0)['state'],'DELIVERY_UNKNOWN');self.assertEqual(t.calls,0)
    def test_fallback_without_credential_leaves_connector_pending(self):
        o=self.configure({'enabled':True});t=MailTransport(connected=False)
        r=self.poll(t);self.assertEqual(r['state'],'CONNECTOR_PENDING');self.assertIn('Connect-Report-Email.ps1',r['error']);self.assertEqual(t.calls,0)
        self.assertEqual(o.claim('report',r['id'])['id'],r['id'])
    def test_failure_before_transmission_retries_but_uncertain_does_not(self):
        self.configure({'enabled':True});t=RaisingTransport(MailNotSent('offline'))
        self.assertEqual(self.poll(t)['state'],'CONNECTOR_PENDING');self.assertEqual(self.poll(t,9,35)['state'],'CONNECTOR_PENDING');self.assertEqual(t.calls,2)
        t=RaisingTransport(TimeoutError('mid-send'));self.assertEqual(self.poll(t,9,40)['state'],'DELIVERY_UNKNOWN');self.poll(t,9,45);self.assertEqual(t.calls,1)
    def test_rejected_app_password_stops_fallback_for_the_day(self):
        o=self.configure({'enabled':True});t=RaisingTransport(smtplib.SMTPAuthenticationError(535,b'bad'))
        self.poll(t);r=self.poll(t,9,35);self.assertEqual(t.calls,1);self.assertEqual(r['state'],'CONNECTOR_PENDING')
        self.assertEqual(o.claim('report',r['id'])['id'],r['id'])
    def test_supersede_only_past_never_claimed_reports(self):
        o=self.configure();reporter=DailyReporter(self.s)
        old=reporter.prepare(datetime.now(timezone.utc)-timedelta(days=2));reporter.send(old['id'])
        with self.assertRaises(PolicyError):reporter.supersede(old['id'],'stale',actor='agent')
        self.assertEqual(reporter.supersede(old['id'],'Owner chose not to send a stale shortlist')['state'],'SUPERSEDED')
        with self.assertRaises(PolicyError):reporter.supersede(old['id'],'again')
        sent=reporter.prepare(datetime.now(timezone.utc)-timedelta(days=1));reporter.send(sent['id'],MailTransport())
        with self.assertRaises(PolicyError):reporter.supersede(sent['id'],'already sent')
        with self.assertRaises(PolicyError):reporter.supersede(reporter.prepare()['id'],'today')

if __name__=='__main__':unittest.main()
