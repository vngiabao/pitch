"""Growth agents: credit expiry, relationship follow-ups, press and gift-guide outreach.

Agents prepare; the owner sends. Nothing here emails, posts, pitches or submits anything.
"""
import json
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from .store import now,js,digest,uid,PolicyError
from .funding_hunter import FundingHunter

ET=ZoneInfo('America/New_York')
FOLLOWUP_PREFIX='Draft follow-up: '
PRESS_PREFIX='Draft press pitch: '
PRESS_DISCOVERY='Press and gift-guide discovery'
CONTACT_KINDS=('Investor','Partner','Program','Press','Mentor','Customer','Other')
PRESS_KINDS=('gift_guide','newsletter','podcast','journalist','local_news','blog','community')
PRESS_STATES=('NEW','PITCHED','SKIPPED','PUBLISHED')
CREDIT_STATES=('ACTIVE','NOT_ACTIVATED','USED_UP','ENDED')

SCHEMA='''
CREATE TABLE IF NOT EXISTS credit_grants(id TEXT PRIMARY KEY,provider TEXT NOT NULL UNIQUE,program TEXT NOT NULL,opportunity_id TEXT,
 covers TEXT,allowance TEXT,after_expiry TEXT,program_url TEXT,account_email TEXT,started_on TEXT,expires_on TEXT,term_months INTEGER,
 balance_note TEXT,balance_checked_on TEXT,state TEXT NOT NULL DEFAULT 'ACTIVE',notes TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contacts(id TEXT PRIMARY KEY,name TEXT NOT NULL,org TEXT,kind TEXT NOT NULL,email TEXT,context TEXT,
 next_followup_on TEXT,cadence_days INTEGER NOT NULL DEFAULT 14,state TEXT NOT NULL DEFAULT 'ACTIVE',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contact_touches(id TEXT PRIMARY KEY,contact_id TEXT NOT NULL REFERENCES contacts(id),occurred_on TEXT NOT NULL,summary TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS growth_drafts(id TEXT PRIMARY KEY,subject_kind TEXT NOT NULL,subject_id TEXT NOT NULL,title TEXT,body TEXT NOT NULL,note TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS press_targets(id TEXT PRIMARY KEY,key TEXT NOT NULL UNIQUE,outlet TEXT NOT NULL,kind TEXT NOT NULL,url TEXT,submit_url TEXT,
 submit_method TEXT,deadline TEXT,audience TEXT,angle TEXT,why TEXT,source_url TEXT,state TEXT NOT NULL DEFAULT 'NEW',found_at TEXT NOT NULL,updated_at TEXT NOT NULL);
'''

def today():return datetime.now(ET).date()

def day(value,field='date'):
    if value in (None,''):return None
    try:return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:raise ValueError(field+' must be a date like 2026-10-15')

def text(value,limit,field):
    value='' if value is None else value
    if not isinstance(value,str) or len(value)>limit:raise ValueError(field+' must be text of at most '+str(limit)+' characters')
    return value.strip()

def web(url):
    return url if url and urlsplit(str(url)).scheme in ('http','https') else None

def add_months(start,months):
    m=start.month-1+months;y=start.year+m//12;m=m%12+1
    for d in (start.day,30,29,28):
        try:return date(y,m,d)
        except ValueError:continue

