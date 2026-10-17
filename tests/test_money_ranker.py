import os,unittest
from datetime import datetime,timedelta,timezone
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from test_application_drafter import FORM,FakeReader
from founder_os.form_reader import parse
from founder_os.money_ranker import rank,value_of,likelihood,urgency,pitch_minutes,MoneyRanker,brief_rows,DEFAULT_HOURS,CREDIT_DISCOUNT
from founder_os.application_drafter import DRAFT_PREFIX


def item(name,cash=25000,credits=None,fit=70,eligibility='ELIGIBLE',hours=2,days=30,recommendation='APPLY NOW',status='OPEN',kind=None,program=None,decisions=(),outcomes=()):
    kind=kind or ('CASH' if cash else 'CREDITS')
    return {'opportunity_id':'opp-'+name.lower().replace(' ','-'),'program_id':program or 'prog-'+name.lower().replace(' ','-'),'fit_score':fit,'recommendation':recommendation,
            'decisions':list(decisions),'outcomes':list(outcomes),
            'data':{'canonical_name':name,'status':status,'opportunity_type':'pitch_competition','notes':'','requirements':[],'eligibility':{},'dates':{'deadline':'2026-11-30'}},
            'analysis':{'money':{'kind':kind,'cash_max':cash,'credits_face_value':credits,'rank':3},'eligibility':{'status':eligibility},
                        'materials':{'estimated_hours':hours},'scoring':{'estimate':fit if fit is not None else 60,'dates':{'days_remaining':days,'expired':days is not None and days<0}}}}


class RankingMathTests(unittest.TestCase):
    def test_every_component_is_shown_and_multiplied(self):
        v=value_of(item('Cash Cup',cash=25000,fit=70,hours=2,days=7))
        self.assertEqual(v['money']['counted'],25000);self.assertEqual(v['money']['basis'],'cash prize max')
        self.assertEqual(v['likelihood']['value'],0.3);self.assertEqual(v['likelihood']['eligibility_factor'],1.0)
        self.assertEqual(v['hours']['value'],2);self.assertTrue(v['hours']['known'])
        self.assertEqual(v['urgency']['factor'],1.5)
        self.assertEqual(v['expected_value'],7500);self.assertEqual(v['per_hour'],5625)
        self.assertTrue(v['estimate']);self.assertIn('estimate',v['label'].lower())
        self.assertIn('$25,000 x 30% likelihood (fit 70, eligible) / 2 hours estimated, x1.5 for closing in 7 days.',v['reason'])

    def test_credits_count_at_a_quarter_and_unknowns_use_defaults(self):
        v=value_of(item('Voice Credits',cash=None,credits=10000,fit=None,eligibility='ELIGIBILITY UNKNOWN',hours=None,days=None))
        self.assertEqual(v['money']['counted'],10000*CREDIT_DISCOUNT);self.assertIn('25 percent',v['money']['basis'])
        self.assertEqual(v['hours']['value'],DEFAULT_HOURS);self.assertFalse(v['hours']['known'])
        self.assertEqual(v['likelihood']['eligibility_factor'],0.5);self.assertFalse(v['likelihood']['fit_known'])
        self.assertEqual(v['urgency']['factor'],1.0)
        self.assertEqual(v['likelihood']['value'],likelihood(60,'ELIGIBILITY UNKNOWN')[0])
        self.assertEqual(v['per_hour'],round(2500*v['likelihood']['value']/3,2))

    def test_likelihood_and_urgency_curves(self):
        self.assertEqual(likelihood(100,'ELIGIBLE')[0],0.6);self.assertEqual(likelihood(40,'ELIGIBLE')[0],0.012);self.assertEqual(likelihood(70,'ELIGIBILITY UNKNOWN')[0],0.15)
        self.assertEqual(urgency(0),2.0);self.assertEqual(urgency(14),1.0);self.assertEqual(urgency(15),1.0);self.assertEqual(urgency(None),1.0)

    def test_rank_orders_by_dollars_per_hour_and_skips_applied_closed_and_unpriced(self):
        items=[item('Slow Grant',cash=100000,fit=70,hours=40,days=60),              # 30000 / 40 = 750/h
               item('Quick Night',cash=5000,fit=70,hours=1,days=3),                 # 1500 x 1.79 = 2678/h
               item('Applied Already',cash=50000,recommendation='ALREADY APPLIED'),
               item('Closed One',cash=50000,status='CLOSED'),
               item('Bao Skipped',cash=50000,decisions=[{'decision':'SKIP'}]),
               item('Not Eligible',cash=50000,eligibility='INELIGIBLE'),
               item('Mystery Prize',cash=None,credits=None,kind='CASH'),
               item('Same Program Later Cycle',cash=5000,fit=70,hours=1,days=3,program='prog-quick-night')]
        rows,unpriced=rank(items)
        self.assertEqual([r['name'] for r in rows],['Quick Night','Slow Grant'])
        self.assertEqual([u['name'] for u in unpriced],['Mystery Prize'])
        self.assertEqual(rank(items,limit=1)[0][0]['name'],'Quick Night')

    def test_pitch_minutes_reads_the_program_text(self):
        self.assertEqual(pitch_minutes({'notes':'Finalists give a 5-minute pitch followed by Q&A.','requirements':[]}),5)
        self.assertEqual(pitch_minutes({'notes':'Applications close in 10 minutes of reading time.','requirements':[]}),3)
        self.assertEqual(pitch_minutes({'notes':'','requirements':[{'kind':'deck','label':'Deck for a 90 second pitch'}]}),3)
        self.assertEqual(pitch_minutes({'notes':'','requirements':[{'kind':'deck','label':'Pitch presentation, 7 min max'}]}),7)


class PreparationTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record
    approve_fact=fixtures.HunterTests.approve_fact

    def program(self,name,cash=25000,days=20,kind='pitch_competition',notes=''):
        d=self.record(name);d['opportunity_type']=kind;d['notes']=notes
        d['funding'].update(cash_prize_max=cash)
        d['dates'].update(deadline=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat())
        return self.h.upsert(d)['opportunity_id']

    def test_top_carries_preparation_state(self):
        a=self.program('Top Cup',cash=50000,days=5);self.program('Far Grant',cash=20000,days=60,kind='grant')
        rows=MoneyRanker(self.s).top()
        self.assertEqual(rows[0]['opportunity_id'],a);self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['preparation']['form'],'NOT_READ');self.assertEqual(rows[0]['preparation']['next'],'read the form')
        self.assertTrue(rows[0]['pitch']);self.assertFalse(rows[1]['pitch'])
        self.assertIn('/hour',brief_rows(rows,lambda u:'https://os.test'+u)[0]['per_hour_label'])

    def test_prepare_takes_one_action_per_cycle_in_rank_order(self):
        for k,v in (('company_name','A Story Technologies, Inc.'),('team_size',2),('incorporated',True)):self.approve_fact(k,v)
        top=self.program('Top Cup',cash=50000,days=5,notes='Each finalist gives a 5-minute pitch.');second=self.program('Second Cup',cash=10000,days=25)
        r=MoneyRanker(self.s);reader=FakeReader(parse(FORM))
        # Cycle 1: the top program's form is read (and its open questions are queued for the drafter by the reader itself).
        first=r.prepare(reader);self.assertEqual((first['action'],first['opportunity_id']),('read_form',top))
        aid=first['application_id'];self.assertTrue(self.s.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state='QUEUED'",(DRAFT_PREFIX+aid,)).fetchone())
        # Cycle 2: the top program's answers are drafting, so the pitch edition is started with the stated 5 minutes. Nothing is submitted.
        second_action=r.prepare(reader);self.assertEqual((second_action['action'],second_action['opportunity_id'],second_action['minutes']),('start_edition',top,5))
        ed=self.s.db.execute("SELECT stage FROM work_items WHERE kind='PITCH_EDITION' AND opportunity_id=?",(top,)).fetchone();self.assertIsNotNone(ed)
        # Cycle 3: the top program is fully prepared; the second program's form is read next.
        third=r.prepare(reader);self.assertEqual((third['action'],third['opportunity_id']),('read_form',second))
        # If a draft request is lost before the drafter ran, the ranker queues it again.
        self.s.db.execute('DELETE FROM hunter_requests WHERE reason=?',(DRAFT_PREFIX+aid,))
        fourth=r.prepare(reader);self.assertEqual((fourth['action'],fourth['application_id']),('queue_draft',aid))
        # Once drafts exist, there is nothing left to queue for either program except the second one's edition.
        self.s.db.execute('DELETE FROM hunter_requests WHERE reason=?',(DRAFT_PREFIX+aid,))
        drafter=r.drafter;drafter.save_drafts(aid,[{'question_id':q['id'],'answer':'An AI biographer that calls families.','note':''} for q in drafter.open_questions(aid)])
        fifth=r.prepare(reader);self.assertEqual((fifth['action'],fifth['opportunity_id']),('start_edition',second))
        self.assertEqual(r.prepare(reader)['action'],None)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0],0)
        prep=[x for x in r.top() if x['opportunity_id']==top][0]['preparation']
        self.assertEqual(prep['form'],'QUESTIONS_READ');self.assertIsNotNone(prep['edition']);self.assertIsNone(prep['next'])

    def test_prepare_without_a_reader_skips_form_reads(self):
        self.program('Top Cup',cash=50000,days=5)
        self.assertEqual(MoneyRanker(self.s).prepare(None)['action'],None)

    def test_daily_brief_lists_apply_first(self):
        from founder_os.report_email import DailyReporter
        from founder_os.application_pilot import ApplicationPilot
        self.program('Top Cup',cash=50000,days=5)
        p=ApplicationPilot(self.s);p.authorize('daily_email_report',{'recipient':'gbao.n.vo@gmail.com'},'fixture')
        rep=DailyReporter(self.s);rendered=rep.render()
        self.assertIn('APPLY TO THESE FIRST',rendered['body']);self.assertIn('Top Cup',rendered['body']);self.assertIn('/hour',rendered['body'])
        self.assertIn('Apply to these first',rendered['body_html']);self.assertIn('estimate',rendered['body_html'])


if __name__=='__main__':unittest.main()
