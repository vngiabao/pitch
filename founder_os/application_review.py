"""Immutable question/answer TXT snapshots, including unfinished applications.

Snapshots are review evidence, never permission to submit. Saved historical
questions are deliberately separated from inspected current official forms.
"""
import json,sqlite3
from pathlib import Path
from .store import now,digest,js,PolicyError
from .owner_links import founder_url

SCHEMA='''
CREATE TABLE IF NOT EXISTS review_artifacts(id TEXT PRIMARY KEY,filename TEXT NOT NULL,body TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS report_attachments(report_id TEXT PRIMARY KEY REFERENCES daily_reports(id),artifact_id TEXT NOT NULL REFERENCES review_artifacts(id));
CREATE TABLE IF NOT EXISTS report_supplements(id TEXT PRIMARY KEY,message_json TEXT NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL,sent_at TEXT,receipt_json TEXT);
CREATE TRIGGER IF NOT EXISTS review_artifact_immutable BEFORE UPDATE ON review_artifacts BEGIN SELECT RAISE(ABORT,'Review artifacts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS review_artifact_retain BEFORE DELETE ON review_artifacts BEGIN SELECT RAISE(ABORT,'Review artifacts must be retained'); END;
CREATE TRIGGER IF NOT EXISTS supplement_message_immutable BEFORE UPDATE OF message_json ON report_supplements BEGIN SELECT RAISE(ABORT,'Supplement messages are immutable'); END;
'''

