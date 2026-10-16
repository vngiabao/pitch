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
 {'key':'competitions','name':'Competition Scout','group':'Money for the company','hunts':'Pitch competitions, pitch nights and hackathons with cash prizes and open deadlines, big and local.',
  'lands':('/money#cat-big_pitch','Money map: pitch competitions'),'families':('pitch_competitions','big_pitch_competitions','local_pitch_nights','hackathons'),
  'focus':'You are the Competition Scout. Only pitch competitions, pitch nights, startup challenges and hackathons with a cash prize count. Open or upcoming deadlines first; Michigan and student-founder events before national ones. Record the prize, the deadline and whether equity is taken.',
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
 {'key':'credits','name':'Credits Scout','group':'Money for the company','hunts':'Free voice, AI and cloud credits that cut what A Story pays, with the conditions attached.',
  'lands':('/credits','Credits'),'families':None,'focus':None,'reason':'Daily free credits discovery','days':DAY,'hour':7,'minute':30,'external':True},
 {'key':'investors','name':'Investor Scout','group':'People to reach','hunts':'Angel groups, pre-seed funds, university and alumni funds and syndicates that back consumer, family or aging products, with how to reach each.',
  'lands':('/growth','Deals: investors'),'families':None,'focus':None,'reason':INVESTOR_DISCOVERY,'days':('WE',),'hour':8,'minute':15},
 {'key':'partners','name':'Partner Scout','group':'People to reach','hunts':'Organizations that reach adult children or buy gifts for many older adults.',
  'lands':('/growth','Deals: partners'),'families':None,'focus':None,'reason':'Partner and deal discovery','days':('TU',),'hour':8,'minute':0,'external':True},
 {'key':'press','name':'Press Scout','group':'People to reach','hunts':'Holiday gift guides, newsletters, podcasts and local outlets that take pitches.',
  'lands':('/press','Press and gift guides'),'families':None,'focus':None,'reason':'Press and gift-guide discovery','days':('MO','TH'),'hour':8,'minute':0,'external':True},
]
BY_KEY={s['key']:s for s in SCOUTS}
for _s in SCOUTS:_s.setdefault('reason',SCOUT_PREFIX+_s['name'].replace(' Scout',''))
BY_REASON={s['reason']:s for s in SCOUTS}
BROAD='Scheduled broad discovery'


def handles(reason):return reason==INVESTOR_DISCOVERY


def apply(reason,families):
    """For a Hunter scout's run: only its families and its focus. Anything else passes through unchanged."""
    s=BY_REASON.get(reason)
    if not s or not s.get('families'):return families,None
    return {k:v for k,v in families.items() if k in s['families']},s['focus']


def next_run(s,local):
    for offset in range(8):
        day=local+timedelta(days=offset)
        if DAY[day.weekday()] not in s['days']:continue
        at=day.replace(hour=s['hour'],minute=s['minute'],second=0,microsecond=0)
        if at>local:return at
    return None


class Scouts:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store)

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
            if s['key']=='press':last=self._setting('press_last_run')
            elif s['key']=='partners':last=self._setting('partners_last_run')
            elif s['key']=='investors':last=self._setting('investors_last_run')
            else:last=self._last(s['reason'])
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
