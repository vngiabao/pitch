"""Growth desk: outreach that lands deals, the holiday gift-pass campaign, and channel math.

Partner Scout finds organizations and investors worth a note. Deal Drafter writes the note from approved facts.
Campaign Planner turns the pricing and the calendar into a dated plan. Channel Math turns what Bao records
(visits, signups, purchases, spend) into the numbers judges ask for. Bao sends every message, books every
meeting and closes every deal himself. Nothing here emails, posts or spends.
"""
import json
from datetime import date,datetime,timedelta
from .store import now,js,digest,uid
from .funding_hunter import FundingHunter
from .growth_agents import Growth,today,day,text,web,ET

DEAL_PREFIX='Draft deal note: '
PARTNER_DISCOVERY='Partner and deal discovery'
CAMPAIGN_PREFIX='Campaign plan: '
DEAL_KINDS=('partner','buyer','press','investor','program','other')
KIND_WORDS={'partner':'Partner','buyer':'Buys for many families','press':'Press','investor':'Investor','program':'Program','other':'Other'}
STAGES=('FOUND','DRAFTED','SENT','REPLIED','MEETING','PROPOSAL','WON','LOST','PARKED')
OPEN_STAGES=STAGES[:6]
STAGE_WORDS={'FOUND':'Found','DRAFTED':'Note ready','SENT':'Sent, waiting','REPLIED':'They replied','MEETING':'Meeting set','PROPOSAL':'Proposal out','WON':'Won','LOST':'Lost','PARKED':'Parked'}
# How many days until the next step is due after each stage change, when Bao sets no date.
FOLLOW_DAYS={'SENT':7,'REPLIED':3,'MEETING':1,'PROPOSAL':7}
CHANNELS=('gift_passes','referrals','partners','press','email','paid_social','search','events','other')
CHANNEL_WORDS={'gift_passes':'Gift passes','referrals':'Referrals','partners':'Partners','press':'Press and gift guides','email':'Email and mailing list','paid_social':'Paid social','search':'Search','events':'Events and pitch nights','other':'Other'}
DECK_FORMULA={'visits':1000,'rate':0.03,'families':30}
CAMPAIGNS=[('holiday-gift-passes','Holiday gift passes 2026','Adult children buy A Story as a gift for a parent or grandparent before Thanksgiving and the December holidays. The $1 reservation closes November 2.')]

SCHEMA='''
CREATE TABLE IF NOT EXISTS deals(id TEXT PRIMARY KEY,key TEXT NOT NULL UNIQUE,name TEXT NOT NULL,kind TEXT NOT NULL,region TEXT,url TEXT,contact_route TEXT,why TEXT,angle TEXT,
 stage TEXT NOT NULL DEFAULT 'FOUND',value_usd INTEGER,value_note TEXT,next_step TEXT,next_on TEXT,contact_id TEXT,source TEXT NOT NULL DEFAULT 'owner',source_url TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS deal_events(id TEXT PRIMARY KEY,deal_id TEXT NOT NULL REFERENCES deals(id),occurred_on TEXT NOT NULL,kind TEXT NOT NULL,summary TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,key TEXT NOT NULL UNIQUE,title TEXT NOT NULL,brief TEXT NOT NULL,owner_note TEXT,plan_json TEXT,issues_json TEXT,state TEXT NOT NULL DEFAULT 'NEW',planned_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS channel_entries(id TEXT PRIMARY KEY,channel TEXT NOT NULL,week_start TEXT NOT NULL,visits INTEGER NOT NULL DEFAULT 0,signups INTEGER NOT NULL DEFAULT 0,purchases INTEGER NOT NULL DEFAULT 0,
 spend_usd REAL NOT NULL DEFAULT 0,revenue_usd REAL NOT NULL DEFAULT 0,source TEXT NOT NULL DEFAULT 'manual',note TEXT,created_at TEXT NOT NULL);
'''


def num(value,field,kind=int,low=0,high=10_000_000):
    if value in (None,''):return kind(0)
    try:v=kind(value)
    except (TypeError,ValueError):raise ValueError(field+' must be a number')
    if not low<=v<=high:raise ValueError(field+' must be between '+str(low)+' and '+str(high))
    return v


