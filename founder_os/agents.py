"""Offline specialist handlers. These are deterministic tools, not model agents.

A future model may compose these tools through the Founder dispatcher. No
network, subprocess, spending or owner-decision method is exposed to handlers.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .store import digest, js, now, uid, PolicyError


CAPABILITIES = {
    'funding_hunter': 'Run the integrated Funding Hunter on sourced research observations',
    'opportunity_scout': 'Deduplicate and assess supplied opportunity records',
    'application': 'Review question coverage, limits and answer evidence',
    'pitch': 'Register a sourced draft and estimate delivery duration',
    'research': 'Retrieve cited passages from selected local source snapshots',
    'follow_up': 'Inspect known deadline records and prepare a follow-up review',
    'customer_evidence': 'Register supplied, attributed customer evidence',
    'consistency_truth': 'Check source changes and risky language in draft sources',
}


class Founder:
    def __init__(self, store):
        self.store=store

    def _funding_hunter(self,payload):
        from .funding_hunter import FundingHunter
        return FundingHunter(self.store).runFundingHunter(payload,payload.get('request_key'))

    def enqueue(self, capability, payload, idempotency_key=None):
        if capability not in CAPABILITIES:
            raise PolicyError('Unknown or external capability denied')
        if not isinstance(payload,dict):raise ValueError('Job payload must be an object')
        key=idempotency_key or digest([capability,payload])
        jid='job-'+digest(key)[:24]
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM jobs WHERE idempotency_key=?',(key,)).fetchone()
            if old and (old['capability']!=capability or old['input_json']!=js(payload)):
                raise ValueError('Idempotency key belongs to a different request')
            if not old:
                self.store.db.execute('INSERT INTO jobs VALUES(?,?,?, ?,\'queued\',0,3,NULL,NULL,NULL,?,?)',(jid,capability,js(payload),key,now(),now()))
                self.store.log('job.queued','founder',{'job_id':jid,'capability':capability})
        return jid

    def run_one(self):
        with self.store.transaction():
            self.store.db.execute("UPDATE jobs SET state=CASE WHEN attempts<max_attempts THEN 'queued' ELSE 'failed' END,error='Previous worker lease expired',lease_until=NULL,updated_at=? WHERE state='running' AND lease_until<?",(now(),now()))
            job=self.store.db.execute("SELECT * FROM jobs WHERE state='queued' AND attempts<max_attempts ORDER BY created_at,id LIMIT 1").fetchone()
            if job is None:return None
            job=dict(job)
            lease=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
            self.store.db.execute("UPDATE jobs SET state='running',attempts=attempts+1,lease_until=?,updated_at=? WHERE id=?",(lease,now(),job['id']))
        try:
            result=getattr(self,'_'+job['capability'])(json.loads(job['input_json']))
            self.store.db.execute("UPDATE jobs SET state='complete',result_json=?,error=NULL,lease_until=NULL,updated_at=? WHERE id=?",(js(result),now(),job['id']))
            self.store.log('job.completed',job['capability'],{'job_id':job['id']})
        except Exception as e:
            self.store.db.execute("UPDATE jobs SET state='failed',error=?,lease_until=NULL,updated_at=? WHERE id=?",(str(e),now(),job['id']))
            self.store.log('job.failed',job['capability'],{'job_id':job['id'],'error':str(e)})
        return self.store.one('SELECT * FROM jobs WHERE id=?',(job['id'],))

    def retry(self, job_id):
        with self.store.transaction():
            job=self.store.one('SELECT * FROM jobs WHERE id=?',(job_id,))
            if job['state']!='failed' or job['attempts']>=job['max_attempts']:
                raise ValueError('Only failed jobs with remaining attempts can be retried')
            self.store.db.execute("UPDATE jobs SET state='queued',updated_at=? WHERE id=?",(now(),job_id))

    def _opportunity_scout(self, payload):
        results=[]
        for item in payload.get('opportunities',[]):
            # No false precision: unknown criteria mean the fit score stays unknown.
            criteria=item.get('criteria',{})
            allowed=('eligibility','stage_fit','geographic_fit','sector_fit','terms_fit')
            known=[criteria.get(k) for k in allowed]
            if any(v not in (None,True,False) for v in known):raise ValueError('Fit criteria must be true, false or unknown')
            score=round(100*sum(v is True for v in known)/len(known)) if all(v is not None for v in known) else None
            recommendation='skip' if criteria.get('eligibility') is False else ('review_apply' if score is not None and score>=80 else 'research_required')
            oid=self.store.upsert_opportunity(item['organizer'],item['program'],item['cycle'],item.get('source_version_id'),official_url=item.get('official_url'),deadline=item.get('deadline'),deadline_timezone=item.get('deadline_timezone'),terms=item.get('terms',{}),eligibility='eligible_reported' if criteria.get('eligibility') is True else ('ineligible_reported' if criteria.get('eligibility') is False else 'unknown'),fit_score=score,fit_reason='Supplied criteria only; not independently verified',state=recommendation)
            results.append({'opportunity_id':oid,'proposed_fit_score':score,'recommendation':recommendation,'verification':'supplied_only'})
        return {'records':results,'live_search_performed':False}

    def _application(self, payload):
        app=self.store.one('SELECT * FROM applications WHERE id=?',(payload['application_id'],))
        result=[]
        for q in self.store.rows('SELECT * FROM questions WHERE application_id=? ORDER BY ordinal',(app['id'],)):
            answers=self.store.rows('SELECT id FROM answer_versions WHERE question_id=? ORDER BY created_at DESC',(q['id'],))
            result.append({'question_id':q['id'],'prompt':q['prompt'],'limit':q['limit_value'],'unit':q['limit_unit'],'source_checked':bool(q['checked']),'versions':[self.store.answer_readiness(a['id']) for a in answers],'approved_reuse_candidates':[a['id'] for a in self.store.approved_answers(q['prompt'])[:3]]})
        ready=bool(result) and all(q['source_checked'] and any(v['ready_for_review'] and self.store.one('SELECT status FROM answer_reviews WHERE version_id=?',(v['version_id'],))['status']=='approved' for v in q['versions']) for q in result)
        return {'application_id':app['id'],'questions':result,'submission_ready':ready,'status':'internal readiness review; no submission performed'}

    def _pitch(self,payload):
        duration=payload['duration_seconds']
        if duration not in (30,60,180,300,900,1200):raise ValueError('Choose 30, 60, 180, 300, 900 or 1200 seconds')
        body=payload['body'];facts=payload.get('claim_versions',[])
        for fid in facts:self.store.one('SELECT id FROM claim_versions WHERE id=?',(fid,))
        pid='pitch-'+digest(payload)[:24]
        source=payload.get('source_version_id')
        self.store.db.execute('INSERT OR IGNORE INTO pitches VALUES(?,?,?,?,?,\'draft\',?,?)',(pid,duration,payload.get('audience','general'),body,js(facts),now(),source))
        if source:self.store.import_receipt(source,'pitch',pid,'draft narrative','revised wording; unapproved')
        wc=len(body.split())
        return {'pitch_id':pid,'word_count':wc,'estimated_seconds_at_130_wpm':round(wc/130*60),'target_seconds':duration,'status':'draft','requires_rehearsal':True}

    def _research(self,payload):
        query=payload.get('query','')
        terms=set(re.findall(r'\w+',query.casefold()))
        limit=min(20,max(1,int(payload.get('limit',8))))
        results=[]
        for src in self.store.rows('SELECT v.*,s.original_path FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE v.body IS NOT NULL'):
            lines=src['body'].splitlines()
            for start in range(0,len(lines),12):
                text='\n'.join(lines[start:start+12]);score=len(terms & set(re.findall(r'\w+',text.casefold())))
                if score:
                    results.append({'source_version_id':src['id'],'path':src['original_path'],'sha256':src['sha256'],'locator':f'lines {start+1}-{min(start+12,len(lines))}','text':text,'score':score,'evidence_status':'source_text_not_verified'})
        results.sort(key=lambda x:-x['score'])
        return {'query':query,'citations':results[:limit],'live_web_research':False}

    def _follow_up(self,payload):
        due=[];unverified=[];until=datetime.now(timezone.utc)+timedelta(days=int(payload.get('days',30)))
        for r in self.store.rows('SELECT * FROM opportunities'):
            if not r['deadline'] or not r['deadline_timezone'] or not r['last_checked_at']:
                unverified.append({'opportunity_id':r['id'],'reason':'Deadline, timezone or current verification missing'});continue
            try:
                dt=datetime.fromisoformat(r['deadline'])
                if dt.tzinfo is None:raise ValueError('No timezone offset')
                if dt<=until:due.append({'opportunity_id':r['id'],'deadline':r['deadline'],'state':'overdue' if dt<datetime.now(timezone.utc) else 'upcoming'})
            except ValueError:unverified.append({'opportunity_id':r['id'],'reason':'Deadline timestamp needs confirmation'})
        return {'due':due,'unverified':unverified,'messages_sent':0,'calendar_connected':False}

    def _customer_evidence(self,payload):
        ids=[]
        for item in payload.get('items',[]):
            if item['kind'] not in ('pilot_feedback','testimonial','objection','product_learning','reported_metric','analyst_review'):
                raise ValueError('Unrecognized evidence kind')
            if not item.get('locator'):raise ValueError('Evidence requires its source locator')
            eid='evidence-'+digest(item)[:24]
            self.store.db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?)',(eid,item['kind'],item['body'],item['source_version_id'],item['locator'],item.get('permission_status','internal_only_unverified'),item.get('submission_id'),now()))
            self.store.import_receipt(item['source_version_id'],'evidence',eid,item['locator'],'attributed internal evidence, not canonical traction')
            ids.append(eid)
        return {'evidence_ids':ids,'canonical_facts_changed':0}

    def _consistency_truth(self,payload):
        findings=[]
        for src in self.store.rows('SELECT v.*,s.original_path,s.kind FROM source_versions v JOIN sources s ON s.id=v.source_id'):
            if payload.get('check_source_changes',False):
                p=Path(src['original_path'])
                if not p.exists():
                    findings.append({'source':src['id'],'issue':'Original source is unavailable'})
                elif digest(p.read_bytes())!=src['sha256']:
                    iid=self.store.issue('source_change','Source changed '+src['id'],'A new source version needs ingestion and dependent answer review.',[src['id']]);findings.append({'source':src['id'],'issue_id':iid})
            if src['kind']=='unfinalized_essay' and src['body']:
                patterns={'Unverified permanence promise':r'\bforever\b','Blanket competitor claim':r'competitors end in one book|most of the category still ends','Runway must follow cash and burn':r'12 tháng|3 months runway','Modeled margins need reconciliation':r'55[–-]67%','Future affiliation needs correct wording':r'I.m Daniel from UIUC'}
                for title,pattern in patterns.items():
                    matches=[{'line':i+1,'quote':line.strip()} for i,line in enumerate(src['body'].splitlines()) if re.search(pattern,line,re.I)]
                    if matches:
                        iid=self.store.issue('language_review',title,js(matches),[src['id']]);findings.append({'issue_id':iid,'matches':matches})
        for answer in self.store.rows('SELECT a.id FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id WHERE r.status=\'approved\''):
            check=self.store.answer_readiness(answer['id'])
            if check['blockers']:findings.append({'answer':answer['id'],'blockers':check['blockers']})
        return {'findings':findings,'method':'explicit checks and patterns; not exhaustive semantic contradiction detection','canonical_facts_changed':0}
