import os
import unittest
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os import win_scout
from founder_os.win_scout import WinScout,WIN_PREFIX
from founder_os.pitch_lab import PitchLab


def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}


def brief(competitors=('Memoir Co',),judges=('Pat Judge',)):
    return {'rules':{'format':'Five minutes on stage','time_limit':'5 minutes','slide_limit':'not published','qa':'3 minutes','audience':'Local investors and students','where':'Muskegon','deadline':'not published','event_date':'2026-11-05'},
            'criteria':[{'name':'Traction','weight':'30%','evidence':'Rubric on the rules page'},{'name':'Team','weight':'not published','evidence':''}],
            'judges':[{'name':j,'role':'Partner at a seed fund','cares_about':'Repeat use and a clear first customer','source_url':'https://example.org/judges'} for j in judges],
            'past_winners':[{'year':'2025','company':'Porch Co','what_they_did':'Home repair marketplace','why_it_won':'Showed paying customers in Grand Rapids','source_url':'https://example.org/winners'}],
            'competitors':[{'name':c,'what_they_do':'Memoir books by email','stage':'Seed','strength':'Revenue','source_url':'https://example.org/c'} for c in competitors],
            'unstated':[{'insight':'Judges favor founders who name a local first customer','evidence':'Three of four past winners did'}],
            'how_we_win':[{'move':'Open with the Hope College students who want to gift it','why':'Local demand is what won in 2025','applies_to':'pitch'},{'move':'Answer the retention question before it is asked','why':'The seed-fund judge asks it every year','applies_to':'qa'},{'move':'','why':'','applies_to':'nope'}],
            'risks':['No live demo slot'],'open_questions':['Will Daniel attend?'],'sources':['https://example.org/rules','not a url'],'queries':['5x5 night rules'],'errors':[]}


class WinScoutTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record

    def program(self,name='5x5 Night'):return self.h.upsert(self.record(name))['opportunity_id']

    def test_brief_is_cleaned_and_changes_are_noticed(self):
        oid=self.program();ws=WinScout(self.s)
        self.assertIsNone(ws.brief(oid)['brief']);self.assertIsNone(ws.for_agents(oid))
        b=ws.save(oid,brief())
        self.assertEqual(b['changes'],[]);self.assertTrue(b['seen'])
        self.assertEqual([m['applies_to'] for m in b['brief']['how_we_win']],['pitch','qa'],'a bad applies_to falls back to pitch, an empty move is dropped')
        self.assertEqual(b['brief']['sources'],['https://example.org/rules'])
        b2=ws.save(oid,brief(competitors=('Memoir Co','Voice Legacy'),judges=('Pat Judge','Sam Angel')))
        self.assertEqual(b2['changes'],['New competitor: Voice Legacy','New judge: Sam Angel']);self.assertFalse(b2['seen']);self.assertEqual(b2['runs'],2)
        [a]=ws.alerts();self.assertIn('5x5 Night: New competitor: Voice Legacy',a['title']);self.assertEqual(a['url'],'/opportunity/'+oid)
        self.assertTrue(ws.mark_seen(oid)['seen']);self.assertEqual(ws.alerts(),[])
        fa=ws.for_agents(oid);self.assertEqual([j['name'] for j in fa['judges']],['Pat Judge','Sam Angel']);self.assertNotIn('source_url',fa['judges'][0]);self.assertIn('no facts about A Story',fa['note'])

    def test_tailor_and_coach_read_the_brief(self):
        oid=self.program();ws=WinScout(self.s);ws.save(oid,brief());lab=PitchLab(self.s)
        it=lab.start_edition(oid,3);prompt,_,stem,_=lab.prompt_for(lab.item(it['id']))
        self.assertEqual(stem,'tailor');self.assertIn('win_brief',prompt);self.assertIn('Pat Judge',prompt);self.assertIn('build the edition to win this exact program',prompt)
        other=lab.start_edition(self.program('Other Prize'),3);p2,_,_,_=lab.prompt_for(lab.item(other['id']))
        self.assertNotIn('Pat Judge',p2)

    def test_weekly_refresh_only_for_programs_in_play(self):
        applied=self.program('Applied Prize');self.h.owner_outcome(applied,'Applied','test')
        skipped=self.program('Skipped Prize');self.h.decide(skipped,'SKIP','not for us')
        ws=WinScout(self.s)
        self.assertEqual(ws.candidates(),[applied])
        self.assertEqual(ws.poll()['queued'],[applied]);self.assertEqual(ws.poll()['queued'],[],'once a week')
        self.assertTrue(ws.brief(applied)['researching']);self.assertTrue(ws.summary()['running'])

    def test_worker_run_requires_the_web_and_saves(self):
        oid=self.program();calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search));self.assertIn('5x5 Night',prompt);self.assertIn('never state facts about A Story',prompt);return brief(),1
        r=win_scout.run(self.h,request(WIN_PREFIX+oid),fake)
        self.assertEqual((r['judges'],r['competitors'],r['moves']),(1,1,2));self.assertEqual(calls,[('win-brief',True)])
        self.assertTrue(win_scout.handles(WIN_PREFIX+'x'));self.assertFalse(win_scout.handles('Scout: Grant'))
        def no_web(h,request,prompt,schema,stem,search=False,timeout=900):return brief(),0
        with self.assertRaises(RuntimeError):win_scout.run(self.h,request(WIN_PREFIX+oid),no_web)


if __name__=='__main__':unittest.main()
