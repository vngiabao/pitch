"""Turn an official application form into questions with prepared answers on the website.

1. Read the form (founder_os.form_reader); record whether the agent could reach it.
2. Fill what approved company facts and approved answers already cover.
3. Queue the remaining open questions for the AI drafter (tools/research_worker.py).
Nothing here submits, signs in or accepts terms. Drafts stay drafts until the owner uses them.
"""
import json,re
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .store import now,js,digest,uid
from .funding_hunter import FundingHunter,stamp
from .founder_profile import FounderProfile,FACT_FALLBACK

SCHEMA='''CREATE TABLE IF NOT EXISTS form_inspections(
 opportunity_id TEXT PRIMARY KEY,url TEXT,state TEXT NOT NULL,reason TEXT NOT NULL,
 question_count INTEGER NOT NULL DEFAULT 0,application_id TEXT,checked_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS draft_notes(question_id TEXT PRIMARY KEY,note TEXT NOT NULL,created_at TEXT NOT NULL);'''
TERMINAL=('SKIP','EXPIRED','REJECTED','ACCEPTED','ALREADY APPLIED')
DRAFT_PREFIX='Draft application: '
OPEN_TYPES=('textarea','text','email','tel','url','number')
CHOICE_TYPES=('select','checkbox','radio')


def norm(text):return re.sub(r'[^a-z0-9 ]+',' ',(text or '').lower()).strip()


FUNDING_STAGE_WORDS={'bootstrapped':['Bootstrapped','No Funding Raised','Pre-Seed']}


def choose_option(value,options):
    # Pick the form's own option text for a known value, or None when nothing matches safely.
    if isinstance(value,bool):value='Yes' if value else 'No'
    if isinstance(value,(int,float)):
        for o in options:
            text=o.replace(',','')
            scale=1e6 if re.search(r'\d\s*M\b',text) else 1e3 if re.search(r'\d\s*K\b',text,re.I) else 1
            nums=[float(n)*scale for n in re.findall(r'\d+(?:\.\d+)?',text)]
            if text.strip().startswith('<') and nums and value<nums[0]:return o
            if len(nums)>=2 and nums[0]<=value<=nums[1]:return o
            if len(nums)==1 and ('+' in text or 'more' in text.lower()) and value>=nums[0]:return o
            if len(nums)==1 and value==nums[0]:return o
        return None
    v=str(value).strip().lower()
    for o in options:
        if o.lower()==v:return o
    if v=='bootstrapped':
        for word in ('no funding','bootstrapped'):
            for o in options:
                if word in o.lower():return o
    for o in options:
        if v and (v in o.lower() or o.lower() in v):return o
    return None


