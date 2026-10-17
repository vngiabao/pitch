"""Money per founder hour: which open programs are worth Bao's time first, and the preparation
the agents can do for them before he opens them.

The ranking is a pure function over the hunter's analysis. Every component is shown with the
number, and the number is an estimate: it orders work, it does not forecast awards. Nothing here
submits anything; the preparation step only reads forms, queues the drafter or starts a Pitch Lab
edition, one action per autonomy cycle.
"""
import re
from datetime import datetime,timedelta,timezone
from .store import now

DEFAULT_HOURS=3.0          # when the hunter has no planning estimate
MIN_HOURS=0.5              # no application takes less than half an hour
CREDIT_DISCOUNT=0.25       # credits count at a quarter of face value
LIKELIHOOD_CEILING=0.6     # a perfect fit is given 60 percent, never certainty
FIT_FLOOR=40.0             # fit at or below this scores the minimum likelihood
URGENT_DAYS=14             # closing within this many days raises the figure, up to 2x on closing day
TOP=5
TERMINAL=('SKIP','EXPIRED','REJECTED','ACCEPTED','ALREADY APPLIED')
PITCH_TYPES=('pitch_competition','competition','pitch_night','prize','award')
LABEL='Estimate: expected money per founder hour. It orders the work; it does not forecast an award.'
MINUTES=re.compile(r'(\d+(?:\.\d+)?)\s*[- ]?\s*min(?:ute)?s?\b',re.I)


def clamp(v,lo,hi):return max(lo,min(hi,v))


def money_counted(money):
    """(amount counted as cash, label). Cash is the prize ceiling; credits are discounted to 25 percent of face value."""
    cash=money.get('cash_max');credits=money.get('credits_face_value')
    if cash:return float(cash),'cash prize max'+(' (investment, equity attached)' if money.get('kind')=='INVESTMENT' else '')
    if credits:return float(credits)*CREDIT_DISCOUNT,'credits at %d percent of $%s face value'%(int(CREDIT_DISCOUNT*100),format(int(credits),','))
    return 0.0,'amount not published'


def likelihood(fit,eligibility):
    """Win likelihood from the fit score: fit above 40 scaled to a 60 percent ceiling, halved when eligibility is unknown."""
    factor=1.0 if eligibility=='ELIGIBLE' else 0.5
    base=clamp((float(fit)-FIT_FLOOR)/(100-FIT_FLOOR),0.02,1.0)*LIKELIHOOD_CEILING
    return round(base*factor,3),factor


def urgency(days):
    """1.0 normally; closing within 14 days scales up to 2.0 on the closing day."""
    if days is None or days<0 or days>URGENT_DAYS:return 1.0
    return round(1+(URGENT_DAYS-days)/URGENT_DAYS,2)


def pitch_minutes(data,default=3.0):
    """The pitch length the program states, when its text says so; otherwise the default."""
    parts=[data.get('notes') or '']+[str(r.get('label') or r.get('kind') or '') for r in data.get('requirements') or []]
    parts+=[str(v) for v in (data.get('eligibility') or {}).values() if v]+[str(x) for x in data.get('other_assets_required') or []]
    text=' '.join(parts)
    for m in MINUTES.finditer(text):
        window=text[max(0,m.start()-60):m.end()+60].lower()
        if 'pitch' in window or 'present' in window:
            v=float(m.group(1))
            if 0.5<=v<=30:return v
    return default


def is_pitch(data):
    t=str(data.get('opportunity_type') or '').lower()
    text=' '.join(str(data.get(k) or '') for k in ('canonical_name','notes','opportunity_type')).lower()
    return t in PITCH_TYPES or 'pitch' in text


def eligible_for_ranking(d):
    """Open, not yet applied, not ruled out by Bao or by an eligibility failure."""
    if d['recommendation'] in TERMINAL or d.get('superseded_by'):return False
    if d['data'].get('status')!='OPEN':return False
    if d['analysis']['eligibility']['status']=='INELIGIBLE':return False
    if d.get('decisions') and d['decisions'][0]['decision']=='SKIP':return False
    if d.get('outcomes'):return False
    dates=d['analysis']['scoring']['dates']
    if dates.get('expired'):return False
    return True


