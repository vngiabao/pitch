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
              ('state.assumptions','Assumptions'),('state.customer_voice','Customer voice'),('state.','Founder OS '))


def plain_sources(text):
    for k,v in SOURCE_WORDS:text=text.replace(k,v)
    return re.sub(r'(Today brief|Win brief|Pitch Lab|Channel math|Campaigns|Deals board|Reservation drive|Families page|Credits page|Scouts|Assumptions|Customer voice)(\.[\w]+)+',r'\1',text)


def _s(v,n=600):return plain_sources((str(v) if v is not None else '')[:n].strip())


def clean(data):
    return {'title':_s(data.get('title'),140) or 'Plan','answer':[_s(p,1200) for p in (data.get('answer') or [])[:8] if _s(p)],
            'plan':[{'when':_s(x.get('when'),60),'what':_s(x.get('what'),300),'why':_s(x.get('why'),300),'owner':x.get('owner') if x.get('owner') in OWNERS else 'Bao','link':_s(x.get('link'),300)} for x in (data.get('plan') or [])[:14] if _s(x.get('what'))],
            'numbers':[{'label':_s(x.get('label'),80),'value':_s(x.get('value'),60),'source':_s(x.get('source'),160)} for x in (data.get('numbers') or [])[:8] if _s(x.get('label'))],
            'questions_for_bao':[_s(q,300) for q in (data.get('questions_for_bao') or [])[:10] if _s(q)],'risks':[_s(r,300) for r in (data.get('risks') or [])[:6] if _s(r)]}


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
        if not rep['questions_for_bao']:rep['questions_for_bao']=self.open_questions(state)[:8]
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
                'task':'You are the Planner for A Story Founder OS. Answer CONTEXT.question for Bao using ONLY CONTEXT.state. Write like a sharp chief of staff: plain sentences, no staging ("not X but Y", "here is the thing"), no triads for rhythm, no inflated words, no em dashes, no bold labels. '
                       'answer: 2 to 5 short paragraphs that answer the question directly, numbers only from CONTEXT with their source. plan: the dated next moves in order (when, what, why, who: Bao, Daniel or agents, link from CONTEXT when one applies), at most 10, the first three being what matters most this week. '
                       'Name a source by its desk in plain words (Today brief, Deals board, Win brief for Columbus, Pitch Lab, Channel math), never by a field path, and never write "state." in the report. '
                       'numbers: up to 6 figures that frame the week, each with its source. questions_for_bao: the decisions and facts only he can supply, drawn from already_asked_of_bao and the state, each one sentence, no duplicates. risks: up to 4, specific. Never invent a program, a number, a person or a date.'},state


