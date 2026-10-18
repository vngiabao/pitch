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
    return {'title':'Convert the five waiting families before Columbus','bottom_line':'Five families are waiting to pay. Convert them this week, then pitch Columbus with a real number. Everything else waits on two decisions only you can make.',
            'moves':[{'what':'Call the five waiting families','by':'today','owner':'Bao','why':'First paying families'},{'what':'Pitch in Columbus','by':'Fri Oct 24','owner':'Bao','why':''},
                     {'what':'Finish the gift page','by':'this week','owner':'Daniel','why':'Gift passes need it'},{'what':'Fourth move is dropped','by':'','owner':'Bao','why':''}],
            'decisions':[{'decision':'What group price for employers?','recommend':'needs your input','unblocks':'Partner proposals'}],
            'numbers':[{'label':'Open cash programs','value':'5','source':'Today brief'},{'label':'Deals in play','value':'$4,000','source':'Deals board'}],
            'by_agent':[{'agent':'Investor Scout','result':'7 funds found, check sizes unverified','needs':'Pick which to approach'}],
            'risks':['No measured retention number before Friday'],'later':[{'what':'Scouts keep searching','by':'daily','owner':'nobody'}]}


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
        self.assertEqual((out['title'],out['moves'],out['decisions'],calls),('Convert the five waiting families before Columbus',3,1,[('plan',False)]))
        saved=pl.report(r['id']);self.assertEqual(saved['state'],'READY');self.assertEqual(saved['report']['later'][0]['owner'],'Bao','an unknown owner falls back to Bao')
        page=Path(saved['html_path']).read_text(encoding='utf-8')
        for c in (THEME['navy'],THEME['paper'],THEME['brass']):self.assertIn(c,page)
        self.assertIn('Brygada 1918',page);self.assertIn('Mona Sans',page);self.assertIn('Call the five waiting families',page);self.assertIn('What group price for employers?',page);self.assertNotIn('Fourth move',page,'three moves at most')
        self.assertIsNone(saved['pdf_url'],'PDF rendering is off in tests');self.assertTrue(saved['html_url'])
        lst=pl.reports();self.assertEqual(lst['latest']['id'],r['id']);self.assertFalse(lst['writing'])
        self.assertEqual(pl.latest_for_brief()['title'],'Convert the five waiting families before Columbus')

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

    def test_sources_read_as_desks_not_field_paths(self):
        from founder_os.planner import clean
        c=clean({'title':'x','bottom_line':'Zero reservations, per state.reservation_drive.counts.reserved.','numbers':[{'label':'Open','value':'5','source':'state.growth.channel_math.totals'}]})
        self.assertEqual(c['bottom_line'],'Zero reservations, per Reservation drive.');self.assertEqual(c['numbers'][0]['source'],'Channel math')

    def test_every_line_has_a_word_limit(self):
        from founder_os.planner import clean,words
        long=' '.join(['word']*80)
        c=clean({'title':'One two three four five six seven eight nine ten eleven','bottom_line':'First sentence is short. '+long,'moves':[{'what':long,'by':'today','owner':'Bao','why':long}]})
        self.assertLessEqual(len(c['title'].split()),9);self.assertEqual(c['bottom_line'],'First sentence is short.')
        self.assertLessEqual(len(c['moves'][0]['what'].split()),16);self.assertTrue(c['moves'][0]['what'].endswith('…'))
        self.assertEqual(words('Short.',5),'Short.')

    def test_agent_names_match_the_scouts_page(self):
        from founder_os.planner import agent_name
        self.assertEqual([agent_name(x) for x in ('Scout: Competition','Scout: Founder Money','Daily free credits discovery','Win brief: opp-1','Draft deal note: deal-1','Due program re-verifications','Pipeline: work-1')],
                         ['Competition Scout','Founder Money Scout','Credits Scout','Win Scout','Deal Drafter','Funding Hunter',''])

    def test_render_escapes_and_handles_empty_sections(self):
        page=render_html({'title':'<b>x</b>','bottom_line':'','moves':[],'decisions':[],'numbers':[],'by_agent':[],'risks':[],'later':[]},'q <script>',datetime(2026,10,16,tzinfo=ET))
        self.assertIn('&lt;b&gt;x&lt;/b&gt;',page);self.assertNotIn('<script>',page);self.assertNotIn('This week',page);self.assertNotIn('By agent',page)


if __name__=='__main__':unittest.main()