def value_of(d):
    """Every component of the estimate for one program. Pure."""
    a=d['analysis'];money=a['money'];sc=a['scoring']
    counted,basis=money_counted(money)
    fit=d.get('fit_score');fit_known=fit is not None
    fit_used=fit if fit_known else (sc.get('estimate') if sc.get('estimate') is not None else FIT_FLOOR)
    status=a['eligibility']['status']
    p,factor=likelihood(fit_used,status)
    hours=a['materials'].get('estimated_hours')
    hours_known=hours is not None
    h=max(MIN_HOURS,float(hours)) if hours_known else DEFAULT_HOURS
    days=sc['dates'].get('days_remaining');u=urgency(days)
    ev=counted*p;per_hour=ev*u/h
    amount=money.get('cash_max') or money.get('credits_face_value')
    reason=(('$'+format(int(amount),',') if amount else 'No published amount')+(' credits' if not money.get('cash_max') and money.get('credits_face_value') else '')+' x '+str(int(round(p*100)))+'% likelihood (fit '+
            ('%g'%fit_used if fit_known else 'about %g'%fit_used)+', '+('eligible' if status=='ELIGIBLE' else 'eligibility unknown, halved')+') / '+('%g'%h)+(' hours' if h!=1 else ' hour')+
            (' estimated' if hours_known else ' assumed')+(', x%g for closing in %d day%s'%(u,days,'' if days==1 else 's') if u>1 else '')+'.')
    return {'opportunity_id':d['opportunity_id'],'program_id':d.get('program_id'),'name':d['data']['canonical_name'],'kind':money['kind'],'estimate':True,'label':LABEL,
            'money':{'amount':amount,'counted':round(counted,2),'basis':basis},
            'likelihood':{'fit':fit_used,'fit_known':fit_known,'eligibility':status,'eligibility_factor':factor,'value':p,'ceiling':LIKELIHOOD_CEILING},
            'hours':{'value':h,'known':hours_known,'source':'planning estimate' if hours_known else 'default when unknown'},
            'urgency':{'days':days,'factor':u,'window_days':URGENT_DAYS},
            'expected_value':round(ev,2),'per_hour':round(per_hour,2),'reason':reason,'deadline':d['data']['dates'].get('deadline'),'recommendation':d['recommendation'],
            'url':'/opportunity/'+d['opportunity_id'],'pitch':is_pitch(d['data']),'pitch_minutes':pitch_minutes(d['data']) if is_pitch(d['data']) else None}


def rank(items,limit=None):
    """Rank hunter detail records by expected money per founder hour. Pure: no database, no clock beyond the records' own day counts.
    Returns (ranked rows, programs left out because no amount is published)."""
    rows=[];unpriced=[];seen=set()
    for d in items:
        if not eligible_for_ranking(d):continue
        v=value_of(d)
        if not v['money']['counted']:unpriced.append({'opportunity_id':d['opportunity_id'],'name':d['data']['canonical_name']});continue
        rows.append(v)
    rows.sort(key=lambda r:(-r['per_hour'],-r['expected_value'],r['name']))
    out=[]
    for r in rows:
        key=r['program_id'] or r['opportunity_id']
        if key in seen:continue
        seen.add(key);out.append(r)
        if limit and len(out)>=limit:break
    return out,unpriced


