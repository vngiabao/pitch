import copy,json,tempfile,unittest,smtplib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from founder_os.store import Store,now,digest,js,PolicyError
from founder_os.funding_hunter import FundingHunter,blank_record
from founder_os.application_pilot import ApplicationPilot
from founder_os.report_email import DailyReporter,GmailTransport
from founder_os.public_forms import Forms,form_definition,public_https

class FormsTransport:
    def __init__(self):
        self.calls=0;self.fail=False;self.confirm=True
        html='<form method="post" action="https://example.org/apply"><label for="company">Company name</label><input id="company" name="company" required><label for="email">Work email</label><input id="email" name="email" type="email" required></form>'
        p=Forms();p.feed(html);self.form=p.finish('https://example.org/apply')[0]
    def read(self,url):return {'form':self.form,'definition':form_definition(self.form),'fingerprint':digest(form_definition(self.form))}
    def submit(self,session,fields):
        self.calls+=1
        if self.fail:raise TimeoutError('fixture')
        return {'confirmed':self.confirm,'url':'https://example.org/apply','receipt':'application received' if self.confirm else None,'http_status':200}

class MailTransport:
    def __init__(self,connected=True,fail=False):self.calls=0;self.connected=connected;self.fail=fail
    def available(self):return self.connected
    def send(self,r):
        self.calls+=1
        if self.fail:raise TimeoutError('fixture')
        return {'accepted':True,'recipient':r['recipient'],'transport':'fixture'}

class AutonomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'test.sqlite');self.p=ApplicationPilot(self.s);self.h=self.p.h
        self.p.authorize('free_application_pilot',{'personal_email':'gbao.n.vo@gmail.com','company_email':'bao@astoryapp.com'},'Owner explicitly requests auto apply to free programs')
        self.p.authorize('daily_email_report',{'recipient':'gbao.n.vo@gmail.com'},'Owner requests one report every day')
        self.transport=FormsTransport();r=blank_record();url='https://example.org/program';r.update(canonical_name='Fixture credits',organizer='Fixture',opportunity_type='credits_grant',cycle='rolling',cycle_kind='rolling',official_url=url,application_url='https://example.org/apply',status='OPEN',eligibility_complete=True)
        r['funding'].update(application_fee=0,equity_required=False,credits_value=1000)
        r['credit_benefits'].update(company_email_required=True,deposit_required=False,paid_account_required=False,minimum_spend=0,terms_acceptance_required=False)
        r['eligibility_rules']=[{'fact_key':'company_name','op':'eq','value':'A Story','description':'Company identity','source_url':url}]
        r['sources']=[{'url':url,'role':'official_program','checked_at':now(),'excerpt':'Fixture official program section: rolling, open, free, no equity or payment. Work email required.'}]
        r['field_sources']={k:[url] for k in ('status','cycle_kind','application_url','eligibility_complete','funding.application_fee','funding.equity_required','funding.credits_value','credit_benefits.company_email_required','credit_benefits.deposit_required','credit_benefits.paid_account_required','credit_benefits.minimum_spend','credit_benefits.terms_acceptance_required')}
        self.record=r;result=self.h.upsert(r);self.oid=result['opportunity_id']
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def facts(self):
        f=Path(self.tmp.name)/'fact.txt';f.write_text('Verified fixture company facts')
        v=self.s.import_source(str(f),'text','KEEP');cid=self.s.propose_claim('team','Fixture current facts','A Story', 'verified',v,'fixture',last_verified_at=now())
        self.h.attach_fact_value(cid,'company_name','A Story');self.h.attach_fact_value(cid,'website_url','https://astoryapp.com')
        a=self.s.request_approval('promote_claim',{'version_id':cid});self.s.decide(a,'approved',True);return cid
    def ready(self):
        self.facts();p=self.p.inspect(self.oid,self.transport);c=self.p.preview(p['id']);self.p.send_preview(c['id'],MailTransport());self.p.confirm(c['id'],'APPROVED',True);return p
    def test_missing_truth_blocks_submission(self):
        p=self.p.build(self.oid);self.assertEqual(p['state'],'NEEDS_REVIEW');self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'NEEDS_REVIEW');self.assertEqual(self.transport.calls,0)
    def test_business_email_switch_and_native_submission(self):
        p=self.ready();self.assertEqual(p['selected_email'],'bao@astoryapp.com');self.assertEqual(p['payload']['fields']['email'],'bao@astoryapp.com');self.assertEqual(p['state'],'READY')
        sent=self.p.execute(p['id'],self.transport);self.assertEqual(sent['state'],'SUBMITTED');self.assertEqual(self.s.one('SELECT count(*) n FROM submissions')['n'],1);self.assertEqual(self.h.detail(self.oid)['recommendation'],'ALREADY APPLIED')
        self.p.execute(p['id'],self.transport);self.assertEqual(self.transport.calls,1)
    def test_uncertain_submission_never_retries(self):
        p=self.ready();self.transport.fail=True;self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'SUBMISSION_UNKNOWN');self.p.execute(p['id'],self.transport);self.assertEqual(self.transport.calls,1);self.assertEqual(self.s.one('SELECT count(*) n FROM submissions')['n'],0)
    def test_http_200_is_not_submission_receipt(self):
        p=self.ready();self.transport.confirm=False;self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'SUBMISSION_UNKNOWN');self.assertEqual(self.s.one('SELECT count(*) n FROM submissions')['n'],0)
    def test_changed_form_and_revoked_scope_block(self):
        p=self.ready();self.transport.form['fields'][0]['label']='Another question'
        with self.assertRaises(PolicyError):self.p.execute(p['id'],self.transport)
        self.p.revoke(self.p.authorization('free_application_pilot')['id']);self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'NEEDS_REVIEW');self.assertEqual(self.transport.calls,0)
    def test_paid_unknown_or_terms_are_not_free(self):
        self.facts()
        for key,value in [('deposit_required',True),('minimum_spend',50000),('terms_acceptance_required',True),('paid_account_required',None)]:
            r=copy.deepcopy(self.record);r['credit_benefits'][key]=value;self.h.upsert(r);p=self.p.build(self.oid);self.assertEqual(p['state'],'NEEDS_REVIEW')
    def test_unknown_questions_are_not_guessed(self):
        self.facts();self.transport.form['fields'].append({'name':'revenue','id':'revenue','type':'text','required':True,'label':'How much revenue do you have?','value':'','maxlength':None,'disabled':False})
        p=self.p.inspect(self.oid,self.transport);self.assertTrue(any('Missing current approved answer' in b for b in p['blockers']))
    def test_stale_company_source_blocks_plan(self):
        p=self.ready();f=Path(self.tmp.name)/'fact.txt';f.write_text('Changed fixture facts');self.s.import_source(str(f),'text','KEEP');self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'NEEDS_REVIEW');self.assertEqual(self.transport.calls,0)
    def test_founder_skip_overrides_standing_application_authorization(self):
        p=self.ready();self.h.decide(self.oid,'SKIP','Owner does not want this program');self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'NEEDS_REVIEW');self.assertEqual(self.transport.calls,0)
    def test_credit_condition_boolean_and_provenance_required(self):
        r=copy.deepcopy(self.record);r['credit_benefits']['deposit_required']=0
        with self.assertRaises(ValueError):self.h.validate(r)
        r=copy.deepcopy(self.record);r['field_sources']['credit_benefits.minimum_spend']=[]
        with self.assertRaises(ValueError):self.h.validate(r)
    def test_daily_report_is_once_per_day_and_private_answers_excluded(self):
        p=self.ready();reporter=DailyReporter(self.s);r=reporter.prepare();self.assertNotIn('"fields"',r['body']);self.assertNotIn('Fixture current facts',r['body']);self.assertEqual(r['recipient'],'gbao.n.vo@gmail.com')
        t=MailTransport();reporter.send(r['id'],t);reporter.send(r['id'],t);self.assertEqual(t.calls,1);self.assertEqual(reporter.prepare()['id'],r['id'])
    def test_mail_blocker_and_timeout_not_labeled_sent(self):
        reporter=DailyReporter(self.s);r=reporter.prepare();t=MailTransport(False);self.assertEqual(reporter.send(r['id'],t)['state'],'MAIL_CONNECTION_REQUIRED');self.assertEqual(t.calls,0)
        t=MailTransport(True,True);self.assertEqual(reporter.send(r['id'],t)['state'],'DELIVERY_UNKNOWN');reporter.send(r['id'],t);self.assertEqual(t.calls,1)
    def test_report_schedule_dst_and_no_backlog(self):
        reporter=DailyReporter(self.s)
        with patch.object(reporter,'send',return_value={'state':'fixture'}) as send:
            self.assertEqual(reporter.poll(datetime.fromisoformat('2026-11-02T13:59:00+00:00')),{'waiting':True});reporter.poll(datetime.fromisoformat('2026-11-02T14:00:00+00:00'));self.assertEqual(send.call_count,1)
        self.assertEqual(self.s.one('SELECT local_date FROM daily_reports')['local_date'],'2026-11-02')
    def test_scope_immutable_and_report_revocation(self):
        a=self.p.authorization('daily_email_report')
        with self.assertRaises(Exception):self.s.db.execute('UPDATE autonomy_authorizations SET payload_json=? WHERE id=?',('{}',a['id']))
        self.p.revoke(a['id'])
        with self.assertRaises(PolicyError):DailyReporter(self.s).prepare()
    def test_never_submits_without_emailed_preview_and_exact_owner_confirmation(self):
        self.facts();p=self.p.inspect(self.oid,self.transport)
        self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'AWAITING_CONFIRMATION');self.assertEqual(self.transport.calls,0)
        c=self.p.preview(p['id'])
        with self.assertRaises(PolicyError):self.p.confirm(c['id'],'APPROVED',True)
        self.p.send_preview(c['id'],MailTransport())
        with self.assertRaises(PolicyError):self.p.confirm(c['id'],'APPROVED',False)
        self.p.execute(p['id'],self.transport);self.assertEqual(self.transport.calls,0)
    def test_owner_decline_blocks_application(self):
        self.facts();p=self.p.inspect(self.oid,self.transport);c=self.p.preview(p['id']);self.p.send_preview(c['id'],MailTransport());self.p.confirm(c['id'],'REJECTED',True)
        self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'OWNER_REJECTED');self.assertEqual(self.transport.calls,0)
    def test_superseded_placeholder_preserves_history_and_prevents_submission(self):
        p=self.ready();r=copy.deepcopy(self.record);r.update(cycle='2027',cycle_kind='annual')
        newer=self.h.upsert(r)['opportunity_id'];before=self.s.one('SELECT count(*) n FROM funding_versions')['n']
        self.s.db.execute('INSERT INTO opportunity_supersessions VALUES(?,?,?,?)',(self.oid,newer,'Unknown placeholder resolved to verified cycle',now()))
        old=self.h.detail(self.oid);self.assertEqual(old['recommendation'],'SKIP');self.assertEqual(old['superseded_by'],newer)
        self.assertEqual(self.h.detail(newer)['data']['cycle'],'2027')
        self.assertEqual(self.s.one('SELECT count(*) n FROM funding_versions')['n'],before)
        self.assertEqual(self.p.execute(p['id'],self.transport)['state'],'NEEDS_REVIEW');self.assertEqual(self.transport.calls,0)
    def test_preview_auth_failure_is_reconnectable_without_false_sent_state(self):
        self.facts();p=self.p.inspect(self.oid,self.transport);c=self.p.preview(p['id']);t=MailTransport()
        with patch.object(t,'send',side_effect=smtplib.SMTPAuthenticationError(535,b'fixture rejected')):
            self.assertEqual(self.p.send_preview(c['id'],t)['email_state'],'MAIL_CONNECTION_REQUIRED')
        with self.assertRaises(PolicyError):self.p.confirm(c['id'],'APPROVED',True)
        self.assertEqual(self.p.send_preview(c['id'],t)['email_state'],'SENT')
    def test_new_unknown_cycle_links_to_rolling_but_annual_cycle_is_preserved(self):
        r=copy.deepcopy(self.record);r.update(cycle='unknown',cycle_kind='unknown');unknown=self.h.upsert(r)['opportunity_id']
        r=copy.deepcopy(self.record);r.update(cycle='2027',cycle_kind='annual');annual=self.h.upsert(r)['opportunity_id']
        self.assertIn(unknown,self.p.reconcile_placeholders());self.assertEqual(self.h.detail(unknown)['recommendation'],'SKIP')
        self.assertNotIn('superseded_by',self.h.detail(annual));self.assertEqual(self.p.reconcile_placeholders(),[])
    def test_private_url_and_embedded_credentials_denied(self):
        for url in ('http://example.org','https://user:pass@example.org','https://127.0.0.1','https://[::1]'):
            with self.assertRaises(PolicyError):public_https(url)
    def test_refreshing_token_does_not_change_question_fingerprint(self):
        f=copy.deepcopy(self.transport.form);f['fields'].append({'name':'csrf_token','id':'csrf','type':'hidden','required':False,'label':'','value':'one','maxlength':None,'disabled':False})
        first=digest(form_definition(f));f['fields'][-1]['value']='two';self.assertEqual(first,digest(form_definition(f)))

if __name__=='__main__':unittest.main()