def pct(a,b):return round(100*a/b,1) if b else None


def per(a,b):return round(a/b,2) if b else None


class GrowthDesk:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.g=Growth(store);self.h=FundingHunter(store)
        for statement in SCHEMA.split(';'):
            if statement.strip():self.db.execute(statement)
        for key,title,brief in CAMPAIGNS:
            self.db.execute('INSERT OR IGNORE INTO campaigns(id,key,title,brief,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(uid('campaign'),key,title,brief,'NEW',now(),now()))

    # ---------- deals ----------
    def add_deal(self,p):
        name=text(p.get('name'),160,'Name')
        if not name:raise ValueError('An organization or person is required')
        kind=p.get('kind') or 'partner'
        if kind not in DEAL_KINDS:raise ValueError('Unknown deal type')
        key=digest([name.lower(),kind])[:24]
        if self.db.execute('SELECT 1 FROM deals WHERE key=?',(key,)).fetchone():raise ValueError(name+' is already on the board')
        did=uid('deal');value=num(p.get('value_usd'),'Value',int) or None
        self.db.execute('INSERT INTO deals(id,key,name,kind,region,url,contact_route,why,angle,stage,value_usd,value_note,next_step,next_on,contact_id,source,source_url,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (did,key,name,kind,text(p.get('region'),80,'Region'),web(p.get('url')),text(p.get('contact_route'),300,'How to reach them'),text(p.get('why'),600,'Why them'),text(p.get('angle'),600,'Angle'),
             'FOUND',value,text(p.get('value_note'),200,'What it is worth'),text(p.get('next_step'),300,'Next step'),day(p.get('next_on'),'Next step date'),p.get('contact_id') or None,'owner',None,now(),now()))
        if p.get('summary'):self.log_event(did,{'summary':p['summary'],'kind':'note'})
        self.s.log('growth.deal_added','owner',{'deal_id':did,'kind':kind})
        return self.deal(did)

    def update_deal(self,did,p):
        d=self.s.one('SELECT * FROM deals WHERE id=?',(did,))
        kind=p.get('kind',d['kind'])
        if kind not in DEAL_KINDS:raise ValueError('Unknown deal type')
        value=num(p.get('value_usd',d['value_usd']),'Value',int) or None
        self.db.execute('UPDATE deals SET name=?,kind=?,region=?,url=?,contact_route=?,why=?,angle=?,value_usd=?,value_note=?,next_step=?,next_on=?,updated_at=? WHERE id=?',
            (text(p.get('name',d['name']),160,'Name') or d['name'],kind,text(p.get('region',d['region']),80,'Region'),web(p.get('url',d['url'])) ,text(p.get('contact_route',d['contact_route']),300,'How to reach them'),
             text(p.get('why',d['why']),600,'Why them'),text(p.get('angle',d['angle']),600,'Angle'),value,text(p.get('value_note',d['value_note']),200,'What it is worth'),
             text(p.get('next_step',d['next_step']),300,'Next step'),day(p.get('next_on',d['next_on']),'Next step date'),now(),did))
        return self.deal(did)

    def set_stage(self,did,stage,note='',next_on=None):
        """Only Bao moves a deal forward: he sent it, they replied, a meeting is set, it is won or lost."""
        if stage not in STAGES:raise ValueError('Unknown stage')
        d=self.s.one('SELECT * FROM deals WHERE id=?',(did,))
        nxt=day(next_on,'Next step date') or ((today()+timedelta(days=FOLLOW_DAYS[stage])).isoformat() if stage in FOLLOW_DAYS else None)
        step={'SENT':'Follow up if no reply','REPLIED':'Answer them','MEETING':'Prepare for the meeting','PROPOSAL':'Check in on the proposal'}.get(stage,'')
        with self.s.transaction():
            self.db.execute('UPDATE deals SET stage=?,next_on=?,next_step=?,updated_at=? WHERE id=?',(stage,nxt,step or d['next_step'],now(),did))
            self.db.execute('INSERT INTO deal_events VALUES(?,?,?,?,?,?)',(uid('event'),did,today().isoformat(),'stage',(STAGE_WORDS[stage]+('. '+note.strip() if note else '')).strip()[:2000],now()))
            # A note written before this conversation no longer fits it.
            if stage in ('REPLIED','MEETING','PROPOSAL','WON','LOST'):self.db.execute("DELETE FROM growth_drafts WHERE subject_kind='deal' AND subject_id=?",(did,))
        self.s.log('growth.deal_stage','owner',{'deal_id':did,'stage':stage})
        return self.deal(did)

    def log_event(self,did,p):
        self.s.one('SELECT id FROM deals WHERE id=?',(did,))
        summary=text(p.get('summary'),2000,'What happened')
        if not summary:raise ValueError('Say what happened, in a sentence')
        on=day(p.get('occurred_on'),'Date') or today().isoformat()
        with self.s.transaction():
            self.db.execute('INSERT INTO deal_events VALUES(?,?,?,?,?,?)',(uid('event'),did,on,p.get('kind') if p.get('kind') in ('note','sent','reply','meeting') else 'note',summary,now()))
            if p.get('next_on') or p.get('next_step'):self.db.execute('UPDATE deals SET next_on=COALESCE(?,next_on),next_step=COALESCE(NULLIF(?,\'\'),next_step),updated_at=? WHERE id=?',(day(p.get('next_on'),'Next step date'),text(p.get('next_step'),300,'Next step'),now(),did))
        return self.deal(did)

    def deal(self,did):
        d=self.s.one('SELECT * FROM deals WHERE id=?',(did,));t=today().isoformat()
        d['events']=self.s.rows('SELECT occurred_on,kind,summary FROM deal_events WHERE deal_id=? ORDER BY occurred_on DESC,created_at DESC LIMIT 8',(did,))
        d['draft']=self.g.draft('deal',did)
        d['drafting']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(DEAL_PREFIX+did,)).fetchone())
        if d['draft'] and d['stage']=='FOUND':
            self.db.execute("UPDATE deals SET stage='DRAFTED',updated_at=? WHERE id=? AND stage='FOUND'",(now(),did));d['stage']='DRAFTED'
        d['open']=d['stage'] in OPEN_STAGES
        d['due']=bool(d['open'] and d['next_on'] and d['next_on']<=t)
        d['stage_words']=STAGE_WORDS[d['stage']];d['kind_words']=KIND_WORDS[d['kind']]
        return d

    def deals(self):
        ids=[r['id'] for r in self.s.rows("SELECT id FROM deals ORDER BY CASE WHEN stage IN ('WON','LOST','PARKED') THEN 1 ELSE 0 END,COALESCE(next_on,'9999'),created_at DESC")]
        return [self.deal(i) for i in ids]

    def due_deals(self):return [d for d in self.deals() if d['due']]

    def save_targets(self,targets):
        """Partner Scout results become FOUND deals. Nothing without a public page is kept; nothing is contacted."""
        saved=0
        for t in targets[:30]:
            name=(t.get('name') or '').strip()[:160];kind=t.get('kind') if t.get('kind') in DEAL_KINDS else 'partner'
            source=web(t.get('source_url')) or web(t.get('url'))
            if not name or not source:continue
            key=digest([name.lower(),kind])[:24]
            if self.db.execute('SELECT 1 FROM deals WHERE key=?',(key,)).fetchone():continue
            self.db.execute('INSERT INTO deals(id,key,name,kind,region,url,contact_route,why,angle,stage,source,source_url,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (uid('deal'),key,name,kind,(t.get('region') or '')[:80],web(t.get('url')),(t.get('contact_route') or '')[:300],(t.get('why') or '')[:600],(t.get('angle') or '')[:600],'FOUND','partner_scout',source,now(),now()));saved+=1
        return saved

    def request_partner_discovery(self,key=None):
        key=key or 'partners-manual-'+datetime.now(ET).strftime('%Y-%m-%dT%H')
        return self.h.request_run(PARTNER_DISCOVERY,key=key)

    def record_partner_run(self,report):
        self.db.execute('INSERT INTO hunter_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',('partners_last_run',js(report)))
        self.s.log('growth.partner_discovery','research_worker',report)

    def queue_deal_draft(self,did,manual=False):
        self.s.one('SELECT id FROM deals WHERE id=?',(did,))
        key='deal-draft-'+did+'-'+(datetime.now(ET).strftime('%Y-%m-%dT%H%M%S') if manual else today().isoformat())
        return self.h.request_run(DEAL_PREFIX+did,key=key)

    def save_deal_draft(self,did,title,body,note=''):
        draft_id=self.g.save_draft('deal',did,title,body,note)
        if draft_id:self.db.execute("UPDATE deals SET stage='DRAFTED',updated_at=? WHERE id=? AND stage='FOUND'",(now(),did))
        return draft_id

    # ---------- what the AI agents read ----------
    def deal_context(self,did):
        d=self.deal(did)
        return {**self.g.base_context(),'task':'Write a short first note from Bao to this organization, or a follow-up if the log shows an earlier conversation. Lead with why their people would care: an adult child gives a parent or grandparent A Story, the parent tells their life story by phone, the family keeps it and can print a book. '
                'Offer one easy next step: a 20-minute call, a gifted plan for one of their families to try, or a group arrangement for the holidays. State prices only from CONTEXT.pricing; never invent a pilot fee, discount or number. Under 150 words. Give a subject line in title.',
                'deal':{k:d[k] for k in ('name','kind','region','why','angle','contact_route','stage','value_note')},'conversation_log':d['events']}

    def discovery_context(self):
        return {**{k:v for k,v in self.g.base_context().items() if k!='writing_guide'},'known':[r['name'] for r in self.s.rows('SELECT name FROM deals')],
                'task':'Find organizations that reach adult children or buy gifts for many older adults, so A Story can be offered to their people before the 2026 holidays: employer benefits and HR gifting teams, alumni associations, senior living and continuing-care communities, hospices, faith communities, genealogy societies, libraries, credit unions and employee resource groups. '
                'Also find angel groups and pre-seed funds in Michigan and Ohio that back consumer, family or aging products. Michigan and Ohio first, then the Midwest. Prefer organizations that publish a way to reach them for partnerships, vendors or pitches.'}

    def campaign_context(self,key):
        c=self.campaign(key);mm=self.money_moves()
        return {**{k:v for k,v in self.g.base_context().items() if k!='writing_guide'},'today':today().isoformat(),'campaign':{'title':c['title'],'brief':c['brief'],'owner_note':c['owner_note'] or ''},
                'money_moves':mm,'press_targets':[{'outlet':t['outlet'],'kind':t['kind'],'deadline':t['deadline'],'state':t['state']} for t in self.s.rows('SELECT outlet,kind,deadline,state FROM press_targets ORDER BY COALESCE(deadline,\'9999\') LIMIT 20')],
                'deals':[{'name':d['name'],'kind':d['kind'],'stage':d['stage']} for d in self.deals()[:20]],'channel_math':self.math()['channels'],'channels':list(CHANNELS),
                'task':'Plan this campaign as a dated, measurable plan Bao can run himself with no team and no budget beyond what owner_note allows. For each channel: what to do, when to start and end, the one message to lead with, how success is measured, and what Bao must supply. '
                'Put spend caps only if owner_note gives a budget; otherwise spend_cap_usd is null. Dates fall between today and December 24, 2026; the $1 reservation deadline is November 2. Use only CONTEXT facts and pricing. '
                'Open questions are the decisions only Bao can make. Risks are honest and specific.'}

    def money_moves(self):
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='money_moves'").fetchone():return []
        return self.s.rows('SELECT title,detail,state FROM money_moves ORDER BY updated_at')

    # ---------- campaigns ----------
    def campaign(self,key):
        c=self.s.one('SELECT * FROM campaigns WHERE key=?',(key,))
        c['plan']=json.loads(c['plan_json']) if c['plan_json'] else None;c['issues']=json.loads(c['issues_json']) if c['issues_json'] else []
        c['planning']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(CAMPAIGN_PREFIX+key,)).fetchone())
        c['drafts']=self.s.rows("SELECT * FROM growth_drafts WHERE subject_kind='campaign' AND subject_id=? ORDER BY created_at DESC",(c['id'],))
        for k in ('plan_json','issues_json'):c.pop(k)
        return c

    def campaigns(self):return [self.campaign(r['key']) for r in self.s.rows('SELECT key FROM campaigns ORDER BY created_at')]

    def request_plan(self,key,note=None):
        c=self.s.one('SELECT id,owner_note FROM campaigns WHERE key=?',(key,))
        if note is not None:self.db.execute('UPDATE campaigns SET owner_note=?,updated_at=? WHERE key=?',(text(note,1000,'Note'),now(),key))
        return self.h.request_run(CAMPAIGN_PREFIX+key,key='campaign-'+key+'-'+datetime.now(ET).strftime('%Y-%m-%dT%H%M'))

    def save_plan(self,key,plan):
        """Stores the plan, runs Fact Guard over its words, and hands each channel message to Bao's Voice through the growth drafts."""
        from .pitch_lab import PitchLab,FactGuard
        c=self.s.one('SELECT id FROM campaigns WHERE key=?',(key,))
        channels=[ch for ch in plan.get('channels',[]) if ch.get('channel') in CHANNELS][:9]
        plan={'goal':(plan.get('goal') or '')[:600],'audience':(plan.get('audience') or '')[:600],'offer':(plan.get('offer') or '')[:600],
              'channels':[{'channel':ch['channel'],'what':(ch.get('what') or '')[:600],'start_on':day(ch.get('start_on')) if self._safe_day(ch.get('start_on')) else None,'end_on':day(ch.get('end_on')) if self._safe_day(ch.get('end_on')) else None,
                           'message':(ch.get('message') or '')[:800],'success_metric':(ch.get('success_metric') or '')[:300],'spend_cap_usd':ch.get('spend_cap_usd') if isinstance(ch.get('spend_cap_usd'),(int,float)) else None,'needs_from_bao':(ch.get('needs_from_bao') or '')[:300]} for ch in channels],
              'checkpoints':[{'on':day(x.get('on')) if self._safe_day(x.get('on')) else None,'check':(x.get('check') or '')[:300]} for x in plan.get('checkpoints',[])[:8]],
              'open_questions':[str(q)[:300] for q in plan.get('open_questions',[])[:8]],'risks':[str(r)[:300] for r in plan.get('risks',[])[:6]]}
        segs=[{'key':'goal','text':plan['goal']},{'key':'offer','text':plan['offer']}]+[{'key':ch['channel'],'text':ch['what']+' '+ch['message']} for ch in plan['channels']]
        check=FactGuard(PitchLab(self.s)).check(segs,'GROWTH_DRAFT')
        issues=[{'where':i['where'],'text':i['text'],'severity':i['severity']} for i in check['issues'] if i['severity']!='fixed']
        with self.s.transaction():
            self.db.execute('UPDATE campaigns SET plan_json=?,issues_json=?,state=?,planned_at=?,updated_at=? WHERE key=?',(js(plan),js(issues),'PLANNED',now(),now(),key))
            self.db.execute("DELETE FROM growth_drafts WHERE subject_kind='campaign' AND subject_id=?",(c['id'],))
            for ch in plan['channels']:
                if ch['message']:self.g.save_draft('campaign',c['id'],CHANNEL_WORDS[ch['channel']],ch['message'],'Lead message for '+CHANNEL_WORDS[ch['channel']].lower()+'.')
        return self.campaign(key)

    @staticmethod
    def _safe_day(v):
        try:return bool(day(v))
        except ValueError:return False

    def set_campaign_state(self,key,state):
        if state not in ('NEW','PLANNED','RUNNING','DONE'):raise ValueError('Unknown campaign state')
        self.db.execute('UPDATE campaigns SET state=?,updated_at=? WHERE key=?',(state,now(),key))
        return self.campaign(key)

    # ---------- channel math ----------
    def add_entry(self,p):
        channel=p.get('channel') or 'other'
        if channel not in CHANNELS:raise ValueError('Unknown channel')
        week=day(p.get('week_start'),'Week') or (today()-timedelta(days=today().weekday())).isoformat()
        row=(uid('entry'),channel,week,num(p.get('visits'),'Visits'),num(p.get('signups'),'Signups'),num(p.get('purchases'),'Purchases'),num(p.get('spend_usd'),'Spend',float),num(p.get('revenue_usd'),'Revenue',float),'manual',text(p.get('note'),300,'Note'),now())
        if row[5]>row[3] and row[3]:raise ValueError('Purchases cannot exceed visits')
        self.db.execute('INSERT INTO channel_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',row)
        self.s.log('growth.channel_entry','owner',{'channel':channel,'week':week})
        return self.math()

    def delete_entry(self,eid):
        self.s.one('SELECT id FROM channel_entries WHERE id=?',(eid,));self.db.execute('DELETE FROM channel_entries WHERE id=?',(eid,));return self.math()

    def math(self):
        """Per channel and in total: conversion, cost per purchasing family, revenue per dollar. Measured, with the dates they cover."""
        rows=self.s.rows('SELECT * FROM channel_entries ORDER BY week_start DESC,created_at DESC')
        by={}
        for r in rows:
            a=by.setdefault(r['channel'],{'channel':r['channel'],'label':CHANNEL_WORDS[r['channel']],'visits':0,'signups':0,'purchases':0,'spend_usd':0.0,'revenue_usd':0.0,'weeks':set()})
            for k in ('visits','signups','purchases','spend_usd','revenue_usd'):a[k]+=r[k]
            a['weeks'].add(r['week_start'])
        def finish(a):
            weeks=sorted(a.pop('weeks'));a['from']=weeks[0] if weeks else None;a['to']=weeks[-1] if weeks else None;a['weeks']=len(weeks)
            a['signup_rate']=pct(a['signups'],a['visits']);a['conversion']=pct(a['purchases'],a['visits']);a['cost_per_family']=per(a['spend_usd'],a['purchases']) if a['spend_usd'] else None
            a['revenue_per_dollar']=per(a['revenue_usd'],a['spend_usd']);a['spend_usd']=round(a['spend_usd'],2);a['revenue_usd']=round(a['revenue_usd'],2);return a
        channels=[finish(a) for a in by.values()]
        total={'channel':'all','label':'All channels','visits':sum(c['visits'] for c in channels),'signups':sum(c['signups'] for c in channels),'purchases':sum(c['purchases'] for c in channels),
               'spend_usd':sum(c['spend_usd'] for c in channels),'revenue_usd':sum(c['revenue_usd'] for c in channels),'weeks':{r['week_start'] for r in rows}}
        total=finish(total)
        rate=total['conversion']/100 if total['conversion'] else None
        formula={**DECK_FORMULA,'measured_rate':total['conversion'],'measured_families':total['purchases'],'visits_needed_for_30':round(30/rate) if rate else None}
        return {'entries':rows[:80],'channels':sorted(channels,key=lambda c:-c['purchases']),'totals':total,'deck_formula':formula,'as_of':total['to']}

    def measured_facts(self):
        """Numbers measured from Bao's own entries, each with its source and dates, for Fact Guard and the pitch."""
        t=self.math()['totals'];out=[]
        if not t['weeks']:return out
        span=f"{t['from']} to {t['to']}";src='Channel math entries, recorded by Bao'
        out.append({'key':'purchasing_families','label':'Purchasing families','value':t['purchases'],'unit':'families','source':src,'as_of':span,'denominator':f"{t['visits']} visits"})
        if t['conversion'] is not None:out.append({'key':'conversion','label':'Visit to purchase','value':t['conversion'],'unit':'%','source':src,'as_of':span,'denominator':f"{t['purchases']} of {t['visits']} visits"})
        if t['cost_per_family'] is not None:out.append({'key':'cost_per_family','label':'Cost per purchasing family','value':t['cost_per_family'],'unit':'USD','source':src,'as_of':span,'denominator':f"${t['spend_usd']:g} over {t['purchases']} families"})
        if t['revenue_usd']:out.append({'key':'revenue','label':'Revenue recorded','value':t['revenue_usd'],'unit':'USD','source':src,'as_of':span,'denominator':f"{t['purchases']} families"})
        return out

    # ---------- the desk ----------
    def board(self):
        deals=self.deals();t=today().isoformat()
        counts={s:len([d for d in deals if d['stage']==s]) for s in STAGES}
        last=self.db.execute("SELECT value_json FROM hunter_settings WHERE key='partners_last_run'").fetchone()
        return {'stages':[{'key':s,'label':STAGE_WORDS[s],'deals':[d for d in deals if d['stage']==s]} for s in STAGES],'counts':counts,
                'pipeline_value':sum(d['value_usd'] or 0 for d in deals if d['open']),'open':len([d for d in deals if d['open']]),'due':[d for d in deals if d['due']],
                'ready_to_send':[d for d in deals if d['stage']=='DRAFTED' and d['draft']],'won_value':sum(d['value_usd'] or 0 for d in deals if d['stage']=='WON'),
                'kinds':[{'key':k,'label':KIND_WORDS[k]} for k in DEAL_KINDS],'stage_words':STAGE_WORDS,'channel_words':CHANNEL_WORDS,
                'searching':bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(PARTNER_DISCOVERY,)).fetchone()),'last_run':json.loads(last['value_json']) if last else None,
                'campaigns':self.campaigns(),'math':self.math(),'measured':self.measured_facts(),'today':t}

    def alerts(self):
        """For Today and the daily email. Every item is something only Bao can do: send, answer, meet, decide."""
        items=[];deals=self.deals()
        due=[d for d in deals if d['due']]
        if due:items.append({'title':'Next step due: '+', '.join(d['name'] for d in due[:3])+(' and '+str(len(due)-3)+' more' if len(due)>3 else ''),'detail':'; '.join(f"{d['name']}: {d['next_step'] or STAGE_WORDS[d['stage']].lower()}" for d in due[:3])[:160],'url':'/growth','link':'Open deals'})
        ready=[d for d in deals if d['stage']=='DRAFTED' and d['draft'] and not d['due']]
        if ready:items.append({'title':plural_(len(ready),'outreach note')+' ready to send','detail':'To '+', '.join(d['name'] for d in ready[:3])+'. Copy each one and send it yourself.','url':'/growth','link':'Open notes'})
        for c in self.campaigns():
            if c['state']=='PLANNED' and c['plan']:items.append({'title':c['title']+': the plan is ready','detail':(c['plan'].get('goal') or 'Review the channels and dates, then mark it running.')[:160],'url':'/growth#campaigns','link':'Review the plan'})
        return items

    def poll(self,limit=1):
        """Queue at most one deal note per cycle, oldest found deal first. Partner Scout runs Tuesday mornings until the holidays."""
        queued=[]
        for d in sorted(self.deals(),key=lambda x:x['created_at']):
            if len(queued)>=limit:break
            if d['stage']=='FOUND' and not d['draft'] and not d['drafting']:queued.append(self.queue_deal_draft(d['id']))
        local=datetime.now(ET)
        if local.weekday()==1 and local.hour>=8 and local.date()<=date(2026,12,15):self.request_partner_discovery('partners-'+local.date().isoformat())
        return {'drafts_queued':len(queued)}


