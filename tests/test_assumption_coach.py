import http.client
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os import assumption_coach
from founder_os.assumption_coach import AssumptionCoach,SEED,CHALLENGE_PREFIX,FactGuardRule
from founder_os.pitch_lab import PitchLab,numbers_in,norm
from founder_os.growth_desk import GrowthDesk
from founder_os.product_desk import ProductDesk
from founder_os.server import FounderServer

ET=ZoneInfo('America/New_York')
def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}
def challenge(items):return {'weakest':items,'note':''}
def item(key,why='The pitch leans on it and nothing is recorded.',test='Log it in channel math this week.',q='What is your measured conversion?'):
    return {'key':key,'why_weak':why,'cheapest_test':test,'judge_question':q}


class AssumptionCoachTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def entry(self,**kw):
        GrowthDesk(self.s).add_entry({'channel':'email','week_start':'2026-10-12','visits':50,'signups':5,'purchases':1,'spend_usd':20,'revenue_usd':1,'source':'test'}|kw)

    def test_seed_uses_only_deck_numbers_and_real_slides(self):
        ac=AssumptionCoach(self.s);lab=PitchLab(self.s);allowed=lab.allowed_numbers();ids={x['id'] for x in lab.master_deck()['slides']}
        rows=ac.items();self.assertEqual(len(rows),len(SEED));self.assertEqual([r['key'] for r in rows],[a['key'] for a in SEED])
        for a in rows:
            self.assertIn(a['status'],('assumed','modeled'),a['key'])
            self.assertEqual([n for n in numbers_in(a['statement']+' '+a['number']) if norm(n) not in allowed],[],a['key']+' says a number the deck does not')
            self.assertEqual([x for x in a['slides'] if x not in ids],[],a['key']+' names a slide that is not in the deck')
            self.assertTrue(a['cheapest_test']);self.assertNotIn('—',a['statement']+a['cheapest_test'])
        self.assertEqual(ac.board()['counts'],{'assumed':12,'modeled':6,'measured':0})
        # Seeding is idempotent and never overwrites an edit.
        ac.update('plan_mix',{'owner_note':'Ask at Hope College','status':'modeled'})
        again=AssumptionCoach(self.s).get('plan_mix');self.assertEqual((again['owner_note'],again['status'],again['seeded_status']),('Ask at Hope College','modeled','modeled'))
        self.assertEqual(len(AssumptionCoach(self.s).items()),len(SEED))
        with self.assertRaises(ValueError):ac.update('plan_mix',{'status':'measured'})

    def test_measured_facts_flip_status_and_flow_back(self):
        ac=AssumptionCoach(self.s);self.assertEqual(ac.sync(),[])
        self.entry()
        flips=ac.sync();self.assertEqual({f['key'] for f in flips},{'visit_conversion','visits_to_families','acquisition_cost'})
        conv=ac.get('visit_conversion');self.assertEqual(conv['status'],'measured');self.assertEqual(conv['measured']['fact']['key'],'conversion')
        self.assertIn('2026-10-12',conv['measured']['fact']['as_of']);self.assertIn('1 of 50 visits',conv['measured']['fact']['text'])
        self.assertEqual([e['key'] for e in conv['measured']['evidence']],['purchasing_families'])
        # A watched fact is evidence, not a flip.
        pay=ac.get('willingness_to_pay');self.assertEqual(pay['status'],'assumed');self.assertEqual({e['key'] for e in pay['measured']['evidence']},{'purchasing_families','revenue'})
        with self.assertRaises(ValueError):ac.update('visit_conversion',{'status':'assumed'})
        # The journal flips the retention rows with their dates.
        d=ProductDesk(self.s);d.add_family({'label':'Tran','status':'active'});fam=[f for f in d.families() if f['label']=='Tran'][0]
        d.log_event({'family_id':fam['id'],'kind':'first_call','at':'2026-10-01'});d.log_event({'family_id':fam['id'],'kind':'second_call','at':'2026-10-08'})
        flips=ac.sync();self.assertEqual({f['key'] for f in flips},{'second_call','relatives_contribute'})
        second=ac.get('second_call');self.assertEqual(second['status'],'measured');self.assertIn('Measured as of Oct 8, 2026',second['measured']['fact']['text'])
        self.assertEqual(ac.get('renewal')['status'],'assumed');self.assertEqual(ac.get('renewal')['measured']['evidence'][0]['key'],'second_call_rate')
        titles=[a['title'] for a in ac.alerts()];self.assertTrue(titles and all(t.startswith('Now measured: ') for t in titles));self.assertLessEqual(len(titles),4)
        ac.mark_seen();self.assertEqual(ac.alerts(),[])
        # Entries removed: back to what the deck said, and Today says so once.
        for e in GrowthDesk(self.s).math()['entries']:GrowthDesk(self.s).delete_entry(e['id'])
        flips=ac.sync();self.assertEqual({(f['key'],f['to']) for f in flips},{('visit_conversion','assumed'),('visits_to_families','assumed'),('acquisition_cost','modeled')})
        self.assertIsNone(ac.get('acquisition_cost')['measured']);self.assertTrue(any(a['title'].startswith('Back to modeled: Acquisition plus trial') for a in ac.alerts()))
        self.assertTrue(any(e['event']=='assumption.status_changed' for e in self.s.rows('SELECT event FROM audit')))

    def test_challenge_saves_through_fact_guard_and_reaches_today(self):
        ac=AssumptionCoach(self.s);self.entry();calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search));ctx=json.loads(prompt.split('CONTEXT:\n',1)[1])
            self.assertEqual(len(ctx['assumptions']),len(SEED));self.assertTrue(ctx['measured_facts']);self.assertEqual(ctx['edition']['title'],'Core deck (master notes)')
            self.assertIn('never introduce a figure',prompt);self.assertIn('Fact Guard drops the item',prompt)
            return challenge([item('renewal'),item('plan_mix',why='Only 11% of families pick Family in our experience.'),item('not_a_key'),item('willingness_to_pay',test='Run the $1 reservation drive; 5 families are waiting.'),item('gift_buyer')]),0
        r=assumption_coach.run(self.h,request(CHALLENGE_PREFIX+'assumptions-week-2026-42'),fake)
        self.assertEqual(calls,[('assumptions',False)]);self.assertEqual(r['weakest'],['renewal','willingness_to_pay','gift_buyer']);self.assertEqual(r['rejected'],2)
        c=ac.latest_challenge();self.assertFalse(c['seen']);self.assertEqual([x['reason'][:30] for x in c['rejected']],['Introduced numbers not in the ','Not an assumption in the table'])
        self.assertEqual(c['weakest'][0]['statement'],'Families renew after the first year because the call becomes a habit.');self.assertTrue(c['measured'])
        [a]=[x for x in ac.alerts() if x['url']=='/assumptions' and 'weakest' in x['title']];self.assertIn('Families renew',a['detail']);self.assertEqual(a['link'],'See the tests')
        ac.mark_seen();self.assertEqual([x for x in ac.alerts() if 'weakest' in x['title']],[])
        self.assertTrue(assumption_coach.handles(CHALLENGE_PREFIX+'x'));self.assertFalse(assumption_coach.handles('Win brief: x'))
        def empty(h,request,prompt,schema,stem,search=False,timeout=900):return challenge([item('plan_mix',why='A 9.5% lift.')]),0
        with self.assertRaisesRegex(RuntimeError,'no usable items'):assumption_coach.run(self.h,request(CHALLENGE_PREFIX+'assumptions-2026-10-16T0800'),empty)
        guard=FactGuardRule(ac.allowed_numbers());self.assertEqual(guard.strangers('We model $0.32 to $0.45 and 3 percent in 2026, 12 calls'),[]);self.assertEqual(guard.strangers('a 4.5% lift on 300 visits'),['4.5%','300'])
        # for_agents puts the challenge's weakest first.
        fa=ac.for_agents();self.assertEqual([x['key'] for x in fa['items'][:3]],['renewal','willingness_to_pay','gift_buyer']);self.assertEqual(fa['weakest'][:3],['renewal','willingness_to_pay','gift_buyer'])

    def test_weekly_challenge_queues_once_after_monday_730(self):
        ac=AssumptionCoach(self.s)
        early=datetime(2026,10,19,7,0,tzinfo=ET)  # Monday 7:00
        self.assertEqual(ac.poll(early),{'flips':[],'queued':False})
        self.assertTrue(ac.poll(datetime(2026,10,19,7,31,tzinfo=ET))['queued'])
        self.assertFalse(ac.poll(datetime(2026,10,21,9,0,tzinfo=ET))['queued'],'once a week')
        self.assertTrue(ac.researching());self.assertEqual(self.s.rows('SELECT reason FROM hunter_requests')[0]['reason'],CHALLENGE_PREFIX+'assumptions-week-2026-43')
        self.assertTrue(ac.poll(datetime(2026,10,26,7,30,tzinfo=ET))['queued'],'the next week')
        ac.request();self.assertEqual(len(self.s.rows('SELECT 1 FROM hunter_requests')),3)
        self.entry();self.assertIn('visit_conversion',ac.poll(datetime(2026,10,26,8,0,tzinfo=ET))['flips'])

    def test_tailor_and_coach_read_the_statuses(self):
        oid=self.h.upsert(fixtures.HunterTests.record(self,'Example Competition'))['opportunity_id'];lab=PitchLab(self.s)
        it=lab.start_edition(oid,3);prompt,_,stem,_=lab.prompt_for(lab.item(it['id']))
        self.assertEqual(stem,'tailor');ctx=json.loads(prompt.split('CONTEXT:\n',1)[1])
        self.assertEqual(len(ctx['assumptions']['items']),len(SEED));self.assertTrue(any('Never present an assumed or modeled number as a result' in r for r in ctx['rules']))
        per={x['key']:x for x in ctx['assumptions']['items']};self.assertEqual(per['interview_cost']['say'],'modeled, not observed');self.assertIn('example input',per['visit_conversion']['say'])
        self.entry();prompt,_,_,_=lab.prompt_for(lab.item(it['id']));ctx=json.loads(prompt.split('CONTEXT:\n',1)[1]);per={x['key']:x for x in ctx['assumptions']['items']}
        self.assertTrue(per['visit_conversion']['say'].startswith('measured as of 2026-10-12'));self.assertNotIn('visit_conversion',ctx['assumptions']['weakest'])
        lab._save(it['id'],'COACH',lab.item(it['id'])['payload']|{'brief':{'script':[{'slide_id':'cover','title':'Cover','text':'We are A Story.','seconds':20}]}})
        prompt,_,stem,_=lab.prompt_for(lab.item(it['id']));self.assertEqual(stem,'coach');self.assertIn('ask about the weakest ones in hard_questions',prompt);self.assertIn('"weakest"',prompt)


class AssumptionsPageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=FounderServer(str(Path(self.tmp.name)/'test.sqlite'),0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port;self.host='127.0.0.1:'+str(self.port)
    def tearDown(self):self.server.shutdown();self.thread.join();self.server.server_close();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port);conn.request(method,path,body,headers or {});r=conn.getresponse();data=r.read();status=r.status;h=dict(r.getheaders());conn.close();return status,data,h
    def test_page_api_and_owner_edit(self):
        status,html,h=self.request('GET','/assumptions',headers={'Host':self.host})
        self.assertEqual(status,200);self.assertIn(b'/assumptions.js',html);self.assertIn(b'href="/assumptions"',html)
        cookie=h['Set-Cookie'].split(';')[0];token=cookie.split('=',1)[1]
        self.assertEqual(self.request('GET','/assumptions.js',headers={'Host':self.host})[0],200)
        self.assertEqual(self.request('GET','/api/assumptions',headers={'Host':self.host})[0],403)
        status,data,_=self.request('GET','/api/assumptions',headers={'Host':self.host,'Cookie':cookie});b=json.loads(data)
        self.assertEqual(status,200);self.assertEqual(b['counts']['assumed'],12);self.assertIsNone(b['challenge']);self.assertIn('next-90',b['slide_titles'])
        headers={'Host':self.host,'Cookie':cookie,'X-Founder-CSRF':token,'Origin':'http://'+self.host,'Content-Type':'application/json'}
        status,data,_=self.request('POST','/api/assumption',json.dumps({'key':'gift_buyer','evidence_for':'50 leads from the MVP\n\nHope College students asked to gift it','owner_note':'Ask reservers who the storyteller is'}),headers)
        self.assertEqual(status,200);a=json.loads(data);self.assertEqual(a['evidence_for'],['50 leads from the MVP','Hope College students asked to gift it']);self.assertEqual(a['owner_note'],'Ask reservers who the storyteller is')
        self.assertEqual(self.request('POST','/api/assumption',json.dumps({'key':'gift_buyer','status':'measured'}),headers)[0],400)
        self.assertEqual(json.loads(self.request('POST','/api/assumptions-seen','{}',headers)[1]),{'seen':True})
        status,data,_=self.request('GET','/api/growth-alerts',headers={'Host':self.host,'Cookie':cookie});self.assertEqual(status,200)


if __name__=='__main__':unittest.main()
