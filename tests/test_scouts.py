import json
import os
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os import scouts
from founder_os.scouts import Scouts,SCOUTS,INVESTOR_DISCOVERY,SCOUT_PREFIX
from founder_os.growth_desk import GrowthDesk

ET=ZoneInfo('America/New_York')
ROOT=Path(__file__).resolve().parents[1]


def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}


class ScoutTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def test_every_scout_has_its_own_corner(self):
        families=json.loads((ROOT/'funding-search-families.json').read_text(encoding='utf-8'))['families']
        keys=[s['key'] for s in SCOUTS];self.assertEqual(len(keys),len(set(keys)))
        used=[f for s in SCOUTS for f in (s['families'] or ())]
        self.assertEqual(len(used),len(set(used)),'no family belongs to two scouts')
        self.assertTrue(set(used)<=set(families),set(used)-set(families))
        self.assertEqual(set(families)-set(used),{'voice_credits','bootstrap_credits','cloud_credits','creative_credits','ai_tool_credits'},'credit families belong to the Credits Scout')
        self.assertEqual(set(next(s for s in SCOUTS if s['key']=='perks')['families']),{'dev_tool_perks','business_perks','marketing_credits','founder_benefits'})

    def test_uncovered_costs_steer_the_credits_and_perks_scouts(self):
        from founder_os.money_map import classify
        sc=Scouts(self.s);st=sc.stack()
        self.assertEqual(st['monthly_uncovered'],0);self.assertTrue(any(r['item']=='Voice calls' for r in st['items']))
        voice=next(r for r in st['items'] if r['item']=='Voice calls')
        sc.save_cost({'id':voice['id'],'item':'Voice calls','provider':'Cartesia','monthly_usd':'120','covered_by':'Cartesia'})
        st=sc.save_cost({'item':'Email sending','provider':'Resend','monthly_usd':'20'})
        self.assertEqual((st['monthly_covered'],st['monthly_uncovered']),(120.0,20.0))
        families=json.loads((ROOT/'funding-search-families.json').read_text(encoding='utf-8'))['families']
        fam,focus=scouts.apply('Daily free credits discovery',families,self.s)
        self.assertEqual(fam,families,'the credits scan keeps its own rotation');self.assertIn('Email sending (Resend) about $20 a month',focus);self.assertNotIn('Voice calls',focus)
        _,perks=scouts.apply(SCOUT_PREFIX+'Perks',families,self.s);self.assertIn('Perks Scout',perks);self.assertIn('Email sending',perks)
        _,grant=scouts.apply(SCOUT_PREFIX+'Grant',families,self.s);self.assertNotIn('Email sending',grant)
        with self.assertRaises(ValueError):sc.save_cost({'item':'','monthly_usd':'5'})
        sc.delete_cost(next(r['id'] for r in st['items'] if r['item']=='Email sending'));self.assertEqual(sc.stack()['monthly_uncovered'],0)
        perk={'data':{'opportunity_type':'startup_program','canonical_name':'Notion for Startups','organizer':'Notion','notes':'Free plan for startups'},'analysis':{'money':{'kind':'SUPPORT','cash_max':None}}}
        self.assertEqual(classify(perk),'perks')
        cash={'data':{'opportunity_type':'startup_program','canonical_name':'Founders Challenge','organizer':'X','notes':'$10,000 prize for startups'},'analysis':{'money':{'kind':'CASH','cash_max':10000}}}
        self.assertNotEqual(classify(cash),'perks')
        self.assertEqual({s['reason'] for s in SCOUTS if s['key'] in ('competitions','grants','founder_money','accelerators')},{SCOUT_PREFIX+'Competition',SCOUT_PREFIX+'Grant',SCOUT_PREFIX+'Founder Money',SCOUT_PREFIX+'Accelerator'})

    def test_hunter_scout_runs_with_only_its_families_and_focus(self):
        families=json.loads((ROOT/'funding-search-families.json').read_text(encoding='utf-8'))['families']
        fam,focus=scouts.apply(SCOUT_PREFIX+'Grant',families)
        self.assertEqual(set(fam),{'grants','federal_state_grants','agetech','vertical'});self.assertIn('Grant Scout',focus)
        same,none=scouts.apply('Scheduled broad discovery',families)
        self.assertEqual(same,families);self.assertIsNone(none)
        self.assertTrue(scouts.handles(INVESTOR_DISCOVERY));self.assertFalse(scouts.handles(SCOUT_PREFIX+'Grant'))

    def test_poll_queues_each_due_scout_once_a_day(self):
        sc=Scouts(self.s);wed=datetime(2026,10,21,8,20,tzinfo=ET)
        self.assertEqual(sc.poll(wed)['queued'],['founder_money','investors'])
        self.assertEqual(sc.poll(wed)['queued'],['founder_money','investors'],'same keys, no new rows')
        rows=self.s.rows("SELECT reason FROM hunter_requests WHERE reason LIKE 'Scout: %' ORDER BY reason")
        self.assertEqual([r['reason'] for r in rows],['Scout: Founder Money','Scout: Investors'])
        self.assertEqual(sc.poll(datetime(2026,10,21,7,30,tzinfo=ET))['queued'],[],'before the hour nothing is due')
        st=sc.status(wed);by={x['key']:x for x in st['scouts']}
        self.assertTrue(by['investors']['running']);self.assertFalse(by['press']['running'])
        self.assertEqual(by['competitions']['next_run'][:16],'2026-10-22T07:45')
        self.assertEqual(by['grants']['lands_url'],'/money#cat-grants');self.assertIn('schedule',st['broad_sweep'])

    def test_run_now_and_last_run_show_on_the_page(self):
        sc=Scouts(self.s);r=sc.request_run('competitions')
        self.assertEqual(r['state'],'QUEUED')
        self.db=self.s.db;self.db.execute("UPDATE hunter_requests SET state='COMPLETE' WHERE reason=?",('Scout: Competition',))
        last=sc.status()['scouts'][0]['last_run'];self.assertTrue(last and last['at'])
        with self.assertRaises(ValueError):sc.request_run('astrology')

    def test_investor_scout_lands_on_the_deal_board(self):
        calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search));self.assertIn('Michigan and Ohio first',prompt)
            return {'queries':['q'],'targets':[{'name':'Michigan Rise','url':'https://example.org/rise','contact_route':'Application form','region':'Michigan','thesis_fit':'Backs Michigan pre-seed companies.','check_size':'$100,000 to $250,000','stage':'Pre-seed','source_url':'https://example.org/rise/apply'}],'errors':[]},1
        self.assertEqual(scouts.run(self.h,request(INVESTOR_DISCOVERY),fake),{'investors_found':1})
        [d]=[x for x in GrowthDesk(self.s).deals() if x['kind']=='investor']
        self.assertEqual((d['name'],d['stage'],d['source']),('Michigan Rise','FOUND','partner_scout'));self.assertIn('Check size: $100,000 to $250,000',d['angle'])
        self.assertEqual(calls,[('investors',True)])
        self.assertEqual(Scouts(self.s).status()['scouts'][[s['key'] for s in SCOUTS].index('investors')]['last_run']['found'],1)
        def no_web(h,request,prompt,schema,stem,search=False,timeout=900):return {'queries':[],'targets':[],'errors':[]},0
        with self.assertRaises(RuntimeError):scouts.run(self.h,request(INVESTOR_DISCOVERY),no_web)
        self.assertNotIn('angel',GrowthDesk(self.s).discovery_context()['task'].lower(),'Partner Scout no longer hunts investors')


if __name__=='__main__':unittest.main()
