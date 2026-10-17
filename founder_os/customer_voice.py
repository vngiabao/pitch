"""Customer Voice Scout: what adult children and family caregivers say online about a parent's stories, memory, aging and gifts.

Once a week (Thursday 8:15 Eastern) and on request, a read-only web job reads public threads (Reddit's r/AgingParents,
r/CaregiverSupport, r/Genealogy and r/GiftIdeas, X, Quora, genealogy and senior-care forums) and returns the themes with how many
threads voiced each, short quotes with their URLs, what people tried (Storyworth, Remento, recording apps, nothing), the objections
and what they say they would pay. Every run is kept, so the themes can be compared week to week. The result is evidence about the
market for Pitch Tailor and Pitch Coach, and the objections and words families use for the Campaign Planner and the field-day
script. It never states a fact about A Story, and Fact Guard still blocks every count from it unless it is quoted with its source.
"""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from .store import now,js,uid
from .funding_hunter import FundingHunter

ET=ZoneInfo('America/New_York')
VOICE_REASON='Scout: Customer Voice'
SCHEMA='CREATE TABLE IF NOT EXISTS customer_voice(id TEXT PRIMARY KEY,run_on TEXT NOT NULL,week TEXT NOT NULL,report_json TEXT NOT NULL,sources_json TEXT NOT NULL,queries_json TEXT,created_at TEXT NOT NULL);'
PLACES=('r/AgingParents','r/CaregiverSupport','r/Genealogy','r/GiftIdeas','X','Quora','genealogy forums','senior-care forums')
TRIED=('Storyworth','Remento','recording apps','nothing')


def _s(v,n=400):return (str(v) if v is not None else '')[:n].strip()


def _n(v):
    try:return max(0,int(v))
    except (TypeError,ValueError):return 0


def _url(v):
    u=_s(v,500)
    return u if u.startswith('http') else ''


def _quote(q):
    """A quote keeps only its text, who said it (as the thread shows it) and the URL; a quote with no URL is dropped."""
    if not isinstance(q,dict):return None
    text=_s(q.get('text'),300);url=_url(q.get('url'))
    return {'text':text,'who':_s(q.get('who'),80),'url':url} if text and url else None


def _quotes(xs,limit=4):return [q for q in (_quote(x) for x in (xs or [])[:limit*2]) if q][:limit]


def clean(data):
    """Only the shapes the desk and the agents read, each string bounded, each quote with a URL. Nothing is invented here, only trimmed."""
    themes=[]
    for t in (data.get('themes') or [])[:12]:
        name=_s(t.get('theme'),120)
        if not name:continue
        themes.append({'theme':name,'summary':_s(t.get('summary'),300),'threads':_n(t.get('threads')),'quotes':_quotes(t.get('quotes'))})
    themes.sort(key=lambda t:-t['threads'])
    tried=[{'what':_s(x.get('what'),80),'threads':_n(x.get('threads')),'said':_s(x.get('said'),300),'quote':_quote(x.get('quote'))} for x in (data.get('tried') or [])[:8] if _s(x.get('what'),80)]
    objections=[{'objection':_s(x.get('objection'),200),'threads':_n(x.get('threads')),'quote':_quote(x.get('quote'))} for x in (data.get('objections') or [])[:8] if _s(x.get('objection'),200)]
    objections.sort(key=lambda o:-o['threads'])
    pay=[{'said':_s(x.get('said'),200),'url':_url(x.get('url'))} for x in (data.get('willing_to_pay') or [])[:8] if _s(x.get('said'),200) and _url(x.get('url'))]
    words=[]
    for w in (data.get('words') or [])[:20]:
        w=_s(w,60)
        if w and w.lower() not in {x.lower() for x in words}:words.append(w)
    sources=[]
    for u in (data.get('sources') or [])[:40]:
        u=_url(u)
        if u and u not in sources:sources.append(u)
    for t in themes:
        for q in t['quotes']:
            if q['url'] not in sources:sources.append(q['url'])
    return {'themes':themes,'tried':tried,'objections':objections,'willing_to_pay':pay,'words':words,'sources':sources,
            'places_read':[_s(p,60) for p in (data.get('places_read') or [])[:12] if _s(p,60)],'threads_read':_n(data.get('threads_read'))}


def _key(name):return re.sub(r'[^a-z0-9]+',' ',(name or '').lower()).strip()


def compare(old,new):
    """How the themes moved since the previous run: new, gone, up or down, by threads voiced. Pure over two cleaned reports."""
    if not old:return {'new':[t['theme'] for t in new['themes']],'gone':[],'up':[],'down':[],'same':[],'first':True}
    before={_key(t['theme']):t for t in old['themes']};after={_key(t['theme']):t for t in new['themes']}
    out={'new':[],'gone':[],'up':[],'down':[],'same':[],'first':False}
    for k,t in after.items():
        if k not in before:out['new'].append(t['theme']);continue
        d=t['threads']-before[k]['threads']
        (out['up'] if d>0 else out['down'] if d<0 else out['same']).append({'theme':t['theme'],'from':before[k]['threads'],'to':t['threads']} if d else t['theme'])
    out['gone']=[t['theme'] for k,t in before.items() if k not in after]
    return out


