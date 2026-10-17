"""Win Scout: for one competition, everything that decides who wins it.

The rules as published, how it is scored, who judges and what they have said they care about, who won before and why,
who else is in this cycle, and the expectations nobody writes down. The result is a win brief with sources. Pitch Tailor
builds the edition to it, the Application Drafter shapes answers to it, Pitch Coach judges by it. It refreshes weekly for
programs A Story is in, and tells Bao what changed. Read-only; it never contacts anyone and never states a fact about A Story.
"""
import json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .store import now,js,uid
from .funding_hunter import FundingHunter

ET=ZoneInfo('America/New_York')
WIN_PREFIX='Win brief: '
APPLIES=('pitch','application','qa','demo','materials')
IN_PLAY=('Applied','Advanced','Finalist')
SCHEMA='CREATE TABLE IF NOT EXISTS win_briefs(id TEXT PRIMARY KEY,opportunity_id TEXT NOT NULL UNIQUE,brief_json TEXT NOT NULL,changes_json TEXT,seen_at TEXT,checked_at TEXT NOT NULL,runs INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);'


def _s(v,n=400):return (str(v) if v is not None else '')[:n].strip()


def clean(data):
    """Only the shapes the agents read, each string bounded; nothing invented here, only trimmed."""
    r=data.get('rules') or {}
    return {'rules':{k:_s(r.get(k),300) for k in ('format','time_limit','slide_limit','qa','audience','where','deadline','event_date')},
            'criteria':[{'name':_s(c.get('name'),120),'weight':_s(c.get('weight'),60),'evidence':_s(c.get('evidence'))} for c in (data.get('criteria') or [])[:10] if _s(c.get('name'))],
            'judges':[{'name':_s(j.get('name'),120),'role':_s(j.get('role'),200),'cares_about':_s(j.get('cares_about')),'source_url':_s(j.get('source_url'),500)} for j in (data.get('judges') or [])[:12] if _s(j.get('name'))],
            'past_winners':[{'year':_s(w.get('year'),12),'company':_s(w.get('company'),120),'what_they_did':_s(w.get('what_they_did')),'why_it_won':_s(w.get('why_it_won')),'source_url':_s(w.get('source_url'),500)} for w in (data.get('past_winners') or [])[:10] if _s(w.get('company'))],
            'competitors':[{'name':_s(c.get('name'),120),'what_they_do':_s(c.get('what_they_do')),'stage':_s(c.get('stage'),120),'strength':_s(c.get('strength')),'source_url':_s(c.get('source_url'),500)} for c in (data.get('competitors') or [])[:15] if _s(c.get('name'))],
            'unstated':[{'insight':_s(u.get('insight')),'evidence':_s(u.get('evidence'))} for u in (data.get('unstated') or [])[:8] if _s(u.get('insight'))],
            'how_we_win':[{'move':_s(m.get('move')),'why':_s(m.get('why')),'applies_to':m.get('applies_to') if m.get('applies_to') in APPLIES else 'pitch'} for m in (data.get('how_we_win') or [])[:10] if _s(m.get('move'))],
            'risks':[_s(x) for x in (data.get('risks') or [])[:6] if _s(x)],'open_questions':[_s(x) for x in (data.get('open_questions') or [])[:6] if _s(x)],
            'sources':[_s(x,500) for x in (data.get('sources') or [])[:20] if _s(x,500).startswith('http')]}


def changes_between(old,new):
    if not old:return []
    out=[]
    names=lambda xs,k:{x[k] for x in xs}
    for label,key,field in (('competitor','competitors','name'),('judge','judges','name'),('past winner','past_winners','company'),('criterion','criteria','name')):
        added=names(new[key],field)-names(old[key],field)
        if added:out.append(f"New {label}{'s' if len(added)>1 else ''}: "+', '.join(sorted(added)[:6]))
    for k in ('format','time_limit','slide_limit','deadline','event_date','qa'):
        if new['rules'].get(k) and new['rules'].get(k)!=old['rules'].get(k):out.append(f"{k.replace('_',' ').capitalize()} now: {new['rules'][k]}")
    return out


