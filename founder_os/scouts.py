"""Specialized scouts: one agent per kind of money or person, each with its own search families, focus,
schedule and landing page. The broad sweep stays as a weekly safety net; it is no longer the way money is found.

Hunter scouts (competitions, grants, founder money, accelerators, credits) run through the Funding Hunter's
verified research routine with only their own families. People scouts (investors, partners, press) run a
bounded web search and land on the deal board or the press page. Every result still waits for Bao.
"""
import json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .store import now,js,uid
from .funding_hunter import FundingHunter

ET=ZoneInfo('America/New_York')
SCOUT_PREFIX='Scout: '
INVESTOR_DISCOVERY='Scout: Investors'
DAY=('MO','TU','WE','TH','FR','SA','SU')

# key, name, group, what it hunts, where it lands (page, label), families (Hunter scouts) or None, focus, schedule (days, hour, minute), reason
SCOUTS=[
 {'key':'competitions','name':'Competition Scout','group':'Money for the company','hunts':'Pitch competitions, pitch nights, hackathons and AI builder competitions like VibeCon, with cash prizes and open deadlines, big and local.',
  'lands':('/money#cat-big_pitch','Money map: pitch competitions'),'families':('pitch_competitions','big_pitch_competitions','local_pitch_nights','hackathons','builder_competitions'),
  'focus':'You are the Competition Scout. Only pitch competitions, pitch nights, startup challenges, hackathons and AI builder or vibe-coding competitions (VibeCon and similar contests run by AI app-building platforms) with a cash prize, credits or investment count; A Story is a shipped consumer AI product, so builder contests that judge a working app fit. Open or upcoming deadlines first; Michigan and student-founder events before national ones. Record the prize, the deadline and whether equity is taken.',
  'days':('MO','TH'),'hour':7,'minute':45},
 {'key':'grants','name':'Grant Scout','group':'Money for the company','hunts':'Non-dilutive grants: foundations, state and federal (SBIR/STTR, MEDC), AgeTech and family-tech programs.',
  'lands':('/money#cat-grants','Money map: grants and SBIR'),'families':('grants','federal_state_grants','agetech','vertical'),
  'focus':'You are the Grant Scout. Only non-dilutive grants and grant-like programs count: foundations, state and federal programs, AgeTech and aging programs, family and storytelling technology funds. Record eligibility rules exactly as published; never call investment a grant.',
  'days':('TU','FR'),'hour':7,'minute':45},
 {'key':'founder_money','name':'Founder Money Scout','group':'Money for the founders','hunts':'Fellowships, stipends and grants paid to Bao or Daniel personally, and student or alumni founder awards.',
  'lands':('/money#cat-founder','Money map: money for the founders'),'families':('founder_personal','ecosystem','michigan'),
  'focus':'You are the Founder Money Scout. Only money that reaches a founder personally counts: fellowships, stipends, founder grants, student and alumni awards, residencies with pay. Judge eligibility on the founders (age, student status, Michigan, immigrant founder), not company traction. Record what is paid and to whom.',
  'days':('WE',),'hour':7,'minute':45},
 {'key':'accelerators','name':'Accelerator Scout','group':'Money for the company','hunts':'Pre-seed accelerators and programs that invest cash, plus corporate and AI startup programs with money attached.',
  'lands':('/money#cat-accelerators','Money map: accelerators and investment'),'families':('accelerators_with_cash','ai_programs','midwest','corporate'),
  'focus':'You are the Accelerator Scout. Only programs that put cash in count: accelerators and pre-seed programs with investment or a stipend, corporate and AI startup programs with a cash award. Label equity, SAFE and note terms plainly. Michigan, Ohio and the Midwest first, then remote-friendly national programs.',
  'days':('SA',),'hour':7,'minute':45},
 {'key':'credits','name':'Credits Scout','group':'Money you do not have to spend','hunts':'Credits for the top AI models, voice, transcription, media and cloud: what A Story would otherwise pay for, with the conditions attached.',
  'lands':('/credits','Credits'),'families':None,'reason':'Daily free credits discovery','days':DAY,'hour':7,'minute':30,'external':True,
  'focus':'You are the Credits Scout. Only credit and free-usage programs count: AI model APIs (OpenAI, Anthropic, Google, Mistral, Cohere and peers), voice and transcription, image, video and media generation, cloud and hosting. Prefer programs open to bootstrapped companies with no VC referral. Record the face value, what it covers, expiry, renewal and paid-account or deposit conditions exactly as published.'},
 {'key':'perks','name':'Perks Scout','group':'Money you do not have to spend','hunts':'Free tools, software, ad credits, fee waivers, office space, legal and accounting help and expert hours that a bootstrapped two-founder startup can get free.',
  'lands':('/money#cat-perks','Money map: free tools and perks'),'families':('dev_tool_perks','business_perks','marketing_credits','founder_benefits'),
  'focus':'You are the Perks Scout. Only free or nearly free benefits count: startup programs from software and dev-tool companies, banking and legal perks, ad and marketing credits, developer fee waivers, coworking space, university and alumni founder resources, expert office hours. No VC referral required. Record each as a startup program with what is free, for how long, the conditions (company email, paid account, deposit) and the application route. Never call a free trial a grant.',
  'days':('SU',),'hour':7,'minute':45},
 {'key':'investors','name':'Investor Scout','group':'People to reach','hunts':'Angel groups, pre-seed funds, university and alumni funds and syndicates that back consumer, family or aging products, with how to reach each.',
  'lands':('/growth','Deals: investors'),'families':None,'focus':None,'reason':INVESTOR_DISCOVERY,'days':('WE',),'hour':8,'minute':15},
 {'key':'partners','name':'Partner Scout','group':'People to reach','hunts':'Organizations that reach adult children or buy gifts for many older adults.',
  'lands':('/growth','Deals: partners'),'families':None,'focus':None,'reason':'Partner and deal discovery','days':('TU',),'hour':8,'minute':0,'external':True},
 {'key':'win','name':'Win Scout','group':'How to win','hunts':'For one competition: the rules, the scoring, the judges and what they look for, past winners and why, the other companies this cycle, and the expectations nobody writes down. Feeds Pitch Tailor, the Drafter and the Coach.',
  'lands':('/opportunities','Each program’s page: How we win here'),'families':None,'focus':None,'reason':'Win brief','days':DAY,'hour':8,'minute':30,'external':True},
 {'key':'customer_voice','name':'Customer Voice Scout','group':'How to win','hunts':'What adult children and caregivers say online about a parent’s stories, memory, aging and gifts: the themes with how many threads voiced each, short quotes with links, what they tried, their objections and what they would pay. Feeds Pitch Tailor, the Coach, the Campaign Planner and the field-day script.',
  'lands':('/growth#families-say','Deals & campaigns: What families say online'),'families':None,'focus':None,'reason':'Scout: Customer Voice','days':('TH',),'hour':8,'minute':15},
 {'key':'press','name':'Press Scout','group':'People to reach','hunts':'Holiday gift guides, newsletters, podcasts and local outlets that take pitches.',
  'lands':('/press','Press and gift guides'),'families':None,'focus':None,'reason':'Press and gift-guide discovery','days':('MO','TH'),'hour':8,'minute':0,'external':True},
]
BY_KEY={s['key']:s for s in SCOUTS}
for _s in SCOUTS:_s.setdefault('reason',SCOUT_PREFIX+_s['name'].replace(' Scout',''))
BY_REASON={s['reason']:s for s in SCOUTS}
BROAD='Scheduled broad discovery'


