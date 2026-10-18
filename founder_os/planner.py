"""Planner: on request, a report that answers Bao's question from everything the desks know, as a PDF in his own identity.

It gathers the state of every desk (what needs him, money ranked per hour, deals, campaigns, channel math, scouts, win
briefs, pitch editions, measured facts), asks the model to answer the question and lay out a dated plan, lists the
questions only Bao can answer, and renders the result in "The Turn" (navy, paper, brass, maize; Brygada 1918 and Mona
Sans). A weekly plan writes itself on Monday morning; any other report is written when he asks. Nothing here sends.
"""
import html,json,os,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .store import now,js,uid
from .funding_hunter import FundingHunter

ET=ZoneInfo('America/New_York')
ROOT=Path(__file__).resolve().parents[1]
PLAN_PREFIX='Plan report: '
DEFAULT_QUESTION='Where are we this week, what should I do first, and what do you need from me?'
OWNERS=('Bao','Daniel','agents')
SCHEMA='CREATE TABLE IF NOT EXISTS planner_reports(id TEXT PRIMARY KEY,question TEXT NOT NULL,state TEXT NOT NULL,title TEXT,report_json TEXT,html_path TEXT,pdf_path TEXT,error TEXT,auto INTEGER NOT NULL DEFAULT 0,week TEXT,created_at TEXT NOT NULL,finished_at TEXT);'
# Bao's identity for everything hosted on gbaonvo: The Turn.
THEME={'navy':'#00274c','navy2':'#0d3a66','ink':'#1b2733','paper':'#f5f1e8','paper2':'#ede6d8','soft':'#fbf9f4','stone':'#d9d0bf','muted':'#5c6670','brass':'#b58420','brass_text':'#7a5612','maize':'#e8c064','maize_wash':'#f6ecd0','urgent':'#8c3a22','good':'#2f6b4a'}


# The model sees the desks as CONTEXT.state keys; Bao reads desk names.
SOURCE_WORDS=(('state.today_brief','Today brief'),('state.win_briefs','Win brief'),('state.pitch_lab','Pitch Lab'),('state.growth.channel_math','Channel math'),('state.growth.campaigns','Campaigns'),
              ('state.growth','Deals board'),('state.reservation_drive','Reservation drive'),('state.measured_retention','Families page'),('state.credits_and_costs','Credits page'),('state.scouts','Scouts'),
              ('state.assumptions','Assumptions'),('state.customer_voice','Customer voice'),('state.found_this_week','Funding pipeline'),('state.agent_runs','Agent activity'),('state.','Founder OS '))


def plain_sources(text):
    for k,v in SOURCE_WORDS:text=text.replace(k,v)
    return re.sub(r'(Today brief|Win brief|Pitch Lab|Channel math|Campaigns|Deals board|Reservation drive|Families page|Credits page|Scouts|Assumptions|Customer voice|Funding pipeline|Agent activity)(\.[\w]+)+',r'\1',text)


AGENT_NAMES=(('Scout: ',None),('Daily free credits discovery','Credits Scout'),('Partner and deal discovery','Partner Scout'),('Press and gift-guide discovery','Press Scout'),
             ('Win brief','Win Scout'),('Plan report','Planner'),('Campaign plan','Campaign Planner'),('Draft deal note','Deal Drafter'),('Draft follow-up','Follow-up Drafter'),
             ('Draft press pitch','Press Drafter'),('Draft application','Application Drafter'),('Due program re-verifications','Funding Hunter'),('Scheduled broad discovery','Funding Hunter'),
             ('Manual broad discovery','Funding Hunter'),('Research opportunity','Funding Hunter'),('Assumption','Assumption Coach'),('Pipeline',''))


def agent_name(reason):
    """The name an agent has on the Scouts page; empty for orchestration jobs that are not an agent of their own."""
    for prefix,name in AGENT_NAMES:
        if reason.startswith(prefix):
            if name is None:return reason[len(prefix):].split(':')[0].strip()+' Scout'
            return name
    return reason.split(':')[0][:40]


def words(text,cap):
    """Keep a line to cap words: the first sentence when it fits, otherwise the first cap words."""
    t=' '.join(str(text or '').split())
    if len(t.split())<=cap:return t
    first=re.split(r'(?<=[.!?])\s+',t)[0]
    if len(first.split())<=cap:return first
    return ' '.join(t.split()[:cap]).rstrip(',;:')+'…'