def movement_words(m):
    """One line Bao can read: what is new, what grew, what faded."""
    if not m:return ''
    if m.get('first'):return 'First run; nothing to compare yet.'
    parts=[]
    if m['new']:parts.append('New: '+', '.join(m['new'][:4]))
    if m['up']:parts.append('Up: '+', '.join(f"{x['theme']} ({x['from']} to {x['to']})" for x in m['up'][:4]))
    if m['down']:parts.append('Down: '+', '.join(f"{x['theme']} ({x['from']} to {x['to']})" for x in m['down'][:4]))
    if m['gone']:parts.append('Gone: '+', '.join(m['gone'][:4]))
    return '. '.join(parts)+'.' if parts else 'Same themes as last week.'


QUOTE_SPANS=re.compile(r'[“"]([^”"]{3,400})[”"]')


def cited(text,number,urls):
    """True when the number sits inside a quotation and one of the scout's source URLs is in the same text. That is the only way a count from the threads may appear in a draft."""
    if not text or not urls:return False
    spans=[m.group(1) for m in QUOTE_SPANS.finditer(text)]
    if not any(number in s for s in spans):return False
    return any(u in text for u in urls)


class CustomerVoice:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.db.execute(SCHEMA)

    # ---------- runs and history ----------
    def _row(self,r):
        return {'id':r['id'],'run_on':r['run_on'],'week':r['week'],'report':json.loads(r['report_json']),'sources':json.loads(r['sources_json']),'queries':json.loads(r['queries_json'] or '[]'),'created_at':r['created_at']}

    def runs(self,limit=12):
        return [self._row(r) for r in self.s.rows('SELECT * FROM customer_voice ORDER BY created_at DESC LIMIT ?',(limit,))]

    def latest(self):
        r=self.db.execute('SELECT * FROM customer_voice ORDER BY created_at DESC LIMIT 1').fetchone()
        return self._row(r) if r else None

    def previous(self,before_id):
        """The newest run from an earlier week than the given one, so a second run in the same week compares to last week, not to this morning."""
        cur=self.db.execute('SELECT week FROM customer_voice WHERE id=?',(before_id,)).fetchone()
        if not cur:return None
        r=self.db.execute('SELECT * FROM customer_voice WHERE week<? ORDER BY created_at DESC LIMIT 1',(cur['week'],)).fetchone()
        return self._row(r) if r else None

    def save(self,data,queries=None,instant=None):
        local=(instant or datetime.now(ET)).astimezone(ET);new=clean(data)
        rid=uid('voice');self.db.execute('INSERT INTO customer_voice VALUES(?,?,?,?,?,?,?)',(rid,local.date().isoformat(),local.strftime('%G-W%V'),js(new),js(new['sources']),js([_s(q,200) for q in (queries or [])[:12]]),now()))
        prev=self.previous(rid);m=compare(prev['report'] if prev else None,new)
        self.s.log('customer_voice.saved','research_worker',{'id':rid,'themes':len(new['themes']),'threads_read':new['threads_read'],'new':m['new'][:6],'gone':m['gone'][:6]})
        return self.current()

    def researching(self):
        return bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(VOICE_REASON,)).fetchone())

    def request(self,manual=True):
        stamp=datetime.now(ET).strftime('%Y-%m-%dT%H%M') if manual else datetime.now(ET).date().isoformat()
        return self.h.request_run(VOICE_REASON,key='scout-customer_voice-'+stamp)

    def current(self):
        """What the Growth desk shows: this week's themes, counts, quotes and links, and how they moved since last week."""
        cur=self.latest()
        if not cur:return {'report':None,'run_on':None,'week':None,'movement':None,'movement_words':'','previous_on':None,'runs':0,'researching':self.researching()}
        prev=self.previous(cur['id']);m=compare(prev['report'] if prev else None,cur['report'])
        return {'report':cur['report'],'run_on':cur['run_on'],'week':cur['week'],'movement':m,'movement_words':movement_words(m),'previous_on':prev['run_on'] if prev else None,
                'runs':self.db.execute('SELECT COUNT(*) FROM customer_voice').fetchone()[0],'queries':cur['queries'],'researching':self.researching()}

    def summary(self):
        r=self.db.execute('SELECT COUNT(*) n,MAX(created_at) at FROM customer_voice').fetchone();cur=self.latest()
        return {'runs':r['n'],'last_checked':r['at'],'themes':len(cur['report']['themes']) if cur else 0,'running':self.researching()}

    # ---------- what the agents read ----------
    def for_agents(self):
        """For Pitch Tailor and Pitch Coach: themes with counts and two quotes each. Evidence about the market, never about A Story."""
        cur=self.latest()
        if not cur:return None
        r=cur['report']
        return {'as_of':cur['run_on'],'threads_read':r['threads_read'],'places_read':r['places_read'],
                'themes':[{'theme':t['theme'],'threads':t['threads'],'summary':t['summary'],'quotes':[{'text':q['text'],'url':q['url']} for q in t['quotes'][:2]]} for t in r['themes'][:8]],
                'tried':[{'what':x['what'],'threads':x['threads'],'said':x['said']} for x in r['tried']],
                'objections':[{'objection':o['objection'],'threads':o['threads']} for o in r['objections'][:6]],
                'willing_to_pay':[x['said'] for x in r['willing_to_pay'][:5]],
                'note':'Public comments by adult children and caregivers, read by the Customer Voice Scout on '+cur['run_on']+'. They describe the market and what families tried, never A Story; take no fact about A Story from them. '
                       'A thread count may appear in a draft only as a quoted figure with its URL beside it, for example “14 of 60 threads” (https://...); otherwise do not say the number.'}

    def for_field_day(self):
        """For the Campaign Planner and the field-day script: the top objections and the words families use, each objection with one quote and its URL."""
        cur=self.latest()
        if not cur:return None
        r=cur['report']
        return {'as_of':cur['run_on'],'objections':[{'objection':o['objection'],'threads':o['threads'],'quote':o['quote']['text'] if o['quote'] else '','url':o['quote']['url'] if o['quote'] else ''} for o in r['objections'][:5]],
                'words':r['words'][:12],'tried':[x['what'] for x in r['tried'][:4]],
                'note':'Objections and words from public threads, not from A Story customers. Answer the objections in Bao’s words; never claim a family said this about A Story.'}

    def source_urls(self):
        cur=self.latest()
        return cur['sources'] if cur else []

    # ---------- the research job ----------
    def context(self):
        prev=self.latest()
        return {'today':datetime.now(ET).date().isoformat(),'places':list(PLACES),'tried_options':list(TRIED),'previous_themes':[t['theme'] for t in prev['report']['themes']] if prev else [],
                'task':'Read public threads from the last 90 days where adult children and family caregivers talk about a parent’s or grandparent’s stories, memory, aging, legacy and gifts: '
                       'wanting to record a parent’s life, regret after a death, dementia and memory loss, what to give a parent who has everything, Storyworth and Remento experiences, recording apps and voice memos, and doing nothing. '
                       'Report the themes people voice, with how many distinct threads voiced each (count threads, not comments), one short representative quote per theme with its URL and the poster as the thread shows it (a username is fine); '
                       'what people tried (Storyworth, Remento, recording apps, nothing) with how many threads and what they said about it; the objections people raise to any such product or to asking a parent (price, the parent will not talk, privacy, who hears it, a robot, too late), each with a quote and URL; '
                       'what people say they would pay or did pay, quoted with the URL; and the exact words and phrases families use for the problem (ten to twelve short phrases). '
                       'If previous_themes exists, use the same theme names where the theme is the same so weeks can be compared, and add new ones only when the threads show them. '
                       'Quote only public text, at most 300 characters each, never a full name of a private person, never an email or phone number. Every quote needs the URL of its thread. Never invent a thread, a quote, a count or a price. '
                       'Nothing here is about A Story and you must not state anything about A Story.'}


