import os
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os import customer_voice
from founder_os.customer_voice import CustomerVoice,VOICE_REASON,compare,cited,clean
from founder_os.scouts import Scouts,SCOUTS
from founder_os.growth_desk import GrowthDesk
from founder_os.pitch_lab import PitchLab,FactGuard

ET=ZoneInfo('America/New_York')
URL='https://www.reddit.com/r/AgingParents/comments/abc/i_wish_i_had_recorded_dad/'


def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}


def report(themes=(('Regret after a parent dies',14),('Mom will not talk about the past',9),('Storyworth sat unanswered',6)),threads_read=60):
    return {'themes':[{'theme':t,'summary':'What people said about it.','threads':n,'quotes':[{'text':'I wish I had recorded Dad telling the farm stories.','who':'u/quietmaple','url':URL},{'text':'Second quote.','who':'u/other','url':URL+'?2'},{'text':'Third, dropped.','who':'','url':URL+'?3'},{'text':'No link, dropped','who':'x','url':''}]} for t,n in themes],
            'tried':[{'what':'Storyworth','threads':8,'said':'Loved the idea; the parent stopped answering after month two.','quote':{'text':'She did three and then nothing.','who':'u/a','url':URL}},{'what':'nothing','threads':5,'said':'Kept meaning to.','quote':{'text':'','who':'','url':''}}],
            'objections':[{'objection':'She will not talk to a robot','threads':7,'quote':{'text':'My mom hangs up on anything automated.','who':'u/b','url':URL}},{'objection':'Too expensive for a maybe','threads':4,'quote':{'text':'$100 for a book she may never fill in is a lot.','who':'u/c','url':URL+'?p'}}],
            'willing_to_pay':[{'said':'I paid $99 for Storyworth and would pay double for calls.','url':URL+'?pay'},{'said':'no link','url':''}],
            'words':['the stories go with them','before it is too late','Before It Is Too Late','she lights up when she talks about the farm'],'places_read':['r/AgingParents','r/GiftIdeas'],'threads_read':threads_read,
            'sources':[URL,'https://www.quora.com/How-do-I-record-my-grandmother','not a url'],'queries':['reddit aging parents record stories'],'errors':[]}


class CustomerVoiceTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def test_save_keeps_history_and_compares_week_to_week(self):
        cv=CustomerVoice(self.s)
        empty=cv.current();self.assertIsNone(empty['report']);self.assertEqual(empty['runs'],0);self.assertIsNone(cv.for_agents());self.assertIsNone(cv.for_field_day())
        first=cv.save(report(),['q1'],datetime(2026,10,15,8,20,tzinfo=ET))
        self.assertEqual([t['theme'] for t in first['report']['themes']],['Regret after a parent dies','Mom will not talk about the past','Storyworth sat unanswered'])
        self.assertEqual(len(first['report']['themes'][0]['quotes']),3,'a quote without a URL is dropped');self.assertTrue(first['movement']['first']);self.assertEqual(first['movement_words'],'First run; nothing to compare yet.')
        self.assertEqual(first['report']['words'],['the stories go with them','before it is too late','she lights up when she talks about the farm'],'words deduplicate case-insensitively')
        self.assertEqual(first['report']['willing_to_pay'],[{'said':'I paid $99 for Storyworth and would pay double for calls.','url':URL+'?pay'}])
        self.assertIn(URL,first['report']['sources']);self.assertNotIn('not a url',first['report']['sources']);self.assertEqual((first['run_on'],first['week']),('2026-10-15','2026-W42'))
        second=cv.save(report(themes=(('Regret after a parent dies',20),('Mom will not talk about the past',5),('Who hears the recordings',3))),[],datetime(2026,10,22,8,20,tzinfo=ET))
        m=second['movement']
        self.assertEqual((m['new'],m['gone']),(['Who hears the recordings'],['Storyworth sat unanswered']))
        self.assertEqual(m['up'],[{'theme':'Regret after a parent dies','from':14,'to':20}]);self.assertEqual(m['down'],[{'theme':'Mom will not talk about the past','from':9,'to':5}])
        self.assertEqual(second['previous_on'],'2026-10-15');self.assertEqual(second['runs'],2);self.assertIn('Up: Regret after a parent dies (14 to 20)',second['movement_words'])
        # A second run in the same week still compares to last week, not to this morning.
        again=cv.save(report(themes=(('Regret after a parent dies',21),)),[],datetime(2026,10,22,15,0,tzinfo=ET))
        self.assertEqual(again['previous_on'],'2026-10-15');self.assertEqual(again['movement']['up'],[{'theme':'Regret after a parent dies','from':14,'to':21}])
        self.assertEqual(len(cv.runs()),3,'every run is kept')
        self.assertEqual(compare(None,clean(report()))['first'],True)

    def test_agents_get_themes_counts_and_two_quotes_each(self):
        cv=CustomerVoice(self.s);cv.save(report())
        fa=cv.for_agents()
        self.assertEqual(fa['as_of'],datetime.now(ET).date().isoformat());self.assertEqual(fa['threads_read'],60)
        self.assertEqual([(t['theme'],t['threads'],len(t['quotes'])) for t in fa['themes']],[('Regret after a parent dies',14,2),('Mom will not talk about the past',9,2),('Storyworth sat unanswered',6,2)])
        self.assertEqual(set(fa['themes'][0]['quotes'][0]),{'text','url'},'the agents get the quote and its URL, not the username')
        self.assertEqual(fa['objections'][0],{'objection':'She will not talk to a robot','threads':7});self.assertIn('take no fact about A Story',fa['note'])
        fd=cv.for_field_day()
        self.assertEqual([o['objection'] for o in fd['objections']],['She will not talk to a robot','Too expensive for a maybe']);self.assertEqual(fd['objections'][0]['url'],URL)
        self.assertEqual(fd['words'][:2],['the stories go with them','before it is too late']);self.assertEqual(fd['tried'],['Storyworth','nothing'])
        # Pitch Tailor and the Coach see it as evidence about the market; the Campaign Planner and the field day get objections and words.
        lab=PitchLab(self.s);oid=self.h.upsert(fixtures.HunterTests.record(self,'Voice Prize'))['opportunity_id']
        it=lab.start_edition(oid,3);prompt,_,stem,_=lab.prompt_for(lab.item(it['id']))
        self.assertEqual(stem,'tailor');self.assertIn('"customer_voice"',prompt);self.assertIn('Regret after a parent dies',prompt);self.assertIn('take no traction, customer or number about A Story from it',prompt)
        lab._save(it['id'],'COACH',{**lab.item(it['id'])['payload'],'brief':{'script':[{'slide_id':'cover','title':'A Story','seconds':20,'text':'Hi.'}],'strategy':'','slide_plan':[],'ask':'','materials':[],'open_questions':[],'answers_to_feedback':[],'rules':{}}})
        cp,_,cstem,_=lab.prompt_for(lab.item(it['id']))
        self.assertEqual(cstem,'coach');self.assertIn('She will not talk to a robot',cp);self.assertIn('never treat it as our traction',cp)
        desk=GrowthDesk(self.s);ctx=desk.campaign_context('holiday-gift-passes')
        self.assertEqual(ctx['customer_voice']['words'][0],'the stories go with them');self.assertIn('customer_voice.objections',ctx['task'])
        field=desk.campaign('hope-college-onsite-2026-10-17')
        self.assertEqual(field['voice']['objections'][0]['objection'],'She will not talk to a robot');self.assertIsNone(desk.campaign('holiday-gift-passes')['voice'])
        self.assertEqual(desk.board()['voice']['report']['threads_read'],60)

    def test_fact_guard_blocks_thread_counts_unless_quoted_with_the_source(self):
        lab=PitchLab(self.s);g=FactGuard(lab,'Voice Prize')
        bare=g.check([{'key':'problem','text':'17 of 63 threads on r/AgingParents voiced regret.'}],'PITCH_EDITION')
        self.assertEqual([i['rule'] for i in bare['issues']],['unverified_number','unverified_number'],'before the scout has run, any such count is blocked')
        CustomerVoice(self.s).save(report());g=FactGuard(lab,'Voice Prize')
        bare=g.check([{'key':'problem','text':'17 of 63 threads on r/AgingParents voiced regret.'}],'PITCH_EDITION')
        self.assertEqual(bare['blocking'],2);self.assertIn('inside a quotation with the thread’s URL',bare['issues'][0]['text'])
        quoted=g.check([{'key':'problem','text':'One caregiver wrote “17 of 63 threads here are people who waited too long” ('+URL+').'}],'PITCH_EDITION')
        self.assertEqual(quoted['blocking'],0);self.assertEqual([i['rule'] for i in quoted['issues']],['cited','cited'])
        no_source=g.check([{'key':'problem','text':'One caregiver wrote “17 of 63 threads here are people who waited too long”.'}],'PITCH_EDITION')
        self.assertEqual(no_source['blocking'],2,'a quotation without its URL is still blocked')
        wrong_source=g.check([{'key':'problem','text':'“17 threads” (https://example.org/not-a-source)'}],'PITCH_EDITION')
        self.assertEqual(wrong_source['blocking'],1)
        self.assertTrue(cited("“17 threads” "+URL,"17",[URL]));self.assertFalse(cited("17 threads "+URL,"17",[URL]));self.assertFalse(cited("“17 threads”","17",[]))
        still=g.check([{'key':'traction','text':'We have 17 paying customers.'}],'PITCH_EDITION')
        self.assertTrue(any(i['rule']=='unverified_number' for i in still['issues']),'a bare number about A Story is never licensed by the scout')

    def test_scheduled_thursday_and_on_request_from_the_scouts_page(self):
        sc=Scouts(self.s);s=next(x for x in SCOUTS if x['key']=='customer_voice')
        self.assertEqual((s['days'],s['hour'],s['minute'],s['reason'],s['lands'][0]),(('TH',),8,15,VOICE_REASON,'/growth#families-say'))
        thu=datetime(2026,10,22,8,20,tzinfo=ET)
        self.assertIn('customer_voice',sc.poll(thu)['queued']);self.assertEqual(sc.poll(thu)['queued'],sc.poll(thu)['queued'],'once a day')
        self.assertEqual(len(self.s.rows('SELECT id FROM hunter_requests WHERE reason=?',(VOICE_REASON,))),1)
        self.assertNotIn('customer_voice',sc.poll(datetime(2026,10,22,8,0,tzinfo=ET))['queued'],'before 8:15 nothing is due')
        self.assertNotIn('customer_voice',Scouts(self.s).poll(datetime(2026,10,21,9,0,tzinfo=ET))['queued'],'Wednesday is not its day')
        st=sc.status(thu);by={x['key']:x for x in st['scouts']}
        self.assertTrue(by['customer_voice']['running']);self.assertIsNone(by['customer_voice']['last_run']);self.assertEqual(by['customer_voice']['next_run'][:16],'2026-10-29T08:15')
        self.assertTrue(CustomerVoice(self.s).current()['researching']);self.assertTrue(GrowthDesk(self.s).board()['voice']['researching'])
        r=sc.request_run('customer_voice');self.assertEqual(r['state'],'QUEUED'),'Research now on the Growth desk and the Scouts page queue the same job'

    def test_worker_run_requires_the_web_and_saves(self):
        calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search));self.assertIn('r/AgingParents',prompt);self.assertIn('must not state anything about A Story',prompt);self.assertIn('Never invent a thread',prompt);return report(),1
        r=customer_voice.run(self.h,request(VOICE_REASON),fake)
        self.assertEqual((r['themes'],r['threads_read'],r['new']),(3,60,['Regret after a parent dies','Mom will not talk about the past','Storyworth sat unanswered']));self.assertEqual(calls,[('customer-voice',True)])
        self.assertTrue(customer_voice.handles(VOICE_REASON));self.assertFalse(customer_voice.handles('Scout: Grant'))
        last=Scouts(self.s).status()['scouts'][[s['key'] for s in SCOUTS].index('customer_voice')]['last_run'];self.assertEqual(last['found'],3)
        def no_web(h,request,prompt,schema,stem,search=False,timeout=900):return report(),0
        with self.assertRaises(RuntimeError):customer_voice.run(self.h,request(VOICE_REASON),no_web)
        self.assertEqual(len(CustomerVoice(self.s).runs()),1,'a rejected run saves nothing')
        # The second run's prompt carries last week's theme names so the weeks compare.
        def fake2(h,request,prompt,schema,stem,search=False,timeout=900):self.assertIn('"previous_themes": ["Regret after a parent dies"',prompt);return report(),1
        customer_voice.run(self.h,request(VOICE_REASON),fake2)


if __name__=='__main__':unittest.main()
