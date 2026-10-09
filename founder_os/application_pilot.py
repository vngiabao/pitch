"""Application Pilot: authorized free applications using only current company truth.

The model never controls external submission. A narrow deterministic transport
checks eligibility, financial terms, exact form layout and every field first.
"""
import json,re,smtplib
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
from .store import now,js,digest,uid,PolicyError
from .funding_hunter import FundingHunter,stamp
from .public_forms import PublicFormTransport,TOKEN

FIELD_FACTS={
 'company name':'company_name','startup name':'company_name','company website':'website_url','website':'website_url',
 'full name':'founder_name','founder name':'founder_name','name':'founder_name','first name':'founder_first_name','last name':'founder_last_name',
 'company description':'product_description','product description':'product_description','describe your startup':'product_description',
 'number of employees':'team_size','team size':'team_size','headquarters':'headquarters','year founded':'founded_year',
}
EMAIL_LABELS={'email','email address','work email','business email','company email'}
SUPPORTED_TYPES={'grant','credits','credits_grant','startup_program','ai_program'}

def field_key(label):return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]',' ',label.lower())).strip()

class ApplicationPilot:
    def __init__(self,store):
        self.store=store;self.db=store.db;self.h=FundingHunter(store)
        self.db.executescript(Path(__file__).with_name('autonomy_schema.sql').read_text(encoding='utf-8'))

    def authorize(self,scope,payload,instruction):
        if scope not in ('free_application_pilot','daily_email_report'):raise PolicyError('Unsupported autonomous action scope')
        if not instruction.strip():raise PolicyError('An explicit owner instruction must be retained')
        aid='authorization-'+digest([scope,payload,instruction])[:24]
        self.db.execute('INSERT OR IGNORE INTO autonomy_authorizations VALUES(?,?,?,?,?,NULL,?)',(aid,scope,js(payload),digest(payload),now(),instruction))
        self.store.log('autonomy.owner_authorized','owner',{'id':aid,'scope':scope,'payload':payload,'instruction':instruction})
        return aid

    def authorization(self,scope):
        rows=self.store.rows('SELECT * FROM autonomy_authorizations WHERE scope=? AND revoked_at IS NULL ORDER BY granted_at DESC',(scope,))
        if not rows:return None
        a=rows[0];p=json.loads(a['payload_json'])
        if digest(p)!=a['payload_sha256']:raise PolicyError('Authorization payload changed')
        return {**a,'payload':p}

    def revoke(self,aid):
        self.store.one('SELECT id FROM autonomy_authorizations WHERE id=?',(aid,))
        self.db.execute('UPDATE autonomy_authorizations SET revoked_at=? WHERE id=?',(now(),aid));self.store.log('autonomy.revoked','owner',{'id':aid})

    def build(self,oid):
        d=self.h.detail(oid);data=d['data'];facts=self.h.company_memory()['attributes'];a=self.authorization('free_application_pilot')
        pref=a['payload'] if a else {'personal_email':'gbao.n.vo@gmail.com','company_email':'bao@astoryapp.com'}
        email=pref['company_email'] if data.get('credit_benefits',{}).get('company_email_required') is True else pref['personal_email']
        blockers=[]
        if not a:blockers.append('Autonomous applications are paused; owner authorization is required')
        if data['opportunity_type'] not in SUPPORTED_TYPES:blockers.append('This opportunity is outside the free grant / credits authorization')
        if d['verification_state']!='VERIFIED' or not d['last_verified'] or stamp(d['last_verified'])<datetime.now(timezone.utc)-timedelta(days=7):blockers.append('Recheck official sources within seven days before applying')
        if data['status']!='OPEN' or d['analysis']['scoring']['dates']['expired']:blockers.append('Application is not currently open')
        if d['analysis']['eligibility']['status']!='ELIGIBLE':blockers.extend(d['analysis']['eligibility']['missing'] or ['Company eligibility is not confirmed'])
        funding=data['funding'];benefits=data.get('credit_benefits',{})
        if funding.get('application_fee')!=0:blockers.append('Zero application fee must be verified')
        if funding.get('equity_required') is not False:blockers.append('Non-dilutive terms must be verified')
        for key,label,value in [('deposit_required','No deposit',False),('paid_account_required','No paid account activation',False),('minimum_spend','No minimum spend',0),('terms_acceptance_required','No unreviewed terms acceptance',False)]:
            if benefits.get(key)!=value:blockers.append(label+' must be verified; otherwise owner review is required')
        if funding.get('investment_terms'):blockers.append('Investment terms are outside autonomous application scope')
        if not data.get('application_url'):blockers.append('Official application URL is unknown')
        if d['recommendation'] in ('SKIP','EXPIRED','REJECTED','ACCEPTED','ALREADY APPLIED'):blockers.append('Opportunity has a terminal or skip recommendation')
        if d['decisions'] and d['decisions'][0]['decision']!='APPLY':blockers.append('Your latest opportunity decision is '+d['decisions'][0]['decision']+'; automatic application is paused for this program')
        if self.h._history_status(oid):blockers.append('An application outcome or submission already exists for this cycle')
        if data.get('credit_benefits',{}).get('company_email_required') is True:
            site=facts.get('website_url',{}).get('value')
            if not site or urlsplit(site).hostname!=email.split('@')[-1]:blockers.append('Verified company website must match the required company-email domain')
        aid=self.h.start_application(oid);pid='application-plan-'+digest(oid)[:24]
        fields={};claims={};answers={};adapter=self.db.execute('SELECT * FROM application_adapters WHERE opportunity_id=?',(oid,)).fetchone()
        if adapter:
            definition=json.loads(adapter['definition_json'])
            for c in definition['fields']:
                if c['type']=='hidden':continue
                key=field_key(c['label'])
                if key in EMAIL_LABELS:
                    fields[c['name']]=pref['company_email'] if key in ('work email','business email','company email') else email
                elif key in FIELD_FACTS and FIELD_FACTS[key] in facts:
                    fact=facts[FIELD_FACTS[key]];v=fact['value']
                    if isinstance(v,(str,int,float)) and not isinstance(v,bool):fields[c['name']]=str(v);claims[c['name']]=fact['claim_version_id']
                    else:blockers.append('Unsupported fact format for '+c['label'])
                else:
                    matches=[a for a in self.store.approved_answers(c['label']) if field_key(a['prompt'])==key]
                    if len(matches)==1:
                        fields[c['name']]=matches[0]['body'];answers[c['name']]=matches[0]['id']
                    elif c['required']:blockers.append('Missing current approved answer for: '+(c['label'] or c['name']))
                if c['maxlength'] and c['name'] in fields and len(fields[c['name']])>int(c['maxlength']):blockers.append('Answer exceeds form limit: '+c['label'])
        else:blockers.append('Official application form needs inspection or a provider-specific adapter')
        # A saved intent, even after a timeout or crash, is never silently resubmitted.
        attempts=self.store.rows('SELECT state FROM application_attempts WHERE plan_id=?',(pid,))
        if attempts:blockers.append('A submission attempt already exists; receipt reconciliation is required before any further action')
        payload={'opportunity_id':oid,'application_id':aid,'program_id':d['program_id'],'cycle_id':d['cycle_id'],'email':email,
          'application_url':data['application_url'],'fields':fields,'claim_versions':claims,'research_revision':d['revision'],
          'answer_versions':answers,'form_fingerprint':adapter['fingerprint'] if adapter else None,'authorization_id':a['id'] if a else None,'files':[],'accept_terms':False}
        state='NEEDS_REVIEW' if blockers else 'READY'
        self.db.execute('INSERT INTO application_plans VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET state=excluded.state,selected_email=excluded.selected_email,payload_json=excluded.payload_json,blockers_json=excluded.blockers_json,updated_at=excluded.updated_at',
          (pid,oid,aid,state,email,js(payload),js(list(dict.fromkeys(blockers))),now(),now()))
        return self.plan(pid)

    def plan(self,pid):
        p=self.store.one('SELECT * FROM application_plans WHERE id=?',(pid,));p['payload']=json.loads(p.pop('payload_json'));p['blockers']=json.loads(p.pop('blockers_json'));return p

    def inspect(self,oid,transport=None):
        d=self.h.detail(oid);url=d['data']['application_url']
        if not url:raise PolicyError('Official application URL is unknown')
        if d['verification_state']!='VERIFIED':raise PolicyError('Verify the official program before inspecting its form')
        session=(transport or PublicFormTransport()).read(url)
        self.db.execute('INSERT INTO application_adapters VALUES(?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET definition_json=excluded.definition_json,fingerprint=excluded.fingerprint,checked_at=excluded.checked_at',(oid,js(session['definition']),session['fingerprint'],now()))
        return self.build(oid)

    def preview(self,pid):
        p=self.plan(pid)
        if p['state']=='SUBMITTED':raise PolicyError('This application is already submitted')
        p=self.build(p['opportunity_id'])
        if p['blockers']:raise PolicyError('Resolve application blockers before requesting submission confirmation')
        sha=digest(p['payload']);cid='application-confirmation-'+digest([pid,sha])[:24]
        name=self.h.detail(p['opportunity_id'])['data']['canonical_name']
        lines=['A Story application preview — '+name,'','NOT SUBMITTED. Your confirmation is required.',
          'Application: '+p['payload']['application_url'],'Account email: '+p['selected_email'],'', 'EXACT FILLED FIELDS']
        definition=json.loads(self.store.one('SELECT definition_json FROM application_adapters WHERE opportunity_id=?',(p['opportunity_id'],))['definition_json'])
        for field in definition['fields']:
            if field['type']=='hidden':continue
            lines+=['','Question: '+(field['label'] or field['name']),'Field: '+field['name'],'Answer: '+p['payload']['fields'].get(field['name'],'[blank]')]
        lines+=['','No files, payment or terms acceptance included.','Review and confirm this exact preview on your PC:','http://127.0.0.1:8765/applications#'+cid,
          'If company facts, questions or program details change, this confirmation becomes invalid. You will receive a new preview.']
        email={'id':cid,'recipient':'gbao.n.vo@gmail.com','subject':'Confirm before submission: '+name,'body':'\n'.join(lines)}
        if not self.db.execute('SELECT id FROM application_confirmations WHERE id=?',(cid,)).fetchone():
            from .application_review import ApplicationReview
            email['attachments']=[ApplicationReview(self.store).snapshot(pid)]
        self.db.execute("INSERT OR IGNORE INTO application_confirmations VALUES(?,?,?,?,?,'PENDING',NULL,'PENDING',NULL,?)",(cid,pid,js(p['payload']),sha,js(email),now()))
        c=self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        state='OWNER_REJECTED' if c['decision']=='REJECTED' else 'CONFIRMED' if c['decision']=='APPROVED' and c['email_state']=='SENT' else 'AWAITING_CONFIRMATION' if c['email_state']=='SENT' else 'AWAITING_EMAIL_PREVIEW'
        self.db.execute('UPDATE application_plans SET state=? WHERE id=?',(state,pid))
        return c

    def send_preview(self,cid,mail=None):
        from .report_email import GmailTransport
        c=self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        if c['email_state'] in ('SENT','SENDING','DELIVERY_UNKNOWN'):return c
        if not self.authorization('free_application_pilot'):raise PolicyError('Application preparation is paused')
        if mail is None and self.h.settings().get('mail_delivery',{}).get('mode')=='gmail_connector':
            self.db.execute("UPDATE application_confirmations SET email_state='CONNECTOR_PENDING' WHERE id=?",(cid,));return self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        mail=mail or GmailTransport()
        if not mail.available():
            self.db.execute("UPDATE application_confirmations SET email_state='MAIL_CONNECTION_REQUIRED' WHERE id=?",(cid,));return self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        with self.store.transaction():
            changed=self.db.execute("UPDATE application_confirmations SET email_state='SENDING' WHERE id=? AND email_state IN ('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING')",(cid,)).rowcount
            if not changed:return self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        try:
            receipt=mail.send(json.loads(c['email_json']))
            if receipt.get('accepted') is not True:raise PolicyError('No preview email acceptance')
            self.db.execute("UPDATE application_confirmations SET email_state='SENT',email_receipt_json=? WHERE id=?",(js(receipt),cid))
            self.db.execute("UPDATE application_plans SET state='AWAITING_CONFIRMATION' WHERE id=?",(c['plan_id'],))
        except smtplib.SMTPAuthenticationError:
            self.db.execute("UPDATE application_confirmations SET email_state='MAIL_CONNECTION_REQUIRED' WHERE id=?",(cid,))
        except Exception:
            self.db.execute("UPDATE application_confirmations SET email_state='DELIVERY_UNKNOWN' WHERE id=?",(cid,))
        return self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))

    def confirm(self,cid,decision,owner_confirmation=False):
        if owner_confirmation is not True or decision not in ('APPROVED','REJECTED'):raise PolicyError('An explicit owner confirmation of this preview is required')
        c=self.store.one('SELECT * FROM application_confirmations WHERE id=?',(cid,))
        if c['email_state']!='SENT':raise PolicyError('The preview email must be accepted by Gmail before confirmation')
        if c['decision']!='PENDING':raise PolicyError('Preview is already decided')
        p=self.plan(c['plan_id']);current=self.build(p['opportunity_id'])
        if current['blockers'] or digest(current['payload'])!=c['payload_sha256'] or digest(json.loads(c['payload_json']))!=c['payload_sha256']:raise PolicyError('Preview or current application changed; send a new preview')
        self.db.execute('UPDATE application_confirmations SET decision=?,decided_at=? WHERE id=?',(decision,now(),cid))
        self.db.execute('UPDATE application_plans SET state=? WHERE id=?',('CONFIRMED' if decision=='APPROVED' else 'OWNER_REJECTED',c['plan_id']))
        self.store.log('application.owner_confirmed','local_owner',{'confirmation_id':cid,'decision':decision,'payload_sha256':c['payload_sha256']})
        return self.plan(c['plan_id'])

    def execute(self,pid,transport=None):
        previous=self.plan(pid)
        if previous['state'] in ('SUBMITTED','OWNER_REJECTED'):return previous
        transport=transport or PublicFormTransport();p=self.build(previous['opportunity_id'])
        if p['blockers']:return p
        confirmation=self.db.execute("SELECT * FROM application_confirmations WHERE plan_id=? AND payload_sha256=? AND decision='APPROVED' AND email_state='SENT'",(pid,digest(p['payload']))).fetchone()
        if not confirmation:
            self.db.execute("UPDATE application_plans SET state='AWAITING_CONFIRMATION' WHERE id=?",(pid,))
            return self.plan(pid)
        session=transport.read(p['payload']['application_url'])
        if session['fingerprint']!=p['payload']['form_fingerprint']:raise PolicyError('Application form changed; rebuild and review its questions')
        # Recheck canonical facts and owner scope after reading the current form.
        current=self.build(p['opportunity_id'])
        if current['blockers'] or current['payload']!=p['payload']:raise PolicyError('Application truth or authorization changed')
        attempt=uid('application-attempt');sha=digest(p['payload']);approval=uid('approval')
        with self.store.transaction():
            self.db.execute('INSERT INTO application_attempts VALUES(?,?,?,\'IN_FLIGHT\',?,NULL,NULL,NULL)',(attempt,pid,sha,now()))
            approval_payload={**p['payload'],'confirmation_id':confirmation['id'],'preview_email_receipt':json.loads(confirmation['email_receipt_json'])}
            self.db.execute('INSERT INTO approvals VALUES(?,?,?, ?,NULL,\'approved\',\'application_pilot\',?,\'local_owner\',?,?)',(approval,'submit_application',js(approval_payload),digest(approval_payload),now(),confirmation['decided_at'],'Owner confirmed this exact emailed application preview'))
            self.db.execute("UPDATE application_plans SET state='SUBMITTING',updated_at=? WHERE id=?",(now(),pid))
            self.store.log('application.submission_intent','application_pilot',{'attempt_id':attempt,'plan_id':pid,'payload_sha256':sha,'authorization_id':p['payload']['authorization_id']})
        try:
            receipt=transport.submit(session,p['payload']['fields']);confirmed=receipt.get('confirmed') is True and bool(receipt.get('receipt'))
            state='SUBMITTED' if confirmed else 'SUBMISSION_UNKNOWN'
            with self.store.transaction():
                self.db.execute('UPDATE application_attempts SET state=?,completed_at=?,receipt_json=? WHERE id=?',(state,now(),js(receipt),attempt))
                self.db.execute('UPDATE application_plans SET state=?,updated_at=? WHERE id=?',(state,now(),pid))
                if confirmed:
                    snapshot={**p['payload'],'actual_receipt':receipt,'submitted_at':now()};sid=uid('submission')
                    self.db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?,?)',(sid,p['application_id'],snapshot['submitted_at'],receipt['receipt'],js(snapshot),digest(snapshot),approval,now()))
                    self.db.execute("UPDATE applications SET state='submitted' WHERE id=?",(p['application_id'],))
                    self.h.outcome(p['opportunity_id'],'Applied','Official response confirmed receipt',evidence_url=receipt.get('url'),application_id=p['application_id'],submission_id=sid)
                self.store.log('application.'+state.lower(),'application_pilot',{'attempt_id':attempt,'receipt':receipt})
        except Exception:
            with self.store.transaction():
                self.db.execute("UPDATE application_attempts SET state='SUBMISSION_UNKNOWN',completed_at=?,error='Network or response failure after submission intent; do not retry automatically' WHERE id=?",(now(),attempt))
                self.db.execute("UPDATE application_plans SET state='SUBMISSION_UNKNOWN',updated_at=? WHERE id=?",(now(),pid))
            # Private fields and transport errors are not printed or mailed.
        return self.plan(pid)

    def reconcile_placeholders(self):
        # An unknown-cycle mention of an already verified rolling program is a
        # retained reference, not a second application. Never merge annual cycles
        # or overwrite actual outcomes/submissions.
        linked=[]
        for r in self.store.rows('SELECT opportunity_id,program_id,data_json FROM funding_intelligence'):
            data=json.loads(r['data_json'])
            if data.get('cycle_kind')!='unknown':continue
            if self.db.execute('SELECT 1 FROM submissions su JOIN applications a ON a.id=su.application_id WHERE a.opportunity_id=?',(r['opportunity_id'],)).fetchone():continue
            if self.db.execute('SELECT 1 FROM funding_outcomes WHERE opportunity_id=?',(r['opportunity_id'],)).fetchone():continue
            targets=self.store.rows("SELECT i.opportunity_id FROM funding_intelligence i JOIN funding_cycles c ON c.id=i.cycle_id WHERE i.program_id=? AND c.cycle_key='rolling' AND i.verification_state='VERIFIED'",(r['program_id'],))
            if len(targets)!=1:continue
            reason='Unknown-cycle reference resolved to the same program\'s verified rolling record; original versions and paths are preserved.'
            with self.store.transaction():
                n=self.db.execute('INSERT OR IGNORE INTO opportunity_supersessions VALUES(?,?,?,?)',(r['opportunity_id'],targets[0]['opportunity_id'],reason,now())).rowcount
                if n:self.store.log('funding.placeholder_superseded','identity_reconciliation',{'old':r['opportunity_id'],'current':targets[0]['opportunity_id']});linked.append(r['opportunity_id'])
        return linked

    def poll(self):
        if not self.authorization('free_application_pilot'):return {'paused':True}
        self.reconcile_placeholders()
        # Existing plans are revisited when facts or program intelligence changes.
        candidates=[d for d in self.h.list('All') if d['data']['opportunity_type'] in SUPPORTED_TYPES and d['recommendation'] not in ('SKIP','EXPIRED','REJECTED','ACCEPTED','ALREADY APPLIED')]
        self.db.execute("UPDATE application_plans SET state='SUPERSEDED' WHERE opportunity_id IN (SELECT superseded_id FROM opportunity_supersessions) AND state NOT IN ('SUBMITTED','SUBMITTING','SUBMISSION_UNKNOWN')")
        results=[]
        for d in candidates[:24]:
            old=self.db.execute('SELECT * FROM application_plans WHERE opportunity_id=?',(d['opportunity_id'],)).fetchone()
            if old and old['state'] in ('SUBMITTED','SUBMITTING','SUBMISSION_UNKNOWN','OWNER_REJECTED'):continue
            p=self.build(d['opportunity_id'])
            # Read public forms only after eligibility and financial gates pass.
            if p['blockers']==['Official application form needs inspection or a provider-specific adapter']:
                try:p=self.inspect(d['opportunity_id'])
                except Exception as e:
                    self.db.execute('UPDATE application_plans SET blockers_json=?,updated_at=? WHERE id=?',(js([str(e)[:300]]),now(),p['id']))
                    continue
            if p['state']=='READY':
                c=self.preview(p['id']);c=self.send_preview(c['id'])
                if c['decision']=='APPROVED' and c['email_state']=='SENT':p=self.execute(p['id'])
                else:p=self.plan(p['id'])
            results.append({'plan_id':p['id'],'state':p['state']})
        return {'plans':results,'external_submissions':sum(p['state']=='SUBMITTED' for p in results)}

    def dashboard(self):
        return {'authorizations':self.store.rows('SELECT id,scope,granted_at,revoked_at FROM autonomy_authorizations'),
          'plans':[self.plan(p['id']) for p in self.store.rows('SELECT id FROM application_plans ORDER BY updated_at DESC')],
          'attempts':self.store.rows('SELECT id,plan_id,state,started_at,completed_at,error FROM application_attempts ORDER BY started_at DESC'),
          'confirmations':self.store.rows('SELECT id,plan_id,payload_json,payload_sha256,email_state,decision,created_at,decided_at FROM application_confirmations ORDER BY created_at DESC'),
          'reports':self.store.rows('SELECT id,local_date,recipient,subject,state,created_at,sent_at,error FROM daily_reports ORDER BY local_date DESC LIMIT 14')}
