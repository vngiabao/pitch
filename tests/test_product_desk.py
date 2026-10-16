import http.client
import os
import tempfile
import threading
import unittest
from datetime import date,timedelta
from pathlib import Path

os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os.product_desk import ProductDesk,retention,measured_facts,measured_numbers,parse_export,parse_day,api_pull,CREDENTIAL_PREFIX
from founder_os.pitch_lab import PitchLab,FactGuard
from founder_os.server import FounderServer

TODAY=date.today().isoformat()
def day(n):return (date.today()-timedelta(days=n)).isoformat()

def ev(fam,kind,at,source='manual'):return {'family_id':fam,'kind':kind,'at':at,'source':source}
EVENTS=[ev('a','first_call','2026-09-01'),ev('a','relative_contribution','2026-09-05'),ev('a','second_call','2026-09-10'),
        ev('b','first_call','2026-09-03'),ev('b','second_call','2026-09-20'),
        ev('c','first_call','2026-09-15',source='import'),ev('c','photo_upload','2026-09-16'),
        ev('d','relative_contribution','2026-09-18')]  # d contributed before any call: it is not in the first-call denominator


class RetentionTests(unittest.TestCase):
    def metric(self,r,key):return next(m for m in r['metrics'] if m['key']==key)

    def test_rates_carry_their_denominators_and_range(self):
        r=retention(EVENTS)
        second=self.metric(r,'second_call_rate')
        self.assertEqual((second['numerator'],second['denominator'],second['percent']),(2,3,67))
        self.assertEqual(second['denominator_label'],'families with a first call')
        rel=self.metric(r,'relatives_contributing');self.assertEqual((rel['numerator'],rel['denominator']),(1,3))
        after=self.metric(r,'calls_after_contribution');self.assertEqual((after['numerator'],after['denominator'],after['calls']),(1,2,1))
        self.assertEqual(r['range'],{'start':'2026-09-01','end':'2026-09-20'});self.assertEqual(r['as_of'],'2026-09-20')
        self.assertEqual(r['sources'],['import','manual'])

    def test_empty_denominator_is_not_zero(self):
        r=retention([ev('a','relative_contribution','2026-09-05')])
        second=self.metric(r,'second_call_rate')
        self.assertFalse(second['measurable']);self.assertIsNone(second['rate']);self.assertIsNone(second['percent'])
        self.assertEqual(retention([])['as_of'],None)

    def test_date_range_filters_events(self):
        r=retention(EVENTS,start='2026-09-02',end='2026-09-16')
        second=self.metric(r,'second_call_rate');self.assertEqual((second['numerator'],second['denominator']),(0,2))
        self.assertEqual(r['range'],{'start':'2026-09-03','end':'2026-09-16'})

    def test_measured_facts_are_labelled_with_as_of_and_license_numbers(self):
        facts=measured_facts(retention(EVENTS),families_enrolled=4)
        self.assertEqual([f['key'] for f in facts],['beta_families','second_call_rate','relatives_contributing','calls_after_contribution'])
        second=facts[1]
        self.assertIn('Measured as of Sep 20, 2026',second['text']);self.assertIn('2 of 3 families with a first call had a second call (67%)',second['text'])
        self.assertIn('import and manual entries',second['text']);self.assertEqual(second['source'],'measured')
        nums=measured_numbers(facts)
        for n in ('2','3','67','66.7','4','50','1'):self.assertIn(n,nums)
        self.assertNotIn('0',nums)

    def test_parse_day_accepts_export_formats(self):
        self.assertEqual(parse_day('10/03/2026'),'2026-10-03');self.assertEqual(parse_day('2026-10-01 14:03'),'2026-10-01')
        self.assertEqual(parse_day('2026-10-01T14:03:00Z'),'2026-10-01');self.assertIsNone(parse_day('yesterday'))


class JournalTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def desk(self):return ProductDesk(self.s)

    def test_add_family_and_log_calls_updates_the_measured_rate(self):
        d=self.desk()
        f=d.add_family({'label':'The Tran family','storyteller':'Grandma Lan','adult_child':'Minh','enrolled_on':day(20)})
        g=d.add_family({'label':'The Pham family'})
        d.log_event({'family_id':f['id'],'kind':'first_call','at':day(10),'detail':'40 minutes'})
        d.log_event({'family_id':f['id'],'kind':'second_call','at':day(3)})
        d.log_event({'family_id':g['id'],'kind':'first_call','at':day(8)})
        b=d.board()
        second=next(m for m in b['retention']['metrics'] if m['key']=='second_call_rate')
        self.assertEqual((second['numerator'],second['denominator'],second['percent']),(1,2,50))
        self.assertEqual(b['counts'],{'families':2,'first_calls':2,'second_calls':1,'contributing':0,'issues':0})
        self.assertEqual(b['families'][0]['label'],'The Tran family');self.assertEqual(b['families'][0]['counts']['first_call'],1)
        self.assertEqual(b['measured'][0]['text'].split(':')[1].strip(),'2 beta families in the journal.')
        self.assertTrue(any('1 of 2 families with a first call had a second call (50%)' in m['text'] for m in b['measured']))
        self.assertEqual(b['retention']['as_of'],day(3))

    def test_journal_rejects_invented_or_future_entries(self):
        d=self.desk()
        with self.assertRaisesRegex(ValueError,'name or label'):d.add_family({'label':'  '})
        f=d.add_family({'label':'Family 1'})
        with self.assertRaisesRegex(ValueError,'Unknown event kind'):d.log_event({'family_id':f['id'],'kind':'upsell','at':TODAY})
        with self.assertRaisesRegex(ValueError,'planned'):d.log_event({'family_id':f['id'],'kind':'first_call','at':(date.today()+timedelta(days=1)).isoformat()})
        with self.assertRaisesRegex(ValueError,'calendar day'):d.log_event({'family_id':f['id'],'kind':'first_call','at':'soon'})
        with self.assertRaises(ValueError):d.log_event({'family_id':'family-missing','kind':'first_call','at':TODAY})
        with self.assertRaisesRegex(ValueError,'Unknown family status'):d.update_family(f['id'],{'status':'vip'})

    def test_remove_event_and_change_status(self):
        d=self.desk();f=d.add_family({'label':'Family 1'})
        e=d.log_event({'family_id':f['id'],'kind':'issue','at':TODAY,'detail':'Call dropped'})
        self.assertEqual(d.board()['counts']['issues'],1)
        d.delete_event(e['id']);self.assertEqual(d.board()['counts']['issues'],0)
        self.assertEqual(d.update_family(f['id'],{'status':'dropped','notes':'Moved abroad'})['status_words'],'Dropped out')
        self.assertEqual(d.measured_facts(),[])  # a dropped family is not counted as enrolled, and no calls were logged

    def test_fact_guard_reports_measured_numbers_and_prefers_them(self):
        lab=PitchLab(self.s)
        blocked=FactGuard(lab,'Startup World Cup').check([{'key':'traction','text':'2 of 3 beta families had a second call (67%).'}],'PITCH_EDITION')
        self.assertTrue(any(i['rule']=='unverified_number' and '67%' in i['text'] for i in blocked['issues']))
        d=self.desk();fams=[d.add_family({'label':'Family '+str(i)}) for i in range(3)]
        for f in fams:d.log_event({'family_id':f['id'],'kind':'first_call','at':day(9)})
        for f in fams[:2]:d.log_event({'family_id':f['id'],'kind':'second_call','at':day(2)})
        g=FactGuard(lab,'Startup World Cup')
        r=g.check([{'key':'traction','text':'2 of 3 beta families had a second call (67%).'}],'PITCH_EDITION')
        self.assertEqual(r['blocking'],0)
        measured=[i for i in r['issues'] if i['rule']=='measured']
        self.assertTrue(measured);self.assertEqual(measured[0]['severity'],'info');self.assertIn('Measured as of',measured[0]['text'])
        ctx=lab.base_context('TAILOR')
        self.assertTrue(ctx['measured']);self.assertIn('prefer them over owner-reported',ctx['rules'][0]);self.assertIn('2 of 3 families with a first call',ctx['rules'][0])

    def test_no_journal_leaves_context_unchanged(self):
        ctx=PitchLab(self.s).base_context('TAILOR')
        self.assertEqual(ctx['measured'],[]);self.assertTrue(ctx['rules'][0].startswith('Use only the facts'))


