from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else js(value).encode()).hexdigest()


def uid(prefix):
    return prefix + '-' + uuid.uuid4().hex


class PolicyError(ValueError):
    pass


EXTERNAL_ACTIONS = frozenset({'send_email', 'submit_application', 'publish', 'delete', 'spend_money', 'destructive_change'})
INTERNAL_REVIEW_ACTIONS = frozenset({'promote_claim', 'approve_answer', 'record_submission'})
TOPICS = frozenset({'product_description','positioning','pricing','traction','team','market','competitors','features','customer_evidence','fundraising','approved_language','rejected_language'})


class Store:
    """Single-user local store. Agent workers receive methods, never owner credentials.

    Owner approval is an explicit local CLI action. This is not an authentication
    boundary against someone who can edit the database or Python files.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=10000')
        self.db.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def rows(self, sql, values=()):
        return [dict(r) for r in self.db.execute(sql, values)]

    def one(self, sql, values=()):
        r = self.db.execute(sql, values).fetchone()
        if r is None:
            raise ValueError('Record not found')
        return dict(r)

    def log(self, event, actor, payload):
        self.db.execute('INSERT INTO audit(event,actor,payload_json,created_at) VALUES(?,?,?,?)', (event, actor, js(payload), now()))

    def import_source(self, path, kind, classification, expected_sha256=None, text=None, extraction='reference_only', document_date=None):
        p = Path(path).resolve()
        raw = p.read_bytes()
        sha = digest(raw)
        if expected_sha256 and sha != expected_sha256:
            raise ValueError('Source changed since inventory: ' + str(p))
        sid = 'source-' + digest(str(p))[:24]
        vid = 'sv-' + digest([sid, sha])[:24]
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?)', (sid,str(p),kind,classification,now()))
            existing = self.db.execute('SELECT id FROM source_versions WHERE id=?', (vid,)).fetchone()
            if not existing:
                self.db.execute('INSERT INTO source_versions VALUES(?,?,?,?,?,?,?,?,?)', (vid,sid,sha,len(raw),now(),document_date,None,text,extraction))
                self.import_receipt(vid,'source_version',vid,'entire file',extraction)
                self.log('source.imported','ingestion',{'source_id':sid,'version_id':vid,'sha256':sha,'original_path':str(p)})
        return vid

    def import_receipt(self, source_version, destination_type, destination_id, locator, transformation):
        self.db.execute('INSERT OR IGNORE INTO imports VALUES(?,?,?,?,?,?,?)', (uid('import'),source_version,destination_type,destination_id,locator,transformation,now()))

    def propose_claim(self, topic, label, body, evidence_status, source_version, locator, claim_id=None, last_verified_at=None):
        if topic not in TOPICS:
            raise ValueError('Unknown claim topic')
        if not locator.strip() or not body.strip():
            raise ValueError('A claim needs text and a precise source locator')
        if evidence_status=='verified' and not last_verified_at:
            raise ValueError('Verified evidence requires a verification date')
        self.one('SELECT id FROM source_versions WHERE id=?',(source_version,))
        cid=claim_id or 'claim-'+digest([topic,label])[:20]
        vid='cv-'+digest([cid,body,evidence_status,source_version,locator,last_verified_at])[:24]
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO claims VALUES(?,?,?,NULL)',(cid,topic,label))
            c=self.one('SELECT * FROM claims WHERE id=?',(cid,))
            if c['topic']!=topic or c['label']!=label:
                raise ValueError('Claim ID already has a different meaning')
            self.db.execute('INSERT OR IGNORE INTO claim_versions VALUES(?,?,?,?,?,?,?,?,?,?)',(vid,cid,body,evidence_status,source_version,locator,last_verified_at,None,now(),c['canonical_version_id']))
            self.db.execute('INSERT OR IGNORE INTO claim_reviews VALUES(?,\'proposed\',NULL)',(vid,))
            self.import_receipt(source_version,'claim_version',vid,locator,'proposed claim; not a canonical promotion')
        return vid

    def issue(self, kind, title, detail, sources):
        iid='issue-'+digest([kind,title])[:20]
        for source in sources:
            self.one('SELECT id FROM source_versions WHERE id=?',(source,))
        self.db.execute('INSERT OR IGNORE INTO issues VALUES(?,?,?,?,?,\'open\',?)',(iid,kind,title,detail,js(sources),now()))
        return iid

    def upsert_opportunity(self, organizer, program, cycle, source_version=None, **details):
        key='|'.join(re.sub(r'\s+',' ',v.strip().casefold()) for v in (organizer,program,cycle))
        if not all((organizer.strip(),program.strip(),cycle.strip())):
            raise ValueError('Organizer, program and cycle are required')
        oid='opp-'+digest(key)[:20]
        existing=self.db.execute('SELECT id FROM opportunities WHERE dedup_key=?',(key,)).fetchone()
        if existing:
            return existing[0]
        score=details.get('fit_score')
        if score is not None and not 0<=score<=100:
            raise ValueError('Fit score must be 0 through 100 or unknown')
        self.db.execute('INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid,key,organizer,program,cycle,details.get('official_url'),details.get('deadline'),details.get('deadline_timezone'),js(details.get('terms',{})),details.get('eligibility','unknown'),score,details.get('fit_reason','Not assessed'),details.get('state','needs_research'),details.get('last_checked_at'),source_version))
        return oid

    def create_application(self, opportunity_id, title):
        aid='app-'+digest([opportunity_id,title])[:20]
        self.db.execute('INSERT OR IGNORE INTO applications VALUES(?,?,?,\'draft\',?)',(aid,opportunity_id,title,now()))
        return aid

    def add_question(self, application_id, ordinal, prompt, source_version, locator, limit_value=None, limit_unit=None, checked=False):
        qid='q-'+digest([application_id,ordinal,prompt,limit_value,limit_unit])[:20]
        self.db.execute('INSERT OR IGNORE INTO questions VALUES(?,?,?,?,?,?,?,?,?,?)',(qid,application_id,ordinal,prompt,limit_value,limit_unit,1,source_version,locator,int(checked)))
        self.import_receipt(source_version,'question',qid,locator,'question parsed from unfinalized template')
        return qid

    def add_answer(self, question_id, body, source_versions, fact_versions=(), unresolved=(), provenance='drafted', supersedes=None):
        self.one('SELECT id FROM questions WHERE id=?',(question_id,))
        if not source_versions:
            raise ValueError('An answer needs provenance')
        for source in source_versions:
            self.one('SELECT id FROM source_versions WHERE id=?',(source,))
        for fact in fact_versions:
            self.one('SELECT id FROM claim_versions WHERE id=?',(fact,))
        if supersedes:
            old=self.one('SELECT * FROM answer_versions WHERE id=?',(supersedes,))
            if old['question_id']!=question_id:
                raise ValueError('Answer revision must refer to the same question')
        vid='answer-'+digest([question_id,body,source_versions,fact_versions,unresolved,provenance])[:24]
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO answer_versions VALUES(?,?,?,?,?,?,?,?,?)',(vid,question_id,body,js(list(fact_versions)),js(list(source_versions)),js(list(unresolved)),now(),supersedes,provenance))
            self.db.execute('INSERT OR IGNORE INTO answer_reviews VALUES(?,\'draft\',NULL)',(vid,))
            for source in source_versions:
                self.import_receipt(source,'answer_version',vid,'question '+question_id,provenance)
        return vid

    def answer_readiness(self, version_id):
        a=self.one('SELECT a.*,q.limit_value,q.limit_unit,q.checked FROM answer_versions a JOIN questions q ON q.id=a.question_id WHERE a.id=?',(version_id,))
        blockers=list(json.loads(a['unresolved_json']))
        count=len(a['body'].split()) if a['limit_unit']=='words' else len(a['body'])
        if a['limit_value'] is not None and count>a['limit_value']:
            blockers.append(f"Over {a['limit_unit']} limit: {count}/{a['limit_value']}")
        if not a['body'].strip():blockers.append('Answer is empty')
        if not a['checked']:blockers.append('Original application prompt and limit need confirmation')
        dependencies=set(json.loads(a['sources_json']))
        for fid in json.loads(a['facts_json']):
            f=self.one('SELECT v.*,c.canonical_version_id FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=?',(fid,))
            if f['canonical_version_id']!=fid:blockers.append('Fact is unapproved or superseded: '+fid)
            if f['valid_until'] and f['valid_until']<now():blockers.append('Fact requires re-verification: '+fid)
            dependencies.add(f['source_version_id'])
        for sid in dependencies:
            version=self.one('SELECT source_id,captured_at FROM source_versions WHERE id=?',(sid,))
            newer=self.db.execute('SELECT 1 FROM source_versions WHERE source_id=? AND captured_at>? LIMIT 1',(version['source_id'],version['captured_at'])).fetchone()
            if newer:blockers.append('A newer source version needs review: '+sid)
        for issue in self.rows("SELECT sources_json FROM issues WHERE kind='source_change' AND state='open'"):
            if dependencies & set(json.loads(issue['sources_json'])):blockers.append('A linked original source changed; review its new version')
        return {'version_id':version_id,'count':count,'character_count':len(a['body']),'word_count':len(a['body'].split()),'limit':a['limit_value'],'unit':a['limit_unit'] or 'characters','blockers':blockers,'ready_for_review':not blockers}

    def request_approval(self, action, payload, actor='founder', expected_version=None):
        if action not in EXTERNAL_ACTIONS|INTERNAL_REVIEW_ACTIONS:
            raise PolicyError('Unknown action denied')
        if action=='promote_claim':
            v=self.one('SELECT claim_id FROM claim_versions WHERE id=?',(payload['version_id'],))
            current=self.one('SELECT canonical_version_id FROM claims WHERE id=?',(v['claim_id'],))['canonical_version_id']
            expected_version=current
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='company_fact_values'").fetchone():
                payload={**payload,'structured_values':self.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=? ORDER BY fact_key',(payload['version_id'],))}
        aid=uid('approval')
        self.db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,\'pending\',?,?,NULL,NULL,NULL)',(aid,action,js(payload),digest(payload),expected_version,actor,now()))
        self.log('approval.requested',actor,{'id':aid,'action':action,'payload_sha256':digest(payload)})
        return aid

    def decide(self, approval_id, decision, owner_confirmation=False, note=''):
        if not owner_confirmation:
            raise PolicyError('Only an explicit owner decision may approve or reject')
        if decision not in {'approved','rejected'}:raise ValueError('Invalid decision')
        with self.transaction():
            a=self.one('SELECT * FROM approvals WHERE id=?',(approval_id,))
            if a['state']!='pending':raise PolicyError('Approval is already decided')
            payload=json.loads(a['payload_json'])
            if digest(payload)!=a['payload_sha256']:raise PolicyError('Approval payload was changed')
            if decision=='approved':
                if a['action'] in EXTERNAL_ACTIONS:
                    raise PolicyError('External action connector is not installed; no action taken')
                if a['action']=='promote_claim':
                    v=self.one('SELECT * FROM claim_versions WHERE id=?',(payload['version_id'],))
                    c=self.one('SELECT * FROM claims WHERE id=?',(v['claim_id'],))
                    if 'structured_values' in payload:
                        actual=self.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=? ORDER BY fact_key',(v['id'],))
                        if actual!=payload['structured_values']:raise PolicyError('Structured facts changed after review')
                    if c['canonical_version_id']!=a['expected_version']:
                        raise PolicyError('Canonical value changed since this approval was prepared')
                    self.db.execute('UPDATE claims SET canonical_version_id=? WHERE id=?',(v['id'],c['id']))
                    self.db.execute('UPDATE claim_reviews SET status=\'approved\',approval_id=? WHERE version_id=?',(approval_id,v['id']))
                elif a['action']=='approve_answer':
                    readiness=self.answer_readiness(payload['version_id'])
                    if readiness['blockers']:raise PolicyError('; '.join(readiness['blockers']))
                    self.db.execute('UPDATE answer_reviews SET status=\'approved\',approval_id=? WHERE version_id=?',(approval_id,payload['version_id']))
                elif a['action']=='record_submission':
                    frozen=self.build_submission_payload(payload['application_id'],payload['answer_versions'],payload['files'],payload['submitted_at'],payload['receipt'])
                    if frozen!=payload:raise PolicyError('Submission payload changed after review')
                    for file in payload['files']:
                        raw=Path(file['path']).read_bytes()
                        if digest(raw)!=file['sha256']:raise PolicyError('File changed during submission capture')
                        self.db.execute('INSERT OR IGNORE INTO submission_blobs VALUES(?,?)',(file['sha256'],raw))
                    self.db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?,?)',(uid('submission'),payload['application_id'],payload['submitted_at'],payload['receipt'],js(payload),digest(payload),approval_id,now()))
            elif a['action']=='promote_claim':
                self.db.execute("UPDATE claim_reviews SET status='rejected',approval_id=? WHERE version_id=? AND status='proposed'",(approval_id,payload['version_id']))
            elif a['action']=='approve_answer':
                self.db.execute("UPDATE answer_reviews SET status='rejected',approval_id=? WHERE version_id=? AND status='draft'",(approval_id,payload['version_id']))
            self.db.execute('UPDATE approvals SET state=?,decided_by=\'local_owner\',decided_at=?,decision_note=? WHERE id=?',(decision,now(),note,approval_id))
            self.log('approval.'+decision,'local_owner',{'approval_id':approval_id,'action':a['action'],'payload_sha256':a['payload_sha256']})

    def approved_answers(self, query=''):
        answers=self.rows('SELECT a.*,q.prompt,q.application_id FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id JOIN questions q ON q.id=a.question_id WHERE r.status=\'approved\' ORDER BY a.created_at DESC')
        terms=set(re.findall(r'\w+',query.casefold()))
        eligible=[{**a,'match_score':len(terms & set(re.findall(r'\w+',(a['prompt']+' '+a['body']).casefold())))} for a in answers if not self.answer_readiness(a['id'])['blockers']]
        return sorted(eligible,key=lambda a:-a['match_score'])

    def build_submission_payload(self, application_id, answer_versions, files, submitted_at, receipt):
        if not receipt.strip():raise PolicyError('An actual submission receipt/reference is required')
        when=datetime.fromisoformat(submitted_at)
        if when.tzinfo is None or when>datetime.now(timezone.utc):raise PolicyError('Submission time must be an actual past timestamp with timezone')
        app=self.one('SELECT * FROM applications WHERE id=?',(application_id,))
        questions=self.rows('SELECT * FROM questions WHERE application_id=? ORDER BY ordinal',(application_id,))
        if not questions:raise PolicyError('Application has no checked questions to freeze')
        snapshots=[];seen=set()
        for vid in answer_versions:
            a=self.one('SELECT a.*,r.status FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id WHERE a.id=?',(vid,))
            q=next((q for q in questions if q['id']==a['question_id']),None)
            if not q or q['id'] in seen:raise PolicyError('Duplicate or foreign application answer')
            if a['status']!='approved' or self.answer_readiness(vid)['blockers']:raise PolicyError('Answer is not approved and current')
            seen.add(q['id'])
            facts=[self.one('SELECT * FROM claim_versions WHERE id=?',(fid,)) for fid in json.loads(a['facts_json'])]
            source_ids=set(json.loads(a['sources_json']))|{f['source_version_id'] for f in facts}
            sources=[self.one('SELECT v.id,v.sha256,v.source_id,s.original_path FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE v.id=?',(sid,)) for sid in sorted(source_ids)]
            snapshots.append({'question':q,'answer':a,'facts':facts,'sources':sources})
        if any(q['required'] and q['id'] not in seen for q in questions):raise PolicyError('Required questions are missing')
        for f in files:
            if not f.get('path') or not re.fullmatch('[a-f0-9]{64}',f.get('sha256','')):raise PolicyError('Every submitted file needs its original path and SHA-256')
            if digest(Path(f['path']).read_bytes())!=f['sha256']:raise PolicyError('Submitted file bytes changed')
        return {'application_id':app['id'],'answer_versions':list(answer_versions),'answers':snapshots,'files':files,'submitted_at':submitted_at,'receipt':receipt}

    def prepare_submission_record(self, application_id, answer_versions, files, submitted_at, receipt):
        payload=self.build_submission_payload(application_id,answer_versions,files,submitted_at,receipt)
        return self.request_approval('record_submission',payload,actor='application')

    def snapshots(self, program):
        return self.rows('SELECT s.* FROM submissions s JOIN applications a ON a.id=s.application_id JOIN opportunities o ON o.id=a.opportunity_id WHERE o.program LIKE ? ORDER BY s.submitted_at DESC',('%'+program+'%',))

    def export_ledger(self):
        return self.rows('SELECT i.*,s.original_path,v.sha256,v.captured_at,v.last_verified_at FROM imports i JOIN source_versions v ON v.id=i.source_version_id JOIN sources s ON s.id=v.source_id ORDER BY i.imported_at,i.id')
