import copy,json,unittest
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
import test_funding_hunter as fixtures
import test_application_pilot as autonomy
from founder_os.store import now,js,PolicyError
from founder_os.opportunity_curation import shortlist
from founder_os.report_email import DailyReporter
from founder_os.connector_outbox import ConnectorOutbox,OWNER
from tools.research_worker import output_schema,normalize_observations


def brief(url):
    return {'why_applicable':'Potential fit for the proposed interviewing product.',
            'how_it_helps':'Could reduce prototype costs if the provider fits the stack.',
            'application_angle':'Describe the supported customer problem and intended experiment.',
            'agent_next_step':'Verify exact application questions and overage terms.',
            'owner_decisions':['Confirm whether this provider is in the intended stack.'],
            'company_fact_keys':[], 'source_urls':[url], 'priority':'CORE_PRODUCT','basis':'conditional'}


class CurationTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record
    approve_fact=fixtures.HunterTests.approve_fact
    def curated(self,name='Example Competition',cycle='2026'):
        d=self.record(name,cycle);d['organizer']=name+' Organizer';d['founder_brief']=brief(d['official_url'])
        return self.h.upsert(d)['opportunity_id']
    def test_no_optimistic_upper_bound_ranking(self):
        ids=[self.curated('Program '+str(i)) for i in range(6)]
        items=[self.h.detail(i) for i in ids]
        for i,d in enumerate(items):d['fit_score']=None;d['analysis']['scoring']['upper_bound']=100 if i==0 else 50
        items[0]['analysis']['founder_brief']['priority']='EXPLORATORY'
        selected=shortlist(items)
        self.assertEqual(len(selected),5);self.assertNotIn(ids[0],[d['opportunity_id'] for d in selected])
    def test_program_dedup_stale_expired_and_owner_skip(self):
        first=self.curated();second=self.curated(cycle='2027')
        stale=self.curated('Stale');skip=self.curated('Skipped');expired=self.curated('Expired')
        self.h.decide(skip,'SKIP','Founder time')
        items=[self.h.detail(i) for i in (first,second,stale,skip,expired)]
        items[2]['last_verified']=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat()
        items[4]['recommendation']='EXPIRED'
        self.assertEqual(len(shortlist(items)),1)
    def test_brief_cannot_assert_unapproved_facts_or_uncited_sources(self):
        d=self.record();d['founder_brief']=brief(d['official_url']);d['founder_brief'].update(basis='approved_memory',company_fact_keys=['industry'])
        with self.assertRaisesRegex(ValueError,'current canonical'):self.h.upsert(d)
        d['founder_brief']=brief('https://unverified.example.org')
        with self.assertRaisesRegex(ValueError,'official source'):self.h.upsert(d)
    def test_canonical_changes_invalidate_existing_brief(self):
        self.approve_fact('funding_stage','bootstrapped')
        d=self.record();d['founder_brief']=brief(d['official_url']);d['founder_brief'].update(basis='approved_memory',company_fact_keys=['funding_stage'])
        oid=self.h.upsert(d)['opportunity_id'];self.assertEqual(len(self.h.daily_shortlist()),1)
        self.approve_fact('funding_stage','seed')
        self.assertEqual(self.h.detail(oid)['analysis']['founder_brief']['basis'],'unknown');self.assertEqual(self.h.daily_shortlist(),[])
    def test_reconfirming_same_fact_value_keeps_brief(self):
        self.approve_fact('funding_stage','bootstrapped')
        d=self.record();d['founder_brief']=brief(d['official_url']);d['founder_brief'].update(basis='approved_memory',company_fact_keys=['funding_stage'])
        oid=self.h.upsert(d)['opportunity_id']
        self.approve_fact('funding_stage','bootstrapped')
        self.assertNotEqual(self.h.detail(oid)['analysis']['founder_brief']['basis'],'unknown');self.assertEqual(len(self.h.daily_shortlist()),1)
    def test_source_capture_timestamp_tie_uses_newest_import(self):
        self.approve_fact('funding_stage','bootstrapped')
        captured=self.s.one('SELECT captured_at FROM source_versions WHERE id=?',(self.src,))['captured_at']
        self.file.write_text('Changed source')
        with patch('founder_os.store.now',return_value=captured):self.s.import_source(self.file,'fixture','REFERENCE',text='Changed source')
        self.assertNotIn('funding_stage',self.h.company_memory()['attributes'])
    def test_schema_and_missing_research_brief(self):
        properties=output_schema()['properties']['opportunities']['items']['properties']
        self.assertIn('founder_brief',properties)
        batch=normalize_observations({'opportunities':[self.record()]})
        self.assertIn('founder decision brief',batch['errors'][0]['message'])


class ReportCurationTests(unittest.TestCase):
    setUp=autonomy.AutonomyTests.setUp
    tearDown=autonomy.AutonomyTests.tearDown
    def test_sample_and_daily_share_briefs_and_do_not_approve(self):
        old=self.p.authorization('daily_email_report');self.p.revoke(old['id'])
        self.p.authorize('daily_email_report',{'recipient':OWNER,'question_answer_attachments':True},'Owner requests private sample report')
        self.s.db.execute("INSERT INTO hunter_settings VALUES('mail_delivery',?)",(js({'mode':'gmail_connector'}),))
        r=copy.deepcopy(self.record);r['founder_brief']=brief(r['official_url']);self.h.upsert(r)
        reporter=DailyReporter(self.s);sample=reporter.render(sample=True)
        self.assertIn('NEEDS YOU TODAY',sample['body']);self.assertIn('ACCESS REPORT',sample['body']);self.assertIn('Nothing is submitted for you',sample['body'])
        self.assertNotIn('OPPORTUNITIES TO REVIEW',sample['body'])
        daily=reporter.prepare();out=ConnectorOutbox(self.s);claimed=out.claim('report',daily['id']);out.complete('report',daily['id'],claimed['message_sha256'],'fixture-day',OWNER)
        key=reporter.prepare_sample();claim=out.claim('supplement',key);out.complete('supplement',key,claim['message_sha256'],'fixture-sample',OWNER)
        self.assertEqual(reporter.prepare()['body'],daily['body'])
        with self.assertRaises(PolicyError):out.claim('supplement',key)
        self.assertEqual(self.s.one('SELECT count(*) n FROM application_confirmations')['n'],0)
        self.assertEqual(self.s.one('SELECT count(*) n FROM submissions')['n'],0)

if __name__=='__main__':unittest.main()
