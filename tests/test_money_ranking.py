import unittest
from datetime import datetime,timedelta,timezone
import test_funding_hunter as fixtures
from test_opportunity_curation import brief
from founder_os.hunter_policy import money_profile,date_info
from founder_os.opportunity_curation import shortlist


class MoneyRankingTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record

    def curated(self,name,kind='pitch_competition',days=30,priority='CORE_PRODUCT',cash=25000,credits=None):
        d=self.record(name);d['organizer']=name+' Organizer';d['opportunity_type']=kind
        d['funding'].update(cash_prize_max=cash,credits_value=credits)
        if credits is not None:d['field_sources']['funding.credits_value']=[d['official_url']]
        d['dates'].update(deadline=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat())
        d['founder_brief']=brief(d['official_url']);d['founder_brief']['priority']=priority
        return self.h.upsert(d)['opportunity_id']

    def test_credits_are_never_cash(self):
        self.assertEqual(money_profile({'opportunity_type':'credits_grant','funding':{'cash_prize_max':None,'credits_value':5000}})['kind'],'CREDITS')
        self.assertEqual(money_profile({'opportunity_type':'pitch_competition','funding':{'cash_prize_max':None,'credits_value':None}})['kind'],'CASH')
        self.assertEqual(money_profile({'opportunity_type':'accelerator','funding':{'cash_prize_max':100000,'equity_required':True}})['kind'],'INVESTMENT')

    def test_estimate_is_midpoint_not_upper_bound(self):
        oid=self.curated('Unrated Program');sc=self.h.detail(oid)['analysis']['scoring']
        self.assertEqual(sc['estimate'],sc['score'] if sc['score'] is not None else round((sc['lower_bound']+sc['upper_bound'])/2,1))

    def test_closing_cash_beats_core_product_credits(self):
        credit_ids=[self.curated('Credit '+str(i),kind='credits_grant',days=200,cash=None,credits=5000) for i in range(5)]
        closing=self.curated('Closing Competition',days=2,priority='EXPLORATORY')
        selected=[d['opportunity_id'] for d in shortlist([self.h.detail(i) for i in credit_ids+[closing]])]
        self.assertEqual(selected[0],closing)

    def test_money_board_separates_cash_credits_and_tracked(self):
        cash=self.curated('Cash Prize');credit=self.curated('Voice Credits',kind='credits_grant',cash=None,credits=1000)
        done=self.curated('Already Rejected')
        self.h.outcome(done,'Rejected','Owner meeting notes',source_version_id=self.src)
        board=self.h.dashboard()['money_board']
        self.assertEqual([d['opportunity_id'] for d in board['cash']],[cash])
        self.assertEqual([d['opportunity_id'] for d in board['credits']],[credit])
        self.assertEqual([t['outcome'] for t in board['tracked']],['Rejected'])

    def test_date_only_deadline_uses_local_day(self):
        # 8:55 PM Eastern on Oct 14 is already Oct 15 in UTC; an Oct 15 deadline is still tomorrow.
        evening=datetime(2026,10,15,0,55,tzinfo=timezone.utc)
        self.assertEqual(date_info('2026-10-15',None,evening)['days_remaining'],1)
        self.assertEqual(date_info('2026-10-15','America/Los_Angeles',evening)['days_remaining'],1)


if __name__=='__main__':unittest.main()
