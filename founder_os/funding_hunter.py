"""Funding Hunter domain service, integrated with the existing Founder store.

The research runner supplies source-grounded observations. This module owns
identity, eligibility, scores, currentness, history, policy and notifications.
It has no model, email, payment or submission credentials.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .store import now, js, digest, uid, PolicyError
from .hunter_policy import FACT_KEYS, WEIGHTS, SCORING_VERSION, evaluate_eligibility, score, recommend, money_profile
from .credit_policy import BENEFIT_KEYS,credits_report

RECOMMENDATIONS={'APPLY NOW','PREPARE','WATCH','REVIEW','SKIP','EXPIRED','ALREADY APPLIED','REJECTED','ACCEPTED'}
ALIASES={
 'anthropic startups':'Claude Startups','anthropic for startups':'Claude Startups','claude for startups':'Claude Startups','claude startup program':'Claude Startups',
 'nvidia inception program':'NVIDIA Inception','nvidia for startups':'NVIDIA Inception','nvidia inception':'NVIDIA Inception',
 'michigan business challenge':'Michigan Business Challenge','mbc':'Michigan Business Challenge',
 'elevenlabs startup grants':'ElevenLabs Startup Grants','elevenlabs grants program':'ElevenLabs Startup Grants',
 'aws activate':'AWS Activate','aws activate credits':'AWS Activate',
 'google for startups cloud program':'Google for Startups Cloud Program',
 'microsoft for startups founders hub':'Microsoft for Startups','microsoft for startups':'Microsoft for Startups',
}
SOURCE_RANK={'official_program':1,'official_organizer':2,'official_announcement':3,'reputable_fund':4,'directory':5,'discovery':6,'historical':7}
FUNDING_KEYS=('cash_prize_min','cash_prize_max','credits_value','estimated_usable_credits','currency','award_scope','other_benefits','equity_required','equity_percentage','investment_terms','application_fee','travel_cost')
DATES_KEYS=('application_open','deadline','timezone','event_date')
ELIGIBILITY_KEYS=('company_stage','revenue_requirement','funding_requirement','founder_requirement','student_requirement','university_requirement','location_requirement','industry_requirement','incorporation_requirement','age_requirement','other_restrictions')
ASSET_HOURS={'deck':3,'video':3,'financials':4,'references':2,'founder_bio':.5,'product_description':.5,'traction':1,'market':1,'competitors':1,'use_of_funds':1.5,'pitch_script':1,'customer_evidence':1}

def normalize(text):
    return re.sub(r'\s+',' ',re.sub(r'[^\w ]',' ',text.casefold())).strip()

def clean_url(url):
    if not url:return None
    p=urlsplit(url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:raise ValueError('Public HTTP URL required')
    if p.hostname in ('localhost','127.0.0.1','::1') or p.hostname.endswith('.local'):raise ValueError('Private URLs denied')
    query=urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_','fbclid','gclid'))])
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',query,''))

def stamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Research timestamps require timezone')
    return dt

def blank_record():
    return {'canonical_name':'','organizer':'','opportunity_type':'unknown','cycle':'unknown','cycle_kind':'unknown','official_url':None,'application_url':None,'status':'UNKNOWN',
      'dates':dict.fromkeys(DATES_KEYS),'funding':dict.fromkeys(FUNDING_KEYS),'eligibility':dict.fromkeys(ELIGIBILITY_KEYS),
      'eligibility_rules':[],'eligibility_complete':False,'requirements':[],'questions_known':None,
      'deck_required':None,'video_required':None,'financials_required':None,'references_required':None,'other_assets_required':[],
      'strategic_matches':[],'network_evidence':{},'probability_estimate':None,'why_fit':[],'why_not_fit':[],'risks':[],
      'credit_benefits':dict.fromkeys(BENEFIT_KEYS),
      'notes':'','field_sources':{},'sources':[],'discovery_sources':[],'aliases':[],'verification_state':'VERIFICATION_REQUIRED','founder_brief':None}

class FundingHunter:
    def __init__(self,store):
        self.store=store
        self.db=store.db
        self.db.executescript(Path(__file__).with_name('hunter_schema.sql').read_text(encoding='utf-8'))
        columns={r['name'] for r in self.db.execute('PRAGMA table_info(hunter_requests)')}
        for col,kind in [('attempts','INTEGER NOT NULL DEFAULT 0'),('next_attempt','TEXT'),('last_error','TEXT')]:
            if col not in columns:self.db.execute('ALTER TABLE hunter_requests ADD COLUMN '+col+' '+kind)
        version={'weights':WEIGHTS,'rubric':'hunter_policy.py','unknown_policy':'bounded score; no imputation','notifications':85}
        self.db.execute('INSERT OR IGNORE INTO scoring_versions VALUES(?,?,?,1)',(SCORING_VERSION,js(version),now()))
        defaults={'schedule':{'days':['MO','TH'],'hour':8,'minute':0,'timezone':'America/New_York'},'research_budget':{'max_queries':24,'max_candidates':120,'max_deep_verifications':24,'max_sources_per_opportunity':8},'runner':{'type':'codex_cli','status':'not_connected'}}
        for k,v in defaults.items():self.db.execute('INSERT OR IGNORE INTO hunter_settings VALUES(?,?)',(k,js(v)))
        self.migrate_existing()

    def settings(self):return {r['key']:json.loads(r['value_json']) for r in self.store.rows('SELECT * FROM hunter_settings')}

    def set_runner(self,runner):
        self.db.execute('UPDATE hunter_settings SET value_json=? WHERE key=\'runner\'',(js(runner),))

    def company_memory(self):
        # A draft never provides an eligibility fact. Approved-but-stale facts also fail closed.
        attributes={};conflicts=[]
        rows=self.store.rows('''SELECT f.*,v.source_version_id,v.last_verified_at,v.valid_until,c.topic,v.body
           FROM company_fact_values f JOIN claim_versions v ON v.id=f.claim_version_id
           JOIN claims c ON c.canonical_version_id=v.id JOIN claim_reviews r ON r.version_id=v.id WHERE r.status='approved' AND v.evidence_status='verified' ''')
        for r in rows:
            if not r['last_verified_at'] or (r['valid_until'] and stamp(r['valid_until'])<datetime.now(timezone.utc)):continue
            newest=self.store.one('SELECT id FROM source_versions WHERE source_id=(SELECT source_id FROM source_versions WHERE id=?) ORDER BY captured_at DESC,rowid DESC LIMIT 1',(r['source_version_id'],))
            if newest['id']!=r['source_version_id']:continue
            issues=self.store.rows("SELECT sources_json FROM issues WHERE kind='source_change' AND state='open'")
            if any(r['source_version_id'] in json.loads(i['sources_json']) for i in issues):continue
            if r['fact_key'] in attributes:
                conflicts.append(r['fact_key']);continue
            attributes[r['fact_key']]={'value':json.loads(r['value_json']),'claim_version_id':r['claim_version_id'],'last_verified':r['last_verified_at']}
        for k in conflicts:attributes.pop(k,None)
        canonical=self.store.rows('SELECT c.topic,c.label,v.id,v.body,v.last_verified_at,v.valid_until FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id JOIN claim_reviews r ON r.version_id=v.id WHERE r.status=\'approved\'')
        return {'attributes':attributes,'canonical_claims':canonical,'conflicting_attributes':sorted(set(conflicts)),'missing_attributes':sorted(FACT_KEYS-set(attributes))}

    def attach_fact_value(self,claim_version_id,key,value):
        if key not in FACT_KEYS:raise ValueError('Unsupported structured company attribute')
        review=self.store.one('SELECT status FROM claim_reviews WHERE version_id=?',(claim_version_id,))
        if review['status']!='proposed':raise PolicyError('Add structured values before requesting canonical approval')
        self.db.execute('INSERT INTO company_fact_values VALUES(?,?,?)',(claim_version_id,key,js(value)))

    def _program(self,name,organizer,official_url=None,aliases=(),kind='unknown'):
        canonical=ALIASES.get(normalize(name),name.strip())
        # Curated aliases carry organizer corrections, preventing false separate NVIDIA identities.
        if canonical=='NVIDIA Inception':organizer='NVIDIA'
        if canonical=='Michigan Business Challenge':organizer='Zell Lurie Institute, University of Michigan'
        if canonical=='ElevenLabs Startup Grants':organizer='ElevenLabs'
        alias=self.db.execute('SELECT program_id FROM program_aliases WHERE alias_key=?',(normalize(organizer)+'|'+normalize(canonical),)).fetchone()
        key=normalize(organizer)+'|'+normalize(canonical)
        existing=self.db.execute('SELECT * FROM funding_programs WHERE identity_key=?',(key,)).fetchone()
        pid=alias['program_id'] if alias else existing['id'] if existing else 'program-'+digest(key)[:20]
        url=clean_url(official_url)
        if not existing and not alias:
            self.db.execute('INSERT INTO funding_programs VALUES(?,?,?,?,?,?,?)',(pid,canonical,organizer,key,url,kind,now()))
        elif url:self.db.execute('UPDATE funding_programs SET official_url=COALESCE(official_url,?),opportunity_type=CASE WHEN opportunity_type=\'unknown\' THEN ? ELSE opportunity_type END WHERE id=?',(url,kind,pid))
        for a in (name,canonical,*aliases):
            akey=normalize(organizer)+'|'+normalize(a)
            prior=self.db.execute('SELECT program_id FROM program_aliases WHERE alias_key=?',(akey,)).fetchone()
            if prior and prior['program_id']!=pid:raise ValueError('Alias conflicts with an existing program')
            self.db.execute('INSERT OR IGNORE INTO program_aliases VALUES(?,?,?,?)',(akey,pid,a,'curated identity / supplied official alias'))
        return pid

    def _cycle(self,pid,label):
        key=normalize(label)
        if not key:raise ValueError('Cycle is required, including explicit unknown')
        cid='cycle-'+digest([pid,key])[:20]
        self.db.execute('INSERT OR IGNORE INTO funding_cycles VALUES(?,?,?,?)',(cid,pid,key,label))
        return cid

    def migrate_existing(self):
        for old in self.store.rows('SELECT * FROM opportunities WHERE id NOT IN (SELECT opportunity_id FROM funding_intelligence)'):
            name=old['program'];organizer=old['organizer'];label=old['cycle']
            if 'elevenlabs' in organizer.lower():name='ElevenLabs Startup Grants'
            if '2025-2026 historical' in label:label='2025-2026'
            pid=self._program(name,organizer,old['official_url'])
            cid=self._cycle(pid,label)
            prior=self.db.execute('SELECT opportunity_id FROM funding_intelligence WHERE cycle_id=?',(cid,)).fetchone()
            if prior:
                self.store.issue('duplicate_suspected','Legacy cycle duplicate '+old['id'],'Preserved original application links; needs explicit record reconciliation.',[old['source_version_id']] if old['source_version_id'] else [])
                continue
            data=blank_record();data.update(canonical_name=name,organizer=organizer,cycle=label,official_url=old['official_url'],notes='Migrated existing record. Historical materials do not establish submission or result.')
            el=evaluate_eligibility([],{},False);ready=self.material_readiness(data);sc=score(data,el,ready,{})
            analysis={'eligibility':el,'scoring':sc,'materials':ready,'missing_company_facts':[],'historical':True}
            self.db.execute('INSERT INTO funding_intelligence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)',(old['id'],pid,cid,js(data),js(analysis),'REVIEW','VERIFICATION_REQUIRED',sc['lower_bound'],sc['upper_bound'],None,None,now(),now(),now()))
            if old['source_version_id']:
                path=self.store.one('SELECT original_path FROM sources WHERE id=(SELECT source_id FROM source_versions WHERE id=?)',(old['source_version_id'],))['original_path']
                self.db.execute('INSERT OR IGNORE INTO program_history VALUES(?,?,?,?,?,?,?,?)',('history-'+digest([pid,path,old['id']])[:20],pid,cid,old['source_version_id'],path,'legacy record '+old['id'],'saved_material',data['notes']))

    def identity_candidates(self,name,organizer,url=None):
        title=normalize(ALIASES.get(normalize(name),name));url=clean_url(url)
        matches=[]
        for p in self.store.rows('SELECT * FROM funding_programs'):
            names=[normalize(p['canonical_name'])]+[normalize(a['alias']) for a in self.store.rows('SELECT alias FROM program_aliases WHERE program_id=?',(p['id'],))]
            sim=max(SequenceMatcher(None,title,n).ratio() for n in names)
            same_url=bool(url and p['official_url'] and clean_url(p['official_url'])==url)
            if same_url or sim>=.8:matches.append({'program_id':p['id'],'name':p['canonical_name'],'similarity':round(sim,3),'exact_official_url':same_url,'organizer_match':normalize(organizer)==normalize(p['organizer'])})
        return matches

    def validate(self,item):
        data=blank_record()
        for k,v in item.items():
            if k not in data:raise ValueError('Unexpected opportunity field: '+k)
            if k in ('funding','dates','eligibility','credit_benefits'):data[k].update(v)
            else:data[k]=v
        if not data['canonical_name'] or not data['organizer']:raise ValueError('Program name and organizer required')
        if data['status'] not in {'OPEN','CLOSED','UPCOMING','UNKNOWN','EXPIRED'}:raise ValueError('Unknown application status')
        if data['cycle_kind'] not in {'annual','cohort','rolling','unknown'}:raise ValueError('Unknown cycle kind')
        if data['cycle_kind']=='rolling':data['cycle']='rolling'
        if data['cycle_kind'] in ('annual','cohort') and data['cycle']=='unknown':raise ValueError('Annual/cohort identity needs a cycle')
        data['official_url']=clean_url(data['official_url']);data['application_url']=clean_url(data['application_url'])
        if len(data['sources'])>self.settings()['research_budget']['max_sources_per_opportunity']:raise ValueError('Source budget exceeded')
        available={}
        for s in data['sources']:
            s['url']=clean_url(s['url'])
            if s['role'] not in SOURCE_RANK:raise ValueError('Source quality role required')
            checked=stamp(s['checked_at'])
            if checked>datetime.now(timezone.utc)+timedelta(minutes=5):raise ValueError('Future source checks denied')
            if not s.get('excerpt'):raise ValueError('Every verification source requires evidence text/locator')
            if len(s['excerpt'])>12000:raise ValueError('Keep evidence excerpts bounded')
            available[s['url']]=s
        def evidence(field):
            urls=data['field_sources'].get(field,[])
            if isinstance(urls,str):urls=[urls]
            refs=[available.get(clean_url(u)) for u in urls]
            valid=refs and all(r and SOURCE_RANK[r['role']]<=3 and (datetime.now(timezone.utc)-stamp(r['checked_at'])).days<=30 for r in refs)
            if not valid:raise ValueError('Current official provenance missing for '+field)
        for k in ('status','cycle_kind','application_url'):
            if data[k] not in (None,'UNKNOWN','unknown'):evidence(k)
        for section,keys in (('funding',FUNDING_KEYS),('dates',DATES_KEYS),('eligibility',ELIGIBILITY_KEYS),('credit_benefits',BENEFIT_KEYS)):
            if any(k not in keys for k in data[section]):raise ValueError('Unexpected '+section+' field')
            for k,v in data[section].items():
                if v is not None and v!=[]:evidence(section+'.'+k)
        for k in ('questions_known','deck_required','video_required','financials_required','references_required'):
            if data[k] is not None and not (k=='questions_known' and data[k] is False):evidence(k)
        if data['requirements']:evidence('requirements')
        if data['eligibility_complete']:evidence('eligibility_complete')
        for r in data['eligibility_rules']:
            if r['fact_key'] not in FACT_KEYS or r['op'] not in ('eq','in','contains','gte','lte','lt','present'):raise ValueError('Invalid eligibility rule')
            if clean_url(r['source_url']) not in available:raise ValueError('Eligibility rule lacks checked source')
            if SOURCE_RANK[available[clean_url(r['source_url'])]['role']]>3:raise ValueError('Eligibility cannot rely on discovery source')
        if data['strategic_matches']:evidence('strategic_matches')
        if any(v is not None for k,v in data['network_evidence'].items() if k!='complete') or data['network_evidence'].get('complete') is True:evidence('network_evidence')
        if data['probability_estimate']:evidence('probability_estimate')
        for k in ('cash_prize_min','cash_prize_max','credits_value','estimated_usable_credits','application_fee','travel_cost','equity_percentage'):
            v=data['funding'][k]
            if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or v<0):raise ValueError('Invalid funding amount '+k)
            if v is not None:
                import math
                if not math.isfinite(v):raise ValueError('Funding amount must be finite')
        if data['funding']['equity_percentage'] is not None and data['funding']['equity_percentage']>100:raise ValueError('Invalid equity percentage')
        if data['funding']['equity_required'] not in (True,False,None):raise ValueError('Equity flag must be known boolean or null')
        for k in ('referral_required','company_email_required','paid_account_required','deposit_required','terms_acceptance_required'):
            v=data['credit_benefits'][k]
            if v is not None and not isinstance(v,bool):raise ValueError('Benefit condition must be boolean or unknown: '+k)
        for k in ('minimum_spend','expiration_months'):
            v=data['credit_benefits'][k]
            if v is not None:
                import math
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid credit condition: '+k)
        if data['funding']['cash_prize_min'] is not None and data['funding']['cash_prize_max'] is not None and data['funding']['cash_prize_min']>data['funding']['cash_prize_max']:raise ValueError('Invalid prize range')
        for k in ('application_open','event_date','deadline'):
            if data['dates'][k]:datetime.fromisoformat(data['dates'][k].replace('Z','+00:00'))
        if data['probability_estimate']:
            p=data['probability_estimate']
            if not 0<=p['numerator']<=p['denominator'] or p['denominator']<=0:raise ValueError('Invalid probability counts')
        official=[s for s in data['sources'] if SOURCE_RANK[s['role']]<=3]
        data['verification_state']='VERIFIED' if official and data['official_url'] and data['status']!='UNKNOWN' else 'VERIFICATION_REQUIRED'
        from .opportunity_curation import validate_brief
        validate_brief(data['founder_brief'],data,self.company_memory()['attributes'],clean_url)
        return data

    def material_readiness(self,data):
        requirements=data.get('requirements',[])
        ready=[];adapt=[];missing=[];hours=.5 if requirements else None
        refs=self.store.rows('SELECT m.*,s.original_path,v.sha256 FROM material_registry m JOIN source_versions v ON v.id=m.source_version_id JOIN sources s ON s.id=v.source_id')
        for req in requirements:
            kind=req['kind'];label=req.get('label',kind)
            answers=self.store.approved_answers(req.get('question') or label)
            answers=[a for a in answers if a['match_score']>=2]
            materials=[m for m in refs if m['kind']==kind]
            current=[]
            for m in materials:
                links=json.loads(m['claim_versions_json'])
                claim_current=all(self.store.one('SELECT canonical_version_id FROM claims WHERE id=(SELECT claim_id FROM claim_versions WHERE id=?)',(v,))['canonical_version_id']==v for v in links)
                latest=self.store.one('SELECT id FROM source_versions WHERE source_id=(SELECT source_id FROM source_versions WHERE id=?) ORDER BY captured_at DESC,rowid DESC LIMIT 1',(m['source_version_id'],))['id']==m['source_version_id']
                unchanged=False
                if m['status']=='approved' and m['checked_at'] and links and claim_current and latest:
                    try:unchanged=digest(Path(m['original_path']).read_bytes())==m['sha256']
                    except OSError:pass
                if unchanged:current.append(m)
            if answers or current:
                ready.append({'label':label,'kind':kind,'answer_versions':[a['id'] for a in answers[:3]],'materials':[m['id'] for m in current],'needs_final_adaptation':True})
                hours+=.15
            elif materials:
                adapt.append({'label':label,'kind':kind,'references':[{'id':m['id'],'source_path':m['original_path'],'status':m['status']} for m in materials],'reason':'Referenced material is unapproved or stale'})
                hours+=ASSET_HOURS.get(kind,1)*.6
            else:
                missing.append({'label':label,'kind':kind});hours+=ASSET_HOURS.get(kind,1)
        percentage=round(100*len(ready)/len(requirements)) if requirements else None
        effort='UNKNOWN' if hours is None else 'Very Low' if hours<=.75 else 'Low' if hours<=2 else 'Medium' if hours<=5 else 'High' if hours<=10 else 'Very High'
        return {'percentage':percentage,'estimated_completion_percentage':percentage,'ready':ready,'needs_adaptation':adapt,'missing':missing,'estimated_hours':round(hours,2) if hours is not None else None,'estimated_hours_to_apply':round(hours,2) if hours is not None else None,'effort':effort,'estimate_basis':'0.5h administration + per-asset planning rubric; review estimate, not measured completion time','existing_materials':[{'id':m['id'],'kind':m['kind'],'status':m['status'],'source_path':m['original_path']} for m in refs],'reusable_answers':[x for r in ready for x in r['answer_versions']],'reusable_decks':[m['id'] for m in refs if m['kind']=='deck' and any(m['id'] in r.get('materials',[]) for r in ready)],'reusable_videos':[m['id'] for m in refs if m['kind']=='video' and any(m['id'] in r.get('materials',[]) for r in ready)]}

    def _history_status(self,oid):
        outcomes=self.store.rows('SELECT outcome FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC LIMIT 1',(oid,))
        if outcomes:
            o=outcomes[0]['outcome']
            if o in ('Won','Accepted'):return 'ACCEPTED'
            if o=='Rejected':return 'REJECTED'
            if o in ('Applied','Advanced','Finalist'):return 'ALREADY APPLIED'
        submitted=self.db.execute('SELECT 1 FROM submissions s JOIN applications a ON a.id=s.application_id WHERE a.opportunity_id=?',(oid,)).fetchone()
        return 'ALREADY APPLIED' if submitted else None

    def analyze(self,data,oid=None):
        memory=self.company_memory();facts=memory['attributes']
        eligibility=evaluate_eligibility(data['eligibility_rules'],facts,data['eligibility_complete'])
        materials=self.material_readiness(data)
        scoring=score(data,eligibility,materials,facts)
        recommendation=recommend(data,eligibility,scoring,self._history_status(oid) if oid else None)
        credit_value=data['funding'].get('estimated_usable_credits')
        cash=data['funding'].get('cash_prize_max')
        prob=data.get('probability_estimate')
        probability=prob['numerator']/prob['denominator'] if prob else None
        hours=materials['estimated_hours']
        roi=round(((cash*probability) if cash is not None and probability is not None else credit_value)/hours,2) if hours and (credit_value is not None or cash is not None and probability is not None) else None
        from .opportunity_curation import assessed_brief
        return {'eligibility':eligibility,'scoring':scoring,'materials':materials,'recommended_action':recommendation,'money':money_profile(data),'strategic_value':data['why_fit'],'time_cost':hours,'probability_estimate':{'historical_base_rate':probability,'a_story_probability':None},'roi':{'estimated_value_per_hour':roi,'currency':data['funding'].get('currency'),'basis':'Expected cash from published historical base rate or confirmed usable credits; does not equate headline credits with cash'},'company_fact_versions':{k:v['claim_version_id'] for k,v in facts.items()},'missing_company_facts':eligibility['missing'],'why_fit':data['why_fit'],'why_not_fit':data['why_not_fit'],'risks':data['risks'],'founder_brief':assessed_brief(data,facts)}

    def daily_shortlist(self,instant=None):
        from .opportunity_curation import shortlist
        return shortlist(self.list('All'),self.settings().get('daily_report',{}).get('top_limit',5),instant)

    def upsert(self,item,run_id=None):
        data=self.validate(item)
        canonical=ALIASES.get(normalize(data['canonical_name']),data['canonical_name'])
        candidates=self.identity_candidates(canonical,data['organizer'],data['official_url'])
        exact=[c for c in candidates if c['exact_official_url'] or c['similarity']==1 and c['organizer_match']]
        if len(exact)>1:raise ValueError('DUPLICATE_SUSPECTED: conflicting exact identity')
        if exact:
            pid=exact[0]['program_id'];program=self.store.one('SELECT * FROM funding_programs WHERE id=?',(pid,))
            data['canonical_name']=program['canonical_name'];data['organizer']=program['organizer']
        else:
            fuzzy=[c for c in candidates if c['similarity']>=.85 and c['organizer_match']]
            if fuzzy:raise ValueError('DUPLICATE_SUSPECTED: '+js(fuzzy))
            pid=self._program(canonical,data['organizer'],data['official_url'],data['aliases'],data['opportunity_type'])
        self._program(data['canonical_name'],data['organizer'],data['official_url'],data['aliases'],data['opportunity_type'])
        cid=self._cycle(pid,data['cycle'])
        old=self.db.execute('SELECT * FROM funding_intelligence WHERE cycle_id=?',(cid,)).fetchone()
        oid=old['opportunity_id'] if old else 'opp-'+digest([pid,cid])[:20]
        old_data=json.loads(old['data_json']) if old else None
        old_analysis=json.loads(old['analysis_json']) if old else None
        analysis=self.analyze(data,oid if old else None)
        rec=analysis['recommended_action'];sc=analysis['scoring'];checked=now()
        verified=max((s['checked_at'] for s in data['sources'] if SOURCE_RANK[s['role']]<=3),default=None)
        days=7 if rec=='REVIEW' or not data['dates']['deadline'] else 3 if sc['dates']['days_remaining'] is not None and 0<=sc['dates']['days_remaining']<=21 else 30 if rec in ('EXPIRED','SKIP') else 14
        if rec=='WATCH' and data['dates']['application_open']:
            try:next_check=min(datetime.now(timezone.utc)+timedelta(days=days),datetime.fromisoformat(data['dates']['application_open']).replace(tzinfo=timezone.utc)-timedelta(days=7))
            except ValueError:next_check=datetime.now(timezone.utc)+timedelta(days=days)
        else:next_check=datetime.now(timezone.utc)+timedelta(days=days)
        next_check=max(datetime.now(timezone.utc)+timedelta(days=1),next_check).isoformat()
        with self.store.transaction():
            if not old:
                self.db.execute('INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid, pid+'|'+cid,data['organizer'],data['canonical_name'],data['cycle'],data['official_url'],data['dates']['deadline'],data['dates']['timezone'],js(data['funding']),analysis['eligibility']['status'],sc['score'],js(sc['components']),rec,checked,None))
                self.db.execute('INSERT INTO funding_intelligence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)',(oid,pid,cid,js(data),js(analysis),rec,data['verification_state'],sc['lower_bound'],sc['upper_bound'],sc['score'],verified,checked,checked,next_check))
            else:
                self.db.execute('UPDATE opportunities SET official_url=?,deadline=?,deadline_timezone=?,terms_json=?,eligibility=?,fit_score=?,fit_reason=?,state=?,last_checked_at=? WHERE id=?',(data['official_url'],data['dates']['deadline'],data['dates']['timezone'],js(data['funding']),analysis['eligibility']['status'],sc['score'],js(sc['components']),rec,checked,oid))
                self.db.execute('UPDATE funding_intelligence SET data_json=?,analysis_json=?,recommendation=?,verification_state=?,score_min=?,score_max=?,fit_score=?,last_verified=?,last_checked=?,next_check=?,revision=revision+1 WHERE opportunity_id=?',(js(data),js(analysis),rec,data['verification_state'],sc['lower_bound'],sc['upper_bound'],sc['score'],verified,checked,next_check,oid))
            version_id='funding-version-'+digest([oid,data,analysis])[:24]
            self.db.execute('INSERT OR IGNORE INTO funding_versions VALUES(?,?,?,?,?,?)',(version_id,oid,run_id,js(data),js(analysis),checked))
            for s in data['sources']:
                sha=digest(s['excerpt']);sid='web-'+digest([s['url'],sha,s['role']])[:24]
                self.db.execute('INSERT OR IGNORE INTO funding_sources VALUES(?,?,?,?,?,?,?)',(sid,s['url'],s['role'],s['checked_at'],sha,s['excerpt'],s.get('fetch_status','checked_by_research_runner')))
                self.db.execute('INSERT OR IGNORE INTO funding_source_links VALUES(?,?)',(oid,sid))
            self._notify(oid,data,analysis,old_data,old_analysis,version_id)
            self.store.log('funding.opportunity_updated' if old else 'funding.opportunity_created','funding_hunter',{'opportunity_id':oid,'program_id':pid,'cycle_id':cid,'version_id':version_id,'recommendation':rec})
        return {'opportunity_id':oid,'program_id':pid,'cycle_id':cid,'created':not bool(old),'recommendation':rec,'fit_score':sc['score'],'score_range':[sc['lower_bound'],sc['upper_bound']]}

    def _notify(self,oid,data,analysis,previous,previous_analysis,version_id):
        score_value=analysis['scoring']['score'];days=analysis['scoring']['dates']['days_remaining'];kind=None
        if score_value is not None and score_value>=85 and analysis['eligibility']['status']=='ELIGIBLE' and analysis['recommended_action'] in ('APPLY NOW','PREPARE'):
            if not previous:kind='EXCEPTIONAL' if score_value>=90 else 'NEW_HIGH_FIT'
            elif previous['status']!='OPEN' and data['status']=='OPEN':kind='WATCH_OPENED'
            elif not previous['dates']['deadline'] and data['dates']['deadline']:kind='DEADLINE_KNOWN'
            elif days is not None and 0<=days<=7:kind='HIGH_FIT_DEADLINE'
        if previous_analysis and previous_analysis['eligibility']['status']!=analysis['eligibility']['status'] and (previous_analysis['scoring']['upper_bound']>=80):kind='ELIGIBILITY_CHANGED'
        if kind:
            key=digest([oid,kind,data['cycle'],data['dates']['deadline'],data['status'],analysis['eligibility']['status']])
            payload={'opportunity_id':oid,'program':data['canonical_name'],'fit_score':score_value,'recommendation':analysis['recommended_action'],'funding':data['funding'],'deadline':data['dates']['deadline'],'readiness':analysis['materials']['percentage'],'founder_hours':analysis['materials']['estimated_hours']}
            self.db.execute('INSERT OR IGNORE INTO funding_notifications VALUES(?,?,?,?,?,NULL,?)',('notice-'+key[:24],oid,kind,js(payload),now(),key))

    def runFundingHunter(self,batch,request_key=None):
        """Stable entry point for manual, scheduled and event-driven research runs."""
        key=request_key or batch.get('request_key') or uid('manual')
        payload_hash=digest(batch)
        previous=self.db.execute('SELECT * FROM funding_runs WHERE request_key=?',(key,)).fetchone()
        if previous:
            if previous['input_hash']!=payload_hash:raise ValueError('Run key used with different research payload')
            if previous['state'] in ('COMPLETE','PARTIAL'):return json.loads(previous['report_json'])
            if previous['lease_until'] and stamp(previous['lease_until'])>datetime.now(timezone.utc):raise ValueError('Run is already leased')
        budget=self.settings()['research_budget']
        if len(batch.get('queries',[]))>budget['max_queries'] or len(batch.get('candidates',[]))>budget['max_candidates'] or len(batch.get('opportunities',[]))>budget['max_deep_verifications']:raise ValueError('Research budget exceeded')
        rid='run-'+digest(key)[:24];started=batch.get('research_started_at') or now()
        stamp(started)
        with self.store.transaction():
            if not previous:self.db.execute('INSERT INTO funding_runs VALUES(?,?,?,?,NULL,?,?,?,?)',(rid,key,payload_hash,started,'RUNNING',js({}),js(batch.get('usage',{'api_calls':0,'model_api_cost':0,'research_runner':'codex'})),(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()))
            else:self.db.execute('UPDATE funding_runs SET state=\'RUNNING\',lease_until=? WHERE id=?',((datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),rid))
        report={'run_id':rid,'started_at':started,'queries_used':batch.get('queries',[]),'sources_checked':[],'candidates_discovered':len(batch.get('candidates',[])),'duplicates_removed':0,'records_created':0,'records_updated':0,'recommendations_generated':0,'errors':list(batch.get('errors',[])),'items':[],'usage':batch.get('usage',{'api_calls':0,'model_api_cost':0,'research_runner':'codex'}),'new_programs':0,'verified':0,'skipped':0}
        programs_before=self.db.execute('SELECT count(*) FROM funding_programs').fetchone()[0]
        for c in batch.get('candidates',[]):
            try:
                url=clean_url(c['url']);cid='candidate-'+digest([rid,url])[:24]
                self.db.execute('INSERT OR IGNORE INTO funding_candidates VALUES(?,?,?,?,?,?,?)',(cid,rid,c['title'],url,c.get('family','unspecified'),c.get('state','DISCOVERED'),js(c)))
            except (ValueError,KeyError,TypeError) as e:
                report['errors'].append({'state':'RESEARCH_INCOMPLETE','message':'Invalid discovery candidate: '+str(e)})
        for item in batch.get('opportunities',[]):
            try:
                result=self.upsert(item,rid);report['items'].append(result)
                report['records_created' if result['created'] else 'records_updated']+=1
                if not result['created']:report['duplicates_removed']+=1
                if result['recommendation'] in ('APPLY NOW','PREPARE'):report['recommendations_generated']+=1
                if result['recommendation'] in ('SKIP','EXPIRED'):report['skipped']+=1
                data=self.detail(result['opportunity_id'])['data']
                if data['verification_state']=='VERIFIED':report['verified']+=1
                report['sources_checked'].extend(s['url'] for s in data['sources'])
            except (ValueError,KeyError,TypeError) as e:
                report['errors'].append({'program':item.get('canonical_name'),'state':'DUPLICATE_SUSPECTED' if 'DUPLICATE_SUSPECTED' in str(e) else 'RESEARCH_INCOMPLETE','message':str(e)})
        report['new_programs']=self.db.execute('SELECT count(*) FROM funding_programs').fetchone()[0]-programs_before
        report['decision_briefs_created']=sum(bool(item.get('founder_brief')) for item in batch.get('opportunities',[]))-sum(bool(item.get('founder_brief')) and any(e.get('program')==item.get('canonical_name') for e in report['errors']) for item in batch.get('opportunities',[]))
        report['curated_shortlist']=[{'opportunity_id':d['opportunity_id'],'name':d['data']['canonical_name'],'recommendation':d['recommendation']} for d in self.daily_shortlist()]
        report['shortlist_version']='founder-shortlist-1'
        report['sources_checked']=sorted(set(report['sources_checked']));report['completed_at']=now()
        report['duration_seconds']=round((stamp(report['completed_at'])-stamp(started)).total_seconds(),3)
        state='PARTIAL' if report['errors'] else 'COMPLETE'
        with self.store.transaction():
            self.db.execute('UPDATE funding_runs SET completed_at=?,state=?,report_json=?,lease_until=NULL WHERE id=?',(report['completed_at'],state,js(report),rid))
            if batch.get('request_id'):self.db.execute('UPDATE hunter_requests SET state=\'COMPLETE\',run_id=? WHERE id=?',(rid,batch['request_id']))
            self.store.log('funding.run_completed','funding_hunter',{'run_id':rid,'state':state,'created':report['records_created'],'errors':len(report['errors'])})
        return report

    def request_run(self,reason='Founder requested run now',key=None):
        key=key or uid('manual');rid='request-'+digest(key)[:24]
        self.db.execute('INSERT OR IGNORE INTO hunter_requests(id,request_key,reason,state,created_at,run_id) VALUES(?,?,?,\'QUEUED\',?,NULL)',(rid,key,reason,now()))
        return {'request_id':rid,'state':'QUEUED','runner':self.settings()['runner']}

    def _grounding_changed(self,current,previous):
        """A brief needs re-grounding only when a fact it relied on changed value or disappeared, not when the owner re-confirmed the same value."""
        if set(current)!=set(previous):return True
        for key,vid in current.items():
            if vid==previous[key]:continue
            old=self.db.execute('SELECT value_json FROM company_fact_values WHERE claim_version_id=? AND fact_key=?',(previous[key],key)).fetchone()
            new=self.db.execute('SELECT value_json FROM company_fact_values WHERE claim_version_id=? AND fact_key=?',(vid,key)).fetchone()
            if not old or not new or json.loads(old[0])!=json.loads(new[0]):return True
        return False

    def detail(self,oid):
        r=self.store.one('SELECT * FROM funding_intelligence WHERE opportunity_id=?',(oid,))
        data=json.loads(r.pop('data_json'));saved=json.loads(r.pop('analysis_json'))
        analysis=self.analyze(data,oid)
        brief=analysis.get('founder_brief');previous_brief=saved.get('founder_brief')
        if brief and previous_brief and self._grounding_changed(brief['company_fact_versions'],previous_brief.get('company_fact_versions',{})):
            brief['basis']='unknown';brief['grounding_changed']=True
        analysis['credits']=credits_report(data)
        r.update(data=data,analysis=analysis,saved_analysis=saved,history=self.store.rows('SELECT * FROM program_history WHERE program_id=?',(r['program_id'],)),applications=self.store.rows('SELECT * FROM applications WHERE opportunity_id=?',(oid,)),outcomes=self.store.rows('SELECT * FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC',(oid,)),decisions=self.store.rows('SELECT * FROM funding_decisions WHERE opportunity_id=? ORDER BY created_at DESC',(oid,)),source_provenance=self.store.rows('SELECT s.* FROM funding_sources s JOIN funding_source_links l ON l.source_id=s.id WHERE l.opportunity_id=?',(oid,)))
        if r['last_verified'] and (datetime.now(timezone.utc)-stamp(r['last_verified'])).days>30:
            r['verification_state']='VERIFICATION_REQUIRED';analysis['recommended_action']='REVIEW'
        r['recommendation']=analysis['recommended_action'];r['fit_score']=analysis['scoring']['score']
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='opportunity_supersessions'").fetchone():
            superseded=self.db.execute('SELECT * FROM opportunity_supersessions WHERE superseded_id=?',(oid,)).fetchone()
            if superseded:
                r['recommendation']='SKIP';analysis['recommended_action']='SKIP';analysis['why_not_fit']=[superseded['reason']]+analysis['why_not_fit'];r['superseded_by']=superseded['current_id']
        versions=self.store.rows('SELECT captured_at,data_json FROM funding_versions WHERE opportunity_id=? ORDER BY captured_at DESC LIMIT 2',(oid,))
        r['tracking']={'discovered_by':'Funding Hunter / historical migration','previously_seen':bool(versions and len(versions)>1 or r['history']),'previous_status':json.loads(versions[1]['data_json'])['status'] if len(versions)>1 else None,'next_recheck':r['next_check']}
        return r

    def list(self,view='Recommended',filters=None):
        filters=filters or {};items=[]
        for row in self.store.rows('SELECT opportunity_id FROM funding_intelligence'):
            d=self.detail(row['opportunity_id']);a=d['analysis'];rec=d['recommendation'];sc=a['scoring']
            allowed={'Apply Now':{'APPLY NOW'},'Prepare':{'PREPARE'},'Watching':{'WATCH'},'Applied':{'ALREADY APPLIED'},'Rejected':{'REJECTED'},'Accepted':{'ACCEPTED'},'Skipped':{'SKIP'},'Expired':{'EXPIRED'}}
            if view=='Recommended' and not (rec not in ('EXPIRED','SKIP','REJECTED','ALREADY APPLIED') and ((sc['score'] is not None and sc['score']>=80) or rec=='REVIEW' and sc['upper_bound']>=80 and d['last_verified'] and sc['coverage']>0 and d['data']['status']!='CLOSED')):continue
            if view=='New' and stamp(d['discovered_at'])<datetime.now(timezone.utc)-timedelta(days=7):continue
            if view in allowed and rec not in allowed[view]:continue
            if filters.get('min_score') is not None and (sc['score'] is None or sc['score']<float(filters['min_score'])):continue
            if filters.get('type') and d['data']['opportunity_type']!=filters['type']:continue
            if filters.get('status') and rec!=filters['status']:continue
            if filters.get('effort') and a['materials']['effort']!=filters['effort']:continue
            if filters.get('non_dilutive') and d['data']['funding']['equity_required'] is not False:continue
            if filters.get('location') and filters['location'].casefold() not in str(d['data']['eligibility'].get('location_requirement') or '').casefold():continue
            if filters.get('category') and filters['category'].casefold() not in js(d['data']['strategic_matches']).casefold():continue
            if filters.get('min_cash') and (d['data']['funding']['cash_prize_max'] is None or d['data']['funding']['cash_prize_max']<float(filters['min_cash'])):continue
            if filters.get('deadline_before') and (not d['data']['dates']['deadline'] or d['data']['dates']['deadline'][:10]>filters['deadline_before']):continue
            items.append(d)
        # Unrated programs rank by their midpoint estimate; ranking by upper bound rewarded missing evidence.
        return sorted(items,key=lambda d:(d['recommendation'] in ('EXPIRED','SKIP','REJECTED'),-(d['analysis']['scoring']['estimate'] or 0),d['data']['dates']['deadline'] or '9999'))

    def decide(self,oid,decision,reason,actor='owner'):
        if actor!='owner':raise PolicyError('Funding Hunter cannot impersonate the owner')
        if decision not in ('APPLY','PREPARE','WATCH','SKIP'):raise ValueError('Unsupported founder decision')
        if not reason.strip():raise ValueError('Decision reason is required for learning')
        d=self.detail(oid);did=uid('decision')
        self.db.execute('INSERT INTO funding_decisions VALUES(?,?,?,?,?,?,?,?)',(did,oid,d['recommendation'],js(d['analysis']['scoring']),decision,reason,now(),actor))
        if decision=='WATCH':self.db.execute("UPDATE funding_intelligence SET next_check=? WHERE opportunity_id=?",((datetime.now(timezone.utc)+timedelta(days=7)).isoformat(),oid))
        self.store.log('funding.founder_decision',actor,{'decision_id':did,'opportunity_id':oid,'decision':decision,'reason':reason})
        return {'decision_id':did,'recorded':True,'external_action_performed':False}

    def start_application(self,oid):
        self.detail(oid)
        old=self.db.execute('SELECT id FROM applications WHERE opportunity_id=? ORDER BY created_at LIMIT 1',(oid,)).fetchone()
        if old:return old['id']
        aid='app-'+digest(oid)[:20]
        self.db.execute('INSERT INTO applications VALUES(?,?,?,\'draft\',?)',(aid,oid,self.detail(oid)['data']['canonical_name']+' application',now()))
        self.store.log('funding.application_started','owner',{'application_id':aid,'opportunity_id':oid,'questions':'not yet verified; must import exact prompts'})
        return aid

    def outcome(self,oid,outcome,note,source_version_id=None,evidence_url=None,application_id=None,submission_id=None,occurred_at=None):
        if outcome not in ('Applied','Advanced','Finalist','Won','Rejected','Accepted','Withdrawn'):raise ValueError('Unknown outcome')
        self.detail(oid)
        if not note.strip() or not (source_version_id or evidence_url or submission_id):raise ValueError('Outcome needs attributable evidence')
        if source_version_id:self.store.one('SELECT id FROM source_versions WHERE id=?',(source_version_id,))
        if application_id and self.store.one('SELECT opportunity_id FROM applications WHERE id=?',(application_id,))['opportunity_id']!=oid:raise ValueError('Foreign application')
        if submission_id:
            s=self.store.one('SELECT application_id FROM submissions WHERE id=?',(submission_id,))
            if self.store.one('SELECT opportunity_id FROM applications WHERE id=?',(s['application_id'],))['opportunity_id']!=oid:raise ValueError('Foreign submission')
        when=occurred_at or now()
        if stamp(when)>datetime.now(timezone.utc):raise ValueError('Outcome cannot be in the future')
        eid='outcome-'+digest([oid,outcome,source_version_id,evidence_url,submission_id,note])[:24]
        self.db.execute('INSERT OR IGNORE INTO funding_outcomes VALUES(?,?,?,?,?,?,?,?,?,?)',(eid,oid,application_id,submission_id,outcome,source_version_id,clean_url(evidence_url),note,when,now()))
        return eid

    UNLOCKS={'incorporated':'programs that require a legal entity','us_company':'US-only programs','incorporation_date':'company-age limits',
             'uses_ai':'AI programs and AI credit grants','product_stage':'stage-specific programs','customer_type':'consumer-focused programs',
             'business_type':'business-model tracks','industry':'industry tracks','team_size':'team-size limits','self_funded':'bootstrapped-only credits',
             'institutional_equity_funding':'"no VC funding" programs','funding_stage':'stage-of-funding limits','location':'regional programs',
             'headquarters':'regional programs','previous_programs':'programs that exclude or favor past participants','revenue_usd':'revenue limits',
             'annual_revenue':'revenue limits','founded_date':'company-age limits','monetized_product':'revenue-stage programs'}

    def review_card(self,pending,memory):
        """Plain-language view of one pending proposal: what it says, what approving changes, and the agent's suggestion."""
        p=pending.get('proposal') or {};payload=json.loads(pending['payload_json'])
        values={v['fact_key']:json.loads(v['value_json']) for v in payload.get('structured_values',[])}
        unlocks=list(dict.fromkeys(self.UNLOCKS.get(k,k.replace('_',' ')) for k in values))
        replaces=[{'fact':k,'current':memory[k]['value'],'proposed':v} for k,v in values.items() if k in memory and memory[k]['value']!=v]
        status=p.get('evidence_status')
        if pending['action']!='promote_claim':kind,why='ANSWER','This needs your decision.'
        elif status in ('hypothesis','unknown') and not values:kind,why='REMINDER','This is a reminder, not a fact. Dismiss it once handled.'
        elif status=='verified':kind,why='APPROVE','Comes from your own confirmation or an official source.'
        elif status=='reported':kind,why='CHECK','Reported in your materials but not verified. Approve only if it is still true.'
        else:kind,why='ANSWER','The evidence is unclear. Edit it into a true sentence or reject it.'
        return {'id':pending['id'],'kind':kind,'why':why,'label':p.get('label') or pending['action'].replace('_',' '),'topic':p.get('topic'),
                'sentence':p.get('body') or pending.get('decision_needed'),'unlocks':unlocks,'replaces':replaces,'values':values,
                'source':p.get('original_path'),'locator':p.get('locator'),'requested_at':pending.get('requested_at'),'editable':pending['action']=='promote_claim'}

    def owner_edit_claim(self,approval_id,body):
        """Save the owner's corrected wording as a verified fact, approve it, and retire the original proposal."""
        body=(body or '').strip()
        if not body or len(body)>2000:raise ValueError('Write the corrected fact in one to a few sentences.')
        a=self.store.one('SELECT * FROM approvals WHERE id=?',(approval_id,))
        if a['state']!='pending' or a['action']!='promote_claim':raise PolicyError('Only a pending fact proposal can be edited')
        old=self.store.one('SELECT v.*,c.topic,c.label FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=?',(json.loads(a['payload_json'])['version_id'],))
        folder=Path(self.store.path).parent/'owner-attestations';folder.mkdir(exist_ok=True)
        stamp=now();path=folder/('fact-edit-'+digest([approval_id,body,stamp])[:16]+'.txt')
        statement=f'Owner edited and approved on {stamp} via Founder OS Decisions.\nTopic: {old["topic"]} - {old["label"]}\nFact: {body}\nReplaces proposal: {old["body"]}\n'
        path.write_text(statement,encoding='utf-8')
        sv=self.store.import_source(path,'owner_confirmation','CANONICAL',text=statement,extraction='owner_statement')
        vid=self.store.propose_claim(old['topic'],old['label'],body,'verified',sv,'owner edit in Founder OS Decisions',claim_id=old['claim_id'],last_verified_at=stamp)
        for v in self.store.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=?',(old['id'],)):
            self.attach_fact_value(vid,v['fact_key'],json.loads(v['value_json']))
        self.store.decide(approval_id,'rejected',owner_confirmation=True,note='Replaced by the owner\'s edited wording')
        new=self.store.request_approval('promote_claim',{'version_id':vid,'decision_needed':'Owner-edited fact'},actor='founder')
        self.store.decide(new,'approved',owner_confirmation=True,note='Owner edited and approved in Founder OS')
        return {'claim_version_id':vid,'approval_id':new}

    def owner_outcome(self,oid,outcome,note='',evidence_url=None,application_id=None):
        """Record an outcome the owner reports from the website. Their statement is kept as a dated source file."""
        if outcome not in ('Applied','Advanced','Finalist','Won','Rejected','Accepted','Withdrawn'):raise ValueError('Unknown outcome')
        name=self.detail(oid)['data']['canonical_name']
        folder=Path(self.store.path).parent/'owner-attestations';folder.mkdir(exist_ok=True)
        stamp=now();path=folder/('outcome-'+digest([oid,outcome,stamp])[:16]+'.txt')
        statement=f'Owner reported on {stamp} via Founder OS: {name} ({oid}) -> {outcome}.\nNote: {note.strip() or "none"}\nEvidence URL: {evidence_url or "none"}\n'
        path.write_text(statement,encoding='utf-8')
        vid=self.store.import_source(path,'owner_attestation','REFERENCE',text=statement,extraction='owner_statement')
        with self.store.transaction():
            eid=self.outcome(oid,outcome,(note.strip() or 'Owner marked '+outcome.lower()+' in Founder OS.'),source_version_id=vid,evidence_url=evidence_url or None,application_id=application_id or None)
        self.store.log('funding.owner_outcome','owner',{'opportunity_id':oid,'outcome':outcome,'outcome_id':eid})
        return {'outcome_id':eid,'recommendation':self.detail(oid)['recommendation']}

    def application_view(self,application_id):
        app=self.store.one('SELECT * FROM applications WHERE id=?',(application_id,))
        program=self.db.execute('SELECT p.canonical_name name,c.label cycle FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id JOIN funding_cycles c ON c.id=i.cycle_id WHERE i.opportunity_id=?',(app['opportunity_id'],)).fetchone()
        legacy=self.db.execute('SELECT program,cycle FROM opportunities WHERE id=?',(app['opportunity_id'],)).fetchone()
        questions=[]
        for q in self.store.rows('SELECT * FROM questions WHERE application_id=? ORDER BY ordinal',(application_id,)):
            versions=self.store.rows("SELECT a.id,a.body,a.created_at,a.provenance,r.status FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id WHERE a.question_id=? ORDER BY CASE r.status WHEN 'approved' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END,a.created_at DESC",(q['id'],))
            questions.append({'id':q['id'],'ordinal':q['ordinal'],'prompt':q['prompt'],'limit':q['limit_value'],'unit':q['limit_unit'],'answer':versions[0] if versions else None,'versions':len(versions)})
        outcomes=self.store.rows('SELECT outcome,evidence_note note,occurred_at FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC',(app['opportunity_id'],))
        from .application_drafter import access_status,ApplicationDrafter
        ApplicationDrafter(self.store)
        for q in questions:
            m=re.search(r'type=(\w+)',self.db.execute('SELECT locator FROM questions WHERE id=?',(q['id'],)).fetchone()[0] or '')
            q['type']=m.group(1) if m else 'text'
            opts=re.search(r' \[(.*)\]$',q['prompt'])
            q['options']=opts.group(1).split(', ') if opts else [];q['label']=q['prompt'][:opts.start()] if opts else q['prompt']
            note=self.db.execute('SELECT note FROM draft_notes WHERE question_id=?',(q['id'],)).fetchone()
            q['needs_you']=note[0] if note and not q['answer'] else None
            if q['answer']:
                q['answer']['notes']=json.loads(self.db.execute('SELECT unresolved_json FROM answer_versions WHERE id=?',(q['answer']['id'],)).fetchone()[0] or '[]')
        has_intel=self.db.execute('SELECT 1 FROM funding_intelligence WHERE opportunity_id=?',(app['opportunity_id'],)).fetchone()
        d=self.detail(app['opportunity_id']) if has_intel else None
        return {**app,'program':program['name'] if program else (legacy['program'] if legacy else app['title']),'cycle':program['cycle'] if program else (legacy['cycle'] if legacy else ''),
                'questions':questions,'outcomes':outcomes,'official_url':d['data']['official_url'] if d else None,'application_url':d['data']['application_url'] if d else None,
                'deadline':d['data']['dates']['deadline'] if d else None,'recommendation':d['recommendation'] if d else None,
                'access':access_status(self.store,app['opportunity_id'],d['recommendation'] if d else None,outcomes[0]['outcome'] if outcomes else None)}

    def money_board(self,items):
        """Cash first, then credits; one row per program. Applied and decided programs move to the tracker."""
        closed=('EXPIRED','SKIP','REJECTED','ACCEPTED','ALREADY APPLIED')
        active=[d for d in items if d['recommendation'] not in closed and not d.get('superseded_by') and d['data']['status']!='CLOSED' and not (d['decisions'] and d['decisions'][0]['decision']=='SKIP')]
        def unique(rows):
            seen=set();out=[]
            for d in rows:
                if d['program_id'] in seen:continue
                seen.add(d['program_id']);out.append(d)
            return out
        def due(d):
            days=d['analysis']['scoring']['dates']['days_remaining']
            return days if days is not None and days>=0 else 10**6
        cash=sorted([d for d in active if d['analysis']['money']['kind'] in ('CASH','INVESTMENT')],key=lambda d:(due(d),-d['analysis']['money']['rank'],-(d['analysis']['scoring']['estimate'] or 0)))
        from .opportunity_curation import PRIORITIES
        priority=lambda d:PRIORITIES.get((d['analysis'].get('founder_brief') or {}).get('priority') or 'UNKNOWN',0)
        credits=sorted([d for d in active if d['analysis']['money']['kind']=='CREDITS'],key=lambda d:(-priority(d),due(d),-(d['analysis']['scoring']['estimate'] or 0)))
        tracked=self.store.rows('SELECT o.opportunity_id,o.outcome,o.evidence_note note,o.occurred_at,p.canonical_name,i.data_json,(SELECT a.id FROM applications a WHERE a.opportunity_id=o.opportunity_id ORDER BY a.created_at LIMIT 1) application_id FROM funding_outcomes o JOIN funding_intelligence i ON i.opportunity_id=o.opportunity_id JOIN funding_programs p ON p.id=i.program_id ORDER BY o.occurred_at DESC,o.created_at DESC')
        seen=set();applied=[]
        for t in tracked:
            if t['canonical_name'] in seen:continue
            seen.add(t['canonical_name']);dates=json.loads(t.pop('data_json')).get('dates') or {}
            # The next date worth knowing after applying: the event/finale when published.
            t['next_date']=dates.get('event_date');t['waiting']=t['outcome'] in ('Applied','Advanced','Finalist')
            applied.append(t)
        return {'cash':unique(cash),'credits':unique(credits),'tracked':applied}

    def dashboard(self):
        all_items=self.list('All');runs=self.store.rows('SELECT * FROM funding_runs ORDER BY COALESCE(completed_at,started_at) DESC LIMIT 8')
        for r in runs:r['report']=json.loads(r.pop('report_json'));r['usage']=json.loads(r.pop('usage_json'))
        pending=self.store.rows("SELECT id,action,payload_json,requested_at FROM approvals WHERE state='pending' ORDER BY requested_at")
        for p in pending:
            payload=json.loads(p['payload_json']);v=payload.get('version_id')
            if p['action']=='promote_claim' and v:
                p['proposal']=self.store.one('SELECT c.label,c.topic,v.body,v.evidence_status,v.last_verified_at,v.locator,s.original_path FROM claim_versions v JOIN claims c ON c.id=v.claim_id JOIN source_versions sv ON sv.id=v.source_version_id JOIN sources s ON s.id=sv.source_id WHERE v.id=?',(v,))
            p['decision_needed']=payload.get('decision_needed','Review this exact proposal and its source before deciding.')
        memory=self.company_memory()
        for p in pending:p['card']=self.review_card(p,memory['attributes'])
        recent=self.store.rows("SELECT a.id,a.action,a.state,a.decided_at,a.payload_json FROM approvals a WHERE a.state IN ('approved','rejected') AND a.decided_at IS NOT NULL ORDER BY a.decided_at DESC LIMIT 8")
        for r in recent:
            v=json.loads(r.pop('payload_json')).get('version_id')
            row=self.store.one('SELECT c.label,v.body FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=?',(v,)) if v and r['action']=='promote_claim' else None
            r['label']=row['label'] if row else r['action'].replace('_',' ');r['sentence']=(row['body'] if row else '')[:240]
        return {'needs_decision':pending,'recent_decisions':recent,'company_memory':memory,'opportunities':all_items,'money_board':self.money_board(all_items),'high_fit':[d for d in all_items if d['fit_score'] is not None and d['fit_score']>=80 and d['recommendation'] not in ('SKIP','EXPIRED','REJECTED')],'new_opportunities':[d for d in all_items if stamp(d['discovered_at'])>=datetime.now(timezone.utc)-timedelta(days=7)],'upcoming_deadlines':[d for d in all_items if d['analysis']['scoring']['dates']['days_remaining'] is not None and 0<=d['analysis']['scoring']['dates']['days_remaining']<=21 and d['recommendation'] not in ('EXPIRED','SKIP','REJECTED')],'agent_activity':runs,'notifications':self.store.rows('SELECT * FROM funding_notifications WHERE read_at IS NULL ORDER BY created_at DESC'),'requests':self.store.rows("SELECT * FROM hunter_requests WHERE state IN ('QUEUED','RUNNING')"),'settings':self.settings(),'learning':{'decisions':self.store.rows('SELECT decision,count(*) n FROM funding_decisions GROUP BY decision'),'outcomes':self.store.rows('SELECT outcome,count(*) n FROM funding_outcomes GROUP BY outcome'),'search_families':self.store.rows('SELECT family,count(*) candidates FROM funding_candidates GROUP BY family ORDER BY candidates DESC'),'scoring_changes':'No automatic weight changes; propose a versioned review after enough outcomes'}}

    def research_context(self):
        # Context is consumed locally by Codex. Public search queries must not contain these private facts.
        due=self.store.rows('SELECT i.opportunity_id,i.next_check,i.recommendation,p.canonical_name,p.official_url,c.label cycle FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id JOIN funding_cycles c ON c.id=i.cycle_id WHERE i.next_check<=?',(now(),))
        return {'company_memory':self.company_memory(),'known_programs':self.store.rows('SELECT * FROM funding_programs'),'aliases':self.store.rows('SELECT * FROM program_aliases'),'due_for_recheck':due,'history':self.store.rows('SELECT * FROM program_history'),'submissions':self.store.rows('SELECT id,application_id,submitted_at FROM submissions'),'queued_requests':self.store.rows("SELECT * FROM hunter_requests WHERE state='QUEUED'"),'settings':self.settings()}