def _s(v,cap=40):return plain_sources(words(v,cap))


def clean(data):
    """An executive brief: a conclusion, three moves, the decisions only Bao can make, a few numbers. Every line has a word limit."""
    owner=lambda x:x.get('owner') if x.get('owner') in OWNERS else 'Bao'
    return {'title':_s(data.get('title'),9) or 'Plan','bottom_line':_s(data.get('bottom_line'),45),
            'moves':[{'what':_s(x.get('what'),16),'by':_s(x.get('by'),6),'owner':owner(x),'why':_s(x.get('why'),14)} for x in (data.get('moves') or [])[:3] if _s(x.get('what'))],
            'decisions':[{'decision':_s(x.get('decision'),16),'recommend':_s(x.get('recommend'),14),'unblocks':_s(x.get('unblocks'),10)} for x in (data.get('decisions') or [])[:5] if _s(x.get('decision'))],
            'numbers':[{'label':_s(x.get('label'),6),'value':_s(x.get('value'),5),'source':_s(x.get('source'),5)} for x in (data.get('numbers') or [])[:4] if _s(x.get('label'))],
            'by_agent':[{'agent':_s(x.get('agent'),4),'result':_s(x.get('result'),14),'needs':_s(x.get('needs'),10)} for x in (data.get('by_agent') or [])[:10] if _s(x.get('agent'))],
            'risks':[_s(r,16) for r in (data.get('risks') or [])[:3] if _s(r)],
            'later':[{'what':_s(x.get('what'),14),'by':_s(x.get('by'),6),'owner':owner(x)} for x in (data.get('later') or [])[:6] if _s(x.get('what'))]}