def plural_(n,one):return str(n)+' '+(one if n==1 else one+'s')


# ---------- worker entry: one AI job per request, through the caller's bounded Codex runner ----------
def handles(reason):
    return reason.startswith((DEAL_PREFIX,CAMPAIGN_PREFIX)) or reason==PARTNER_DISCOVERY


def run(h,request,codex_json):
    """codex_json(h,request,prompt,schema,stem,search=False,timeout=900) -> (data, web_events). Search only for Partner Scout."""
    desk=GrowthDesk(h.store);reason=request['reason']
    if reason.startswith(DEAL_PREFIX):
        did=reason[len(DEAL_PREFIX):];ctx=desk.deal_context(did)
        schema={'type':'object','additionalProperties':False,'properties':{'title':{'type':'string'},'body':{'type':'string'},'note':{'type':'string'}},'required':['title','body','note']}
        prompt=('You are the A Story Founder OS writing assistant. '+ctx['task']+' Use ONLY CONTEXT and follow CONTEXT.rules. '
                'Return JSON: title (email subject), body (the message, ready to paste, signed Bao), note (anything Bao should check or fill in). Do not use shell, files, web, email or any tool.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
        data,_=codex_json(h,request,prompt,schema,'deal-note')
        return {'deal':did,'draft_id':desk.save_deal_draft(did,data.get('title'),data.get('body'),data.get('note'))}
    if reason==PARTNER_DISCOVERY:
        ctx=desk.discovery_context()
        target={'type':'object','additionalProperties':False,'properties':{**{k:{'type':'string'} for k in ('name','url','contact_route','region','why','angle','source_url')},'kind':{'type':'string','enum':list(DEAL_KINDS)}},
                'required':['name','kind','url','contact_route','region','why','angle','source_url']}
        schema={'type':'object','additionalProperties':False,'properties':{'queries':{'type':'array','items':{'type':'string'}},'targets':{'type':'array','items':target},
                'errors':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'message':{'type':'string'}},'required':['message']}}},'required':['queries','targets','errors']}
        prompt=('You are A Story Founder OS partner scout, a READ-ONLY research worker. Use ONLY public web search and public page reads. Do not use shell, file, email, form, account or posting tools. '
                +ctx['task']+' Use at most 6 search queries and read at most 12 pages. Return up to 12 targets not in CONTEXT.known. '
                'contact_route is only a route the organization publishes (a partnerships page, a vendor form, a general address, a pitch form); never guess a personal email. source_url is the page that shows the route or the fit. '
                'why is one sentence on the fit; angle is one sentence on how to open. Do not invent programs, people or contacts.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
        data,events=codex_json(h,request,prompt,schema,'partners',search=True,timeout=1200)
        if not events:raise RuntimeError('SOURCE_UNAVAILABLE: no web-tool activity was recorded; partner targets cannot be verified')
        found=desk.save_targets(data.get('targets',[]))
        desk.record_partner_run({'at':now(),'found':found,'returned':len(data.get('targets',[])),'queries':data.get('queries',[])[:10],'errors':[e.get('message','') for e in data.get('errors',[])][:6]})
        return {'deals_found':found}
    key=reason[len(CAMPAIGN_PREFIX):];ctx=desk.campaign_context(key)
    channel={'type':'object','additionalProperties':False,'properties':{'channel':{'type':'string','enum':list(CHANNELS)},'what':{'type':'string'},'start_on':{'type':'string'},'end_on':{'type':'string'},'message':{'type':'string'},
             'success_metric':{'type':'string'},'spend_cap_usd':{'type':['number','null']},'needs_from_bao':{'type':'string'}},'required':['channel','what','start_on','end_on','message','success_metric','spend_cap_usd','needs_from_bao']}
    checkpoint={'type':'object','additionalProperties':False,'properties':{'on':{'type':'string'},'check':{'type':'string'}},'required':['on','check']}
    schema={'type':'object','additionalProperties':False,'properties':{'goal':{'type':'string'},'audience':{'type':'string'},'offer':{'type':'string'},'channels':{'type':'array','items':channel},
            'checkpoints':{'type':'array','items':checkpoint},'open_questions':{'type':'array','items':{'type':'string'}},'risks':{'type':'array','items':{'type':'string'}}},'required':['goal','audience','offer','channels','checkpoints','open_questions','risks']}
    prompt=('You are Campaign Planner for A Story Founder OS. '+ctx['task']+' Use ONLY CONTEXT and follow CONTEXT.rules; never invent numbers, partners, coverage or results. '
            'Write every message in Bao’s voice: warm, plain, short sentences, no hype. Dates are YYYY-MM-DD. Return at most 6 channels, 6 checkpoints, 6 open questions and 5 risks. Do not use shell, files, web, email or any tool.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
    data,_=codex_json(h,request,prompt,schema,'campaign')
    c=desk.save_plan(key,data)
    return {'campaign':key,'channels':len(c['plan']['channels']),'issues':len(c['issues'])}
