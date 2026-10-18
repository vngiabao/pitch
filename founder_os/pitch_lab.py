"""Pitch Lab: the assembly line every outward-facing draft moves through (AGENT-SYSTEM.md).

Pitch Tailor drafts a program edition, Fact Guard checks every number and rule, Bao's Voice rewrites
the wording only, Pitch Coach scores it like a YC partner and sends it back with fixes, Format Check
times it. Bao is always the last step. Results and Bao's own edits feed lessons and voice examples
that every later run reads. Agents prepare; nothing here submits, sends or posts anything.
"""
import json
import re
from pathlib import Path
from .store import now,js,digest,uid
from .funding_hunter import FundingHunter
from .product_desk import measured_numbers

ROOT=Path(__file__).resolve().parents[1]
PIPELINE_PREFIX='Pipeline: '
MAX_ROUNDS=3
PASS_SCORE=4
WORDS_PER_MINUTE=140
LLM_STAGES=('TAILOR','VOICE','COACH','LEARN')
FLOW={'PITCH_EDITION':('TAILOR','FACT_CHECK','VOICE','FACT_RECHECK','COACH','FORMAT','BUILD','SLIDE_QA','READY'),
      'PITCH_REVIEW':('FACT_CHECK','COACH','READY'),
      'APPLICATION_SET':('FACT_CHECK','VOICE','FACT_RECHECK','COACH','FORMAT','READY'),
      'GROWTH_DRAFT':('FACT_CHECK','VOICE','FACT_RECHECK','READY'),
      'OUTCOME_LESSON':('LEARN','READY'),
      'VOICE_RULES':('LEARN','READY')}
STAGE_WORDS={'TAILOR':'Pitch Tailor is drafting','FACT_CHECK':'Fact Guard is checking','VOICE':'Bao’s Voice is editing','FACT_RECHECK':'Fact Guard is rechecking',
             'COACH':'Pitch Coach is reviewing','FORMAT':'Checking time and limits','BUILD':'Building the deck','SLIDE_QA':'Checking every slide','LEARN':'Learning from the result','READY':'Ready for you','APPROVED':'Approved by you','ARCHIVED':'Archived'}
CRITERIA=('Clarity','Problem urgency','Insight','Why now','Evidence','Business','Defensibility','Team','The ask','Delivery')
STORY_SLIDES=('cover','legacy-gap','retelling','want-to-know','cant-wait','todays-options','meet-a-story','every-narrator','the-everyday','why-now')
HYPE=('leverage','leverages','empower','empowers','seamless','seamlessly','revolutionize','revolutionary','cutting-edge','game-changer','game changer','testament','tapestry','delve','robust','curated','journey',
      'pivotal','crucial','transformative','unlock','landscape','elevate','world-class','groundbreaking','renowned','profound','exemplifies','underscores','underscoring','highlighting','showcasing','fostering','ensuring')
# Written-language staging that does not survive being said out loud (BAO-VOICE.md, "Spoken, not written").
WRITTEN=(r"\bnot (just|only|merely) \w+[^.]{0,60}\bbut\b",r"\bit'?s not (just |only )?[^.]{0,40}, it'?s\b",r"\bhere'?s the thing\b",r"\bthe real question\b",r"\bat its core\b",r"\bwhat really matters\b",r"\blet'?s dive\b",r"\bserves as\b",r"\bstands as\b",r"\bboasts\b")
SPOKEN_KINDS=('PITCH_EDITION','GROWTH_DRAFT')
LONG_SENTENCE=24

SCHEMA='''
CREATE TABLE IF NOT EXISTS work_items(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,opportunity_id TEXT,subject_id TEXT,stage TEXT NOT NULL,round INTEGER NOT NULL DEFAULT 1,
 payload_json TEXT NOT NULL,dedupe_key TEXT UNIQUE,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_reviews(id TEXT PRIMARY KEY,item_id TEXT NOT NULL REFERENCES work_items(id),agent TEXT NOT NULL,round INTEGER NOT NULL,verdict TEXT NOT NULL,
 detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS voice_examples(id TEXT PRIMARY KEY,context TEXT NOT NULL,draft TEXT NOT NULL,final TEXT NOT NULL,source TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lessons(id TEXT PRIMARY KEY,kind TEXT NOT NULL,body TEXT NOT NULL,applies_to TEXT NOT NULL,evidence TEXT,source_item TEXT,state TEXT NOT NULL DEFAULT 'PROPOSED',
 created_at TEXT NOT NULL,decided_at TEXT);
CREATE TABLE IF NOT EXISTS pitch_lab_links(pitch_id TEXT PRIMARY KEY,item_id TEXT NOT NULL,version_id TEXT NOT NULL,harvested_version TEXT,created_at TEXT NOT NULL);
'''

NUMBER=re.compile(r'(?<![\w.])\$?\d[\d,]*(?:\.\d+)?(?:\s?[%×xKMBT])?(?![\w])')
# Evidence table numbers (PITCH-PLAYBOOK.md section 4). Anything else must come from approved facts.
EVIDENCE='''79 37 42 74 73 1 5 11,200 467 8 2027 2030 64.6 342 124 2048 66 10 3.3 93 80 2.2 55 0.32 0.45 7 10 9 30 18 2023 2024 2025 95 19 20 65 50
132.7 43.6 15.8 5.19 100 710,000 709,220 1.6 141 119 229 79 19.99 39 69 149 499 2026 2022 2021 2010 2019 3 90 200 140 12 2 77 53 61 13 28 69 8.79 32.74 14.40 18.00 6.00 36.95 24.12 8.61
2,000 1,005 1938 2018 1958 1990 1,000 30 99 59 199 25'''


def norm(token):
    t=token.replace('$','').replace(',','').strip()
    t=re.sub(r'\s?[%×xKMBT]$','',t)
    try:
        v=float(t);return ('%g'%v)
    except ValueError:return t


def dashes(text):
    """Bao writes ' - ', never long dashes. Number ranges like 2023–2025 keep theirs."""
    text=re.sub(r'\s*—\s*',' - ',text or '')
    return re.sub(r'(?<!\d)\s*–\s*|\s*–\s*(?!\d)',' - ',text)


def numbers_in(text):
    return [m.group(0).strip() for m in NUMBER.finditer(text or '')]


def words(text):return len(re.findall(r"[A-Za-z0-9$%’'.-]+",text or ''))