class Planner:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.db.execute(SCHEMA)

    # ---------- what the planner reads: every desk, each guarded so one failure never blanks the report ----------
    def gather(self):
        state={'today':datetime.now(ET).strftime('%A, %B %d, %Y'),'founder_os':'https://pitch.gbaonvo.com'};errors=[]
        def part(name,fn):
            try:state[name]=fn()
            except Exception as e:errors.append(name+': '+type(e).__name__)
        def brief():
            from .report_email import DailyReporter
            from .application_pilot import ApplicationPilot
            instant=datetime.now(timezone.utc);d=DailyReporter(self.s).digest(instant,instant.astimezone(ET),self.h.dashboard(),ApplicationPilot(self.s).dashboard())
            return {k:d.get(k) for k in ('summary','needs_you','apply_first','cash','credits','waiting','access')}
        part('today_brief',brief)
        def growth():
            from .growth_desk import GrowthDesk
            b=GrowthDesk(self.s).board()
            return {'deal_counts':b['counts'],'pipeline_value':b['pipeline_value'],'won_value':b['won_value'],'due':[{'name':d['name'],'next_step':d['next_step'],'next_on':d['next_on']} for d in b['due'][:6]],
                    'notes_ready_to_send':[d['name'] for d in b['ready_to_send'][:8]],'open_deals':[{'name':d['name'],'kind':d['kind'],'stage':d['stage']} for s in b['stages'] for d in s['deals'] if d['open']][:15],
                    'campaigns':[{'title':c['title'],'state':c['state'],'goal':(c['plan'] or {}).get('goal'),'open_questions':(c['plan'] or {}).get('open_questions',[]),'field_day':c.get('field')} for c in b['campaigns']],
                    'channel_math':{'totals':b['math']['totals'],'measured':b['measured'],'deck_formula':b['math']['deck_formula']}}
        part('growth',growth)
        def scouts():
            from .scouts import Scouts
            return [{'name':x['name'],'hunts':x['hunts'][:120],'last_run':x['last_run'],'next_run':x['next_run'],'running':x['running']} for x in Scouts(self.s).status()['scouts']]
        part('scouts',scouts)
        def wins():
            from .win_scout import WinScout
            ws=WinScout(self.s);out=[]
            for r in self.s.rows('SELECT opportunity_id,checked_at FROM win_briefs ORDER BY updated_at DESC LIMIT 8'):
                try:name=self.h.detail(r['opportunity_id'])['data']['canonical_name']
                except ValueError:continue
                b=ws.brief(r['opportunity_id']);bb=b['brief'] or {}
                out.append({'program':name,'checked_at':r['checked_at'],'how_we_win':[m['move'] for m in bb.get('how_we_win',[])[:5]],'unstated':[u['insight'] for u in bb.get('unstated',[])[:3]],'open_questions':bb.get('open_questions',[]),'rules':{k:v for k,v in bb.get('rules',{}).items() if v and 'not published' not in v.lower()},'changes':b['changes']})
            return out
        part('win_briefs',wins)
        def lab():
            from .pitch_lab import PitchLab
            lab=PitchLab(self.s);out=[]
            for it in lab.items(kinds=('PITCH_EDITION','PITCH_REVIEW','APPLICATION_SET'),limit=12):
                if it['stage'] in ('ARCHIVED',):continue
                p=it['payload'];b=p.get('brief') or {};c=it.get('coach') or {}
                out.append({'title':it['title'],'kind':it['kind'],'stage':it['stage'],'round':it['round'],'open_questions':b.get('open_questions',[])[:6],'unresolved':[u.get('text') for u in (p.get('unresolved') or [])][:4],
                            'coach_summary':c.get('summary'),'top_fixes':c.get('top_fixes',[])[:3],'timing':p.get('timing'),'url':'/pitch-lab/'+it['id']})
            return out
        part('pitch_lab',lab)
        def product():
            from .product_desk import ProductDesk
            return ProductDesk(self.s).measured_facts()
        part('measured_retention',product)
        def drive():
            from .reservation_drive import ReservationDrive
            b=ReservationDrive(self.s).board();return {k:v for k,v in b.items() if k in ('counts','days_left','reservations','referrals','sent','total','deadline')} or b
        part('reservation_drive',drive)
        def credits():
            from .growth_agents import Growth
            from .scouts import Scouts
            st=Scouts(self.s).stack()
            return {'credits':[{'provider':c['provider'],'label':c['label'],'level':c['level']} for c in Growth(self.s).credits()],'monthly_uncovered':st['monthly_uncovered'],'monthly_covered':st['monthly_covered'],'uncovered_items':[r['item'] for r in st['items'] if not r['covered_by']]}
        part('credits_and_costs',credits)
        def assumptions():
            if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='assumptions'").fetchone():return None
            return self.s.rows('SELECT * FROM assumptions LIMIT 30')
        part('assumptions',assumptions)
        def voice():
            from .customer_voice import CustomerVoice
            c=CustomerVoice(self.s).current();rep=c.get('report') or {}
            return {'run_on':c.get('run_on'),'movement_words':c.get('movement_words'),'themes':[{k:t.get(k) for k in ('theme','count','quotes')} for t in (rep.get('themes') or [])[:6]],'objections':(rep.get('objections') or [])[:5],'willing_to_pay':rep.get('willing_to_pay')} if rep else None
        part('customer_voice',voice)
        def found():
            # What the scouts and the sweep added to the pipeline in the last seven days, with where each one landed.
            from .money_map import classify,CATEGORIES
            titles=dict((k,t) for k,t,_ in CATEGORIES);out=[]
            for d in self.h.list('All'):
                r=self.db.execute('SELECT discovered_at FROM funding_intelligence WHERE opportunity_id=?',(d['opportunity_id'],)).fetchone()
                if not r or not r['discovered_at'] or (datetime.now(timezone.utc)-datetime.fromisoformat(r['discovered_at'].replace('Z','+00:00'))).days>7:continue
                m=d['analysis']['money']
                out.append({'name':d['data']['canonical_name'],'group':titles.get(classify(d),'Other'),'amount':m.get('cash_max') or m.get('credits_face_value'),'deadline':d['data']['dates'].get('deadline'),'recommendation':d['recommendation'],'found_on':r['discovered_at'][:10]})
            return sorted(out,key=lambda x:x['found_on'],reverse=True)[:40]
        part('found_this_week',found)
        def runs():
            # Every agent job that finished in the last seven days, by agent, with failures named.
            rows=self.s.rows("SELECT reason,state,last_error,created_at FROM hunter_requests WHERE created_at>=datetime('now','-7 days') ORDER BY created_at DESC LIMIT 300");by={}
            for r in rows:
                agent=agent_name(r['reason'])
                if not agent:continue
                a=by.setdefault(agent,{'agent':agent,'runs':0,'complete':0,'queued':0,'failed':0,'last':None})
                a['runs']+=1;a['last']=a['last'] or r['created_at']
                if r['state']=='COMPLETE':a['complete']+=1
                elif r['state'] in ('QUEUED','RUNNING'):a['queued']+=1
                elif r['last_error']:a['failed']+=1
            words_for={'TAILOR':'Pitch Tailor','FACT_GUARD':'Fact Guard','VOICE':"Bao's Voice",'COACH':'Pitch Coach','FORMAT':'Format Check','BUILDER':'Edition Builder','SLIDE_QA':'Slide QA','LEARNER':'Outcome Learner'}
            for r in self.s.rows("SELECT agent,verdict,created_at FROM work_reviews WHERE created_at>=datetime('now','-7 days') AND agent!='OWNER' ORDER BY created_at DESC"):
                name='Pitch Lab';a=by.setdefault(name,{'agent':name,'runs':0,'complete':0,'queued':0,'failed':0,'last':None,'by_step':{}})
                step=words_for.get(r['agent'],r['agent'].title());a['runs']+=1;a['complete']+=1;a['last']=a['last'] or r['created_at']
                a['by_step'].setdefault(step,{});a['by_step'][step][r['verdict']]=a['by_step'][step].get(r['verdict'],0)+1
            return sorted(by.values(),key=lambda a:-a['runs'])
        part('agent_runs',runs)
        state['gather_errors']=errors
        return state

    def open_questions(self,state):
        """Everything the agents have already asked Bao for and not received, in one list."""
        q=[]
        for it in state.get('pitch_lab') or []:q+=[f"{it['title']}: {x}" for x in it.get('open_questions',[])]+[f"{it['title']} (unresolved): {x}" for x in it.get('unresolved',[]) if x]
        for c in (state.get('growth') or {}).get('campaigns',[]):q+=[f"{c['title']}: {x}" for x in c.get('open_questions',[])]
        for w in state.get('win_briefs') or []:q+=[f"{w['program']}: {x}" for x in w.get('open_questions',[])]
        seen=set();out=[]
        for x in q:
            k=x.lower()[:80]
            if k not in seen:seen.add(k);out.append(x[:300])
        return out[:20]

    # ---------- requests and records ----------
    def ask(self,question='',auto=False,week=None):
        question=(question or '').strip()[:600] or DEFAULT_QUESTION
        rid=uid('plan');self.db.execute('INSERT INTO planner_reports(id,question,state,auto,week,created_at) VALUES(?,?,?,?,?,?)',(rid,question,'QUEUED',1 if auto else 0,week,now()))
        self.h.request_run(PLAN_PREFIX+rid,key='plan-'+rid);self.s.log('planner.asked','owner' if not auto else 'planner',{'id':rid,'auto':auto})
        return self.report(rid)

    def report(self,rid):
        r=self.s.one('SELECT * FROM planner_reports WHERE id=?',(rid,));r['report']=json.loads(r['report_json']) if r['report_json'] else None;r.pop('report_json')
        r['pdf_url']='/plan/'+rid+'.pdf' if r['pdf_path'] and Path(r['pdf_path']).exists() else None;r['html_url']='/plan/'+rid+'.html' if r['html_path'] and Path(r['html_path']).exists() else None
        return r

    def reports(self,limit=20):
        rows=[self.report(r['id']) for r in self.s.rows('SELECT id FROM planner_reports ORDER BY created_at DESC LIMIT ?',(limit,))]
        latest=next((r for r in rows if r['state']=='READY'),None)
        return {'items':[{k:v for k,v in r.items() if k!='report'} for r in rows],'latest':latest,'default_question':DEFAULT_QUESTION,'writing':any(r['state']=='QUEUED' for r in rows)}

    def file(self,rid,kind):
        r=self.s.one('SELECT html_path,pdf_path FROM planner_reports WHERE id=?',(rid,));p=r['pdf_path'] if kind=='pdf' else r['html_path']
        if not p or not Path(p).exists():raise ValueError('That report has no '+kind.upper()+' yet')
        return Path(p)

    def fail(self,rid,error):
        self.db.execute('UPDATE planner_reports SET state=?,error=?,finished_at=? WHERE id=?',('FAILED',str(error)[:400],now(),rid))

    def save(self,rid,data,state):
        r=self.s.one('SELECT question,created_at FROM planner_reports WHERE id=?',(rid,));rep=clean(data)
        if not rep['decisions']:rep['decisions']=[{'decision':_s(q,16),'recommend':'needs your input','unblocks':''} for q in self.open_questions(state)[:5]]
        page=render_html(rep,r['question'],datetime.now(ET));paths=write_files(rid,page)
        self.db.execute('UPDATE planner_reports SET state=?,title=?,report_json=?,html_path=?,pdf_path=?,error=NULL,finished_at=? WHERE id=?',('READY',rep['title'],js(rep),str(paths['html']),str(paths['pdf']) if paths['pdf'] else None,now(),rid))
        self.s.log('planner.report_ready','research_worker',{'id':rid,'pdf':bool(paths['pdf'])});return self.report(rid)

    def latest_for_brief(self,founder_url=lambda p:p):
        r=self.db.execute("SELECT id,title,finished_at FROM planner_reports WHERE state='READY' ORDER BY finished_at DESC LIMIT 1").fetchone()
        return {'title':r['title'],'url':founder_url('/plans'),'pdf':founder_url('/plan/'+r['id']+'.pdf'),'when':r['finished_at'][:10]} if r else None

    def poll(self,instant=None):
        """The weekly plan writes itself on Monday after 7:00 Eastern, once per week."""
        local=(instant or datetime.now(ET)).astimezone(ET)
        if local.weekday()!=0 or local.hour<7:return {'queued':False}
        week=local.strftime('%G-%V')
        if self.db.execute('SELECT 1 FROM planner_reports WHERE auto=1 AND week=?',(week,)).fetchone():return {'queued':False}
        self.ask(DEFAULT_QUESTION,auto=True,week=week);return {'queued':True,'week':week}

    def context(self,rid):
        r=self.s.one('SELECT question FROM planner_reports WHERE id=?',(rid,));state=self.gather()
        return {'question':r['question'],'state':state,'already_asked_of_bao':self.open_questions(state),
                'task':('You are the Planner for A Story Founder OS. Write a one-page brief for a busy founder that answers CONTEXT.question using ONLY CONTEXT.state. '
                        'Hard limits. title: up to 9 words, states the conclusion, not the topic. bottom_line: the answer in 1 or 2 sentences, up to 45 words, conclusion first. '
                        'moves: the 3 things that matter most this week, each one action of up to 16 words that starts with a verb, with by (a date or "today", up to 6 words), owner (Bao, Daniel or agents) and why (up to 14 words). '
                        'decisions: up to 5 decisions only Bao can make, ordered by how much work each unblocks; each a question of up to 16 words; recommend is the option you would pick from the evidence in up to 14 words, or "needs your input" when CONTEXT gives no basis; unblocks says what moves once decided, up to 10 words. Merge related asks into one decision and never ask for the same fact twice; already_asked_of_bao lists what the agents have asked. '
                        'numbers: up to 4 figures that change a decision, value short, source named as a desk; leave out anything not recorded rather than showing it as a number. '
                        'by_agent: fill only when the question asks about agents or the week\'s work; at most 10 rows, agents that need Bao first; one row per agent named as in agent_runs (Pitch Lab is one row covering Tailor, Fact Guard, Voice, Coach, Builder and Slide QA); result is what it produced in up to 14 words with counts, taking what each scout found from CONTEXT.state.scouts; needs is what it needs from Bao in up to 10 words or empty. '
                        'risks: up to 3, each up to 16 words. later: up to 6 further moves, short. '
                        'Write like a chief of staff talking: plain words, short sentences, no staging ("not X but Y", "here is the thing"), no triads for rhythm, no stacked hedges, no em dashes. '
                        'Name sources as desks (Today brief, Deals board, Win brief for Columbus, Pitch Lab, Channel math), never as field paths or "state.". '
                        'Address Bao as you. When desks disagree, trust the more specific check (a Pitch Lab review over a Today brief count) and say which. When a check has no record, write "not recorded", never "did not run". Never invent a program, a number, a person or a date.')},state