class Growth:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store)
        # Plain execute, not executescript: this may run inside a caller's open transaction.
        for statement in SCHEMA.split(';'):
            if statement.strip():self.db.execute(statement)

    # ---------- credits ----------
    def sync_credits(self):
        """Every accepted credit program becomes a grant to track. Dates stay empty until the owner adds them."""
        accepted=self.db.execute("SELECT DISTINCT opportunity_id FROM funding_outcomes WHERE outcome IN ('Accepted','Won')").fetchall()
        for row in accepted:
            try:d=self.h.detail(row['opportunity_id'])
            except ValueError:continue
            cb=d['data'].get('credit_benefits') or {};provider=cb.get('provider')
            if not provider or d['analysis']['money']['kind']!='CREDITS':continue
            if self.db.execute('SELECT 1 FROM credit_grants WHERE lower(provider)=lower(?)',(provider,)).fetchone():continue
            self.db.execute('INSERT INTO credit_grants(id,provider,program,opportunity_id,covers,allowance,after_expiry,program_url,term_months,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (uid('credit'),provider,d['data']['canonical_name'],row['opportunity_id'],cb.get('eligible_products'),d['data']['funding'].get('award_scope'),cb.get('renewal_behavior'),
                 web(d['data'].get('official_url')),int(cb['expiration_months']) if cb.get('expiration_months') else None,'ACTIVE',now(),now()))

    def credits(self):
        self.sync_credits();out=[];t=today()
        for c in self.s.rows('SELECT * FROM credit_grants ORDER BY provider'):
            ends=date.fromisoformat(c['expires_on']) if c['expires_on'] else add_months(date.fromisoformat(c['started_on']),c['term_months']) if c['started_on'] and c['term_months'] else None
            left=(ends-t).days if ends else None
            if c['state'] in ('USED_UP','ENDED'):level,label='DONE','Used up' if c['state']=='USED_UP' else 'Ended'
            elif c['state']=='NOT_ACTIVATED':level,label='ACTIVATE','Not activated yet'
            elif ends is None:level,label='NEEDS_DATES','Add the start date'
            elif left<0:level,label='DONE','Expired '+ends.strftime('%b %d, %Y').replace(' 0',' ')
            elif left<=14:level,label='URGENT','Expires in '+str(left)+(' day' if left==1 else ' days')
            elif left<=45:level,label='SOON','Expires in '+str(left)+' days'
            else:level,label='OK','Active until '+ends.strftime('%b %d, %Y').replace(' 0',' ')
            stale=bool(c['balance_checked_on'] and (t-date.fromisoformat(c['balance_checked_on'])).days>30)
            out.append({**c,'ends_on':ends.isoformat() if ends else None,'days_left':left,'level':level,'label':label,'balance_stale':stale})
        return out

    def update_credit(self,cid,p):
        c=self.s.one('SELECT * FROM credit_grants WHERE id=?',(cid,))
        fields={'started_on':day(p.get('started_on',c['started_on']),'Start date'),'expires_on':day(p.get('expires_on',c['expires_on']),'Expiry date'),
                'account_email':text(p.get('account_email',c['account_email']),200,'Account email'),'notes':text(p.get('notes',c['notes']),2000,'Notes')}
        if 'balance_note' in p:
            fields['balance_note']=text(p['balance_note'],300,'Balance');fields['balance_checked_on']=today().isoformat() if fields['balance_note'] else None
        state=p.get('state',c['state'])
        if state not in CREDIT_STATES:raise ValueError('Unknown credit state')
        fields['state']=state;fields['updated_at']=now()
        self.db.execute('UPDATE credit_grants SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),cid))
        self.s.log('growth.credit_updated','owner',{'credit_id':cid,'fields':sorted(fields)})
        return next(x for x in self.credits() if x['id']==cid)

    # ---------- relationships ----------
    def add_contact(self,p):
        name=text(p.get('name'),120,'Name')
        if not name:raise ValueError('A name is required')
        kind=p.get('kind') or 'Other'
        if kind not in CONTACT_KINDS:raise ValueError('Unknown contact type')
        cadence=int(p.get('cadence_days') or 14)
        if not 1<=cadence<=180:raise ValueError('Follow-up spacing must be 1 to 180 days')
        cid=uid('contact')
        self.db.execute('INSERT INTO contacts VALUES(?,?,?,?,?,?,?,?,?,?,?)',(cid,name,text(p.get('org'),120,'Organization'),kind,text(p.get('email'),200,'Email'),
            text(p.get('context'),2000,'Context'),day(p.get('next_followup_on'),'Next follow-up'),cadence,'ACTIVE',now(),now()))
        if p.get('summary'):self.log_touch(cid,{'summary':p['summary'],'occurred_on':p.get('occurred_on'),'next_followup_on':p.get('next_followup_on')})
        self.s.log('growth.contact_added','owner',{'contact_id':cid,'kind':kind})
        return self.contact(cid)

    def update_contact(self,cid,p):
        c=self.s.one('SELECT * FROM contacts WHERE id=?',(cid,))
        state=p.get('state',c['state'])
        if state not in ('ACTIVE','PAUSED','DONE'):raise ValueError('Unknown contact state')
        kind=p.get('kind',c['kind'])
        if kind not in CONTACT_KINDS:raise ValueError('Unknown contact type')
        self.db.execute('UPDATE contacts SET name=?,org=?,kind=?,email=?,context=?,next_followup_on=?,state=?,updated_at=? WHERE id=?',
            (text(p.get('name',c['name']),120,'Name') or c['name'],text(p.get('org',c['org']),120,'Organization'),kind,text(p.get('email',c['email']),200,'Email'),
             text(p.get('context',c['context']),2000,'Context'),day(p.get('next_followup_on',c['next_followup_on']),'Next follow-up'),state,now(),cid))
        return self.contact(cid)

    def log_touch(self,cid,p):
        c=self.s.one('SELECT * FROM contacts WHERE id=?',(cid,))
        summary=text(p.get('summary'),2000,'What happened')
        if not summary:raise ValueError('Say what happened, in a sentence')
        on=day(p.get('occurred_on'),'Date') or today().isoformat()
        nxt=day(p.get('next_followup_on'),'Next follow-up') or (date.fromisoformat(on)+timedelta(days=c['cadence_days'])).isoformat()
        with self.s.transaction():
            self.db.execute('INSERT INTO contact_touches VALUES(?,?,?,?,?)',(uid('touch'),cid,on,summary,now()))
            self.db.execute('UPDATE contacts SET next_followup_on=?,updated_at=? WHERE id=?',(nxt,now(),cid))
            # A draft written before this conversation no longer fits it.
            self.db.execute("DELETE FROM growth_drafts WHERE subject_kind='contact' AND subject_id=?",(cid,))
        return self.contact(cid)

    def contact(self,cid):
        c=self.s.one('SELECT * FROM contacts WHERE id=?',(cid,));t=today().isoformat()
        c['touches']=self.s.rows('SELECT occurred_on,summary FROM contact_touches WHERE contact_id=? ORDER BY occurred_on DESC,created_at DESC LIMIT 6',(cid,))
        c['draft']=self.draft('contact',cid)
        c['due']=bool(c['state']=='ACTIVE' and c['next_followup_on'] and c['next_followup_on']<=t)
        c['drafting']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(FOLLOWUP_PREFIX+cid,)).fetchone())
        return c

    def contacts(self):
        ids=[r['id'] for r in self.s.rows("SELECT id FROM contacts ORDER BY CASE state WHEN 'ACTIVE' THEN 0 ELSE 1 END,COALESCE(next_followup_on,'9999'),name")]
        return [self.contact(i) for i in ids]

    def due_contacts(self):
        return [c for c in self.contacts() if c['due']]

    # ---------- press ----------
    def save_targets(self,targets):
        saved=0
        for t in targets[:30]:
            outlet=(t.get('outlet') or '').strip()[:160];kind=t.get('kind') if t.get('kind') in PRESS_KINDS else 'blog'
            if not outlet or not web(t.get('source_url') or t.get('url')):continue
            try:deadline=day(t.get('deadline'))
            except ValueError:deadline=None
            if deadline and deadline<today().isoformat():continue
            key=digest([outlet.lower(),kind])[:24]
            row=(outlet,kind,web(t.get('url')),web(t.get('submit_url')),(t.get('submit_method') or '')[:300],deadline,(t.get('audience') or '')[:300],(t.get('angle') or '')[:600],(t.get('why') or '')[:600],web(t.get('source_url')) or web(t.get('url')))
            if self.db.execute('SELECT 1 FROM press_targets WHERE key=?',(key,)).fetchone():
                self.db.execute('UPDATE press_targets SET outlet=?,kind=?,url=?,submit_url=?,submit_method=?,deadline=?,audience=?,angle=?,why=?,source_url=?,updated_at=? WHERE key=?',(*row,now(),key))
            else:
                self.db.execute('INSERT INTO press_targets VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(uid('press'),key,*row,'NEW',now(),now()));saved+=1
        return saved

    def press(self):
        out=[]
        for t in self.s.rows("SELECT * FROM press_targets ORDER BY CASE state WHEN 'NEW' THEN 0 WHEN 'PITCHED' THEN 1 ELSE 2 END,COALESCE(deadline,'9999'),found_at DESC"):
            t['draft']=self.draft('press',t['id'])
            t['drafting']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(PRESS_PREFIX+t['id'],)).fetchone())
            t['days_left']=(date.fromisoformat(t['deadline'])-today()).days if t['deadline'] else None
            out.append(t)
        last=self.db.execute("SELECT value_json FROM hunter_settings WHERE key='press_last_run'").fetchone()
        queued=self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(PRESS_DISCOVERY,)).fetchone()
        return {'targets':out,'last_run':json.loads(last['value_json']) if last else None,'searching':bool(queued)}

    def set_press_state(self,tid,state):
        if state not in PRESS_STATES:raise ValueError('Unknown press state')
        self.s.one('SELECT id FROM press_targets WHERE id=?',(tid,))
        self.db.execute('UPDATE press_targets SET state=?,updated_at=? WHERE id=?',(state,now(),tid))
        return {'id':tid,'state':state}

    def request_press_discovery(self,key=None):
        key=key or 'press-manual-'+datetime.now(ET).strftime('%Y-%m-%dT%H')
        return self.h.request_run(PRESS_DISCOVERY,key=key)

    def record_press_run(self,report):
        self.db.execute('INSERT INTO hunter_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',('press_last_run',js(report)))
        self.s.log('growth.press_discovery','research_worker',report)

    # ---------- drafts ----------
    def draft(self,kind,sid):
        row=self.db.execute('SELECT * FROM growth_drafts WHERE subject_kind=? AND subject_id=? ORDER BY created_at DESC LIMIT 1',(kind,sid)).fetchone()
        return dict(row) if row else None

    def queue_draft(self,kind,sid,manual=False):
        if kind not in ('contact','press'):raise ValueError('Unknown draft kind')
        prefix=FOLLOWUP_PREFIX if kind=='contact' else PRESS_PREFIX
        self.s.one('SELECT id FROM '+('contacts' if kind=='contact' else 'press_targets')+' WHERE id=?',(sid,))
        # Automatic drafts get one key a day, so a failing draft is not re-queued every cycle.
        key=kind+'-draft-'+sid+'-'+(datetime.now(ET).strftime('%Y-%m-%dT%H%M%S') if manual else today().isoformat())
        return self.h.request_run(prefix+sid,key=key)

    def save_draft(self,kind,sid,title,body,note=''):
        body=(body or '').strip()
        if not body:return None
        did=uid('draft')
        self.db.execute('INSERT INTO growth_drafts VALUES(?,?,?,?,?,?,?)',(did,kind,sid,(title or '')[:200],body[:6000],(note or '')[:600],now()))
        return did

    def base_context(self):
        mem=self.h.company_memory();guide=Path(__file__).resolve().parents[1]/'PITCH_WRITING.md'
        pricing=self.db.execute("SELECT v.body FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE s.kind='official_pricing_capture' AND v.body IS NOT NULL ORDER BY v.captured_at DESC LIMIT 1").fetchone()
        return {'company_facts':{k:v['value'] for k,v in mem['attributes'].items()},'approved_statements':[{'topic':c['topic'],'text':c['body']} for c in mem['canonical_claims'] if not c['body'].startswith('{')],
                'pricing':pricing['body'][:6000] if pricing else '','writing_guide':guide.read_text(encoding='utf-8')[:7000] if guide.exists() else '','today':today().isoformat(),
                'rules':['Use only the facts and statements given here. Never invent numbers, customers, partners, press coverage, awards or traction.',
                         'Two founders: Daniel Hoang Nguyen (CEO) and Bao Vo (COO). Do not mention Nhi Tran.',
                         'Traction is owner-reported: 50 leads from the first version, 10 families in the private beta, 5 more waiting to join as paying customers. Never call them paying customers.',
                         'Write as Bao, warm and plain, short sentences, normal hyphens, no em dashes, no hype words.',
                         'The owner sends every message himself. Never claim it was sent or promise anything on his behalf.']}

    def followup_context(self,cid):
        from .reservation_drive import drive_task
        c=self.contact(cid)
        return {**self.base_context(),'task':drive_task(self.s,cid) or 'Write a short follow-up email from Bao to this contact. Pick up from the last conversation, give one concrete update from the approved statements, and end with one easy next step. Under 140 words.',
                'contact':{k:c[k] for k in ('name','org','kind','context','next_followup_on')},'conversation_log':c['touches']}

    def press_context(self,tid):
        t=self.s.one('SELECT * FROM press_targets WHERE id=?',(tid,))
        return {**self.base_context(),'task':'Write a pitch from Bao to this outlet for its holiday gift guide or story. Lead with why their readers would care, give the gift angle (a parent or grandparent tells their life story by phone; the family keeps it and can print a book), state the price plainly from pricing, and offer a demo or a gifted plan. Under 170 words. Give a subject line in title.',
                'outlet':{k:t[k] for k in ('outlet','kind','url','submit_method','deadline','audience','angle','why')}}

    def press_discovery_context(self):
        return {**{k:v for k,v in self.base_context().items() if k!='writing_guide'},'known_outlets':[r['outlet'] for r in self.s.rows('SELECT outlet FROM press_targets')],
                'task':'Find holiday 2026 gift guides, newsletters, podcasts and local outlets where A Story (an AI biographer gift for parents and grandparents) could be featured. Prefer outlets that publish a submission page, pitch form or editorial guidelines and a deadline. Michigan and family, parenting, aging, genealogy and gift-guide audiences first.'}

    # ---------- coordination ----------
    def poll(self,limit=1):
        """Queue at most one draft per cycle: a due follow-up first, then the press target closest to its deadline."""
        queued=[]
        for c in self.due_contacts():
            if len(queued)>=limit:break
            if not c['draft'] and not c['drafting']:queued.append(self.queue_draft('contact',c['id']))
        for t in self.press()['targets']:
            if len(queued)>=limit:break
            if t['state']=='NEW' and not t['draft'] and not t['drafting']:queued.append(self.queue_draft('press',t['id']))
        local=datetime.now(ET)
        # Twice a week in the gift-guide season, after the morning funding scan.
        if local.weekday() in (0,3) and local.hour>=8:self.request_press_discovery('press-'+local.date().isoformat())
        return {'drafts_queued':len(queued)}

    def alerts(self):
        """What the owner should act on, for Today and the daily email. Paths are site-relative."""
        items=[];credits=self.credits()
        undated=[c['provider'] for c in credits if c['level']=='NEEDS_DATES']
        if undated:items.append({'title':'Add start dates for your '+' and '.join(undated)+' credits','detail':'Then the agent can warn you before they expire, so none go unused.','url':'/credits','link':'Add dates'})
        for c in credits:
            if c['level'] in ('URGENT','SOON'):items.append({'title':c['provider']+' credits: '+c['label'].lower(),'detail':(c['after_expiry'] or 'Use them before they lapse.')[:160],'url':'/credits','link':'Review'})
            if c['level']=='ACTIVATE':items.append({'title':'Activate your '+c['provider']+' credits','detail':'Credits usually start when you redeem them. Note the date here when you do.','url':'/credits','link':'Open'})
        from .reservation_drive import member_ids
        due=[c for c in self.due_contacts() if c['id'] not in member_ids(self.s)]  # drive members get the drive's own nudges
        if due:items.append({'title':'Follow up with '+', '.join(c['name'] for c in due[:3])+(' and '+str(len(due)-3)+' more' if len(due)>3 else ''),'detail':'Drafts are ready to copy.' if all(c['draft'] for c in due) else 'The agent is drafting the notes.','url':'/people','link':'Open drafts'})
        for t in self.press()['targets']:
            if t['state']=='NEW' and t['days_left'] is not None and 0<=t['days_left']<=10:
                items.append({'title':t['outlet']+': pitch by '+date.fromisoformat(t['deadline']).strftime('%b %d').replace(' 0',' '),'detail':'Pitch drafted. Copy it and send it yourself.' if t['draft'] else 'The agent is drafting the pitch.','url':'/press','link':'Open pitch'})
        return items