class MoneyRanker:
    def __init__(self,store):
        from .funding_hunter import FundingHunter
        from .application_drafter import ApplicationDrafter
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.drafter=ApplicationDrafter(store)

    def _edition(self,oid):
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='work_items'").fetchone():return None
        return self.db.execute("SELECT id,stage FROM work_items WHERE kind='PITCH_EDITION' AND opportunity_id=? ORDER BY updated_at DESC LIMIT 1",(oid,)).fetchone()

    def preparation(self,row):
        """Where the agents' preparation stands for one ranked program, and what they will do next."""
        from .application_drafter import DRAFT_PREFIX
        oid=row['opportunity_id'];insp=self.drafter.inspection(oid);ed=self._edition(oid)
        prep={'form':insp['state'] if insp else 'NOT_READ','form_reason':insp['reason'] if insp else 'The agent has not opened the application form yet.',
              'application_id':insp['application_id'] if insp else None,'questions':0,'answered':0,'drafting':False,
              'edition':{'id':ed['id'],'stage':ed['stage']} if ed else None}
        aid=prep['application_id']
        if aid:
            prep['questions']=self.db.execute('SELECT COUNT(*) FROM questions WHERE application_id=?',(aid,)).fetchone()[0]
            prep['answered']=self.db.execute("SELECT COUNT(DISTINCT q.id) FROM questions q JOIN answer_versions v ON v.question_id=q.id JOIN answer_reviews r ON r.version_id=v.id WHERE q.application_id=? AND r.status!='rejected'",(aid,)).fetchone()[0]
            prep['drafting']=bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",(DRAFT_PREFIX+aid,)).fetchone())
        steps=[]
        if prep['form']=='NOT_READ':steps.append('read the form')
        elif prep['form']=='QUESTIONS_READ':
            if prep['drafting']:steps.append('drafting answers')
            elif prep['answered']<prep['questions'] and self._needs_drafts(aid):steps.append('draft answers')
        if row['pitch'] and not ed:steps.append('start the %g-minute pitch edition'%row['pitch_minutes'])
        prep['next']=steps[0] if steps else None
        done=[]
        if prep['form']=='QUESTIONS_READ':done.append('%d of %d answers ready'%(prep['answered'],prep['questions']))
        elif prep['form']=='LOGIN_REQUIRED':done.append('form needs your login')
        elif prep['form']=='NO_LINK':done.append('no form link yet')
        elif prep['form'] in ('NO_FORM_FOUND','UNREADABLE'):done.append('form not readable')
        if ed:done.append('pitch edition '+('ready' if ed['stage']=='READY' else 'approved' if ed['stage']=='APPROVED' else 'in progress'))
        prep['summary']=(', '.join(done).capitalize()+'. ' if done else '')+('Agents next: '+prep['next']+'.' if prep['next'] else ('Nothing left for the agents; the rest is yours.' if done else 'Agents next: read the form.'))
        return prep

    def _needs_drafts(self,aid):
        """Open questions remain, the drafter has not run, and nothing marks them as questions only Bao can answer."""
        if not aid or not self.drafter.open_questions(aid):return False
        drafted=self.db.execute("SELECT 1 FROM answer_versions v JOIN questions q ON q.id=v.question_id WHERE q.application_id=? AND v.provenance='agent_draft'",(aid,)).fetchone()
        noted=self.db.execute('SELECT 1 FROM draft_notes n JOIN questions q ON q.id=n.question_id WHERE q.application_id=?',(aid,)).fetchone()
        return not drafted and not noted

    def top(self,limit=TOP):
        rows,unpriced=rank(self.h.list('All'),limit)
        for r in rows:r['preparation']=self.preparation(r)
        return rows

    def board(self,limit=TOP):
        rows,unpriced=rank(self.h.list('All'),limit)
        for r in rows:r['preparation']=self.preparation(r)
        return {'rows':rows,'unpriced':unpriced,'label':LABEL,'method':{'credit_discount':CREDIT_DISCOUNT,'default_hours':DEFAULT_HOURS,'likelihood_ceiling':LIKELIHOOD_CEILING,'fit_floor':FIT_FLOOR,'urgent_days':URGENT_DAYS}}

    def prepare(self,reader=None,limit=TOP,max_age_days=7):
        """One preparation action for the top programs, in rank order: read the form, queue the drafter, or start the pitch edition.
        Never submits. Returns what was done, or {'action': None}."""
        from .funding_hunter import stamp
        for r in self.top(limit):
            oid=r['opportunity_id'];insp=self.drafter.inspection(oid)
            stale=insp and stamp(insp['checked_at'])<datetime.now(timezone.utc)-timedelta(days=max_age_days)
            if not insp or stale:
                if reader is None and self.h.detail(oid)['data'].get('application_url'):continue
                self.drafter.reader=reader;result=self.drafter.read_form(oid)
                self.s.log('ranker.prepared','money_ranker',{'opportunity_id':oid,'action':'read_form','state':result.get('state')})
                return {'action':'read_form','opportunity_id':oid,'name':r['name'],**{k:v for k,v in result.items() if k!='filled'}}
            aid=insp['application_id']
            if insp['state']=='QUESTIONS_READ' and aid and self._needs_drafts(aid) and not self.db.execute("SELECT 1 FROM hunter_requests WHERE reason=? AND state IN ('QUEUED','RUNNING')",('Draft application: '+aid,)).fetchone():
                rid=self.drafter.queue_draft(aid)
                self.s.log('ranker.prepared','money_ranker',{'opportunity_id':oid,'action':'queue_draft','request_id':rid})
                return {'action':'queue_draft','opportunity_id':oid,'name':r['name'],'application_id':aid,'request_id':rid}
            if r['pitch'] and not self._edition(oid):
                from .pitch_lab import PitchLab
                it=PitchLab(self.s).start_edition(oid,r['pitch_minutes'],note='Started by the money-per-hour ranker: this program is in the top %d by expected money per founder hour.'%limit)
                self.s.log('ranker.prepared','money_ranker',{'opportunity_id':oid,'action':'start_edition','item_id':it['id'],'minutes':r['pitch_minutes']})
                return {'action':'start_edition','opportunity_id':oid,'name':r['name'],'item_id':it['id'],'minutes':r['pitch_minutes']}
        return {'action':None}


def brief_rows(rows,founder_url):
    """Rows for the daily brief: name, dollars per hour, the reason and where it stands."""
    return [{'name':r['name'],'per_hour':r['per_hour'],'per_hour_label':'$'+format(int(round(r['per_hour'])),',')+'/hour',
             'reason':r['reason'],'status':r['preparation']['summary'],'url':founder_url(r['url'])} for r in rows]