class ApplicationDrafter:
    def __init__(self,store,reader=None):
        self.store=store;self.db=store.db;self.h=FundingHunter(store);self.reader=reader
        self.db.executescript(SCHEMA)

    # ---------- access ----------
    def inspection(self,oid):
        return self.db.execute('SELECT * FROM form_inspections WHERE opportunity_id=?',(oid,)).fetchone()

    def record(self,oid,url,state,reason,count=0,aid=None):
        self.db.execute('INSERT INTO form_inspections VALUES(?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET url=excluded.url,state=excluded.state,reason=excluded.reason,question_count=excluded.question_count,application_id=COALESCE(excluded.application_id,form_inspections.application_id),checked_at=excluded.checked_at',
                        (oid,url,state,reason,count,aid,now()))

    def read_form(self,oid):
        """Read the official form once and prepare the application. Returns a short summary."""
        d=self.h.detail(oid);url=d['data'].get('application_url')
        if not url:
            self.record(oid,None,'NO_LINK','No official application link has been found yet.')
            return {'state':'NO_LINK'}
        if self.reader is None:raise RuntimeError('No form reader configured')
        try:result=self.reader.read(url)
        except Exception as e:result={'state':'UNREADABLE','reason':'The application page could not be read: '+str(e)[:200],'questions':[]}
        if result['state']!='QUESTIONS_READ':
            self.record(oid,url,result['state'],result['reason'])
            return {'state':result['state'],'reason':result['reason']}
        aid=self.h.start_application(oid)
        source=self._snapshot(oid,url,result['questions'])
        known={norm(q['prompt']):q['id'] for q in self.store.rows('SELECT id,prompt FROM questions WHERE application_id=?',(aid,))}
        next_ordinal=(self.db.execute('SELECT COALESCE(MAX(ordinal),0) FROM questions WHERE application_id=?',(aid,)).fetchone()[0])+1
        for q in result['questions']:
            if norm(q['label']) in known:continue
            prompt=q['label']+(' ['+', '.join(q['options'][:40])+']' if q['options'] else '')
            limit=q['limit'];unit=q['unit']
            qid=self.store.add_question(aid,next_ordinal,prompt,source,url+' | type='+q['type']+(' | required' if q['required'] else ''),limit,unit,checked=True)
            known[norm(q['label'])]=qid;next_ordinal+=1
        self.record(oid,url,'QUESTIONS_READ',result['reason'],len(result['questions']),aid)
        filled=self.fill_known(aid)
        queued=self.queue_draft(aid) if self.open_questions(aid) else None
        return {'state':'QUESTIONS_READ','application_id':aid,'questions':len(result['questions']),'filled':filled,'draft_queued':bool(queued)}

    def _snapshot(self,oid,url,questions):
        folder=Path(self.store.path).parent/'form-snapshots';folder.mkdir(exist_ok=True)
        body='Official application form read on '+now()+'\n'+url+'\n\n'+'\n'.join(f"{i+1}. {q['label']} [{q['type']}{', required' if q['required'] else ''}{', limit '+str(q['limit'])+' '+q['unit'] if q['limit'] else ''}]"+(' options: '+'; '.join(q['options'][:40]) if q['options'] else '') for i,q in enumerate(questions))
        path=folder/('form-'+digest([oid,body])[:16]+'.txt');path.write_text(body,encoding='utf-8')
        return self.store.import_source(path,'application_form','REFERENCE',text=body,extraction='form_reader')

    # ---------- answers ----------
    def questions(self,aid):
        rows=self.store.rows('SELECT * FROM questions WHERE application_id=? ORDER BY ordinal',(aid,))
        for q in rows:
            q['answered']=bool(self.db.execute("SELECT 1 FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id WHERE a.question_id=? AND r.status!='rejected'",(q['id'],)).fetchone())
            m=re.search(r'type=(\w+)',q['locator'] or '');q['type']=m.group(1) if m else 'text'
        return rows

    def open_questions(self,aid):
        return [q for q in self.questions(aid) if not q['answered'] and q['type'] in OPEN_TYPES+CHOICE_TYPES]

    def fill_known(self,aid):
        """Answer what approved facts and approved answers already settle."""
        facts=self.h.company_memory()['attributes'];value=lambda k:facts.get(k,{}).get('value');filled=0
        rules=[
            (r'\b(company|startup|organi[sz]ation) name\b|\bname of your (company|startup)\b','company_name'),
            (r'\b(company|startup)?\s*website\b','website_url'),
            (r'\b(work|business|company) email\b','company_email'),
            (r'\bincorporated\b','incorporated_yes'),
            (r'\b(people|customers|users|anyone) using (your|the) product\b','product_in_use'),
            (r'\b(latest|last) (series|round|stage) of (fundraising|funding)\b|\bfundraising stage\b','funding_stage_label'),
            (r'\b(number of employees|how many employees|company size)\b','team_size'),
            (r'\btotal funding raised\b','funding_raised'),
            (r'\b(team member 1|primary contact|founder|your)\b.*\bname first$|^first name','founder_first_name'),
            (r'\b(team member 1|primary contact|founder|your)\b.*\bname last$|^last name','founder_last_name'),
            (r'\bteam member 2\b.*\bname first$','cofounder_first'),
            (r'\bteam member 2\b.*\bname last$','cofounder_last'),
            (r'\b(primary contact|team member 1)\b.*\bjob title\b|\byour (role|title)\b','founder_title'),
            (r'\bteam member 2\b.*\bjob title\b','cofounder_title'),
            (r'\b(primary contact|team member 1|your|contact)\b.*\bemail\b|^email','owner_email'),
            (r'\bteam member 2\b.*\bemail\b','cofounder_email'),
            (r'\bcountry\b.*\b(incorporat|registered|based|located)','country'),
            (r'\b(how many|number of) (employees|team members|people)\b|\bteam size\b','team_size'),
            (r'\bhighest educational level\b.*team member 1|team member 1.*highest educational level','founder_education'),
            (r'\blast stage of funding\b|\bfunding stage\b','funding_stage_label'),
            (r'\bfunding (have you )?raised\b|\braised to date\b','funding_raised'),
            (r'\bcustomer focus\b|\bb2b or b2c\b','customer_focus'),
            (r'\btype of product\b','product_type'),
        ]
        cofounder=(value('cofounder_name') or '').split()
        # "Co-founder, COO & CTO" -> "COO & CTO": a form's job-title box wants the title, not the founder label.
        title=lambda role:re.sub(r'^\s*co-?founder\s*[,&]?\s*','',role,flags=re.I).strip() or None if role else None
        derived={
            'company_name':value('company_name'),'website_url':value('website_url'),
            'founder_first_name':value('founder_first_name'),'founder_last_name':value('founder_last_name'),
            'cofounder_first':cofounder[0] if cofounder else None,'cofounder_last':' '.join(cofounder[1:]) if len(cofounder)>1 else None,
            'founder_title':title(value('founder_role')),'cofounder_title':title(value('cofounder_role')),
            'owner_email':'bao@astoryapp.com','cofounder_email':'daniel@astoryapp.com','company_email':'bao@astoryapp.com',
            'incorporated_yes':'Yes' if value('incorporated') else None,'product_in_use':'Yes' if value('product_stage') in ('private_beta','launched','public') else None,
            'country':'United States' if value('us_company') else None,'team_size':value('team_size'),
            'founder_education':'Masters Degree','funding_stage_label':'Bootstrapped' if value('funding_stage')=='bootstrapped' else None,
            'funding_raised':0 if value('institutional_equity_funding') is False else None,
            'customer_focus':'Consumer Product / Services (B2C)' if value('customer_type')=='B2C' else None,'product_type':'Software' if value('uses_ai') else None,
        }
        fact_versions=list(dict.fromkeys(f['claim_version_id'] for f in facts.values()))
        bios=self.store.approved_answers('founder bio')
        profile=FounderProfile(self.store);vault=profile.values()
        for q in self.open_questions(aid):
            label=norm(q['prompt'].split(' [')[0]);answer=None;why=''
            options=self._options(q['prompt'])
            for pattern,key in rules:
                if re.search(pattern,label) and derived.get(key) not in (None,''):
                    answer=choose_option(derived[key],options) if options else str(derived[key])
                    if answer:why='From your approved company facts';break
            if answer is None:
                # Form Filler: the Founder Profile Vault answers what only Bao knows (EIN, addresses, links, dates).
                key=profile.match(q['prompt'].split(' [')[0]);raw=vault.get(key) if key else None
                if key and not raw and FACT_FALLBACK.get(key) in facts:raw=value(FACT_FALLBACK[key])
                if raw not in (None,''):
                    typed=int(raw) if isinstance(raw,str) and raw.isdigit() else raw
                    answer=choose_option(typed,options) if options else str(raw)
                    if answer:why='founder_profile'
            if answer is None and re.search(r'\bbio\b',label):
                who='bao' if re.search(r'team member 1|primary contact|your bio',label) else 'daniel' if 'team member 2' in label else None
                match=[b for b in bios if who and who in b['prompt'].lower()]
                if match:answer=match[0]['body'];why='Your approved founder bio'
            if answer is None:
                reuse=[a for a in self.store.approved_answers(q['prompt']) if norm(a['prompt'].split(' (max')[0])==label]
                if reuse:answer=reuse[0]['body'];why='Your approved answer to the same question'
            if answer is None:continue
            src=self.db.execute('SELECT source_version_id FROM questions WHERE id=?',(q['id'],)).fetchone()[0]
            self.store.add_answer(q['id'],answer,[src],fact_versions=fact_versions if why.startswith('From your approved') else (),unresolved=(),provenance='founder_profile' if why=='founder_profile' else 'auto_filled')
            if why=='founder_profile':self.db.execute('DELETE FROM draft_notes WHERE question_id=?',(q['id'],))
            filled+=1
        return filled

    def refill_all(self):
        """Run the Form Filler again over every application whose form was read, e.g. after Bao edits his profile. Returns {application_id: newly filled}."""
        out={}
        for row in self.db.execute("SELECT application_id FROM form_inspections WHERE state='QUESTIONS_READ' AND application_id IS NOT NULL").fetchall():
            out[row[0]]=self.fill_known(row[0])
        if any(out.values()):self.store.log('application.profile_filled','form_filler',{'applications':{k:v for k,v in out.items() if v}})
        return out

    @staticmethod
    def _options(prompt):
        m=re.search(r' \[(.*)\]$',prompt or '')
        return [o.strip() for o in m.group(1).split(', ')] if m else []

    def queue_draft(self,aid):
        key='draft-'+aid+'-'+datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        rid='request-'+digest(key)[:24]
        self.db.execute("INSERT OR IGNORE INTO hunter_requests(id,request_key,reason,state,created_at,run_id) VALUES(?,?,?,'QUEUED',?,NULL)",(rid,key,DRAFT_PREFIX+aid,now()))
        return rid

    def win_brief(self,oid):
        from .win_scout import WinScout
        return WinScout(self.store).for_agents(oid)

    def draft_context(self,aid):
        """Everything the AI drafter may use: approved facts, approved answers, owner sources and writing rules."""
        app=self.store.one('SELECT a.*,p.canonical_name FROM applications a LEFT JOIN funding_intelligence i ON i.opportunity_id=a.opportunity_id LEFT JOIN funding_programs p ON p.id=i.program_id WHERE a.id=?',(aid,))
        self.fill_known(aid)  # the Form Filler goes first, so the AI is never asked what the vault already knows
        mem=self.h.company_memory()
        owner_sources=[]
        for kind in ('owner_confirmation','application_history','official_pricing_capture'):
            row=self.db.execute('SELECT v.body FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE s.kind=? AND v.body IS NOT NULL ORDER BY v.captured_at DESC LIMIT 1',(kind,)).fetchone()
            if row:owner_sources.append({'kind':kind,'text':row['body'][:12000]})
        approved=[{'question':a['prompt'][:300],'answer':a['body']} for a in self.store.approved_answers('')[:20]]
        recent_owner=[{'question':r['prompt'][:300],'answer':r['body']} for r in self.store.rows("SELECT q.prompt,a.body FROM answer_versions a JOIN questions q ON q.id=a.question_id WHERE a.provenance='owner_written' ORDER BY a.created_at DESC LIMIT 12")]
        guide=Path(__file__).resolve().parents[1]/'PITCH_WRITING.md'
        return {'program':app['canonical_name'] or app['title'],'questions':[{'question_id':q['id'],'question':q['prompt'],'limit':q['limit_value'],'unit':q['limit_unit'],'type':q['type']} for q in self.open_questions(aid)],
                'company_facts':{k:v['value'] for k,v in mem['attributes'].items()},'approved_statements':[{'topic':c['topic'],'text':c['body']} for c in mem['canonical_claims'] if not c['body'].startswith('{')],
                'owner_sources':owner_sources,'approved_answers':approved,'owner_written_answers':recent_owner,'founder_profile':FounderProfile(self.store).public_values(),'win_brief':self.win_brief(app['opportunity_id']),
                'writing_guide':guide.read_text(encoding='utf-8')[:9000] if guide.exists() else '',
                'rules':['Use only the facts, statements, sources and answers given here. Never invent numbers, customers, partners, awards or traction.',
                         'Two founders: Daniel Hoang Nguyen (CEO) and Bao Vo (COO and CTO). Do not mention Nhi Tran except for the Michigan Business Challenge.',
                         'Runway: no fixed runway; if a number is required, use 8 months. Bootstrapped from founder money.',
                         'Prices come from the astoryapp.com pricing capture. Stats: 79% want to know more, 37% know their mother\'s life before kids, 74% regret not learning more.',
                         'Stay within each word or character limit. For a choice question, answer with the exact option text.',
                         'If the facts cannot answer a question (phone numbers, private details), return an empty answer and say what is missing in note. founder_profile holds the links and public details Bao wrote himself; private ones (EIN, addresses, dates of birth) are filled by the Form Filler, never by you.',
                         'Write in plain founder language, one connected paragraph for short answers, normal hyphens, no em dashes.']}

    def save_drafts(self,aid,drafts):
        valid={q['id']:q for q in self.open_questions(aid)};saved=0
        src=self.db.execute('SELECT source_version_id FROM questions WHERE application_id=? ORDER BY ordinal LIMIT 1',(aid,)).fetchone()
        for d in drafts:
            q=valid.get(d.get('question_id'));text=(d.get('answer') or '').strip()
            if q and not text and d.get('note'):
                # Questions only the owner can answer keep the reason, shown as "Needs you" on the site.
                self.db.execute('INSERT INTO draft_notes VALUES(?,?,?) ON CONFLICT(question_id) DO UPDATE SET note=excluded.note,created_at=excluded.created_at',(q['id'],d['note'][:300],now()))
            if not q or not text:continue
            unresolved=[]
            if q['limit_value']:
                n=len(text.split()) if (q['limit_unit'] or 'words')=='words' else len(text)
                if n>q['limit_value']:unresolved.append(f"Over the {q['limit_value']}-{q['limit_unit']} limit ({n})")
            if d.get('note'):unresolved.append(d['note'][:300])
            self.store.add_answer(q['id'],text,[src[0]],unresolved=unresolved,provenance='agent_draft');saved+=1
        self.store.log('application.agent_drafted','application_drafter',{'application_id':aid,'answers':saved})
        return saved

    # ---------- scheduling ----------
    def due(self,limit=2,max_age_days=7):
        """Open programs whose form was never read or was read more than a week ago."""
        out=[]
        for d in self.h.list('All'):
            if d['recommendation'] in TERMINAL or d.get('superseded_by') or d['data']['status'] not in ('OPEN','UPCOMING'):continue
            row=self.inspection(d['opportunity_id'])
            if row and stamp(row['checked_at'])>datetime.now(timezone.utc)-timedelta(days=max_age_days):continue
            out.append(d['opportunity_id'])
            if len(out)>=limit:break
        return out

    def poll(self,limit=2):
        return [{'opportunity_id':oid,**self.read_form(oid)} for oid in self.due(limit)]