def handles(reason):return reason==VOICE_REASON


def run(h,request,codex_json):
    """One bounded public-web research job. Web search is required; a run with no web activity is rejected."""
    cv=CustomerVoice(h.store);ctx=cv.context()
    S=lambda:{'type':'string'}
    obj=lambda props:{'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
    quote=obj({'text':S(),'who':S(),'url':S()})
    schema=obj({'themes':{'type':'array','items':obj({'theme':S(),'summary':S(),'threads':{'type':'integer'},'quotes':{'type':'array','items':quote}})},
                'tried':{'type':'array','items':obj({'what':S(),'threads':{'type':'integer'},'said':S(),'quote':quote})},
                'objections':{'type':'array','items':obj({'objection':S(),'threads':{'type':'integer'},'quote':quote})},
                'willing_to_pay':{'type':'array','items':obj({'said':S(),'url':S()})},
                'words':{'type':'array','items':S()},'places_read':{'type':'array','items':S()},'threads_read':{'type':'integer'},
                'sources':{'type':'array','items':S()},'queries':{'type':'array','items':S()},'errors':{'type':'array','items':obj({'message':S()})}})
    prompt=('You are A Story Founder OS Customer Voice Scout, a READ-ONLY research worker. Use ONLY public web search and public page reads. Do not use shell, file, email, form, account or posting tools. Never log in, vote, post or reply anywhere. '
            +ctx['task']+' Use at most 12 search queries and read at most 24 pages. Report at most 10 themes, 6 objections, 8 willing-to-pay statements. Keep every field short and specific. Return JSON matching the schema.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
    data,events=codex_json(h,request,prompt,schema,'customer-voice',search=True,timeout=1500)
    if not events:raise RuntimeError('SOURCE_UNAVAILABLE: no web-tool activity was recorded; what families say cannot be verified')
    cur=cv.save(data,data.get('queries'))
    return {'themes':len(cur['report']['themes']),'threads_read':cur['report']['threads_read'],'new':cur['movement']['new'][:6],'gone':cur['movement']['gone'][:6]}