class WinScout:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.db.execute(SCHEMA)

    def program(self,oid):
        d=self.h.detail(oid);data=d['data']
        return {k:data.get(k) for k in ('canonical_name','organizer','opportunity_type','cycle','official_url','application_url','dates','funding','eligibility','requirements','notes')}|{'recommendation':d['recommendation']}

    def researching(self,oid):
        return bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(WIN_PREFIX+oid,)).fetchone())

    def brief(self,oid):
        r=self.db.execute('SELECT * FROM win_briefs WHERE opportunity_id=?',(oid,)).fetchone()
        if not r:return {'opportunity_id':oid,'brief':None,'changes':[],'checked_at':None,'runs':0,'seen':True,'researching':self.researching(oid)}
        changes=json.loads(r['changes_json'] or '[]')
        return {'opportunity_id':oid,'brief':json.loads(r['brief_json']),'changes':changes,'checked_at':r['checked_at'],'runs':r['runs'],
                'seen':not changes or bool(r['seen_at'] and r['seen_at']>=r['updated_at']),'researching':self.researching(oid)}

    def request(self,oid,manual=True):
        self.h.detail(oid)
        stamp=datetime.now(ET).strftime('%Y-%m-%dT%H%M') if manual else 'week-'+datetime.now(ET).strftime('%G-%V')
        return self.h.request_run(WIN_PREFIX+oid,key='win-'+oid+'-'+stamp)

    def save(self,oid,data):
        new=clean(data);old=self.db.execute('SELECT brief_json,runs FROM win_briefs WHERE opportunity_id=?',(oid,)).fetchone()
        changes=changes_between(json.loads(old['brief_json']) if old else None,new)
        if old:self.db.execute('UPDATE win_briefs SET brief_json=?,changes_json=?,checked_at=?,runs=runs+1,updated_at=? WHERE opportunity_id=?',(js(new),js(changes),now(),now(),oid))
        else:self.db.execute('INSERT INTO win_briefs VALUES(?,?,?,?,?,?,?,?,?)',(uid('win'),oid,js(new),js(changes),None,now(),1,now(),now()))
        self.s.log('win.brief_saved','research_worker',{'opportunity_id':oid,'changes':changes[:6],'competitors':len(new['competitors']),'judges':len(new['judges'])})
        return self.brief(oid)

    def mark_seen(self,oid):
        self.db.execute('UPDATE win_briefs SET seen_at=? WHERE opportunity_id=?',(now(),oid));return self.brief(oid)

    def for_agents(self,oid):
        """The compact form Pitch Tailor, the Drafter and the Coach read. It describes the program and other companies, never A Story."""
        if not oid:return None
        b=self.brief(oid)['brief']
        if not b:return None
        return {'criteria':b['criteria'],'judges':[{'name':j['name'],'role':j['role'],'cares_about':j['cares_about']} for j in b['judges']],'how_we_win':b['how_we_win'],'unstated':[u['insight'] for u in b['unstated']],
                'competitors':[{'name':c['name'],'what_they_do':c['what_they_do'],'strength':c['strength']} for c in b['competitors']],'past_winners':[{'year':w['year'],'company':w['company'],'why_it_won':w['why_it_won']} for w in b['past_winners']],
                'rules':b['rules'],'note':'This brief describes the program, its judges and other companies. It holds no facts about A Story; take none from it.'}

    def context(self,oid):
        mem=self.h.company_memory();prev=self.brief(oid)['brief']
        return {'program':self.program(oid),'previous_brief':prev,'today':datetime.now(ET).date().isoformat(),
                'about_us':{'one_line':'A Story is an AI biographer that phone-interviews a parent or grandparent on a schedule; the family keeps the recordings, adds photos and their own versions, and can print a book. Two founders, Michigan, bootstrapped, launching for the 2026 holidays.',
                            'facts':{k:v['value'] for k,v in mem['attributes'].items()}},
                'task':'Research how to win this exact competition. Read the official pages first (rules, format, scoring, judges, schedule, past winners), then press and announcements about past winners and this cycle’s finalists or applicants, then the public profiles of named judges. '
                       'Report: the rules as published; the judging criteria with weights when stated; each judge with their public role and what they have publicly said they look for; past winners with what they did and why they won as reported; other companies in this cycle with what they do and their strength; the expectations nobody writes down but the evidence shows (local traction, a live demo, a tight Q&A, a founder story, a specific audience); and how A Story can win here, each move tied to a criterion, a judge or a past winner, labelled pitch, application, qa, demo or materials. '
                       'If previous_brief exists, look for what changed since. Name only public people in their public judging role. Write "not published" when something is not stated. Never invent judges, winners, weights, dates or companies, and never state facts about A Story beyond about_us.'}

    def candidates(self,limit=2):
        """Programs worth a weekly refresh: ones A Story applied to or advanced in, or is about to apply to, with the event or deadline inside 60 days."""
        out=[]
        for d in self.h.list('All'):
            oid=d['opportunity_id'];days=d['analysis']['scoring']['dates'].get('days_remaining')
            outcome=self.db.execute('SELECT outcome FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC LIMIT 1',(oid,)).fetchone()
            in_play=bool(outcome and outcome['outcome'] in IN_PLAY)
            soon=days is not None and 0<=days<=60
            # A program A Story is in stays in play after its deadline: the pitch or the decision comes later (SWC Columbus: deadline Oct 15, finale Oct 24).
            recent=days is not None and -60<=days<=60
            if (in_play and (recent or days is None)) or (d['recommendation'] in ('APPLY NOW','PREPARE') and soon):out.append((0 if in_play else 1,abs(days) if days is not None else 999,oid))
        return [oid for _,_,oid in sorted(out)[:limit]]

    def poll(self,instant=None):
        queued=[]
        for oid in self.candidates():
            before=self.db.execute('SELECT COUNT(*) FROM hunter_requests').fetchone()[0];self.request(oid,manual=False)
            if self.db.execute('SELECT COUNT(*) FROM hunter_requests').fetchone()[0]>before:queued.append(oid)
        return {'queued':queued}

    def alerts(self):
        items=[]
        for r in self.s.rows("SELECT w.opportunity_id,w.changes_json,w.seen_at,w.updated_at,p.canonical_name FROM win_briefs w LEFT JOIN funding_intelligence i ON i.opportunity_id=w.opportunity_id LEFT JOIN funding_programs p ON p.id=i.program_id WHERE w.changes_json IS NOT NULL AND w.changes_json!='[]' ORDER BY w.updated_at DESC LIMIT 6"):
            if r['seen_at'] and r['seen_at']>=r['updated_at']:continue
            ch=json.loads(r['changes_json']);items.append({'title':(r['canonical_name'] or 'A program')+': '+ch[0][:90],'detail':('Also: '+'; '.join(ch[1:3]))[:160] if len(ch)>1 else 'Win Scout found this on its weekly check.','url':'/opportunity/'+r['opportunity_id'],'link':'See how to win'})
        return items

    def summary(self):
        row=self.db.execute('SELECT COUNT(*) n,MAX(checked_at) at FROM win_briefs').fetchone()
        return {'briefs':row['n'],'last_checked':row['at'],'running':bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason LIKE ? AND state IN ('QUEUED','RUNNING')",(WIN_PREFIX+'%',)).fetchone())}


def handles(reason):return reason.startswith(WIN_PREFIX)


def run(h,request,codex_json):
    """One bounded public-web research job for one program. Web search is required; a run with no web activity is rejected."""
    ws=WinScout(h.store);oid=request['reason'][len(WIN_PREFIX):];ctx=ws.context(oid)
    S=lambda:{'type':'string'}
    obj=lambda props:{'type':'object','additionalProperties':False,'properties':{k:S() for k in props},'required':list(props)}
    move={'type':'object','additionalProperties':False,'properties':{'move':S(),'why':S(),'applies_to':{'type':'string','enum':list(APPLIES)}},'required':['move','why','applies_to']}
    schema={'type':'object','additionalProperties':False,'properties':{
        'rules':obj(('format','time_limit','slide_limit','qa','audience','where','deadline','event_date')),
        'criteria':{'type':'array','items':obj(('name','weight','evidence'))},'judges':{'type':'array','items':obj(('name','role','cares_about','source_url'))},
        'past_winners':{'type':'array','items':obj(('year','company','what_they_did','why_it_won','source_url'))},'competitors':{'type':'array','items':obj(('name','what_they_do','stage','strength','source_url'))},
        'unstated':{'type':'array','items':obj(('insight','evidence'))},'how_we_win':{'type':'array','items':move},
        'risks':{'type':'array','items':S()},'open_questions':{'type':'array','items':S()},'sources':{'type':'array','items':S()},'queries':{'type':'array','items':S()},
        'errors':{'type':'array','items':obj(('message',))}},
        'required':['rules','criteria','judges','past_winners','competitors','unstated','how_we_win','risks','open_questions','sources','queries','errors']}
    prompt=('You are A Story Founder OS Win Scout, a READ-ONLY research worker. Use ONLY public web search and public page reads. Do not use shell, file, email, form, account or posting tools. '
            +ctx['task']+' Use at most 10 search queries and read at most 16 pages. Every judge, winner, competitor and criterion needs a source_url or goes in errors as unverified. '
            'Keep each field short and specific. Return JSON matching the schema.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
    data,events=codex_json(h,request,prompt,schema,'win-brief',search=True,timeout=1500)
    if not events:raise RuntimeError('SOURCE_UNAVAILABLE: no web-tool activity was recorded; the win brief cannot be verified')
    b=ws.save(oid,data)
    return {'opportunity_id':oid,'judges':len(b['brief']['judges']),'competitors':len(b['brief']['competitors']),'moves':len(b['brief']['how_we_win']),'changes':b['changes']}