def application_list(store):
    """Every application record with its access status, for the Applications page."""
    drafter=ApplicationDrafter(store);h=drafter.h;out=[]
    for a in store.rows('SELECT * FROM applications ORDER BY created_at DESC'):
        intel=store.db.execute('SELECT p.canonical_name,i.recommendation FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id WHERE i.opportunity_id=?',(a['opportunity_id'],)).fetchone()
        if not intel:continue
        try:d=h.detail(a['opportunity_id']);rec=d['recommendation'];url=d['data'].get('application_url') or d['data'].get('official_url')
        except Exception:rec=intel['recommendation'];url=None
        outcome=store.db.execute('SELECT outcome FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC LIMIT 1',(a['opportunity_id'],)).fetchone()
        qs=store.db.execute('SELECT COUNT(*) FROM questions WHERE application_id=?',(a['id'],)).fetchone()[0]
        answered=store.db.execute("SELECT COUNT(DISTINCT q.id) FROM questions q JOIN answer_versions v ON v.question_id=q.id JOIN answer_reviews r ON r.version_id=v.id WHERE q.application_id=? AND r.status!='rejected'",(a['id'],)).fetchone()[0]
        out.append({'application_id':a['id'],'opportunity_id':a['opportunity_id'],'program':intel['canonical_name'],'questions':qs,'answered':answered,
                    'outcome':outcome[0] if outcome else None,'url':url,'access':access_status(store,a['opportunity_id'],rec,outcome[0] if outcome else None)})
    order={'READY':0,'DRAFTING':1,'BLOCKED':2,'NOT_CHECKED':3,'FINISHED':4}
    return sorted(out,key=lambda x:(order.get(x['access']['level'],9),x['program']))


