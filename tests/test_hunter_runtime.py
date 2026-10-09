import copy,http.client,json,tempfile,threading,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from founder_os.store import Store,now,js
from founder_os.funding_hunter import FundingHunter,blank_record
from founder_os.hunter_policy import date_info
from founder_os.server import FounderServer
from tools.research_worker import output_schema,safe_env,schedule_key,claim_work,normalize_observations,resolve_cli

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.s=Store(self.path);self.h=FundingHunter(self.s)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_schema_unknown_question_flag_is_boolean(self):
        prop=output_schema()['properties']['opportunities']['items']['properties']
        self.assertEqual(prop['questions_known']['type'],['boolean','null'])
        self.assertNotIn('WATCH',prop['status']['enum'])
    def test_private_keys_not_passed_to_runner(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture-secret','AWS_SECRET_ACCESS_KEY':'fixture-secret','PATH':'test-path'}):
            env=safe_env();self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('AWS_SECRET_ACCESS_KEY',env);self.assertEqual(env['PATH'],'test-path')
    def test_schedule_uses_local_time_and_catches_missed_run(self):
        settings={'schedule':{'days':['MO','TH'],'hour':8,'minute':0,'timezone':'America/New_York'},'runner':{'connected_at':'2026-10-04T20:00:00+00:00'}}
        self.assertIsNone(schedule_key(settings,datetime.fromisoformat('2026-10-05T11:59:00+00:00')))
        self.assertIn('2026-10-05',schedule_key(settings,datetime.fromisoformat('2026-10-06T14:00:00+00:00')))
        self.assertIn('2026-11-02',schedule_key(settings,datetime.fromisoformat('2026-11-02T13:00:00+00:00')))
    def test_worker_lease_prevents_concurrent_research(self):
        self.h.request_run(key='fixture');first=claim_work(self.h);self.assertIsNotNone(first)
        self.assertIsNone(claim_work(self.h))
        self.assertEqual(self.s.one('SELECT attempts FROM hunter_requests')['attempts'],1)
    def test_idle_worker_has_no_research(self):self.assertIsNone(claim_work(self.h))
    def test_exhausted_request_not_reclaimed(self):
        self.h.request_run(key='fixture');self.s.db.execute("UPDATE hunter_requests SET attempts=3,state='FAILED'")
        self.assertIsNone(claim_work(self.h))
    def test_recent_exact_deadline_is_expired(self):
        instant=datetime.now(timezone.utc);d=date_info((instant-timedelta(minutes=1)).isoformat(),'America/New_York',instant)
        self.assertTrue(d['expired']);self.assertEqual(d['days_remaining'],0)
    def test_model_recommendation_is_not_application_status(self):
        d=blank_record();d.update(canonical_name='Fixture',status='WATCH')
        b=normalize_observations({'opportunities':[d],'errors':[]})
        self.assertEqual(b['opportunities'][0]['status'],'UNKNOWN');self.assertEqual(len(b['errors']),1)
    def test_date_range_retained_without_fake_single_date(self):
        d=blank_record();d.update(canonical_name='Fixture');d['dates']['event_date']='2026-10-22/2026-10-24'
        b=normalize_observations({'opportunities':[d],'errors':[]})
        self.assertIsNone(d['dates']['event_date']);self.assertIn('2026-10-22/2026-10-24',d['notes'])
    def test_null_question_can_match_material_label(self):
        self.assertEqual(self.h.material_readiness({'requirements':[{'kind':'deck','label':'Pitch deck','question':None}]})['percentage'],0)
    def test_approved_reported_fact_is_still_unverified(self):
        path=Path(self.tmp.name)/'draft.txt';path.write_text('Draft says incorporated')
        src=self.s.import_source(path,'draft','reference',text=path.read_text())
        v=self.s.propose_claim('team','Reported incorporation','Draft says incorporated','reported',src,'line 1',last_verified_at=now())
        self.h.attach_fact_value(v,'incorporated',True)
        a=self.s.request_approval('promote_claim',{'version_id':v});self.s.decide(a,'approved',True)
        self.assertNotIn('incorporated',self.h.company_memory()['attributes'])
    def test_invalid_candidate_does_not_crash_run(self):
        r=self.h.runFundingHunter({'candidates':[{'title':'Fixture','url':'javascript:alert(1)'}]},'fixture')
        self.assertEqual(len(r['errors']),1);self.assertEqual(self.s.one('SELECT state FROM funding_runs')['state'],'PARTIAL')

class ServerSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=FounderServer(str(Path(self.tmp.name)/'test.sqlite'),0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port;self.host='127.0.0.1:'+str(self.port)
    def tearDown(self):self.server.shutdown();self.thread.join();self.server.server_close();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port);conn.request(method,path,body,headers or {});r=conn.getresponse();data=r.read();status=r.status;response_headers=dict(r.getheaders());conn.close();return status,data,response_headers
    def test_api_requires_owner_cookie(self):self.assertEqual(self.request('GET','/api/dashboard')[0],403)
    def test_cross_origin_post_denied(self):
        headers={'Cookie':'founder_session='+self.server.token,'X-Founder-CSRF':self.server.token,'Origin':'https://example.org','Content-Type':'application/json'}
        self.assertEqual(self.request('POST','/api/run-now','{}',headers)[0],403)
    def test_wrong_host_denied(self):self.assertEqual(self.request('GET','/',headers={'Host':'example.org'})[0],403)
    def test_private_database_is_not_a_public_asset(self):self.assertEqual(self.request('GET','/data/founder.sqlite')[0],403)
    def test_csrf_token_is_required(self):
        headers={'Cookie':'founder_session='+self.server.token,'Origin':'http://'+self.host,'Content-Type':'application/json'}
        self.assertEqual(self.request('POST','/api/run-now','{}',headers)[0],403)
    def test_owner_approval_needs_explicit_confirmation(self):
        headers={'Cookie':'founder_session='+self.server.token,'X-Founder-CSRF':self.server.token,'Origin':'http://'+self.host,'Content-Type':'application/json'}
        status,body,_=self.request('POST','/api/approval',json.dumps({'approval_id':'unknown','decision':'approved'}),headers)
        self.assertEqual(status,400);self.assertIn(b'Explicit confirmation',body)
    def test_page_protects_cookie_and_frames(self):
        status,body,headers=self.request('GET','/')
        self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie']);self.assertEqual(headers['X-Frame-Options'],'DENY')

if __name__=='__main__':unittest.main()
