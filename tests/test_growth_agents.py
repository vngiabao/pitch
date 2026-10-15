import unittest
from datetime import date,timedelta
import test_funding_hunter as fixtures
from founder_os.growth_agents import Growth,add_months,today,FOLLOWUP_PREFIX,PRESS_DISCOVERY


class GrowthTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record

    def credit_program(self,name='Voice Startups Grant',provider='VoiceCo'):
        d=self.record(name);d['opportunity_type']='credits_grant'
        d['credit_benefits'].update(provider=provider,eligible_products='Speech APIs',expiration_months=12,renewal_behavior='$299/month after the grant unless cancelled.')
        d['funding'].update(award_scope='8M units monthly for twelve months.',cash_prize_max=None,cash_prize_min=None)
        url=d['sources'][0]['url']
        for f in ('funding.award_scope','credit_benefits.provider','credit_benefits.eligible_products','credit_benefits.expiration_months','credit_benefits.renewal_behavior'):d['field_sources'][f]=[url]
        return self.h.upsert(d)['opportunity_id']

    def test_add_months_clamps_month_end(self):
        self.assertEqual(add_months(date(2026,1,31),1),date(2026,2,28))
        self.assertEqual(add_months(date(2026,10,15),12),date(2027,10,15))

    def test_accepted_credit_program_becomes_tracked_grant_without_dates(self):
        oid=self.credit_program();g=Growth(self.s)
        self.assertEqual(g.credits(),[])
        self.h.owner_outcome(oid,'Accepted','test')
        [c]=g.credits()
        self.assertEqual((c['provider'],c['level'],c['term_months']),('VoiceCo','NEEDS_DATES',12))
        self.assertIn('$299',c['after_expiry'])
        self.assertEqual(len(g.credits()),1)  # sync is idempotent
        self.assertTrue(any('VoiceCo' in a['title'] and a['url']=='/credits' for a in g.alerts()))

    def test_credit_levels_follow_the_end_date(self):
        oid=self.credit_program();self.h.owner_outcome(oid,'Accepted','test');g=Growth(self.s);cid=g.credits()[0]['id']
        start=add_months(today(),-12)+timedelta(days=10)
        c=g.update_credit(cid,{'started_on':start.isoformat()})
        self.assertEqual(c['level'],'URGENT');self.assertEqual(c['days_left'],10)
        c=g.update_credit(cid,{'expires_on':(today()+timedelta(days=30)).isoformat()})
        self.assertEqual(c['level'],'SOON')
        c=g.update_credit(cid,{'expires_on':(today()+timedelta(days=200)).isoformat(),'balance_note':'6M of 8M'})
        self.assertEqual(c['level'],'OK');self.assertEqual(c['balance_checked_on'],today().isoformat())
        self.assertEqual(g.update_credit(cid,{'state':'USED_UP'})['level'],'DONE')
        with self.assertRaises(ValueError):g.update_credit(cid,{'started_on':'next week'})

    def test_touch_schedules_next_followup_and_drops_stale_draft(self):
        g=Growth(self.s);c=g.add_contact({'name':'Hope College','kind':'Partner','next_followup_on':today().isoformat(),'cadence_days':10})
        self.assertTrue(c['due'])
        self.assertTrue(any('Hope College' in a['title'] for a in g.alerts()))
        g.poll(limit=1)
        self.assertTrue(self.s.db.execute('SELECT 1 FROM hunter_requests WHERE reason=?',(FOLLOWUP_PREFIX+c['id'],)).fetchone())
        g.save_draft('contact',c['id'],'Hello','Body text')
        self.assertEqual(g.contact(c['id'])['draft']['body'],'Body text')
        c=g.log_touch(c['id'],{'summary':'Sent the follow-up email.'})
        self.assertEqual(c['next_followup_on'],(today()+timedelta(days=10)).isoformat())
        self.assertFalse(c['due']);self.assertIsNone(c['draft'])
        with self.assertRaises(ValueError):g.log_touch(c['id'],{'summary':''})
        with self.assertRaises(ValueError):g.add_contact({'name':'X','kind':'Boss'})

    def test_press_targets_dedupe_and_skip_past_deadlines(self):
        g=Growth(self.s);soon=(today()+timedelta(days=5)).isoformat()
        t={'outlet':'Example Gift Guide','kind':'gift_guide','url':'https://example.org/gifts','source_url':'https://example.org/gifts','deadline':soon,'angle':'Gifts for parents'}
        self.assertEqual(g.save_targets([t,dict(t),{**t,'outlet':'Old Guide','deadline':'2020-01-01'},{**t,'outlet':'No Source','url':'javascript:x','source_url':''}]),1)
        self.assertEqual(g.save_targets([{**t,'angle':'Updated angle'}]),0)
        [row]=g.press()['targets'];self.assertEqual(row['angle'],'Updated angle');self.assertEqual(row['days_left'],5)
        self.assertTrue(any('Example Gift Guide' in a['title'] for a in g.alerts()))
        g.set_press_state(row['id'],'PITCHED')
        self.assertFalse(any('Example Gift Guide' in a['title'] for a in g.alerts()))
        with self.assertRaises(ValueError):g.set_press_state(row['id'],'SENT_BY_AGENT')

    def test_press_discovery_requests_are_idempotent_per_key(self):
        g=Growth(self.s);g.request_press_discovery('press-test');g.request_press_discovery('press-test')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM hunter_requests WHERE reason=?',(PRESS_DISCOVERY,)).fetchone()[0],1)


if __name__=='__main__':unittest.main()