def render_html(rep,question,when):
    E=lambda s:html.escape(str(s or ''),quote=False);T=THEME;fonts=(ROOT/'founder_os'/'ui'/'fonts')
    face=lambda name,file,weight:f"@font-face{{font-family:'{name}';src:url('{(fonts/file).as_uri()}') format('woff2');font-weight:{weight}}}"
    css=f"""{face('Mona Sans','mona-sans.woff2','200 900')}{face('Brygada 1918','brygada-1918.woff2','400 700')}
@page{{size:Letter;margin:0.55in 0.6in 0.7in}}*{{box-sizing:border-box}}
body{{margin:0;background:{T['paper']};color:{T['ink']};font-family:'Mona Sans','Helvetica Neue',Arial,sans-serif;font-size:11pt;line-height:1.5}}
.band{{background:{T['navy']};color:{T['paper']};padding:22px 28px 18px;border-bottom:4px solid {T['brass']}}}
.band .kicker{{font-size:9pt;letter-spacing:.14em;text-transform:uppercase;color:{T['maize']};margin:0 0 6px}}
.band h1{{font-family:'Brygada 1918',Georgia,serif;font-weight:400;font-size:22pt;line-height:1.15;margin:0 0 6px;letter-spacing:-.01em}}
.band .q{{color:#cfd8e3;font-size:10.5pt;margin:0}}
.wrap{{padding:20px 28px 28px}}
h2{{font-family:'Brygada 1918',Georgia,serif;font-weight:400;font-size:15pt;color:{T['navy']};margin:18px 0 8px;padding-bottom:4px;border-bottom:1px solid {T['stone']}}}
p{{margin:0 0 9px}}
.numbers{{display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 6px}}
.num{{flex:1 1 150px;background:{T['soft']};border:1px solid {T['stone']};border-radius:8px;padding:10px 12px}}
.num b{{display:block;font-family:'Brygada 1918',Georgia,serif;font-weight:400;font-size:18pt;color:{T['brass_text']};line-height:1.1}}
.num span{{font-size:9.5pt;color:{T['muted']}}}
table{{width:100%;border-collapse:collapse;font-size:10pt;margin:4px 0 6px}}
th{{text-align:left;font-weight:600;font-size:9pt;letter-spacing:.06em;text-transform:uppercase;color:{T['muted']};padding:6px 8px;border-bottom:2px solid {T['stone']}}}
td{{padding:7px 8px;border-bottom:1px solid {T['stone']};vertical-align:top}}
td.when{{white-space:nowrap;color:{T['brass_text']};font-weight:600;width:14%}}td.who{{white-space:nowrap;width:10%;color:{T['muted']}}}
td .why{{color:{T['muted']};font-size:9.5pt}}
.box{{background:{T['maize_wash']};border-left:4px solid {T['brass']};border-radius:0 8px 8px 0;padding:10px 14px;margin:6px 0 8px}}
.box ol{{margin:0;padding-left:18px}}.box li{{margin:0 0 5px}}
ul.risks{{margin:0;padding-left:18px}}ul.risks li{{margin:0 0 4px}}
.foot{{margin-top:22px;padding-top:8px;border-top:1px solid {T['stone']};font-size:8.5pt;color:{T['muted']};display:flex;justify-content:space-between}}
"""
    plan=''.join(f"<tr><td class='when'>{E(x['when'])}</td><td><div>{E(x['what'])}</div>{('<div class=why>'+E(x['why'])+'</div>') if x['why'] else ''}{('<div class=why>'+E(x['link'])+'</div>') if x['link'] else ''}</td><td class='who'>{E(x['owner'])}</td></tr>" for x in rep['plan'])
    nums=''.join(f"<div class='num'><b>{E(n['value'])}</b><span>{E(n['label'])}{(' · '+E(n['source'])) if n['source'] else ''}</span></div>" for n in rep['numbers'])
    qs=''.join(f"<li>{E(q)}</li>" for q in rep['questions_for_bao']);risks=''.join(f"<li>{E(r)}</li>" for r in rep['risks'])
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{E(rep['title'])}</title><style>{css}</style></head><body>"
            f"<div class='band'><p class='kicker'>A Story Founder OS · Planner · {E(when.strftime('%B %d, %Y').replace(' 0',' '))}</p><h1>{E(rep['title'])}</h1><p class='q'>{E(question)}</p></div><div class='wrap'>"
            +(f"<h2>The answer</h2>{''.join('<p>'+E(p)+'</p>' for p in rep['answer'])}" if rep['answer'] else '')
            +(f"<h2>Numbers that frame the week</h2><div class='numbers'>{nums}</div>" if nums else '')
            +(f"<h2>The plan</h2><table><thead><tr><th>When</th><th>What and why</th><th>Who</th></tr></thead><tbody>{plan}</tbody></table>" if plan else '')
            +(f"<h2>Questions only you can answer</h2><div class='box'><ol>{qs}</ol></div>" if qs else '')
            +(f"<h2>Risks</h2><ul class='risks'>{risks}</ul>" if risks else '')
            +f"<div class='foot'><span>Written from the desks: Today, Money, Deals, Scouts, Win briefs, Pitch Lab. Numbers carry their source; nothing here is submitted or sent.</span><span>pitch.gbaonvo.com</span></div></div></body></html>")


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
        step={'type':'object','additionalProperties':False,'properties':{'when':S(),'what':S(),'why':S(),'owner':{'type':'string','enum':list(OWNERS)},'link':S()},'required':['when','what','why','owner','link']}
        num={'type':'object','additionalProperties':False,'properties':{'label':S(),'value':S(),'source':S()},'required':['label','value','source']}
        schema={'type':'object','additionalProperties':False,'properties':{'title':S(),'answer':{'type':'array','items':S()},'plan':{'type':'array','items':step},'numbers':{'type':'array','items':num},
                'questions_for_bao':{'type':'array','items':S()},'risks':{'type':'array','items':S()}},'required':['title','answer','plan','numbers','questions_for_bao','risks']}
        prompt=ctx['task']+' Do not use shell, files, web, email or any tool. Return JSON matching the schema.\nCONTEXT:\n'+json.dumps({k:v for k,v in ctx.items() if k!='task'},ensure_ascii=False,default=str)
        data,_=codex_json(h,request,prompt,schema,'plan')
        r=pl.save(rid,data,state);return {'report':rid,'title':r['title'],'pdf':bool(r['pdf_url']),'plan_steps':len(r['report']['plan'])}
    except Exception as e:
        pl.fail(rid,e);raise