def access_status(store,oid,recommendation=None,outcome=None):
    """One plain line saying whether the agent can actually reach this application."""
    row=store.db.execute('SELECT * FROM form_inspections WHERE opportunity_id=?',(oid,)).fetchone() if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='form_inspections'").fetchone() else None
    if outcome or recommendation in ('ACCEPTED','REJECTED','ALREADY APPLIED'):
        return {'level':'FINISHED','label':'Finished','detail':(outcome or recommendation.title())+'. Nothing left to prepare.'}
    if recommendation in ('SKIP','EXPIRED'):return {'level':'FINISHED','label':'Not pursuing','detail':recommendation.title()+'.'}
    if not row:return {'level':'NOT_CHECKED','label':'Not checked yet','detail':'The agent has read the program page but has not opened the application form yet.'}
    if row['state']=='NO_LINK':return {'level':'BLOCKED','label':'Blocked: no form link','detail':row['reason']}
    if row['state']=='LOGIN_REQUIRED':return {'level':'BLOCKED','label':'Blocked: needs your login','detail':row['reason']+' Open the official form, sign in and apply; the agent can still draft answers if you paste the questions.'}
    if row['state'] in ('NO_FORM_FOUND','UNREADABLE'):return {'level':'BLOCKED','label':'Blocked: form not readable','detail':row['reason']}
    aid=row['application_id'];total=row['question_count']
    answered=store.db.execute("SELECT COUNT(DISTINCT q.id) FROM questions q JOIN answer_versions a ON a.question_id=q.id JOIN answer_reviews r ON r.version_id=a.id WHERE q.application_id=? AND r.status!='rejected'",(aid,)).fetchone()[0] if aid else 0
    drafting=store.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(DRAFT_PREFIX+(aid or ''),)).fetchone()
    if drafting:return {'level':'DRAFTING','label':'Agent is drafting','detail':f'Questions read ({total}). {answered} answered so far; the agent is drafting the rest.','application_id':aid}
    return {'level':'READY','label':'Questions ready to copy','detail':f'{answered} of {total} questions have prepared answers. Copy them into the official form and submit it yourself.','application_id':aid}