def handles(reason):return reason==INVESTOR_DISCOVERY


def apply(reason,families,store=None):
    """For a scout's run: only its families and its focus. The credits and perks scouts also hear what A Story pays for and is not covered. Anything else passes through unchanged."""
    s=BY_REASON.get(reason)
    if not s or not s.get('focus'):return families,None
    fam={k:v for k,v in families.items() if k in s['families']} if s.get('families') else families
    focus=s['focus']
    if store is not None and s['key'] in ('credits','perks'):
        gaps=Scouts(store).uncovered()
        if gaps:focus+=' A Story currently pays for, with no credit covering it: '+'; '.join(f"{g['item']}"+(f" ({g['provider']})" if g['provider'] else '')+(f" about ${g['monthly_usd']:g} a month" if g['monthly_usd'] else '') for g in gaps)+'. Hunt cover for these first.'
    return fam,focus


def next_run(s,local):
    for offset in range(8):
        day=local+timedelta(days=offset)
        if DAY[day.weekday()] not in s['days']:continue
        at=day.replace(hour=s['hour'],minute=s['minute'],second=0,microsecond=0)
        if at>local:return at
    return None


STACK_SCHEMA='CREATE TABLE IF NOT EXISTS stack_costs(id TEXT PRIMARY KEY,item TEXT NOT NULL,provider TEXT,monthly_usd REAL,covered_by TEXT,note TEXT,updated_at TEXT NOT NULL);'
# What a product like A Story pays for. Amounts stay empty until Bao fills them; nothing here is a fact until he does.
STACK_SEED=[('Voice calls','Cartesia'),('Transcription','AssemblyAI'),('AI model API',''),('Cloud hosting and database',''),('Apple Developer Program','Apple'),('Domain, email and website',''),('Design and video tools','')]