APP_STORE_TSV='Provider\tProvider Country\tSKU\tTitle\tProduct Type Identifier\tUnits\tDeveloper Proceeds\tBegin Date\tEnd Date\tCountry Code\nAPPLE\tUS\tASTORY1\tA Story\t1F\t3\t0\t10/01/2026\t10/01/2026\tUS\nAPPLE\tUS\tASTORY1\tA Story\t1F\t2\t0\t10/01/2026\t10/01/2026\tCA\nAPPLE\tUS\tASTORY1\tA Story\tIA1\t1\t55.30\t10/02/2026\t10/02/2026\tUS\n'
REVENUECAT_CSV='﻿Date,Active Subscriptions,MRR,New Customers\n2026-10-01,4,316.00,2\n2026-10-02,5,"395.00",1\n'
STRIPE_CSV='id,Amount,Amount Refunded,Currency,Created (UTC),Status,Customer Email\nch_1,79.00,0.00,usd,2026-10-01 14:03,succeeded,a@example.com\nch_2,119.00,0.00,usd,2026-10-01 18:20,succeeded,b@example.com\nch_3,79.00,79.00,usd,2026-10-02 09:00,succeeded,c@example.com\nch_4,79.00,0.00,usd,2026-10-02 10:00,failed,d@example.com\n'


class IntakeTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def desk(self):
        d=ProductDesk(self.s);d.inbox.mkdir(exist_ok=True);return d

    def points(self,provider,text):return {(p['metric'],p['period']):(p['value'],p['unit']) for p in parse_export(provider,text)['points']}

    def test_app_store_sales_report_sums_units_per_day(self):
        pts=self.points('app_store_connect',APP_STORE_TSV)
        self.assertEqual(pts[('app_units','2026-10-01')],(5.0,'count'));self.assertEqual(pts[('app_units','2026-10-02')],(1.0,'count'))
        self.assertEqual(pts[('proceeds','2026-10-02')],(55.3,'usd'))

    def test_revenuecat_chart_keeps_latest_value_per_day(self):
        pts=self.points('revenuecat',REVENUECAT_CSV)
        self.assertEqual(pts[('active_subscriptions','2026-10-02')],(5.0,'count'));self.assertEqual(pts[('mrr','2026-10-01')],(316.0,'usd'));self.assertEqual(pts[('new_customers','2026-10-01')],(2.0,'count'))

    def test_stripe_payments_count_succeeded_only(self):
        pts=self.points('stripe',STRIPE_CSV)
        self.assertEqual(pts[('payments','2026-10-01')],(2.0,'count'));self.assertEqual(pts[('revenue','2026-10-01')],(198.0,'usd'))
        self.assertEqual(pts[('payments','2026-10-02')],(1.0,'count'));self.assertEqual(pts[('refunds','2026-10-02')],(79.0,'usd'))

    def test_unreadable_exports_are_refused(self):
        with self.assertRaisesRegex(ValueError,'date column'):parse_export('stripe','name,value\nx,1\n')
        with self.assertRaisesRegex(ValueError,'Unknown metrics provider'):parse_export('mixpanel','Date,Users\n2026-10-01,3\n')
        with self.assertRaisesRegex(ValueError,'no numbers'):parse_export('revenuecat','Date,Note\n2026-10-01,hello\n')

    def test_import_keeps_file_fingerprint_and_date_and_refuses_repeats(self):
        d=self.desk();(d.inbox/'stripe-oct.csv').write_text(STRIPE_CSV,encoding='utf-8')
        listed=d.inbox_files();self.assertEqual(listed[0]['name'],'stripe-oct.csv');self.assertIsNone(listed[0]['imported'])
        src=d.import_file('stripe-oct.csv','stripe','Daniel sent this on Oct 16')
        self.assertEqual((src['provider'],src['kind'],src['file_name'],src['row_count'],src['point_count']),('stripe','csv','stripe-oct.csv',4,5))
        self.assertEqual(len(src['file_sha256']),64);self.assertEqual((src['period_start'],src['period_end']),('2026-10-01','2026-10-02'))
        latest={p['metric']:p for p in d.latest_points()}
        self.assertEqual((latest['revenue']['period'],latest['revenue']['value'],latest['revenue']['file_name']),('2026-10-02',79.0,'stripe-oct.csv'))
        self.assertEqual(d.inbox_files()[0]['imported']['provider'],'stripe')
        with self.assertRaisesRegex(ValueError,'already imported'):d.import_file('stripe-oct.csv','stripe')
        self.assertTrue((d.inbox/'stripe-oct.csv').exists())  # read-only: the file stays where Bao put it
        board=d.board()['intake'];self.assertEqual(len(board['sources']),1);self.assertEqual(board['files'][0]['imported']['id'],src['id'])

    def test_import_rejects_paths_outside_the_inbox(self):
        d=self.desk();outside=Path(self.tmp.name)/'secret.csv';outside.write_text(STRIPE_CSV,encoding='utf-8')
        for name in ('../secret.csv','..\\secret.csv',str(outside),'','.hidden.csv'):
            with self.assertRaises(ValueError):d.import_file(name,'stripe')
        (d.inbox/'notes.pdf').write_bytes(b'%PDF');self.assertEqual(d.inbox_files(),[])
        with self.assertRaisesRegex(ValueError,'No such export'):d.import_file('notes.pdf','stripe')

    def test_api_pull_is_a_stub_that_never_returns_a_key(self):
        r=api_pull('stripe')
        self.assertEqual(r['status'],'not_switched_on');self.assertIsInstance(r['credential_present'],bool);self.assertEqual(r['credential_target'],CREDENTIAL_PREFIX+'stripe')
        self.assertFalse({'key','secret','token'}&set(r))
        with self.assertRaises(ValueError):api_pull('mixpanel')
        self.assertEqual([a['provider'] for a in self.desk().api_status()],['app_store_connect','stripe','revenuecat'])


class ProductPageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=FounderServer(str(Path(self.tmp.name)/'test.sqlite'),0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port;self.host='127.0.0.1:'+str(self.port)
    def tearDown(self):self.server.shutdown();self.thread.join();self.server.server_close();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port);conn.request(method,path,body,headers or {});r=conn.getresponse();data=r.read();status=r.status;h=dict(r.getheaders());conn.close();return status,data,h
    def test_families_page_and_api(self):
        status,html,h=self.request('GET','/families',headers={'Host':self.host})
        self.assertEqual(status,200);self.assertIn(b'/product.js',html);self.assertIn(b'href="/families"',html)
        cookie=h['Set-Cookie'].split(';')[0];token=cookie.split('=',1)[1]
        self.assertEqual(self.request('GET','/product.js',headers={'Host':self.host})[0],200)
        self.assertEqual(self.request('GET','/api/product',headers={'Host':self.host})[0],403)
        status,data,_=self.request('GET','/api/product',headers={'Host':self.host,'Cookie':cookie})
        self.assertEqual(status,200);self.assertIn(b'"families": []',data)
        headers={'Host':self.host,'Cookie':cookie,'X-Founder-CSRF':token,'Origin':'http://'+self.host,'Content-Type':'application/json'}
        status,data,_=self.request('POST','/api/family',b'{"label":"The Tran family"}',headers)
        self.assertEqual(status,200);self.assertIn(b'The Tran family',data)
        status,data,_=self.request('POST','/api/family-event',b'{"family_id":"family-missing","kind":"first_call","at":"2026-10-01"}',headers)
        self.assertEqual(status,400)


if __name__=='__main__':unittest.main()
