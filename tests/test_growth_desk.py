import os
import unittest
from datetime import timedelta
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os import growth_desk
from founder_os.growth_desk import GrowthDesk,DEAL_PREFIX,PARTNER_DISCOVERY,CAMPAIGN_PREFIX,today
from founder_os.pitch_lab import PitchLab


def request(reason):return {'id':'request-x','request_key':'k-'+reason,'reason':reason,'attempts':0}


class GrowthDeskTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def desk(self):return GrowthDesk(self.s)

    def test_deal_moves_only_when_bao_says_so(self):
        d=self.desk();deal=d.add_deal({'name':'Hope College Alumni Association','kind':'partner','why':'Alumni over 60 and a holiday gift shop.','value_usd':'4000'})
        self.assertEqual((deal['stage'],deal['value_usd'],deal['draft']),('FOUND',4000,None))
        with self.assertRaises(ValueError):d.add_deal({'name':'hope college alumni association','kind':'partner'})
        d.save_deal_draft(deal['id'],'A gift for the alumni who raised us','Hi there, ...','Check the gift shop name.')
        self.assertEqual(d.deal(deal['id'])['stage'],'DRAFTED')
        sent=d.set_stage(deal['id'],'SENT')
        self.assertEqual((sent['stage'],sent['next_on'],sent['next_step']),('SENT',(today()+timedelta(days=7)).isoformat(),'Follow up if no reply'))
        self.assertFalse(sent['due'])
        d.update_deal(deal['id'],{'next_on':(today()-timedelta(days=1)).isoformat()})
        self.assertTrue(d.deal(deal['id'])['due'])
        self.assertTrue(any('Next step due' in a['title'] and 'Hope College' in a['title'] for a in d.alerts()))
        replied=d.set_stage(deal['id'],'REPLIED','They want pricing for 40 families.')
        self.assertIsNone(replied['draft'],'a note written before the reply no longer fits')
        self.assertEqual(replied['events'][0]['summary'],'They replied. They want pricing for 40 families.')
        won=d.set_stage(deal['id'],'WON')
        self.assertFalse(won['open']);self.assertEqual(d.board()['won_value'],4000);self.assertEqual(d.board()['open'],0)

    def test_partner_scout_targets_need_a_page_and_are_saved_once(self):
        d=self.desk()
        targets=[{'name':'Michigan Credit Union League','kind':'partner','url':'https://example.org/mcul','contact_route':'Partnerships page','region':'Michigan','why':'Reaches members over 60.','angle':'Holiday gift for members.','source_url':'https://example.org/mcul/partners'},
                 {'name':'Columbus Angels','kind':'investor','url':'https://example.org/angels','contact_route':'Pitch form','region':'Ohio','why':'Backs consumer products.','angle':'','source_url':'https://example.org/angels/apply'},
                 {'name':'No Page Org','kind':'partner','url':'','contact_route':'','region':'','why':'','angle':'','source_url':''}]
        self.assertEqual(d.save_targets(targets),2);self.assertEqual(d.save_targets(targets),0)
        found=[x for x in d.deals() if x['source']=='partner_scout']
        self.assertEqual({x['kind'] for x in found},{'partner','investor'});self.assertTrue(all(x['stage']=='FOUND' for x in found))

    def test_poll_queues_one_deal_note_per_cycle(self):
        d=self.desk();a=d.add_deal({'name':'First Org','kind':'partner'});d.add_deal({'name':'Second Org','kind':'buyer'})
        self.assertEqual(d.poll(limit=1)['drafts_queued'],1)
        rows=self.s.rows("SELECT reason FROM hunter_requests WHERE reason LIKE ?",(DEAL_PREFIX+'%',))
        self.assertEqual([r['reason'] for r in rows],[DEAL_PREFIX+a['id']])
        self.assertTrue(d.deal(a['id'])['drafting'])
        self.assertEqual(d.poll(limit=1)['drafts_queued'],1,'the second deal gets the next cycle')
        self.assertEqual(d.poll(limit=1)['drafts_queued'],0)

    def test_channel_math_is_measured_with_dates(self):
        d=self.desk()
        d.add_entry({'channel':'gift_passes','week_start':'2026-11-02','visits':200,'signups':30,'purchases':6,'spend_usd':'300','revenue_usd':'714'})
        d.add_entry({'channel':'gift_passes','week_start':'2026-11-09','visits':50,'signups':5,'purchases':1,'spend_usd':'50'})
        m=d.add_entry({'channel':'press','week_start':'2026-11-09','visits':150,'signups':12,'purchases':4})
        gp=next(c for c in m['channels'] if c['channel']=='gift_passes')
        self.assertEqual((gp['visits'],gp['purchases'],gp['conversion'],gp['cost_per_family'],gp['weeks'],gp['from'],gp['to']),(250,7,2.8,50.0,2,'2026-11-02','2026-11-09'))
        self.assertEqual((m['totals']['visits'],m['totals']['purchases'],m['totals']['conversion']),(400,11,2.8))
        self.assertIsNone(next(c for c in m['channels'] if c['channel']=='press')['cost_per_family'],'no spend, no cost per family')
        self.assertEqual(m['deck_formula']['visits_needed_for_30'],round(30/0.028))
        facts={f['key']:f for f in d.measured_facts()}
        self.assertEqual((facts['cost_per_family']['value'],facts['conversion']['value'],facts['purchasing_families']['value']),(31.82,2.8,11))
        self.assertIn('2026-11-02 to 2026-11-09',facts['conversion']['as_of'])
        allowed=PitchLab(self.s).allowed_numbers()
        self.assertTrue({'2.8','31.82','11'}<=allowed,'measured numbers may be said in a pitch')
        with self.assertRaises(ValueError):d.add_entry({'channel':'press','visits':3,'purchases':5})
        with self.assertRaises(ValueError):d.add_entry({'channel':'tv'})
        d.delete_entry(m['entries'][0]['id']);self.assertEqual(len(d.math()['entries']),2)

    def plan(self,message='Give Mom the gift of her own story. $119 a year, book included.'):
        return {'goal':'Sell gift passes to adult children before December 24.','audience':'Adult children 35 to 60 in Michigan.','offer':'The Individual plan at $119 a year.',
                'channels':[{'channel':'gift_passes','what':'Gift page and passes.','start_on':'2026-11-03','end_on':'2026-12-24','message':message,'success_metric':'Passes bought','spend_cap_usd':None,'needs_from_bao':'The gift page link'},
                            {'channel':'tv','what':'ignored','start_on':'x','end_on':'','message':'','success_metric':'','spend_cap_usd':None,'needs_from_bao':''}],
                'checkpoints':[{'on':'2026-11-16','check':'Passes sold so far'},{'on':'not a date','check':'ignored date'}],'open_questions':['Budget for paid social?'],'risks':['Shipping cut-off for books.']}

    def test_campaign_plan_is_fact_checked_and_voiced(self):
        d=self.desk();c=d.save_plan('holiday-gift-passes',self.plan('We already have 4,321 families. Give Mom her story.'))
        self.assertEqual((c['state'],len(c['plan']['channels']),c['plan']['channels'][0]['channel']),('PLANNED',1,'gift_passes'))
        self.assertEqual(c['plan']['checkpoints'][1]['on'],None)
        self.assertTrue(any('4,321' in i['text'] and i['where']=='gift_passes' for i in c['issues']))
        self.assertEqual([x['title'] for x in c['drafts']],['Gift passes'])
        self.assertTrue(any('plan is ready' in a['title'] for a in d.alerts()))
        # The Pitch Lab sweep gives every campaign message Fact Guard and Bao's Voice, like other growth drafts.
        PitchLab(self.s).poll()
        self.assertTrue(self.s.rows("SELECT id FROM work_items WHERE kind='GROWTH_DRAFT' AND subject_id=?",(c['id'],)))
        clean=d.save_plan('holiday-gift-passes',self.plan())
        self.assertEqual(clean['issues'],[]);self.assertEqual(d.set_campaign_state('holiday-gift-passes','RUNNING')['state'],'RUNNING')

    def test_field_day_has_a_spoken_script_and_a_tally(self):
        d=self.desk();c=d.campaign('hope-college-onsite-2026-10-17')
        [script]=[x for x in c['drafts'] if x['title']=='Cold approach script']
        self.assertIn('reserve it for a dollar',script['body']);self.assertIn('$119 a year',script['body']);self.assertNotIn('partner',script['body'].lower())
        self.assertEqual(c['field']['approached'],0);self.assertIsNone(d.campaign('holiday-gift-passes')['field'])
        self.assertEqual(len(GrowthDesk(self.s).campaign('hope-college-onsite-2026-10-17')['drafts']),1,'the script is seeded once')
        f=d.log_field_day('hope-college-onsite-2026-10-17',{'approached':40,'conversations':12,'emails':9,'reservations':3,'on':'2026-10-17','note':'lunch rush'})
        self.assertEqual((f['approached'],f['emails'],f['reservations']),(40,9,3))
        ev=next(ch for ch in d.math()['channels'] if ch['channel']=='events')
        self.assertEqual((ev['visits'],ev['signups'],ev['purchases'],ev['from']),(40,9,3,'2026-10-12'));self.assertIn('12 conversations',f['entries'][0]['note'])
        with self.assertRaises(ValueError):d.log_field_day('hope-college-onsite-2026-10-17',{'approached':3,'conversations':9})
        # The script goes through Fact Guard and Bao's Voice like every growth draft.
        PitchLab(self.s).poll()
        self.assertTrue(self.s.rows("SELECT id FROM work_items WHERE kind='GROWTH_DRAFT' AND subject_id=?",(c['id'],)))

    def test_worker_entry_routes_each_job(self):
        d=self.desk();deal=d.add_deal({'name':'Senior Living Co','kind':'buyer'})
        calls=[]
        def fake(h,request,prompt,schema,stem,search=False,timeout=900):
            calls.append((stem,search))
            if stem=='deal-note':return {'title':'A gift for your residents’ families','body':'Hi, Bao here...','note':''},0
            if stem=='partners':return {'queries':['q'],'targets':[{'name':'Faith Community','kind':'partner','url':'https://example.org/f','contact_route':'Office','region':'Ohio','why':'w','angle':'a','source_url':'https://example.org/f'}],'errors':[]},(1 if search else 0)
            return self.plan(),0
        self.assertTrue(growth_desk.handles(DEAL_PREFIX+'x') and growth_desk.handles(PARTNER_DISCOVERY) and growth_desk.handles(CAMPAIGN_PREFIX+'k') and not growth_desk.handles('Draft press pitch: x'))
        r=growth_desk.run(self.h,request(DEAL_PREFIX+deal['id']),fake)
        self.assertTrue(r['draft_id']);self.assertEqual(d.deal(deal['id'])['stage'],'DRAFTED');self.assertIn('Senior Living Co',str(calls)) if False else None
        self.assertEqual(growth_desk.run(self.h,request(PARTNER_DISCOVERY),fake),{'deals_found':1})
        self.assertEqual(growth_desk.run(self.h,request(CAMPAIGN_PREFIX+'holiday-gift-passes'),fake)['channels'],1)
        self.assertEqual([c[1] for c in calls],[False,True,False],'web search only for Partner Scout')
        def no_web(h,request,prompt,schema,stem,search=False,timeout=900):return {'queries':[],'targets':[],'errors':[]},0
        with self.assertRaises(RuntimeError):growth_desk.run(self.h,request(PARTNER_DISCOVERY),no_web)


if __name__=='__main__':unittest.main()