def render_html(rep,question,when):
    E=lambda s:html.escape(str(s or ''),quote=False);T=THEME;fonts=(ROOT/'founder_os'/'ui'/'fonts')
    face=lambda name,file,weight:f"@font-face{{font-family:'{name}';src:url('{(fonts/file).as_uri()}') format('woff2');font-weight:{weight}}}"
    css=f"""{face('Mona Sans','mona-sans.woff2','200 900')}{face('Brygada 1918','brygada-1918.woff2','400 700')}
@page{{size:Letter;margin:0.5in 0.55in 0.6in}}*{{box-sizing:border-box}}
body{{margin:0;background:{T['paper']};color:{T['ink']};font-family:'Mona Sans','Helvetica Neue',Arial,sans-serif;font-size:10.5pt;line-height:1.45}}
.band{{background:{T['navy']};color:{T['paper']};padding:18px 26px 16px;border-bottom:4px solid {T['brass']}}}
.kicker{{font-size:8.5pt;letter-spacing:.14em;text-transform:uppercase;color:{T['maize']};margin:0 0 5px}}
.band h1{{font-family:'Brygada 1918',Georgia,serif;font-weight:400;font-size:21pt;line-height:1.15;margin:0;letter-spacing:-.01em}}
.wrap{{padding:16px 26px 20px}}
.q{{font-size:9pt;color:{T['muted']};margin:0 0 12px}}
.bl{{background:{T['maize_wash']};border-left:5px solid {T['brass']};border-radius:0 8px 8px 0;padding:12px 16px;margin:0 0 16px}}
.bl p{{font-family:'Brygada 1918',Georgia,serif;font-size:14pt;line-height:1.35;margin:0;color:{T['navy']}}}
h2{{font-size:8.5pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:{T['brass_text']};margin:16px 0 8px}}
ol.moves{{list-style:none;margin:0;padding:0;counter-reset:m}}
ol.moves li{{counter-increment:m;display:grid;grid-template-columns:28px 1fr;gap:2px 10px;padding:8px 0;border-bottom:1px solid {T['stone']}}}
ol.moves li::before{{content:counter(m);grid-row:span 2;width:24px;height:24px;border-radius:12px;background:{T['navy']};color:{T['paper']};font-weight:700;font-size:10pt;display:flex;align-items:center;justify-content:center}}
.what{{font-weight:600;font-size:11pt}}.meta{{font-size:9pt;color:{T['muted']}}}.meta b{{color:{T['brass_text']};font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:9.5pt}}
th{{text-align:left;font-weight:600;font-size:8pt;letter-spacing:.08em;text-transform:uppercase;color:{T['muted']};padding:5px 8px;border-bottom:2px solid {T['stone']}}}
td{{padding:6px 8px;border-bottom:1px solid {T['stone']};vertical-align:top}}
td.rec{{color:{T['brass_text']};font-weight:600}}td.agent{{white-space:nowrap;font-weight:600}}td.small{{color:{T['muted']}}}
.numbers{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.num{{background:{T['soft']};border:1px solid {T['stone']};border-radius:8px;padding:8px 10px}}
.num b{{display:block;font-family:'Brygada 1918',Georgia,serif;font-weight:400;font-size:16pt;color:{T['navy']};line-height:1.1}}
.num span{{font-size:8.5pt;color:{T['muted']}}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.two ul{{margin:0;padding-left:16px;font-size:9.5pt}}.two li{{margin:0 0 4px}}
.foot{{margin-top:16px;padding-top:6px;border-top:1px solid {T['stone']};font-size:8pt;color:{T['muted']};display:flex;justify-content:space-between}}
"""
    moves=''.join(f"<li><div class='what'>{E(m['what'])}</div><div class='meta'><b>{E(m['owner'])}</b>{(' · '+E(m['by'])) if m['by'] else ''}{(' · '+E(m['why'])) if m['why'] else ''}</div></li>" for m in rep['moves'])
    dec=''.join(f"<tr><td>{E(d['decision'])}</td><td class='rec'>{E(d['recommend'])}</td><td class='small'>{E(d['unblocks'])}</td></tr>" for d in rep['decisions'])
    nums=''.join(f"<div class='num'><b>{E(n['value'])}</b><span>{E(n['label'])}{(' · '+E(n['source'])) if n['source'] else ''}</span></div>" for n in rep['numbers'])
    agents=''.join(f"<tr><td class='agent'>{E(a['agent'])}</td><td>{E(a['result'])}</td><td class='small'>{E(a['needs'])}</td></tr>" for a in rep['by_agent'])
    risks=''.join(f"<li>{E(r)}</li>" for r in rep['risks']);later=''.join(f"<li>{E(x['what'])}<span class='meta'> · {E(x['owner'])}{(' · '+E(x['by'])) if x['by'] else ''}</span></li>" for x in rep['later'])
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{E(rep['title'])}</title><style>{css}</style></head><body>"
            f"<div class='band'><p class='kicker'>A Story · Planner · {E(when.strftime('%B %d, %Y').replace(' 0',' '))}</p><h1>{E(rep['title'])}</h1></div><div class='wrap'><p class='q'>You asked: {E(question)}</p>"
            +(f"<div class='bl'><p>{E(rep['bottom_line'])}</p></div>" if rep['bottom_line'] else '')
            +(f"<h2>This week</h2><ol class='moves'>{moves}</ol>" if moves else '')
            +(f"<h2>Decide</h2><table><thead><tr><th>Decision</th><th>Recommended</th><th>Unblocks</th></tr></thead><tbody>{dec}</tbody></table>" if dec else '')
            +(f"<h2>Numbers</h2><div class='numbers'>{nums}</div>" if nums else '')
            +(f"<h2>By agent</h2><table><thead><tr><th>Agent</th><th>Result</th><th>Needs you</th></tr></thead><tbody>{agents}</tbody></table>" if agents else '')
            +(f"<div class='two'>{('<div><h2>Risks</h2><ul>'+risks+'</ul></div>') if risks else '<div></div>'}{('<div><h2>Later</h2><ul>'+later+'</ul></div>') if later else ''}</div>" if risks or later else '')
            +f"<div class='foot'><span>From every Founder OS desk. Numbers carry their source; nothing is sent or submitted.</span><span>pitch.gbaonvo.com/plans</span></div></div></body></html>")


