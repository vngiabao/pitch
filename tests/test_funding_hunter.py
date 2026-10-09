import copy,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from founder_os.store import Store,now,PolicyError,digest
from founder_os.funding_hunter import FundingHunter,blank_record
from founder_os.hunter_policy import date_info,evaluate_eligibility,score,recommend,WEIGHTS

class HunterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.s=Store(self.path/'test.sqlite');self.h=FundingHunter(self.s)
        self.file=self.path/'evidence.txt';self.file.write_text('Verified company facts and sourced materials',encoding='utf-8')
        self.src=self.s.import_source(self.file,'fixture','REFERENCE',text=self.file.read_text())
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def record(self,name='Example Competition',cycle='2026'):
        d=blank_record();url='https://example.org/program/'+name.lower().replace(' ','-')
        d.update(canonical_name=name,organizer='Example Organizer',opportunity_type='pitch_competition',cycle=cycle,cycle_kind='annual',official_url=url,application_url=url+'/apply',status='OPEN')
        d['sources']=[{'url':url,'role':'official_program','checked_at':now(),'excerpt':'Fixture: current program rules, dates, benefits and application.'}]
        d['field_sources']={k:[url] for k in ('status','cycle_kind','application_url','eligibility_complete','requirements','strategic_matches','network_evidence','probability_estimate','funding.cash_prize_max','funding.equity_required','dates.deadline','dates.timezone')}
        d['funding'].update(cash_prize_max=25000,equity_required=False)
        d['dates'].update(deadline=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat(),timezone='America/New_York')
        d['eligibility_rules']=[{'fact_key':'incorporated','op':'eq','value':True,'description':'Company is incorporated','source_url':url}]
        d['eligibility_complete']=True
        d['strategic_matches']=[{'fact_key':'industry','accepted_values':['consumer_ai']}]
        d['requirements']=[{'kind':'deck','label':'Pitch deck'}]
        d['network_evidence']={k:True for k in ('mentors','investors','alumni','customer_access','public_demo','complete')}
        d['probability_estimate']={'numerator':1,'denominator':10,'note':'Historic fixture base rate'}
        return d
    def approve_fact(self,key,value):
        v=self.s.propose_claim('team','Fixture '+key,json.dumps({key:value}),'verified',self.src,'line 1',last_verified_at=now())
        self.h.attach_fact_value(v,key,value)
        a=self.s.request_approval('promote_claim',{'version_id':v})
        self.s.decide(a,'approved',True)
        return v
    def test_existing_application_links_preserved(self):
        oid=self.s.upsert_opportunity('Michigan Business Challenge','Michigan Business Challenge','2025-2026 historical materials',self.src)
        aid=self.s.create_application(oid,'Original application')
        FundingHunter(self.s)
        d=self.h.detail(oid)
        self.assertEqual(d['applications'][0]['id'],aid)
        self.assertEqual(d['data']['cycle'],'2025-2026')
    def test_new_year_is_new_cycle_not_program(self):
        a=self.h.upsert(self.record(cycle='2026'));b=self.h.upsert(self.record(cycle='2027'))
        self.assertEqual(a['program_id'],b['program_id']);self.assertNotEqual(a['cycle_id'],b['cycle_id'])
    def test_aliases_deduplicate_nvidia(self):
        a=self.record('NVIDIA Inception Program');a['organizer']='NVIDIA';a['official_url']='https://nvidia.com/startups/'
        b=copy.deepcopy(a);b['canonical_name']='NVIDIA for Startups'
        x=self.h.upsert(a);y=self.h.upsert(b)
        self.assertEqual(x['opportunity_id'],y['opportunity_id']);self.assertFalse(y['created'])
    def test_domain_does_not_merge_distinct_programs(self):
        a=self.h.upsert(self.record('AWS Activate'));b=self.h.upsert(self.record('AWS Generative AI Accelerator'))
        self.assertNotEqual(a['program_id'],b['program_id'])
    def test_possible_duplicate_requires_review(self):
        self.h.upsert(self.record('Consumer Innovation Challenge'))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SUSPECTED'):self.h.upsert(self.record('Consumer Innovation Challenges'))
    def test_aggregator_cannot_verify_deadline(self):
        d=self.record();d['sources'][0]['role']='directory'
        with self.assertRaisesRegex(ValueError,'official provenance'):self.h.upsert(d)
    def test_unknown_company_facts_do_not_become_true(self):
        r=self.h.upsert(self.record());d=self.h.detail(r['opportunity_id'])
        self.assertEqual(d['analysis']['eligibility']['status'],'ELIGIBILITY UNKNOWN')
        self.assertIsNone(d['fit_score']);self.assertEqual(d['recommendation'],'REVIEW')
        self.assertIsNone(d['analysis']['scoring']['components']['eligibility']['points'])
    def test_proposed_fact_cannot_qualify_company(self):
        v=self.s.propose_claim('team','Incorporation','Incorporated','reported',self.src,'line 1',last_verified_at=now())
        self.h.attach_fact_value(v,'incorporated',True)
        self.assertNotIn('incorporated',self.h.company_memory()['attributes'])
    def test_canonical_fact_is_bound_to_approval(self):
        v=self.s.propose_claim('team','Incorporation','Incorporated','verified',self.src,'line 1',last_verified_at=now())
        self.h.attach_fact_value(v,'incorporated',True)
        self.s.request_approval('promote_claim',{'version_id':v})
        with self.assertRaises(Exception):self.h.attach_fact_value(v,'us_company',True)
        with self.assertRaises(Exception):self.s.db.execute('UPDATE company_fact_values SET value_json=\'false\'')
    def test_stale_source_invalidates_structured_facts(self):
        self.approve_fact('incorporated',True)
        self.file.write_text('Changed source evidence')
        self.s.import_source(self.file,'fixture','REFERENCE',text='Changed source evidence')
        self.assertNotIn('incorporated',self.h.company_memory()['attributes'])
    def test_ineligible_overrides_score(self):
        self.approve_fact('incorporated',False);self.approve_fact('industry','consumer_ai')
        r=self.h.upsert(self.record())
        self.assertEqual(r['recommendation'],'SKIP')
    def test_weights_sum_to_100_and_immutable_version(self):
        self.assertEqual(sum(WEIGHTS.values()),100)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM scoring_versions').fetchone()[0],1)
    def test_prize_pool_not_assumed_single_company_award(self):
        d=self.record();d['funding']['cash_prize_max']=None;d['funding']['award_scope']='Total program pool $200000, single-company prize not established'
        d['field_sources']['funding.award_scope']=[d['official_url']]
        r=self.h.upsert(d)
        self.assertIsNone(self.h.detail(r['opportunity_id'])['analysis']['scoring']['components']['value']['points'])
    def test_credit_value_requires_real_use(self):
        d=self.record();d['funding'].update(cash_prize_max=None,credits_value=350000)
        d['field_sources']['funding.credits_value']=[d['official_url']]
        r=self.h.upsert(d)
        self.assertIsNone(self.h.detail(r['opportunity_id'])['analysis']['scoring']['components']['value']['points'])
    def test_date_only_does_not_invent_time(self):
        today=datetime.now(timezone.utc).date().isoformat()
        r=date_info(today)
        self.assertFalse(r['expired']);self.assertEqual(r['precision'],'date_only');self.assertEqual(r['days_remaining'],0)
    def test_missing_timezone_exact_deadline_not_urgent(self):
        self.assertEqual(date_info('2026-10-05T10:00:00')['urgency'],'DEADLINE UNKNOWN')
    def test_expired_overrides_unknown_eligibility(self):
        d=self.record();d['dates']['deadline']='2025-01-01'
        self.assertEqual(self.h.upsert(d)['recommendation'],'EXPIRED')
    def test_old_deck_is_adaptation_not_ready(self):
        self.s.db.execute('INSERT INTO material_registry VALUES(?,?,?, ?,\'draft\',\'[]\',NULL)',('m1',self.src,'deck','Old deck'))
        r=self.h.material_readiness(self.record())
        self.assertEqual(r['percentage'],0);self.assertEqual(len(r['needs_adaptation']),1)
    def test_unknown_requirements_do_not_get_zero_or_100_readiness(self):
        self.assertIsNone(self.h.material_readiness(blank_record())['percentage'])
    def test_run_idempotent_and_changed_payload_rejected(self):
        batch={'opportunities':[self.record()],'queries':['fixture query'],'candidates':[]}
        a=self.h.runFundingHunter(batch,'same-key');b=self.h.runFundingHunter(batch,'same-key')
        self.assertEqual(a,b)
        with self.assertRaisesRegex(ValueError,'different research'):self.h.runFundingHunter({**batch,'queries':['different']},'same-key')
    def test_failed_candidate_does_not_abort_valid_program(self):
        bad=self.record('Bad');bad['funding']['cash_prize_max']=-1
        r=self.h.runFundingHunter({'opportunities':[bad,self.record()],'queries':[]},'partial-key')
        self.assertEqual(r['records_created'],1);self.assertEqual(len(r['errors']),1)
    def test_no_notifications_for_high_upper_bound(self):
        self.h.upsert(self.record())
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM funding_notifications').fetchone()[0],0)
    def test_decisions_preserve_agent_recommendation_and_weights(self):
        r=self.h.upsert(self.record());self.h.decide(r['opportunity_id'],'SKIP','too much founder time')
        d=self.h.detail(r['opportunity_id'])
        self.assertEqual(d['decisions'][0]['recommendation'],'REVIEW');self.assertEqual(d['decisions'][0]['decision'],'SKIP')
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM scoring_versions').fetchone()[0],1)
    def test_agent_cannot_decide_for_founder(self):
        r=self.h.upsert(self.record())
        with self.assertRaises(PolicyError):self.h.decide(r['opportunity_id'],'APPLY','good',actor='funding_hunter')
    def test_application_start_reuses_existing_record(self):
        r=self.h.upsert(self.record());a=self.h.start_application(r['opportunity_id']);b=self.h.start_application(r['opportunity_id'])
        self.assertEqual(a,b);self.assertEqual(self.s.db.execute('SELECT count(*) FROM submissions').fetchone()[0],0)
    def test_historical_outcome_is_cycle_scoped(self):
        a=self.h.upsert(self.record(cycle='2026'));b=self.h.upsert(self.record(cycle='2027'))
        self.h.outcome(a['opportunity_id'],'Rejected','Attributable owner-supplied rejection document',source_version_id=self.src)
        self.assertEqual(self.h.detail(a['opportunity_id'])['recommendation'],'REJECTED')
        self.assertEqual(self.h.detail(b['opportunity_id'])['recommendation'],'REVIEW')
    def test_unattributed_rejection_not_recorded(self):
        r=self.h.upsert(self.record())
        with self.assertRaises(ValueError):self.h.outcome(r['opportunity_id'],'Rejected','Hypothetical analyst memo')
    def test_research_versions_immutable(self):
        self.h.upsert(self.record())
        with self.assertRaises(Exception):self.s.db.execute("UPDATE funding_versions SET data_json='{}'")
    def test_model_cannot_supply_arbitrary_fit_number(self):
        d=self.record();d['fit_score']=100
        with self.assertRaisesRegex(ValueError,'Unexpected opportunity field'):self.h.upsert(d)
    def test_false_required_flag_also_needs_evidence(self):
        d=self.record();d['deck_required']=False
        with self.assertRaisesRegex(ValueError,'official provenance'):self.h.upsert(d)
    def test_research_budget_enforced(self):
        with self.assertRaisesRegex(ValueError,'budget exceeded'):self.h.runFundingHunter({'queries':['query']*25},'over-budget')
    def test_unknown_source_result_not_falsely_verified(self):
        d=blank_record();d.update(canonical_name='Unknown',organizer='Unknown Organizer')
        r=self.h.upsert(d);self.assertEqual(self.h.detail(r['opportunity_id'])['verification_state'],'VERIFICATION_REQUIRED')

if __name__=='__main__':unittest.main()