class Scouts:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.db.execute(STACK_SCHEMA)
        if not self.db.execute('SELECT 1 FROM stack_costs LIMIT 1').fetchone():
            for item,provider in STACK_SEED:self.db.execute('INSERT INTO stack_costs VALUES(?,?,?,?,?,?,?)',(uid('cost'),item,provider,None,'',None,now()))

    # ---------- what A Story pays for, and which credit covers it ----------
    def stack(self):
        rows=self.s.rows('SELECT * FROM stack_costs ORDER BY CASE WHEN covered_by IS NULL OR covered_by=\'\' THEN 0 ELSE 1 END,monthly_usd DESC,item')
        uncovered=[r for r in rows if not r['covered_by']]
        return {'items':rows,'monthly_uncovered':round(sum(r['monthly_usd'] or 0 for r in uncovered),2),'monthly_covered':round(sum(r['monthly_usd'] or 0 for r in rows if r['covered_by']),2),
                'credit_providers':[r['provider'] for r in self.s.rows("SELECT DISTINCT provider FROM credit_grants WHERE state NOT IN ('USED_UP','ENDED') ORDER BY provider")] if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='credit_grants'").fetchone() else []}

    def uncovered(self):return [r for r in self.stack()['items'] if not r['covered_by']]

    def save_cost(self,p):
        item=(p.get('item') or '').strip()[:120]
        if not item:raise ValueError('Name what you pay for')
        amount=p.get('monthly_usd')
        if amount in (None,''):amount=None
        else:
            try:amount=float(amount)
            except (TypeError,ValueError):raise ValueError('Monthly cost must be a number')
            if not 0<=amount<=100000:raise ValueError('Monthly cost must be between 0 and 100,000')
        row=(item,(p.get('provider') or '').strip()[:80],amount,(p.get('covered_by') or '').strip()[:80],(p.get('note') or '').strip()[:300],now())
        if p.get('id'):
            self.s.one('SELECT id FROM stack_costs WHERE id=?',(p['id'],))
            self.db.execute('UPDATE stack_costs SET item=?,provider=?,monthly_usd=?,covered_by=?,note=?,updated_at=? WHERE id=?',(*row,p['id']))
        else:self.db.execute('INSERT INTO stack_costs VALUES(?,?,?,?,?,?,?)',(uid('cost'),*row))
        self.s.log('scouts.stack_cost','owner',{'item':item});return self.stack()

    def delete_cost(self,cid):
        self.s.one('SELECT id FROM stack_costs WHERE id=?',(cid,));self.db.execute('DELETE FROM stack_costs WHERE id=?',(cid,));return self.stack()

    def _last(self,reason):
        r=self.db.execute("SELECT request_key,state,created_at,last_error,run_id FROM hunter_requests WHERE reason=? AND state='COMPLETE' ORDER BY created_at DESC LIMIT 1",(reason,)).fetchone()
        if not r:return None
        out={'at':r['created_at'],'found':None}
        run=None
        if r['run_id']:run=self.db.execute('SELECT report_json FROM funding_runs WHERE id=?',(r['run_id'],)).fetchone()
        if not run and 'request_key' in {c[1] for c in self.db.execute('PRAGMA table_info(funding_runs)')}:
            run=self.db.execute('SELECT report_json FROM funding_runs WHERE request_key LIKE ? ORDER BY started_at DESC LIMIT 1',(r['request_key']+'%',)).fetchone()
        if run:
            rep=json.loads(run['report_json']);out['found']=rep.get('new_programs',rep.get('records_created'));out['checked']=rep.get('candidates_discovered')
        return out

    def _setting(self,key):
        r=self.db.execute('SELECT value_json FROM hunter_settings WHERE key=?',(key,)).fetchone()
        return json.loads(r['value_json']) if r else None

    def status(self,instant=None):
        local=(instant or datetime.now(ET)).astimezone(ET);out=[]
        for s in SCOUTS:
            running=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(s['reason'],)).fetchone())
            if s['key']=='win':
                from .win_scout import WinScout
                w=WinScout(self.s).summary();last={'at':w['last_checked'],'found':w['briefs']} if w['last_checked'] else None;running=w['running']
            if s['key']=='customer_voice':
                from .customer_voice import CustomerVoice
                v=CustomerVoice(self.s).summary();last={'at':v['last_checked'],'found':v['themes'],'unit':'themes'} if v['last_checked'] else None;running=v['running']
            if s['key']=='press':last=self._setting('press_last_run')
            elif s['key']=='partners':last=self._setting('partners_last_run')
            elif s['key']=='investors':last=self._setting('investors_last_run')
            elif s['key'] not in ('win','customer_voice'):last=self._last(s['reason'])
            nxt=next_run(s,local)
            out.append({'key':s['key'],'name':s['name'],'group':s['group'],'hunts':s['hunts'],'lands_url':s['lands'][0],'lands_label':s['lands'][1],'families':list(s['families'] or []),
                        'schedule':{'days':list(s['days']),'hour':s['hour'],'minute':s['minute']},'next_run':nxt.isoformat() if nxt else None,'running':running,'last_run':last,'uses_hunter':bool(s.get('families'))})
        sched=(self.h.settings().get('schedule') or {})
        broad=self._last(BROAD)
        return {'scouts':out,'broad_sweep':{'name':'Broad sweep','hunts':'All search families at once, as a safety net behind the specialized scouts.','schedule':sched,'last_run':broad,
                'running':bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason IN (?,?) AND state IN ('QUEUED','RUNNING')",(BROAD,'Manual broad discovery')).fetchone())},'today':local.date().isoformat()}

    def request_run(self,key,manual=True):
        s=BY_KEY.get(key)
        if not s:raise ValueError('Unknown scout')
        stamp=datetime.now(ET).strftime('%Y-%m-%dT%H%M') if manual else datetime.now(ET).date().isoformat()
        return self.h.request_run(s['reason'],key='scout-'+key+'-'+stamp)

    def poll(self,instant=None):
        """Queue each scout once on its scheduled day, after its hour. The credits, partner and press scouts keep their own schedulers."""
        local=(instant or datetime.now(ET)).astimezone(ET);queued=[]
        for s in SCOUTS:
            if s.get('external'):continue
            if DAY[local.weekday()] in s['days'] and (local.hour,local.minute)>=(s['hour'],s['minute']):
                r=self.h.request_run(s['reason'],key='scout-'+s['key']+'-'+local.date().isoformat());queued.append(s['key'])
        return {'queued':queued}

    def record_investor_run(self,report):
        self.db.execute('INSERT INTO hunter_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',('investors_last_run',js(report)))
        self.s.log('scouts.investor_discovery','research_worker',report)

    def investor_context(self):
        from .growth_desk import GrowthDesk
        desk=GrowthDesk(self.s)
        return {**{k:v for k,v in desk.g.base_context().items() if k!='writing_guide'},'known':[r['name'] for r in self.s.rows("SELECT name FROM deals WHERE kind='investor'")],
                'task':'Find investors who could lead or join a first pre-seed round for A Story, a consumer subscription (an AI biographer that phone-interviews a parent; adult children buy it as a gift): angel groups, pre-seed and seed funds, university and alumni venture funds, student-run funds, syndicates and family offices with a published way in. '
                'Michigan and Ohio first (the founders are University of Michigan alumni, the company is in Michigan), then the Midwest, then national funds that state consumer, family, aging, longevity or creator theses and write checks of $25,000 to $500,000. For each: the thesis fit in one sentence, typical check size and stage as published, and the published route in (application form, pitch submission page, office hours, or a named program). Never guess a personal email.'}


def run(h,request,codex_json):
    """Investor Scout: a bounded public-web search; results become FOUND investor deals that Bao decides to approach."""
    from .growth_desk import GrowthDesk
    sc=Scouts(h.store);ctx=sc.investor_context()
    target={'type':'object','additionalProperties':False,'properties':{**{k:{'type':'string'} for k in ('name','url','contact_route','region','thesis_fit','check_size','stage','source_url')}},
            'required':['name','url','contact_route','region','thesis_fit','check_size','stage','source_url']}
    schema={'type':'object','additionalProperties':False,'properties':{'queries':{'type':'array','items':{'type':'string'}},'targets':{'type':'array','items':target},
            'errors':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'message':{'type':'string'}},'required':['message']}}},'required':['queries','targets','errors']}
    prompt=('You are A Story Founder OS Investor Scout, a READ-ONLY research worker. Use ONLY public web search and public page reads. Do not use shell, file, email, form, account or posting tools. '
            +ctx['task']+' Use at most 8 search queries and read at most 14 pages. Return up to 12 investors not in CONTEXT.known. '
            'check_size and stage come from the investor’s own pages or a reputable directory; write "not published" when unknown. source_url is the page that shows the thesis or the route in. Do not invent funds, people, portfolio companies or terms.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
    data,events=codex_json(h,request,prompt,schema,'investors',search=True,timeout=1200)
    if not events:raise RuntimeError('SOURCE_UNAVAILABLE: no web-tool activity was recorded; investors cannot be verified')
    targets=[{'name':t.get('name'),'kind':'investor','url':t.get('url'),'contact_route':t.get('contact_route'),'region':t.get('region'),'source_url':t.get('source_url'),
              'why':(t.get('thesis_fit') or '').strip(),'angle':('Check size: '+(t.get('check_size') or 'not published')+'. Stage: '+(t.get('stage') or 'not published')+'.')} for t in data.get('targets',[])]
    found=GrowthDesk(h.store).save_targets(targets)
    sc.record_investor_run({'at':now(),'found':found,'returned':len(targets),'queries':data.get('queries',[])[:10],'errors':[e.get('message','') for e in data.get('errors',[])][:6]})
    return {'investors_found':found}