class ApplicationReview:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA)

    def plan(self,pid):
        p=self.s.one('SELECT p.*,o.program,o.cycle FROM application_plans p JOIN opportunities o ON o.id=p.opportunity_id WHERE p.id=?',(pid,))
        payload=json.loads(p['payload_json']);adapter=self.db.execute('SELECT * FROM application_adapters WHERE opportunity_id=?',(p['opportunity_id'],)).fetchone();rows=[]
        if adapter:
            for f in json.loads(adapter['definition_json'])['fields']:
                if f['type']=='hidden':continue
                value=payload['fields'].get(f['name']);rows.append({'question':f['label'] or f['name'],'field':f['name'],'required':f.get('required',False),'limit':f.get('maxlength'),'answer':value,'state':'FILLED IN OS PLAN' if value is not None else 'UNFILLED','fact_version':payload.get('claim_versions',{}).get(f['name']),'answer_version':payload.get('answer_versions',{}).get(f['name'])})
        failure=self.db.execute("SELECT payload_json FROM audit WHERE event='application.form_inspection_incomplete' AND json_extract(payload_json,'$.url')=? ORDER BY created_at DESC,rowid DESC LIMIT 1",(payload.get('application_url'),)).fetchone()
        return {'plan_id':pid,'program':p['program'],'cycle':p['cycle'],'state':p['state'],'email':p['selected_email'],'url':payload.get('application_url'),'form_checked_at':adapter['checked_at'] if adapter else None,'form_inspection_failure':json.loads(failure['payload_json']) if failure else None,'form_fingerprint':payload.get('form_fingerprint'),'questions':rows,'blockers':json.loads(p['blockers_json']),'submission_note':'Prepared locally. No live form submission or owner confirmation is implied.'}

    def historical(self):
        return self.s.rows('''SELECT q.id question_id,q.application_id,q.ordinal,q.prompt,q.required,q.limit_value,q.limit_unit,q.checked,q.locator,a.id answer_version,a.body,a.created_at,r.status,s.original_path,ap.title
          FROM questions q JOIN applications ap ON ap.id=q.application_id
          LEFT JOIN answer_versions a ON a.id=(SELECT v.id FROM answer_versions v WHERE v.question_id=q.id ORDER BY v.created_at DESC,v.rowid DESC LIMIT 1)
          LEFT JOIN answer_reviews r ON r.version_id=a.id
          LEFT JOIN source_versions sv ON sv.id=q.source_version_id LEFT JOIN sources s ON s.id=sv.source_id ORDER BY ap.title,q.ordinal''')

    def text(self,pid=None):
        plans=[self.plan(pid)] if pid else [self.plan(p['id']) for p in self.s.rows("SELECT id FROM application_plans WHERE state!='SUPERSEDED' ORDER BY created_at")]
        lines=['A STORY — QUESTIONS & ANSWERS REVIEW', 'Generated: '+now(),'PRIVATE — for gbao.n.vo@gmail.com only.','NOT SUBMITTED. A report or text file is not submission approval.','FILLED IN OS PLAN means a local prepared value, not an externally filled or submitted form.','Unknown official questions are not guessed. Historical essays require validation against current company memory.','']
        for p in plans:
            lines += ['='*60,p['program']+' — '+p['cycle'],'Plan: '+p['plan_id'],'Status: '+p['state'],'Application URL: '+str(p['url'] or 'UNKNOWN'),'Application email: '+p['email'],'Official form checked: '+str(p['form_checked_at'] or 'UNKNOWN'),'Form fingerprint: '+str(p['form_fingerprint'] or 'UNKNOWN'),'']
            if not p['questions']:lines+=['OFFICIAL QUESTIONS UNKNOWN — form needs inspection; login or dynamic forms may require founder review.','No answers have been filled for this form.']
            if p['form_inspection_failure']:
                failure=p['form_inspection_failure'];lines+=['Last incomplete inspection: '+str(failure.get('checked_at','UNKNOWN')),'Reason: '+failure['reason']]
            for n,q in enumerate(p['questions'],1):
                lines+=['QUESTION '+str(n)+': '+q['question'],'Field: '+q['field'],'Required: '+str(q['required'])+' | Character limit: '+str(q['limit'] or 'UNKNOWN'),'State: '+q['state'],'ANSWER:','[blank]' if q['answer'] is None else q['answer'],'Fact version: '+str(q['fact_version'] or 'none'),'Answer version: '+str(q['answer_version'] or 'none'),'']
            lines+=['BLOCKERS:']+['- '+b for b in p['blockers']]+['']
        if not pid:
            lines+=['='*60,'SAVED APPLICATION QUESTIONS & ESSAY DRAFTS','These are saved source questions and draft answers; they have not been filled into a current official form.','']
            for q in self.historical():
                lines+=['Application: '+q['title'],'QUESTION: '+q['prompt'],'Source: '+str(q['original_path'] or 'unknown'),'Locator: '+str(q['locator']),'Question ID: '+q['question_id'],'Current official form verified: '+('yes' if q['checked'] else 'NO — historical / unverified'),'Limit: '+str(q['limit_value'] or 'UNKNOWN')+' '+str(q['limit_unit'] or ''),'Answer state: SAVED '+str(q['status'] or 'UNFILLED').upper()+' — NOT LIVE FORM','Answer version: '+str(q['answer_version'] or 'none'),'ANSWER:',q['body'] or '[blank]','']
            try:
                count=self.s.one('SELECT count(*) total,sum(body IS NOT NULL) text_count FROM material_library')
                lines+=['MATERIALS LIBRARY',str(count['total'])+' source references; '+str(count['text_count'] or 0)+' files with searchable text.','Full provenance manifest and original downloads: '+founder_url('/materials'),'Historical materials remain references, not approved current facts.','']
            except sqlite3.OperationalError as e:
                if 'no such table: material_library' not in str(e):raise
        return '\n'.join(lines)+'\n'

    def snapshot(self,pid=None):
        body=self.text(pid);sha=digest(body.encode('utf-8'));key='review-'+sha[:24];filename='A-Story-questions-and-answers-'+sha[:12]+'.txt'
        self.db.execute('INSERT OR IGNORE INTO review_artifacts VALUES(?,?,?,?,?)',(key,filename,body,sha,now()))
        folder=self.s.path.parent/'application-previews';folder.mkdir(parents=True,exist_ok=True);path=folder/filename
        if path.exists() and digest(path.read_bytes())!=sha:raise PolicyError('Saved review file changed; do not email it')
        if not path.exists():path.write_bytes(body.encode('utf-8'))
        return self.attachment(key)

    def attachment(self,key):
        r=self.s.one('SELECT * FROM review_artifacts WHERE id=?',(key,))
        if digest(r['body'].encode('utf-8'))!=r['sha256']:raise PolicyError('Review attachment integrity mismatch')
        return {'artifact_id':r['id'],'filename':r['filename'],'mime_type':'text/plain','sha256':r['sha256'],'content':r['body']}

    def report_attachment(self,rid):
        row=self.db.execute('SELECT artifact_id FROM report_attachments WHERE report_id=?',(rid,)).fetchone()
        return [self.attachment(row['artifact_id'])] if row else []

    def supplement(self):
        # A distinct owner-requested supplement preserves an already sent daily report.
        a=self.snapshot();key='report-supplement-'+a['sha256'][:24]
        m={'id':key,'recipient':'gbao.n.vo@gmail.com','subject':'A Story — questions, prepared answers & pitch materials','body':'Your requested question-and-answer text preview is attached. It includes known questions, locally prepared values, saved essay drafts, blank fields and blockers. Unknown official questions are explicitly labeled. No application has been submitted. Review your searchable pitch materials at '+founder_url('/materials')+'. Each future daily report will include this text preview. Every submission still requires your individual confirmation of its exact emailed preview.','attachments':[a]}
        self.db.execute("INSERT OR IGNORE INTO report_supplements VALUES(?,?,'PENDING',?,NULL,NULL)",(key,js(m),now()))
        return key