class FactGuard:
    """Deterministic checks. Blocking issues send a draft back; warnings are for Bao's Voice and Bao."""
    def __init__(self,lab,program=''):
        self.lab=lab;self.mbc='michigan business challenge' in (program or '').lower()
        self.allowed=lab.allowed_numbers();self.measured=lab.measured_numbers()
        # Thread counts from the Customer Voice Scout are never approved facts; they may appear only inside a quotation with the thread's URL beside it.
        self.voice_urls=lab.voice_source_urls()

    def check(self,segments,kind):
        from .customer_voice import cited
        issues=[];fixed=[]
        for seg in segments:
            text=seg.get('text') or ''
            if dashes(text)!=text:
                text=dashes(text)
                issues.append({'where':seg['key'],'rule':'dash','severity':'fixed','text':'Long dashes replaced with a short hyphen.'})
            for n in numbers_in(text):
                v=norm(n)
                if v in self.measured:
                    issues.append({'where':seg['key'],'rule':'measured','severity':'info','text':f'“{n}” is measured. '+self.measured[v]})
                elif v not in self.allowed and not re.fullmatch(r'(19|20)\d\d',v) and not (v.isdigit() and int(v)<=12):
                    if cited(text,n,self.voice_urls):issues.append({'where':seg['key'],'rule':'cited','severity':'info','text':f'“{n}” is quoted from a public thread with its source; it is not a fact about A Story.'})
                    else:issues.append({'where':seg['key'],'rule':'unverified_number','severity':'block','text':f'“{n}” is not in approved facts or the evidence table.'+(' A figure from what families say online may appear only inside a quotation with the thread’s URL beside it.' if self.voice_urls else '')})
            if re.search(r'\[[^\]]{1,80}\]',text):
                issues.append({'where':seg['key'],'rule':'placeholder','severity':'block','text':'A bracketed placeholder is still in the text.'})
            for m in re.finditer(r'paying customers?',text,re.I):
                before=text[max(0,m.start()-40):m.start()].lower()
                if not any(w in before for w in ('waiting','join as','our first','to become')):
                    issues.append({'where':seg['key'],'rule':'traction','severity':'block','text':'The five families are waiting to join as paying customers; never call them paying customers.'})
            if not self.mbc and re.search(r'\bNhi\b',text):
                issues.append({'where':seg['key'],'rule':'team','severity':'block','text':'Nhi Tran appears only in Michigan Business Challenge materials.'})
            if re.search(r'Hope College[^.]{0,60}\b(partner|partnership|signed|contract)',text,re.I):
                issues.append({'where':seg['key'],'rule':'hope_college','severity':'block','text':'Hope College is interest only, not a partnership.'})
            if kind=='PITCH_EDITION' and seg['key'] in STORY_SLIDES and re.search(r'\$\s?(119|229|79|19\.99)\b',text):
                issues.append({'where':seg['key'],'rule':'price_placement','severity':'block','text':'No prices on the story or solution slides. Prices go where the business model is told.'})
            hype=[w for w in HYPE if re.search(r'\b'+re.escape(w)+r'\b',text,re.I)]
            if hype:issues.append({'where':seg['key'],'rule':'voice','severity':'warn','text':'Hype words Bao never uses: '+', '.join(hype)+'.'})
            if kind in SPOKEN_KINDS:
                staged=[m.group(0) for p in WRITTEN for m in re.finditer(p,text,re.I)]
                if staged:issues.append({'where':seg['key'],'rule':'spoken','severity':'warn','text':'Written-language staging; say the point instead: '+'; '.join(f'“{s[:50]}”' for s in staged[:3])+'.'})
                long=[s.strip() for s in re.split(r'(?<=[.!?])\s+',text) if len(s.split())>LONG_SENTENCE]
                if long:issues.append({'where':seg['key'],'rule':'spoken','severity':'warn','text':f'{len(long)} sentence'+('s' if len(long)>1 else '')+f' over {LONG_SENTENCE} words; hard to say in one breath: “{long[0][:70]}…”'})
            fixed.append({**seg,'text':text})
        blocking=[i for i in issues if i['severity']=='block']
        return {'issues':issues,'blocking':len(blocking),'segments':fixed}