def write_files(rid,page,timeout=120):
    out=ROOT/'reports'/'plans';out.mkdir(parents=True,exist_ok=True)
    html_path=out/(rid+'.html');html_path.write_text(page,encoding='utf-8');pdf_path=out/(rid+'.pdf')
    from .slide_deck import find_browser
    browser=find_browser();pdf=None
    if browser and os.environ.get('FOUNDER_OS_PDF','on')!='off':
        try:
            subprocess.run([browser,'--headless=new','--disable-gpu','--no-pdf-header-footer','--allow-file-access-from-files','--print-to-pdf='+str(pdf_path),html_path.as_uri()],capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if pdf_path.exists() and pdf_path.stat().st_size>1000:pdf=pdf_path
        except (subprocess.SubprocessError,OSError):pdf=None
    return {'html':html_path,'pdf':pdf}


def handles(reason):return reason.startswith(PLAN_PREFIX)


def run(h,request,codex_json):
    pl=Planner(h.store);rid=request['reason'][len(PLAN_PREFIX):]
    try:
        ctx,state=pl.context(rid)
        S=lambda:{'type':'string'}
        own={'type':'string','enum':list(OWNERS)}
        o=lambda **props:{'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
        schema=o(title=S(),bottom_line=S(),moves={'type':'array','items':o(what=S(),by=S(),owner=own,why=S())},decisions={'type':'array','items':o(decision=S(),recommend=S(),unblocks=S())},
                 numbers={'type':'array','items':o(label=S(),value=S(),source=S())},by_agent={'type':'array','items':o(agent=S(),result=S(),needs=S())},risks={'type':'array','items':S()},
                 later={'type':'array','items':o(what=S(),by=S(),owner=own)})
        prompt=ctx['task']+' Do not use shell, files, web, email or any tool. Return JSON matching the schema.\nCONTEXT:\n'+json.dumps({k:v for k,v in ctx.items() if k!='task'},ensure_ascii=False,default=str)
        data,_=codex_json(h,request,prompt,schema,'plan')
        r=pl.save(rid,data,state);return {'report':rid,'title':r['title'],'pdf':bool(r['pdf_url']),'moves':len(r['report']['moves']),'decisions':len(r['report']['decisions'])}
    except Exception as e:
        pl.fail(rid,e);raise
