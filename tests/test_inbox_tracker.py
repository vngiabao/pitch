import tempfile,unittest
from datetime import datetime,timedelta,timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch
from founder_os.store import Store,now,PolicyError
from founder_os.funding_hunter import FundingHunter,blank_record
from founder_os.inbox_tracker import InboxTracker,ImapInbox,classify

OWNER='gbao.n.vo@gmail.com';COMPANY='bao@astoryapp.com'

def mail(sender,subject,body,days=1,bulk=False,to=OWNER):
    m=EmailMessage();m['From']=sender;m['To']=to;m['Subject']=subject;m['Message-ID']='<'+subject.replace(' ','-')+'@fixture>'
    m['Date']=format_datetime(datetime.now(timezone.utc)-timedelta(days=days))
    if bulk:m['List-Unsubscribe']='<mailto:unsubscribe@fixture.org>'
    m.set_content(body);return m

class FakeInbox:
    def __init__(self,messages,connected=True):self.messages=messages;self.connected=connected;self.fetches=0
    def available(self):return self.connected
    def fetch(self,since,prefilter):self.fetches+=1;return [m for m in self.messages if prefilter(m)]

class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'test.sqlite');self.h=FundingHunter(self.s)
        self.grant=self.program('Fixture Startup Grant','https://fixture.org/grant')
        self.zlcf=self.program('Zell Lurie Commercialization Fund','https://zli.umich.edu/program/zlcf/')
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def program(self,name,url):
        r=blank_record();r.update(canonical_name=name,organizer='Fixture org',opportunity_type='grant',cycle='rolling',cycle_kind='rolling',official_url=url,application_url=url,status='OPEN')
        r['sources']=[{'url':url,'role':'official_program','checked_at':now(),'excerpt':'Fixture official program page, rolling applications.'}]
        r['field_sources']={k:[url] for k in ('status','cycle_kind','application_url')}
        return self.h.upsert(r)['opportunity_id']
    def tracker(self,owner=(),company=()):
        return InboxTracker(self.s,self.h,{OWNER:FakeInbox(list(owner)),COMPANY:FakeInbox(list(company))})
    def pending(self):return self.s.rows("SELECT * FROM inbox_messages WHERE state IN ('PROPOSED','REVIEW')")

    def test_acceptance_is_proposed_then_recorded_only_after_owner_confirms(self):
        t=self.tracker([mail('Team <team@mail.fixture.org>','Congratulations from Fixture Startup Grant','You have been accepted.')])
        t.poll(force=True);p=self.pending()
        self.assertEqual([(x['opportunity_id'],x['proposed_outcome'],x['state']) for x in p],[(self.grant,'Accepted','PROPOSED')])
        self.assertEqual(self.s.rows('SELECT * FROM funding_outcomes'),[])
        with self.assertRaises(PolicyError):t.decide(p[0]['id'],'confirm',actor='agent')
        result=t.decide(p[0]['id'],'confirm')
        self.assertEqual(result['recommendation'],'ACCEPTED')
        o=self.s.one('SELECT o.*,s.kind FROM funding_outcomes o JOIN source_versions v ON v.id=o.source_version_id JOIN sources s ON s.id=v.source_id')
        self.assertEqual((o['outcome'],o['kind']),('Accepted','email'))
        t.poll(force=True);self.assertEqual(self.s.one('SELECT count(*) n FROM inbox_messages')['n'],1)
        with self.assertRaises(PolicyError):t.decide(p[0]['id'],'dismiss')

    def test_dismiss_records_nothing(self):
        t=self.tracker([mail('no-reply@fixture.org','Fixture Startup Grant update','Unfortunately we are not moving forward.')]);t.poll(force=True)
        self.assertEqual(t.decide(self.pending()[0]['id'],'dismiss')['state'],'DISMISSED');self.assertEqual(self.s.rows('SELECT * FROM funding_outcomes'),[])

    def test_noise_is_ignored(self):
        t=self.tracker([mail('news@fixture.org','Welcome to the Fixture newsletter','Weekly news.',bulk=True),
                        mail('shop@store.example','Congratulations, your order shipped','Thanks for your order.'),
                        mail('jobs@company.example','Thank you for applying','Thanks for applying to the analyst role.'),
                        mail(OWNER,'Application submitted to Fixture Startup Grant','Sent by me.')])
        t.poll(force=True);self.assertEqual(self.s.rows('SELECT * FROM inbox_messages'),[])

    def test_shared_sender_matches_by_program_name_or_acronym(self):
        t=self.tracker(company=[mail('zli@umich.edu','Your ZLCF application','We received your application.',to=COMPANY)]);t.poll(force=True)
        p=self.pending();self.assertEqual((p[0]['opportunity_id'],p[0]['proposed_outcome'],p[0]['account']),(self.zlcf,'Applied',COMPANY))
        t=self.tracker([mail('events@umich.edu','Pitch competition finalists announced','Congratulations to the finalists of our startup competition.')]);t.poll(force=True)
        review=[x for x in self.pending() if x['state']=='REVIEW'];self.assertEqual((len(review),review[0]['opportunity_id']),(1,None))
        with self.assertRaises(PolicyError):t.decide(review[0]['id'],'confirm')

    def test_older_or_conflicting_news_does_not_overwrite_recorded_outcome(self):
        self.h.outcome(self.grant,'Accepted','Owner reported',evidence_url='https://fixture.org/grant')
        t=self.tracker([mail('apply@fixture.org','Application received','Thanks for your application.',days=3),
                        mail('apply@fixture.org','Decision','Unfortunately you were not selected.',days=3)]);t.poll(force=True)
        states={r['proposed_outcome']:r['state'] for r in self.s.rows('SELECT * FROM inbox_messages')}
        self.assertEqual(states,{'Applied':'ALREADY_TRACKED','Rejected':'REVIEW'})

    def test_throttle_and_not_connected(self):
        owner=FakeInbox([]);company=FakeInbox([],connected=False);t=InboxTracker(self.s,self.h,{OWNER:owner,COMPANY:company})
        r=t.poll();self.assertEqual(r[COMPANY],{'connected':False});self.assertEqual(company.fetches,0)
        self.assertEqual(t.poll()[OWNER],{'waiting':True});self.assertEqual(owner.fetches,1)
        self.assertFalse(t.settings()['state'][COMPANY]['connected'])

    def test_only_owner_mailboxes(self):
        with self.assertRaises(PolicyError):ImapInbox('someone@example.org')
        with self.assertRaises(PolicyError):InboxTracker(self.s,self.h).ingest('someone@example.org',mail('a@fixture.org','Congratulations','x'),[])

    def test_imap_is_read_only(self):
        msg=mail('team@fixture.org','Congratulations','You have been accepted to Fixture Startup Grant.')
        class FakeIMAP:
            def __init__(self,*a,**k):self.ops=[];FakeIMAP.last=self
            def login(self,user,secret):self.ops.append(('login',user))
            def list(self):return 'OK',[b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"']
            def select(self,box,readonly=False):self.ops.append(('select',box,readonly));return 'OK',[b'1']
            def search(self,charset,*criteria):return 'OK',[b'1']
            def fetch(self,ids,what):self.ops.append(('fetch',what));raw=msg.as_bytes();return 'OK',[(b'1 (RFC822.SIZE %d BODY[] {%d}'%(len(raw),len(raw)),raw),b')']
            def logout(self):self.ops.append(('logout',))
            def __getattr__(self,name):raise AssertionError('IMAP command not allowed: '+name)
        with patch('founder_os.inbox_tracker.imaplib.IMAP4_SSL',FakeIMAP),patch('founder_os.inbox_tracker.read_credential',return_value='test-only'):
            out=ImapInbox(OWNER).fetch(datetime.now(timezone.utc)-timedelta(days=5),lambda m:True)
        ops=FakeIMAP.last.ops
        self.assertEqual(len(out),1);self.assertIn(('select','"[Gmail]/All Mail"',True),ops);self.assertEqual(ops[-1],('logout',))
        self.assertTrue(all('PEEK' in op[1] for op in ops if op[0]=='fetch'))

    def test_export_lists_tracked_programs_with_email_evidence(self):
        t=self.tracker([mail('team@fixture.org','Welcome to Fixture Startup Grant','Your account is approved.')]);t.poll(force=True)
        t.decide(self.pending()[0]['id'],'confirm')
        rows=t.export_csv().lstrip('﻿').splitlines()
        self.assertTrue(rows[0].startswith('Program,Organizer,Status'))
        self.assertIn('Fixture Startup Grant',rows[1]);self.assertIn('Accepted',rows[1]);self.assertIn('Email',rows[1]);self.assertIn(OWNER,rows[1])

    def test_classifier_order(self):
        self.assertEqual(classify('Update','Congratulations to our winners. Unfortunately your team was not selected.'),'Rejected')
        self.assertEqual(classify('You are a finalist!',''),'Finalist')
        self.assertIsNone(classify('Welcome to our newsletter','',bulk=True))

if __name__=='__main__':unittest.main()