class PitchLab:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA);self.h=FundingHunter(store)

    # ---------- shared context ----------
    def master_deck(self):
        p=ROOT/'seed-data'/'master-deck-2026-10.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'slides':[]}

    def doc(self,name,limit=12000):
        p=ROOT/name
        return p.read_text(encoding='utf-8')[:limit] if p.exists() else ''

    def approved_lessons(self,applies=None):
        rows=self.s.rows("SELECT body,applies_to FROM lessons WHERE state='APPROVED' ORDER BY decided_at DESC LIMIT 30")
        return [r['body'] for r in rows if not applies or r['applies_to'] in (applies,'ALL')]

    def voice_examples(self,limit=10):
        return self.s.rows('SELECT context,draft,final FROM voice_examples ORDER BY created_at DESC LIMIT ?',(limit,))

    def facts(self):
        mem=self.h.company_memory()
        pricing=self.db.execute("SELECT v.body FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE s.kind='official_pricing_capture' AND v.body IS NOT NULL ORDER BY v.captured_at DESC LIMIT 1").fetchone()
        return {'company_facts':{k:v['value'] for k,v in mem['attributes'].items()},
                'approved_statements':[{'topic':c['topic'],'text':c['body']} for c in mem['canonical_claims'] if not c['body'].startswith('{')],
                'pricing':pricing['body'][:5000] if pricing else '','measured':self.measured_facts()}

    def measured_facts(self):
        from .product_desk import ProductDesk
        return ProductDesk(self.s).measured_facts()

    def measured_numbers(self):return measured_numbers(self.measured_facts())

    def allowed_numbers(self):
        f=self.facts();text=' '.join([EVIDENCE,json.dumps(f['company_facts']),' '.join(x['text'] for x in f['approved_statements']),f['pricing']]
                                    +[s['spoken'] for s in self.master_deck()['slides']])
        found={norm(n) for n in numbers_in(text)}|{norm(n) for n in EVIDENCE.split()}|set(measured_numbers(f['measured']))
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='channel_entries'").fetchone():
            # Numbers Bao measured on the Growth desk (conversion, cost per purchasing family) may be said as they are.
            from .growth_desk import GrowthDesk
            found|={norm(str(f['value'])) for f in GrowthDesk(self.s).measured_facts()}
        # A spoken pitch rounds: $24.12 may be said as "about $24", $8.61 as "about $9".
        rounded=set()
        for v in found:
            try:
                f=float(v)
                if f!=int(f):rounded|={'%g'%round(f),'%g'%int(f),'%g'%round(f,1)}
            except ValueError:pass
        return found|rounded

    # ---------- items ----------
    def item(self,iid):
        r=self.s.one('SELECT * FROM work_items WHERE id=?',(iid,));r['payload']=json.loads(r.pop('payload_json'))
        r['reviews']=[{**x,'detail':json.loads(x.pop('detail_json'))} for x in self.s.rows('SELECT * FROM work_reviews WHERE item_id=? ORDER BY created_at,rowid',(iid,))]
        r['stage_words']=STAGE_WORDS.get(r['stage'],r['stage']);r['flow']=list(FLOW[r['kind']])
        r['queued']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE request_key=? AND state IN ('QUEUED','RUNNING')",('lab-'+iid+'-'+r['stage']+'-'+str(r['round']),)).fetchone())
        last=self.db.execute("SELECT state,last_error FROM hunter_requests WHERE reason=? ORDER BY created_at DESC LIMIT 1",(PIPELINE_PREFIX+iid,)).fetchone()
        r['error']=last['last_error'] if last and last['state']=='FAILED' else None
        coach=[x for x in r['reviews'] if x['agent']=='COACH']
        r['coach']=coach[-1]['detail'] if coach else None
        return r

    def items(self,kinds=None,limit=60):
        rows=self.s.rows('SELECT id FROM work_items ORDER BY updated_at DESC LIMIT ?',(limit,))
        out=[self.item(r['id']) for r in rows]
        return [x for x in out if not kinds or x['kind'] in kinds]

    def create(self,kind,title,payload,opportunity_id=None,subject_id=None,dedupe_key=None):
        if kind not in FLOW:raise ValueError('Unknown work item')
        if dedupe_key:
            old=self.db.execute('SELECT id FROM work_items WHERE dedupe_key=?',(dedupe_key,)).fetchone()
            if old:return self.item(old['id'])
        iid=uid('work')
        self.db.execute('INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?,?,?)',(iid,kind,title[:200],opportunity_id,subject_id,FLOW[kind][0],1,js(payload),dedupe_key,now(),now()))
        self.s.log('lab.item_created','pitch_lab',{'item_id':iid,'kind':kind})
        self.advance(iid)
        return self.item(iid)

    def _save(self,iid,stage=None,payload=None,round=None):
        cur=self.s.one('SELECT stage,round,payload_json FROM work_items WHERE id=?',(iid,))
        self.db.execute('UPDATE work_items SET stage=?,round=?,payload_json=?,updated_at=? WHERE id=?',
                        (stage or cur['stage'],round or cur['round'],js(payload) if payload is not None else cur['payload_json'],now(),iid))

    def review(self,iid,agent,verdict,detail):
        r=self.s.one('SELECT round FROM work_items WHERE id=?',(iid,))
        self.db.execute('INSERT INTO work_reviews VALUES(?,?,?,?,?,?,?)',(uid('review'),iid,agent,r['round'],verdict,js(detail),now()))

    def next_stage(self,kind,stage):
        flow=FLOW[kind];return flow[flow.index(stage)+1] if stage in flow and flow.index(stage)+1<len(flow) else 'READY'

    def queue(self,iid):
        it=self.s.one('SELECT stage,round FROM work_items WHERE id=?',(iid,))
        return self.h.request_run(PIPELINE_PREFIX+iid,key='lab-'+iid+'-'+it['stage']+'-'+str(it['round']))

    # ---------- segments: what each kind lets the checkers and Voice read ----------
    def segments(self,it):
        p=it['payload']
        if it['kind']=='PITCH_EDITION':return [{'key':x['slide_id'],'title':x.get('title',''),'text':x['text'],'editable':True} for x in (p.get('brief') or {}).get('script',[])]
        if it['kind']=='PITCH_REVIEW':return [{'key':'pitch','title':p.get('title',''),'text':p.get('text',''),'editable':False}]
        if it['kind']=='APPLICATION_SET':return [{'key':a['question_id'],'title':a['question'],'text':a['text'],'editable':a.get('provenance') in ('agent_draft','drafted'),'limit':a.get('limit'),'unit':a.get('unit')} for a in p.get('answers',[])]
        if it['kind']=='GROWTH_DRAFT':return [{'key':'body','title':p.get('title',''),'text':p.get('body',''),'editable':True}]
        return []

    def put_segments(self,it,segs):
        p=it['payload'];by={s['key']:s['text'] for s in segs}
        if it['kind']=='PITCH_EDITION':
            for x in p['brief']['script']:x['text']=by.get(x['slide_id'],x['text'])
        elif it['kind']=='PITCH_REVIEW':p['text']=by.get('pitch',p['text'])
        elif it['kind']=='APPLICATION_SET':
            for a in p['answers']:
                if a['question_id'] in by:a['suggested']=by[a['question_id']]
        elif it['kind']=='GROWTH_DRAFT':p['body']=by.get('body',p['body'])
        return p

    # ---------- the engine ----------
    def advance(self,iid):
        """Run deterministic stages inline; stop at the next AI stage (queued) or at READY."""
        for _ in range(12):
            it=self.item(iid);stage=it['stage']
            if stage in ('READY','APPROVED','ARCHIVED'):return it
            if stage in LLM_STAGES:
                if not it['queued']:self.queue(iid)
                return self.item(iid)
            if stage in ('FACT_CHECK','FACT_RECHECK'):self._fact_stage(it)
            elif stage=='FORMAT':self._format_stage(it)
            elif stage=='BUILD':self._build_stage(it)
            elif stage=='SLIDE_QA':self._qa_stage(it)
        return self.item(iid)

    def _fact_stage(self,it):
        program=it['payload'].get('program','');guard=FactGuard(self,program)
        if it['kind']=='APPLICATION_SET':
            segs=[{**s,'text':it['payload']['answers'][i].get('suggested') or s['text']} for i,s in enumerate(self.segments(it))]
        else:segs=self.segments(it)
        result=guard.check(segs,it['kind'])
        if it['stage']=='FACT_RECHECK' and it['payload'].get('pre_voice'):
            # Only problems Voice introduced count here; ones already in the draft were reported at the first check.
            pre=guard.check([{**s,'text':it['payload']['pre_voice'].get(s['key'],s['text'])} for s in segs],it['kind'])
            seen={(i['where'],i['rule'],i['text']) for i in pre['issues']}
            for i in result['issues']:
                if i['severity']=='block' and (i['where'],i['rule'],i['text']) in seen:i['severity']='warn'
            result['blocking']=len([i for i in result['issues'] if i['severity']=='block'])
        payload=self.put_segments(it,result['segments']) if it['kind']!='APPLICATION_SET' else it['payload']
        brief=payload.get('brief') if it['kind']=='PITCH_EDITION' else None
        if brief:
            for k in ('ask','strategy'):
                if isinstance(brief.get(k),str):brief[k]=dashes(brief[k])
            for k in ('open_questions','materials','answers_to_feedback'):
                if isinstance(brief.get(k),list):brief[k]=[dashes(x) if isinstance(x,str) else x for x in brief[k]]
        if it['stage']=='FACT_CHECK':payload.pop('unresolved',None)
        if it['kind']=='APPLICATION_SET':
            payload['fact_issues']=result['issues']
        if it['stage']=='FACT_RECHECK' and result['blocking']:
            # Voice may only change wording. Restore the pre-voice text wherever it added a problem.
            before={k:v for k,v in (payload.get('pre_voice') or {}).items()}
            bad={i['where'] for i in result['issues'] if i['severity']=='block'}
            if before and it['kind']!='APPLICATION_SET':
                restored=[{**s,'text':before.get(s['key'],s['text']) if s['key'] in bad else s['text']} for s in result['segments']]
                payload=self.put_segments({**it,'payload':payload},restored)
            elif it['kind']=='APPLICATION_SET':
                for a in payload['answers']:
                    if a['question_id'] in bad:a.pop('suggested',None)
        if it['stage']=='FACT_RECHECK':
            # A last-round block that Voice's wording fixed is no longer open; one the recheck still finds stays.
            still={(i['where'],i['text']) for i in result['issues']}
            payload['unresolved']=[u for u in (payload.get('unresolved') or []) if u.get('from')!='Fact Guard' or (u.get('where'),u.get('text')) in still]
            if not payload['unresolved']:payload.pop('unresolved')
        self.review(it['id'],'FACT_GUARD','BLOCK' if result['blocking'] else 'PASS',{'issues':result['issues']})
        if it['stage']=='FACT_CHECK' and result['blocking'] and 'TAILOR' in FLOW[it['kind']] and it['round']<MAX_ROUNDS:
            payload['feedback']={'from':'Fact Guard','fixes':[i['text']+' ('+i['where']+')' for i in result['issues'] if i['severity']=='block']}
            self._save(it['id'],'TAILOR',payload,it['round']+1);return
        if it['stage']=='FACT_CHECK' and result['blocking']:
            # Out of rounds: the draft still reaches Bao, but never silently.
            payload['unresolved']=[{'from':'Fact Guard','text':i['text'],'where':i['where']} for i in result['issues'] if i['severity']=='block']
        self._save(it['id'],self.next_stage(it['kind'],it['stage']),payload)

    def _format_stage(self,it):
        p=it['payload'];issues=[]
        if it['kind']=='PITCH_EDITION':
            total=sum(words(s['text']) for s in self.segments(it));target=int(p.get('minutes',3)*WORDS_PER_MINUTE)
            p['timing']={'words':total,'target_words':target,'seconds':round(total/WORDS_PER_MINUTE*60)}
            if total>target*1.1:issues.append(f'About {total-target} words over a {p.get("minutes")}-minute slot at {WORDS_PER_MINUTE} words a minute. Cut them.')
            limit=p.get('slide_limit') or ((p.get('brief') or {}).get('rules') or {}).get('slide_limit')
            slides=len([s for s in self.segments(it)])
            if limit and slides>int(limit):issues.append(f'{slides} slides planned; the program allows {limit}.')
        elif it['kind']=='APPLICATION_SET':
            for a in p.get('answers',[]):
                text=a.get('suggested') or a['text'];lim=a.get('limit')
                if lim:
                    n=len(text) if a.get('unit')=='characters' else words(text)
                    if n>lim:issues.append(f'“{a["question"][:60]}” is {n} {a.get("unit") or "words"}; the limit is {lim}.')
        self.review(it['id'],'FORMAT','PASS' if not issues else 'FIX',{'issues':issues,'timing':p.get('timing')})
        if issues and 'TAILOR' in FLOW[it['kind']] and it['round']<MAX_ROUNDS:
            p['feedback']={'from':'Format Check','fixes':issues};self._save(it['id'],'TAILOR',p,it['round']+1);return
        if issues:p['unresolved']=(p.get('unresolved') or [])+[{'from':'Format Check','text':x,'where':''} for x in issues]
        p['format_issues']=issues;self._save(it['id'],self.next_stage(it['kind'],it['stage']),p)

    # ---------- Edition Builder and Slide QA (deterministic; slide_deck.py) ----------
    def _build_stage(self,it):
        from . import slide_deck
        p=it['payload']
        try:
            m=slide_deck.build_edition(self.s,it['id'],it['round'],p['brief'],p.get('program',''),p.get('minutes',3))
            p['edition']={k:m[k] for k in ('round','core','built_at','dir','new_slides')}|{'slides':[{k:x[k] for k in ('id','n','title','seconds','source')} for x in m['slides']]}
            self.review(it['id'],'BUILDER','BUILT',{'slides':len(m['slides']),'new_slides':m['new_slides'],'core':m['core']})
            self._save(it['id'],'SLIDE_QA',p)
        except (ValueError,OSError,KeyError) as e:
            p.pop('edition',None);p['unresolved']=[u for u in (p.get('unresolved') or []) if u.get('from')!='Edition Builder']+[{'from':'Edition Builder','text':'The deck could not be built: '+str(e)[:200],'where':''}]
            self.review(it['id'],'BUILDER','FAILED',{'error':str(e)[:300]});self._save(it['id'],'READY',p)

    def _qa_stage(self,it):
        from . import slide_deck
        p=it['payload'];m=self.edition_manifest(it)
        qa=slide_deck.run_qa(m) if m else {'available':False,'reason':'No deck was built','slides':[],'blocking':0,'warnings':0}
        p['slide_qa']=qa
        p['unresolved']=[u for u in (p.get('unresolved') or []) if u.get('from')!='Slide QA']+[
            {'from':'Slide QA','text':i['text'],'where':f"slide {s['n']} · {s['id']}"} for s in qa.get('slides',[]) for i in s['issues'] if i['severity']=='block']
        if not p['unresolved']:p.pop('unresolved')
        self.review(it['id'],'SLIDE_QA','PASS' if qa.get('available') and not qa.get('blocking') else 'FLAGS' if qa.get('available') else 'SKIPPED',
                    {'blocking':qa.get('blocking',0),'warnings':qa.get('warnings',0),'reason':qa.get('reason'),
                     'issues':[{'text':f"Slide {s['n']}: "+i['text'],'severity':i['severity']} for s in qa.get('slides',[]) for i in s['issues'] if i['severity']=='block'][:12]})
        self._save(it['id'],self.next_stage(it['kind'],'SLIDE_QA'),p)

    def edition_manifest(self,it):
        e=(it['payload'] or {}).get('edition')
        if not e or not e.get('dir'):return None
        from pathlib import Path
        f=Path(e['dir'])/'manifest.json'
        return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None

    def build_now(self,iid):
        """Build and check the deck for an edition that reached Bao before Edition Builder existed, without moving its stage."""
        it=self.item(iid)
        if it['kind']!='PITCH_EDITION' or not it['payload'].get('brief'):raise ValueError('Only a tailored pitch edition has a deck to build')
        stage=it['stage'];self._build_stage(it);it=self.item(iid)
        if it['stage']=='SLIDE_QA':self._qa_stage(it)
        if stage!=self.item(iid)['stage']:self._save(iid,stage)
        return self.item(iid)

    # ---------- AI stages (run by the worker with a Codex runner) ----------
    def base_context(self,applies):
        f=self.facts();measured=' '.join(m['text'] for m in f['measured'])
        from .assumption_coach import AssumptionCoach
        assumptions=AssumptionCoach(self.s).for_agents()
        return {**f,'playbook':self.doc('PITCH-PLAYBOOK.md',60000),'lessons':self.approved_lessons(applies),'assumptions':assumptions,
                'rules':[*(['Measured product numbers, from the beta family journal, come first; use them with their denominator and as-of date, and prefer them over owner-reported numbers where both exist: '+measured] if measured else []),'Use only the facts, statements, pricing and evidence given. Never invent numbers, customers, partners, awards, quotes or traction.',
                         assumptions['rule']+' CONTEXT.assumptions lists every number the deck depends on with its status and how to say it.',
                         'Write " - " (a short hyphen with spaces), never a long dash.','Two founders, Daniel Hoang Nguyen (CEO) and Bao Vo (COO and CTO). Nhi Tran only for the Michigan Business Challenge.',
                         'Traction is owner-reported: 50 leads, 10 beta families, 5 waiting to join as paying customers. Hope College: many students want to preorder or join the mailing list to gift it to grandparents for Thanksgiving (interest only, not a partnership).',
                         'Bao reads every field you write. Never mention CONTEXT, the playbook, field names, rounds or these instructions; say "the program page", "our facts" or "the master deck" in plain words.']}

    def win_brief(self,oid):
        from .win_scout import WinScout
        return WinScout(self.s).for_agents(oid)

    def customer_voice(self):
        """What families say online this week (themes, counts, two quotes each): evidence about the market for Tailor and Coach, never about A Story."""
        from .customer_voice import CustomerVoice
        return CustomerVoice(self.s).for_agents()

    def voice_source_urls(self):
        from .customer_voice import CustomerVoice
        return CustomerVoice(self.s).source_urls()

    def program_context(self,oid):
        if not oid:return None
        try:d=self.h.detail(oid)
        except ValueError:return None
        data=d['data']
        return {k:data.get(k) for k in ('canonical_name','organizer','opportunity_type','cycle','official_url','application_url','dates','funding','eligibility','requirements','notes')}|{'recommendation':d['recommendation']}

    def prompt_for(self,it):
        """Returns (prompt, schema, stem, search) for the item's current AI stage."""
        st=it['stage'];p=it['payload']
        if st=='TAILOR':
            program=self.program_context(it['opportunity_id'])
            first=it['round']==1 and not p.get('brief')
            ctx={**self.base_context('TAILOR'),'program':program,'minutes':p.get('minutes'),'slide_limit':p.get('slide_limit'),'owner_note':p.get('owner_note',''),
                 'master_deck':self.master_deck()['slides'],'previous_edition':p.get('brief'),'feedback':p.get('feedback'),'voice_guide':self.doc('BAO-VOICE.md',6000),'win_brief':self.win_brief(it['opportunity_id']),'customer_voice':self.customer_voice()}
            slide=({'type':'object','additionalProperties':False,'properties':{'slide_id':{'type':'string'},'title':{'type':'string'},'seconds':{'type':'integer'},'text':{'type':'string'}},'required':['slide_id','title','seconds','text']})
            plan={'type':'object','additionalProperties':False,'properties':{'slide_id':{'type':'string'},'action':{'type':'string','enum':['keep','change','add','cut']},'change':{'type':'string'},'why':{'type':'string'}},'required':['slide_id','action','change','why']}
            rules={'type':'object','additionalProperties':False,'properties':{'minutes':{'type':['number','null']},'slide_limit':{'type':['integer','null']},'format':{'type':'string'},
                   'judging_criteria':{'type':'array','items':{'type':'string'}},'required_sections':{'type':'array','items':{'type':'string'}},'prize':{'type':'string'},'equity':{'type':'string'},
                   'deadline':{'type':['string','null']},'source_urls':{'type':'array','items':{'type':'string'}}},'required':['minutes','slide_limit','format','judging_criteria','required_sections','prize','equity','deadline','source_urls']}
            schema={'type':'object','additionalProperties':False,'properties':{'rules':rules,'strategy':{'type':'string'},'slide_plan':{'type':'array','items':plan},'script':{'type':'array','items':slide},
                    'ask':{'type':'string'},'materials':{'type':'array','items':{'type':'string'}},'open_questions':{'type':'array','items':{'type':'string'}},'answers_to_feedback':{'type':'array','items':{'type':'string'}}},
                    'required':['rules','strategy','slide_plan','script','ask','materials','open_questions','answers_to_feedback']}
            task=('You are Pitch Tailor for A Story. Build the program edition of the master deck for CONTEXT.program within CONTEXT.minutes. '
                  +('First read ONLY the program’s official pages (official_url, application_url and pages they link to) to learn the format, time limit, slide limit, judging criteria and required sections. Do not use other sites. ' if first and program and (program.get('official_url') or program.get('application_url')) else 'Do not use the web; use CONTEXT only. ')
                  +'Follow CONTEXT.playbook exactly: its story spine, content rules, evidence guardrails and the tailoring section. Choose and reorder slides from CONTEXT.master_deck (use their ids; at most two new slides with ids new-1, new-2: a program-specific why-us slide and the ask). '
                  'Write the timed spoken script in Bao’s voice (CONTEXT.voice_guide), one entry per slide, reusing Bao’s own lines from master_deck.spoken. Total words must fit minutes × 140. '
                  'If CONTEXT.feedback exists, fix every point and say how in answers_to_feedback. If CONTEXT.previous_edition exists, revise it rather than starting over. '
                  'Put anything only Bao can supply (the ask amount, a credential) in open_questions, never as a bracketed placeholder in the script. '
                  +('If CONTEXT.win_brief exists, build the edition to win this exact program: weight and order the slides by win_brief.criteria, make every how_we_win move visible on a slide or in the script, answer each unstated expectation, and prepare for the named judges. win_brief describes the program and other companies; take no fact about A Story from it. ' if ctx.get('win_brief') else '')
                  +('CONTEXT.customer_voice is what families say online this week, as evidence that the problem is real and how people talk about it: use its words on the problem slides and cite a quote with its URL where a judge would want proof. It says nothing about A Story; take no traction, customer or number about A Story from it, and say a thread count only as a quoted figure with its URL. ' if ctx.get('customer_voice') else '')
                  +'rules.deadline is a plain date YYYY-MM-DD or null; put any caveat about the rules in rules.format. Use null for anything the official pages do not state.')
            return task+'\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False),schema,'tailor',first and bool(program)
        if st=='VOICE':
            segs=[s for s in self.segments(it) if s.get('editable')]
            ctx={'voice_guide':self.doc('BAO-VOICE.md',8000),'examples':self.voice_examples(),'lessons':self.approved_lessons('VOICE'),'segments':[{k:s[k] for k in ('key','title','text')}|({'limit':s.get('limit'),'unit':s.get('unit')} if s.get('limit') else {}) for s in segs]}
            seg={'type':'object','additionalProperties':False,'properties':{'key':{'type':'string'},'text':{'type':'string'},'changed':{'type':'boolean'}},'required':['key','text','changed']}
            schema={'type':'object','additionalProperties':False,'properties':{'segments':{'type':'array','items':seg},'notes':{'type':'array','items':{'type':'string'}}},'required':['segments','notes']}
            task=('You are Bao’s Voice. Rewrite each segment so it reads exactly like Bao wrote it, following CONTEXT.voice_guide and the before/after CONTEXT.examples of his own edits. '
                  +('These segments are said out loud. Apply the "Spoken, not written" section of the voice guide: one breath per sentence, contractions, plain verbs, no staging ("not X but Y", "here is the thing"), no triads for rhythm, no inflated words, no dashes. Read each line aloud in your head before returning it. ' if it['kind'] in SPOKEN_KINDS else '')
                  +'Change wording only: keep every fact, number, name and claim exactly. Do not add new claims or numbers. Stay within any limit. '
                  'If a segment already sounds like Bao, return it unchanged with changed=false. notes: the patterns you applied, in one short line each.')
            return task+'\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False),schema,'voice',False
        if st=='COACH':
            content=[{k:s[k] for k in ('key','title','text')} for s in self.segments(it)]
            if it['kind']=='APPLICATION_SET':content=[{**c,'text':it['payload']['answers'][i].get('suggested') or c['text']} for i,c in enumerate(content)]
            ctx={**self.base_context('COACH'),'program':self.program_context(it['opportunity_id']),'win_brief':self.win_brief(it['opportunity_id']),'customer_voice':self.customer_voice(),'kind':it['kind'],'minutes':it['payload'].get('minutes'),'content':content,
                 'rubric':list(CRITERIA),'appendix':[{'id':x['id'],'notes':x['spoken']} for x in self.master_deck()['slides'] if x.get('appendix')],'earlier_reviews':[r['detail'].get('top_fixes') for r in it['reviews'] if r['agent']=='COACH']}
            score={'type':'object','additionalProperties':False,'properties':{'criterion':{'type':'string','enum':list(CRITERIA)},'score':{'type':'integer','minimum':1,'maximum':5},'why':{'type':'string'},'fix':{'type':'string'}},'required':['criterion','score','why','fix']}
            q={'type':'object','additionalProperties':False,'properties':{'question':{'type':'string'},'answer':{'type':'string'},'gap':{'type':'string'}},'required':['question','answer','gap']}
            schema={'type':'object','additionalProperties':False,'properties':{'summary':{'type':'string'},'scores':{'type':'array','items':score},'hard_questions':{'type':'array','items':q},
                    'top_fixes':{'type':'array','items':{'type':'string'}},'verdict':{'type':'string','enum':['PASS','REVISE']}},'required':['summary','scores','hard_questions','top_fixes','verdict']}
            task=('You are Pitch Coach: a YC partner who knows A Story well. Kind, direct and specific; never flattering. Score CONTEXT.content on every criterion in CONTEXT.rubric (1-5) using '
                  'the coaching lens in CONTEXT.playbook section 9, judged for CONTEXT.program and its format. Numbers in CONTEXT.appendix are approved modeled figures (said rounded in the pitch); question how they are framed, not whether they exist. For each score give why and the one concrete fix that would raise it. '
                  'Write 6-8 hard_questions a judge or investor would ask this exact pitch, each with the best honest answer from CONTEXT facts (say "we don’t know yet - here is the test" when true) and gap = what proof is missing. '
                  'top_fixes: the 3 changes that matter most, most important first. verdict PASS only when every score is 4 or higher. Never invent facts. '
                  'CONTEXT.assumptions.items lists every number the pitch depends on with its status, weakest first (CONTEXT.assumptions.weakest): ask about the weakest ones in hard_questions, and where no proof exists the honest answer names that assumption’s cheapest_test.'
                  +(' CONTEXT.win_brief describes this program’s judges, criteria, past winners and other companies: score as those judges would, weight the criteria as win_brief.criteria says, and add the hard questions they or the listed competitors would prompt.' if ctx.get('win_brief') else '')
                  +(' CONTEXT.customer_voice is what families say online this week (themes, thread counts, quotes with URLs): judge Problem urgency and Evidence against it, ask whether the pitch speaks in those words and answers the listed objections, and suggest a cited quote where proof is thin. It is evidence about the market, not about A Story; never treat it as our traction or our customers.' if ctx.get('customer_voice') else ''))
            return task+'\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False),schema,'coach',False
        if st=='LEARN':
            ctx={**{k:v for k,v in self.base_context('ALL').items() if k!='playbook'},'item':it['payload'],'current_lessons':self.approved_lessons()}
            lesson={'type':'object','additionalProperties':False,'properties':{'lesson':{'type':'string'},'applies_to':{'type':'string','enum':['TAILOR','COACH','VOICE','HUNTER','ALL']},'evidence':{'type':'string'}},'required':['lesson','applies_to','evidence']}
            schema={'type':'object','additionalProperties':False,'properties':{'lessons':{'type':'array','items':lesson}},'required':['lessons']}
            task=('You are the Outcome Learner. From CONTEXT.item, propose at most 3 short, specific lessons that would make the next pitch, application or program choice better. '
                  'Each must follow from the evidence given; do not repeat CONTEXT.current_lessons. For voice examples, describe the pattern in Bao’s edits as a writing rule.'
                  if it['kind']=='OUTCOME_LESSON' else
                  'You are the Outcome Learner. CONTEXT.item.examples are Bao’s own edits of agent drafts (draft → final). Propose at most 3 writing rules that capture what he consistently changes. '
                  'Use applies_to VOICE. Do not repeat CONTEXT.current_lessons.')
            return task+'\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False),schema,'learn',False
        raise ValueError('No AI step at stage '+st)

    def run_ai_stage(self,iid,runner):
        """runner(prompt, schema, stem, search) -> dict. One AI call, then deterministic stages inline."""
        it=self.item(iid);st=it['stage']
        if st not in LLM_STAGES:return self.advance(iid)
        prompt,schema,stem,search=self.prompt_for(it);data=runner(prompt,schema,stem,search);p=it['payload']
        if st=='TAILOR':
            ids={s['id'] for s in self.master_deck()['slides']}|{'new-1','new-2'}
            data['script']=[x for x in data.get('script',[]) if x.get('slide_id') in ids]
            if not data['script']:raise RuntimeError('Pitch Tailor returned no usable slides')
            p['brief']=data;p.pop('feedback',None);p.pop('pre_voice',None)
            self.review(iid,'TAILOR','DRAFTED',{'strategy':data.get('strategy'),'answers_to_feedback':data.get('answers_to_feedback',[]),'rules':data.get('rules')})
        elif st=='VOICE':
            before={s['key']:s['text'] for s in self.segments(it)};p['pre_voice']=before
            if it['kind']=='APPLICATION_SET':before={a['question_id']:a.get('suggested') or a['text'] for a in p['answers']};p['pre_voice']=before
            changed=[s for s in data.get('segments',[]) if s.get('changed') and s.get('key') in before and s.get('text','').strip()]
            p=self.put_segments({**it,'payload':p},[{'key':s['key'],'text':s['text'].strip()} for s in changed])
            self.review(iid,'VOICE','EDITED' if changed else 'UNCHANGED',{'changed':[s['key'] for s in changed],'notes':data.get('notes',[])})
        elif st=='COACH':
            low=[s for s in data.get('scores',[]) if s.get('score',5)<PASS_SCORE]
            verdict='PASS' if not low else 'REVISE'
            self.review(iid,'COACH',verdict,data)
            if low and 'TAILOR' in FLOW[it['kind']] and it['round']<MAX_ROUNDS:
                p['feedback']={'from':'Pitch Coach','fixes':data.get('top_fixes',[])+[s['criterion']+': '+s['fix'] for s in low]}
                self._save(iid,'TAILOR',p,it['round']+1);return self.advance(iid)
        elif st=='LEARN':
            saved=0
            for l in data.get('lessons',[])[:3]:
                if l.get('lesson','').strip():
                    self.db.execute('INSERT INTO lessons VALUES(?,?,?,?,?,?,?,?,?)',(uid('lesson'),'VOICE' if it['kind']=='VOICE_RULES' else 'OUTCOME',l['lesson'].strip()[:600],l.get('applies_to','ALL'),l.get('evidence','')[:600],iid,'PROPOSED',now(),None));saved+=1
            self.review(iid,'LEARNER','PROPOSED',{'lessons':saved})
        self._save(iid,self.next_stage(it['kind'],st),p)
        return self.advance(iid)

    # ---------- what Bao does ----------
    def start_edition(self,opportunity_id,minutes,slide_limit=None,note=''):
        d=self.h.detail(opportunity_id);minutes=float(minutes)
        if not 0.5<=minutes<=30:raise ValueError('Pitch length must be between 30 seconds and 30 minutes')
        name=d['data']['canonical_name']
        return self.create('PITCH_EDITION',f'{name} · {minutes:g} min',{'program':name,'minutes':minutes,'slide_limit':int(slide_limit) if slide_limit else None,'owner_note':(note or '')[:1000]},opportunity_id=opportunity_id)

    def start_review(self,pitch_id):
        from .pitch_studio import PitchStudio
        p=PitchStudio(self.s).detail(pitch_id)
        return self.create('PITCH_REVIEW','Coach: '+p['title'],{'title':p['title'],'text':p['body'],'minutes':round(p['duration_seconds']/60,1),'program':p['audience']},subject_id=pitch_id,dedupe_key='review-'+p['id'])

    def start_application(self,application_id):
        view=self.h.application_view(application_id)
        answers=[{'question_id':q['id'],'question':q.get('label') or q['prompt'],'limit':q.get('limit'),'unit':q.get('unit'),'text':q['answer']['body'],'provenance':q['answer'].get('provenance')} for q in view['questions'] if q.get('answer')]
        if not answers:raise ValueError('No prepared answers to review yet')
        key='app-'+digest([(a['question_id'],a['text']) for a in answers])[:24]
        return self.create('APPLICATION_SET','Answers: '+view['program'],{'program':view['program'],'application_id':application_id,'answers':answers},opportunity_id=view['opportunity_id'],subject_id=application_id,dedupe_key=key)

    def rerun(self,iid,note=''):
        it=self.item(iid);first=FLOW[it['kind']][0];p=it['payload']
        if note:p['feedback']={'from':'Bao','fixes':[note[:1000]]}
        self._save(iid,first,p,it['round']+1);self.review(iid,'OWNER','RERUN',{'note':note[:1000]})
        return self.advance(iid)

    def approve(self,iid):
        self._save(iid,'APPROVED');self.review(iid,'OWNER','APPROVED',{});return self.item(iid)

    def save_to_studio(self,iid):
        from .pitch_studio import PitchStudio
        it=self.item(iid)
        if it['kind']!='PITCH_EDITION' or not it['payload'].get('brief'):raise ValueError('Only a tailored pitch edition can be saved to Pitch Studio')
        b=it['payload']['brief'];coach=it['coach'] or {}
        body='\n\n'.join(f"SLIDE {i} - {x['title'].upper()}\n{x['text']}" for i,x in enumerate(b['script'],1))
        notes='\n'.join(['Program edition from Pitch Lab ('+it['id']+').','',
                         'SLIDE PLAN']+[f"- {x['slide_id']}: {x['action']} - {x['change']}" for x in b.get('slide_plan',[])]+['','ASK',b.get('ask',''),'','MATERIALS']
                        +['- '+m for m in b.get('materials',[])]+['','OPEN QUESTIONS FOR BAO']+['- '+q for q in b.get('open_questions',[])]
                        +(['','PITCH COACH',coach.get('summary','')]+['- '+f for f in coach.get('top_fixes',[])] if coach else []))
        pitch=PitchStudio(self.s).create({'title':it['title'][:160],'duration_seconds':max(10,min(7200,int(it['payload']['minutes']*60))),'audience':it['payload']['program'][:100],
                                          'scenario':'Program pitch','speaker':'Bao Vo','body':body[:40000],'notes':notes[:10000],'format':'script','status':'draft',
                                          'change_note':'Pitch Lab edition, round '+str(it['round'])})
        self.db.execute('INSERT OR REPLACE INTO pitch_lab_links VALUES(?,?,?,?,?)',(pitch['pitch_id'],iid,pitch['id'],None,now()))
        self.review(iid,'OWNER','SAVED_TO_STUDIO',{'pitch_id':pitch['pitch_id']})
        return {'pitch_id':pitch['pitch_id']}

    # ---------- lessons ----------
    def lessons(self,state=None):
        return self.s.rows('SELECT * FROM lessons'+(' WHERE state=?' if state else '')+' ORDER BY created_at DESC LIMIT 50',(state,) if state else ())

    def decide_lesson(self,lid,decision):
        if decision not in ('APPROVED','REJECTED'):raise ValueError('Approve or reject')
        self.s.one('SELECT id FROM lessons WHERE id=?',(lid,))
        self.db.execute('UPDATE lessons SET state=?,decided_at=? WHERE id=?',(decision,now(),lid));return {'id':lid,'state':decision}

    # ---------- the loops ----------
    def harvest_voice(self):
        """Bao's own edits of agent drafts become voice examples."""
        found=0
        for link in self.s.rows('SELECT * FROM pitch_lab_links'):
            cur=self.db.execute('SELECT current_version_id FROM pitch_documents WHERE pitch_id=?',(link['pitch_id'],)).fetchone()
            if not cur or cur['current_version_id'] in (link['version_id'],link['harvested_version']):continue
            draft=self.db.execute('SELECT body FROM pitch_versions WHERE id=?',(link['version_id'],)).fetchone();final=self.db.execute('SELECT body FROM pitch_versions WHERE id=?',(cur['current_version_id'],)).fetchone()
            if draft and final and draft['body'].strip()!=final['body'].strip():
                self.db.execute('INSERT OR IGNORE INTO voice_examples VALUES(?,?,?,?,?,?)',(uid('voice'),'pitch',draft['body'][:6000],final['body'][:6000],'pitch:'+cur['current_version_id'],now()));found+=1
            self.db.execute('UPDATE pitch_lab_links SET harvested_version=? WHERE pitch_id=?',(cur['current_version_id'],link['pitch_id']))
        for row in self.s.rows("""SELECT q.id qid,q.prompt,o.body final,o.id oid,(SELECT a.body FROM answer_versions a WHERE a.question_id=q.id AND a.provenance IN ('agent_draft','drafted') ORDER BY a.created_at DESC LIMIT 1) draft
                                  FROM questions q JOIN answer_versions o ON o.question_id=q.id WHERE o.provenance='owner_written'"""):
            if row['draft'] and row['draft'].strip()!=row['final'].strip():
                cur=self.db.execute('INSERT OR IGNORE INTO voice_examples VALUES(?,?,?,?,?,?)',(uid('voice'),'application: '+row['prompt'][:120],row['draft'][:6000],row['final'][:6000],'answer:'+row['oid'],now()))
                found+=cur.rowcount
        return found

    def poll(self):
        """One maintenance pass per autonomy cycle: learn from edits and results, start reviews, keep items moving."""
        out={'voice_examples':self.harvest_voice(),'started':0}
        # Voice rules once three new examples have arrived since the last proposal.
        last=self.db.execute("SELECT MAX(created_at) t FROM work_items WHERE kind='VOICE_RULES'").fetchone()['t'] or ''
        fresh=self.s.rows('SELECT context,draft,final FROM voice_examples WHERE created_at>? ORDER BY created_at DESC LIMIT 10',(last,))
        if len(fresh)>=3:self.create('VOICE_RULES','Learn from Bao’s edits',{'examples':fresh},dedupe_key='voice-'+digest([f['final'] for f in fresh])[:24]);out['started']+=1
        # Results → lessons.
        cursor=self.db.execute("SELECT value_json FROM hunter_settings WHERE key='lab_outcome_cursor'").fetchone()
        since=json.loads(cursor['value_json']) if cursor else now()
        if not cursor:self.db.execute('INSERT INTO hunter_settings VALUES(?,?)',('lab_outcome_cursor',js(since)))
        newest=since
        for o in self.s.rows("SELECT * FROM funding_outcomes WHERE created_at>? AND outcome IN ('Advanced','Finalist','Won','Accepted','Rejected') ORDER BY created_at",(since,)):
            used=[{'kind':w['kind'],'title':w['title'],'coach':(self.item(w['id'])['coach'] or {}).get('summary')} for w in self.s.rows('SELECT id,kind,title FROM work_items WHERE opportunity_id=?',(o['opportunity_id'],))]
            try:name=self.h.detail(o['opportunity_id'])['data']['canonical_name']
            except ValueError:name=o['opportunity_id']
            self.create('OUTCOME_LESSON','Lessons: '+name+' · '+o['outcome'],{'program':name,'outcome':o['outcome'],'note':o.get('evidence_note'),'work_used':used},opportunity_id=o['opportunity_id'],dedupe_key='outcome-'+o['id'])
            out['started']+=1;newest=max(newest,o['created_at'])
        if newest!=since:self.db.execute('UPDATE hunter_settings SET value_json=? WHERE key=?',(js(newest),'lab_outcome_cursor'))
        # Applications whose drafting has finished get a Voice and Coach review once per answer set.
        for a in self.s.rows("SELECT DISTINCT q.application_id aid FROM questions q JOIN answer_versions v ON v.question_id=q.id WHERE v.provenance='agent_draft'"):
            busy=self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",('Draft application: '+a['aid'],)).fetchone()
            if busy:continue
            try:
                before=self.db.execute('SELECT COUNT(*) FROM work_items').fetchone()[0];self.start_application(a['aid'])
                out['started']+=self.db.execute('SELECT COUNT(*) FROM work_items').fetchone()[0]-before
            except (ValueError,KeyError):continue
        # Growth drafts get Fact Guard and Bao's Voice before Bao sees them.
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='growth_drafts'").fetchone():
            for g in self.s.rows("SELECT * FROM growth_drafts WHERE COALESCE(note,'') NOT LIKE 'Bao’s Voice%' ORDER BY created_at DESC LIMIT 5"):
                before=self.db.execute('SELECT COUNT(*) FROM work_items').fetchone()[0]
                self.create('GROWTH_DRAFT','Voice: '+(g['title'] or g['subject_kind']),{'draft_id':g['id'],'subject_kind':g['subject_kind'],'subject_id':g['subject_id'],'title':g['title'],'body':g['body'],'note':g['note']},subject_id=g['subject_id'],dedupe_key='growth-'+g['id'])
                out['started']+=self.db.execute('SELECT COUNT(*) FROM work_items').fetchone()[0]-before
        # Finished growth items publish their edited draft back to the growth page.
        for w in self.s.rows("SELECT id FROM work_items WHERE kind='GROWTH_DRAFT' AND stage='READY'"):
            it=self.item(w['id']);p=it['payload']
            if p.get('published'):continue
            if p.get('body','').strip()!=(p.get('pre_voice') or {}).get('body',p.get('body','')).strip() or any(r['agent']=='VOICE' and r['verdict']=='EDITED' for r in it['reviews']):
                self.db.execute('INSERT INTO growth_drafts VALUES(?,?,?,?,?,?,?)',(uid('draft'),p['subject_kind'],p['subject_id'],p.get('title'),p['body'],'Bao’s Voice edit. '+(p.get('note') or ''),now()))
            p['published']=True;self._save(w['id'],'READY',p)
        for w in self.s.rows("SELECT id FROM work_items WHERE stage NOT IN ('READY','APPROVED','ARCHIVED')"):self.advance(w['id'])
        return out

    # ---------- what Today and the daily email show ----------
    def alerts(self):
        items=[]
        ready=[w for w in self.s.rows("SELECT id,kind,title FROM work_items WHERE stage='READY' AND kind IN ('PITCH_EDITION','PITCH_REVIEW','APPLICATION_SET') ORDER BY updated_at DESC LIMIT 4")]
        for w in ready:
            it=self.item(w['id']);c=it['coach'] or {}
            low=[s for s in c.get('scores',[]) if s.get('score',5)<PASS_SCORE]
            open_=len(it['payload'].get('unresolved') or [])
            items.append({'title':w['title']+(f' - {open_} check'+('s' if open_!=1 else '')+' need your eyes' if open_ else ' - ready' if not low else f' - {len(low)} coach notes open'),'detail':(c.get('summary') or 'Fact-checked and voiced. Review and approve.')[:160],'url':'/pitch-lab/'+w['id'],'link':'Open'})
        pending=self.db.execute("SELECT COUNT(*) FROM lessons WHERE state='PROPOSED'").fetchone()[0]
        if pending:items.append({'title':f'{pending} lesson'+('s' if pending!=1 else '')+' from results and your edits','detail':'Approve the ones every agent should follow from now on.','url':'/pitch-lab#lessons','link':'Review'})
        return items

    def board(self):
        live=self.s.rows("SELECT stage,COUNT(*) n FROM work_items WHERE stage NOT IN ('APPROVED','ARCHIVED') GROUP BY stage")
        return {'stages':{r['stage']:r['n'] for r in live},'items':[{k:v for k,v in it.items() if k!='payload'}|{'summary':self.summary(it)} for it in self.items()],
                'lessons':self.lessons(),'voice_examples':self.db.execute('SELECT COUNT(*) FROM voice_examples').fetchone()[0],'stage_words':STAGE_WORDS}

    def summary(self,it):
        c=it['coach'] or {};scores=c.get('scores',[])
        return {'avg':round(sum(s['score'] for s in scores)/len(scores),1) if scores else None,'low':len([s for s in scores if s['score']<PASS_SCORE]),
                'timing':it['payload'].get('timing'),'minutes':it['payload'].get('minutes')}
