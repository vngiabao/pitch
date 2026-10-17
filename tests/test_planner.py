import os
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
os.environ.setdefault('FOUNDER_OS_PDF','off')
import test_funding_hunter as fixtures
from founder_os import planner
from founder_os.planner import Planner,PLAN_PREFIX,DEFAULT_QUESTION,render_html,THEME

ET=ZoneInfo('America/New_York')


def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}


def report():
    return {'title':'Launch week: five families first','answer':['Five families are waiting. Convert them before anything else.','The Columbus finale is Friday; the deck is ready.'],
            'plan':[{'when':'Today','what':'Call the five waiting families','why':'First paying families','owner':'Bao','link':'https://pitch.gbaonvo.com/growth'},{'when':'Fri Oct 24','what':'Pitch in Columbus','why':'','owner':'Bao','link':''},{'when':'This week','what':'Finish the gift page','why':'Gift passes need it','owner':'Daniel','link':''},{'when':'Daily','what':'Scouts keep searching','why':'','owner':'nobody','link':''}],
            'numbers':[{'label':'Open cash programs','value':'5','source':'Today'},{'label':'Deals in play','value':'$4,000','source':'Deals board'}],
            'questions_for_bao':['What group price for employers?'],'risks':['No measured retention number before Friday']}


class PlannerTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def test_gather_survives_an_empty_desk(self):
        st=Planner(self.s).gather()
        self.assertIn('today',st);self.assertIn('today_brief',st);self.assertIn('growth',st);self.assertIn('scouts',st)
        self.assertEqual(st['gather_errors'],[],st['gather_errors'])

    def test_ask_queues_and_a_report_is_saved_in_the_turn(self):
        pl=Planner(self.s);r=pl.ask('  ')
        self.assertEqual((r['state'],r['question']),('QUEUED',DEFAULT_QUESTION))
        self.assertTrue(self.s.db.execute("SELECT 1 FROM hunter_requests WHERE reason=?",(PLAN_PREFIX+r['id'],)).fetchone())
        self.assertTrue(pl.reports()['writing'])
        calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search));self.assertIn('Planner for A Story',prompt);self.assertIn(DEFAULT_QUESTION,prompt);return report(),0
        out=planner.run(self.h,request(PLAN_PREFIX+r['id']),fake)
        self.assertEqual((out['title'],out['plan_steps'],calls),('Launch week: five families first',4,[('plan',False)]))
        saved=pl.report(r['id']);self.assertEqual(saved['state'],'READY');self.assertEqual(saved['report']['plan'][3]['owner'],'Bao','an unknown owner falls back to Bao')
        page=Path(saved['html_path']).read_text(encoding='utf-8')
        for c in (THEME['navy'],THEME['paper'],THEME['brass']):self.assertIn(c,page)
        self.assertIn('Brygada 1918',page);self.assertIn('Mona Sans',page);self.assertIn('Call the five waiting families',page);self.assertIn('What group price for employers?',page)
        self.assertIsNone(saved['pdf_url'],'PDF rendering is off in tests');self.assertTrue(saved['html_url'])
        lst=pl.reports();self.assertEqual(lst['latest']['id'],r['id']);self.assertFalse(lst['writing'])
        self.assertEqual(pl.latest_for_brief()['title'],'Launch week: five families first')

    def test_failure_is_recorded_not_hidden(self):
        pl=Planner(self.s);r=pl.ask('Why?')
        def boom(h,request,prompt,schema,stem,search=False,timeout=900):raise RuntimeError('Runner failed: offline')
        with self.assertRaises(RuntimeError):planner.run(self.h,request(PLAN_PREFIX+r['id']),boom)
        self.assertEqual(pl.report(r['id'])['state'],'FAILED');self.assertIn('offline',pl.report(r['id'])['error'])

    def test_weekly_plan_writes_itself_once(self):
        pl=Planner(self.s);mon=datetime(2026,10,19,7,10,tzinfo=ET)
        self.assertFalse(pl.poll(datetime(2026,10,18,9,0,tzinfo=ET))['queued'],'not on Sunday')
        self.assertTrue(pl.poll(mon)['queued']);self.assertFalse(pl.poll(mon)['queued'])
        self.assertEqual(pl.reports()['items'][0]['auto'],1)

    def test_render_escapes_and_handles_empty_sections(self):
        page=render_html({'title':'<b>x</b>','answer':[],'plan':[],'numbers':[],'questions_for_bao':[],'risks':[]},'q <script>',datetime(2026,10,16,tzinfo=ET))
        self.assertIn('&lt;b&gt;x&lt;/b&gt;',page);self.assertNotIn('<script>',page);self.assertNotIn('The plan',page)


if __name__=='__main__':unittest.main()
