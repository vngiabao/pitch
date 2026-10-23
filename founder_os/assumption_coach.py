"""Assumption Coach: every number the core deck depends on, what each rests on today, and the cheapest test for it.

The assumptions table is seeded from the deck's own spoken notes (seed-data/master-deck-2026-10.json). Each row
carries the statement, the number, its status (assumed, modeled or measured), the slides it appears on, evidence
for and against, the cheapest test and Bao's note. Measured numbers flow in on their own from channel math
(growth_desk.measured_facts) and the beta family journal (product_desk.measured_facts), with their dates, and
flip the status; when the entries behind them go away, the status goes back to what the deck said.

Once a week (Monday 7:30 Eastern) and on request, Pitch Coach reads the table, the measured numbers and the
latest pitch edition and names the three weakest assumptions: why each is weak, the one cheapest test, and the
question a judge would ask. Fact Guard rules apply: an item that introduces a number not in the table is dropped.
Pitch Tailor and Pitch Coach read the table on every run, so scripts say "modeled" or "measured" correctly.
Nothing here invents a number; owner edits are labelled as Bao's.
"""
import json
import re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .store import now,js,uid
from .funding_hunter import FundingHunter
from .pitch_lab import numbers_in,norm

ET=ZoneInfo('America/New_York')
CHALLENGE_PREFIX='Assumption challenge: '
STATUSES=('assumed','modeled','measured')
STATUS_WORDS={'assumed':'Assumed','modeled':'Modeled','measured':'Measured'}
SAY={'assumed':'an assumption we are testing (an example input), not a result','modeled':'modeled, not observed','measured':'measured'}
WEEKLY=(0,7,30)  # Monday, 7:30 Eastern

SCHEMA='''
CREATE TABLE IF NOT EXISTS assumptions(id TEXT PRIMARY KEY,key TEXT NOT NULL UNIQUE,statement TEXT NOT NULL,number TEXT NOT NULL,status TEXT NOT NULL,seeded_status TEXT NOT NULL,
 slides_json TEXT NOT NULL,evidence_for_json TEXT NOT NULL,evidence_against_json TEXT NOT NULL,cheapest_test TEXT NOT NULL,owner_note TEXT NOT NULL DEFAULT '',
 measures TEXT,watch_json TEXT NOT NULL DEFAULT '[]',measured_json TEXT,status_changed_at TEXT,change_seen_at TEXT,ordinal INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assumption_challenges(id TEXT PRIMARY KEY,request_key TEXT NOT NULL UNIQUE,weakest_json TEXT NOT NULL,rejected_json TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',
 edition_id TEXT,edition_title TEXT,measured_json TEXT NOT NULL,created_at TEXT NOT NULL,seen_at TEXT);
'''

# Seeded from the deck's spoken notes. Every number in a statement is a number the deck already says (the test checks this).
# measures: the measured-fact key that flips the status when it exists. watch: measured facts shown as evidence without flipping.
SEED=[
 dict(key='visit_conversion',statement='3 percent of qualified visits buy and stay.',number='3%',status='assumed',slides=['next-90'],
      evidence_for=['The deck calls this an example input, not a measurement.'],evidence_against=['No visit-to-purchase rate has been recorded yet.'],
      cheapest_test='Record one week of visits, signups and purchases per channel in channel math (the Hope College day and the reservation drive). The measured rate replaces 3 percent on its own.',
      measures='conversion',watch=['purchasing_families']),
 dict(key='visits_to_families',statement='1,000 qualified visits at 3 percent is 30 paying families.',number='30 families from 1,000 visits',status='assumed',slides=['next-90'],
      evidence_for=['Arithmetic on the example conversion rate.'],evidence_against=['No visit count has been recorded yet.'],
      cheapest_test='The same channel-math entries as the conversion test; channel math then says how many visits 30 families really take.',
      measures='purchasing_families',watch=['conversion']),
 dict(key='renewal',statement='Families renew after the first year because the call becomes a habit.',number='unproven',status='assumed',slides=['business','next-90','living-memory'],
      evidence_for=[],evidence_against=['No family has reached a renewal date.'],
      cheapest_test='Offer the five waiting families a prepaid year at release and record who takes it. Until a renewal date arrives, the second-call rate is the leading proxy.',
      measures=None,watch=['second_call_rate']),
 dict(key='second_call',statement='Storytellers come back for a second call.',number='unmeasured',status='assumed',slides=['traction','next-90','competition'],
      evidence_for=[],evidence_against=['The second-call rate is not measured yet.'],
      cheapest_test='Log the first and second call for each of the 10 beta families in the family journal; the rate appears with its denominator.',
      measures='second_call_rate',watch=[]),
 dict(key='relatives_contribute',statement='Relatives add their own versions and photos.',number='unmeasured',status='assumed',slides=['every-narrator','next-90'],
      evidence_for=[],evidence_against=['Not measured yet.'],
      cheapest_test='Log each relative contribution in the family journal; the share of families with a contributing relative appears with its denominator.',
      measures='relatives_contributing',watch=[]),
 dict(key='contribution_shapes_next_call',statement='What relatives add shapes the next call and brings the storyteller back.',number='unmeasured',status='assumed',slides=['every-narrator','competition','next-90'],
      evidence_for=['This is the core design the deck says we are measuring now.'],evidence_against=['Not proven to give an edge yet, as the competition slide says.'],
      cheapest_test='Log the calls that happen after a relative contributed; the journal counts the families that called again.',
      measures='calls_after_contribution',watch=[]),
 dict(key='interview_cost',statement='A 7 to 10 minute interview costs about $0.32 to $0.45 on our stack.',number='$0.32 to $0.45',status='modeled',slides=['why-now','a1-economics'],
      evidence_for=['Modeled on 2026 voice pricing after the price cuts; the same dollar buys about 2.2 times as much voice.'],evidence_against=['No provider invoice has been divided by a count of real interviews yet.'],
      cheapest_test='Take one month of provider invoices for the beta calls and divide by the number of interviews completed that month.',measures=None,watch=[]),
 dict(key='first_year_contribution',statement='First-year contribution per account is $77 at 25 percent of minutes used, $61 at 50 percent and $28 at 100 percent.',number='$77 / $61 / $28',status='modeled',slides=['a1-economics'],
      evidence_for=['Built from the pricing, the modeled interview cost, payment fees, hosting, support and an archive reserve.'],evidence_against=['The share of included minutes families actually use is not observed.'],
      cheapest_test='Pull minutes used per beta family per month from the call logs; that fixes the usage axis and picks the right column.',measures=None,watch=[]),
 dict(key='revenue_per_account',statement='About $141 per account, from an 80/20 mix of Individual and Family plans.',number='$141',status='modeled',slides=['market','a1-economics'],
      evidence_for=['A weighted average of $119 and $229 at 80 percent Individual, 20 percent Family.'],evidence_against=['No paying account exists yet to average.'],
      cheapest_test='Export the first paying accounts from Stripe or RevenueCat into the metrics inbox; the plan mix and the average are then counted, not assumed.',
      measures=None,watch=['revenue','purchasing_families']),
 dict(key='plan_mix',statement='80 percent of accounts choose Individual and 20 percent choose Family.',number='80/20',status='assumed',slides=['market','a1-economics'],
      evidence_for=[],evidence_against=['No account has chosen a plan yet.'],
      cheapest_test='Ask the five waiting families and the reservation-drive reservers which plan they want; count the answers.',measures=None,watch=[]),
 dict(key='accounts_to_100m',statement='Roughly 710,000 paying accounts make this a $100 million a year business.',number='710,000 accounts',status='modeled',slides=['market'],
      evidence_for=['$100 million divided by the modeled $141 per account.'],evidence_against=['It depends entirely on the modeled revenue per account.'],
      cheapest_test='No cheap test of its own; it moves when revenue per account is measured.',measures=None,watch=[]),
 dict(key='market_ceiling',statement='43.6 million U.S. households include someone 65 or older; at $119 that is a $5.19 billion a year ceiling.',number='$5.19 billion',status='modeled',slides=['market'],
      evidence_for=['Household counts from the Census Bureau; the deck labels these demographic ceilings.'],evidence_against=['Demand has not been validated at any price.'],
      cheapest_test='Not testable cheaply. The conversion and willingness-to-pay tests say what share of those households is reachable.',measures=None,watch=[]),
 dict(key='willingness_to_pay',statement='Adult children pay $119 a year for Individual or $229 a year for Family.',number='$119 and $229',status='assumed',slides=['business'],
      evidence_for=['Owner-reported: five families are waiting to join as paying families on the redesigned release.'],evidence_against=['No payment records yet.'],
      cheapest_test='The $1 reservation drive before November 2, then the five waiting families paying full price at release; each reservation and purchase lands in channel math.',
      measures=None,watch=['purchasing_families','revenue']),
 dict(key='acquisition_cost',statement='Acquisition plus trial costs about $37 per account.',number='$37',status='modeled',slides=['a1-economics'],
      evidence_for=['Modeled inside the first-year contribution.'],evidence_against=['No spend per purchasing family has been recorded.'],
      cheapest_test='Record spend and purchases per channel per week in channel math; cost per purchasing family appears as soon as a channel has spend.',
      measures='cost_per_family',watch=[]),
 dict(key='waiting_families_convert',statement='The five waiting families become the first paying families on the redesigned release.',number='5 families',status='assumed',slides=['traction','next-90'],
      evidence_for=['Owner-reported interest.'],evidence_against=['No payment has been taken.'],
      cheapest_test='Ask the five this week for a paid reservation at release; record each yes in channel math.',measures=None,watch=['purchasing_families']),
 dict(key='habit_not_homework',statement='A scheduled call becomes a habit where weekly prompts become homework; a daily habit takes a median of 66 days.',number='66 days',status='assumed',slides=['todays-options','living-memory'],
      evidence_for=['Lally et al. 2010 found a median of 66 days of daily repetition. The research is about habits in general, not about A Story.'],evidence_against=[],
      cheapest_test='Journal every call for the 10 beta families across 66 days and count who is still answering at the end.',measures=None,watch=['second_call_rate']),
 dict(key='hope_college_demand',statement='Hope College students will gift A Story to their grandparents this Thanksgiving.',number='about 10 reservations',status='assumed',slides=['traction','next-90'],
      evidence_for=['Owner-reported first sales on October 17, 2026: at a Hope College on-site table, about 10 students reserved A Story for $1 each and one bought a $29 book. Payment records not yet reconciled. Individual students, not a partnership.'],evidence_against=[],
      cheapest_test='The on-site day at Hope College: count approaches, $1 reservations and mailing-list signups as one channel-math entry for the week.',
      measures=None,watch=['conversion','purchasing_families']),
 dict(key='gift_buyer',statement='The adult child buys A Story as a gift; the parent just answers the phone.',number='who buys',status='assumed',slides=['business','meet-a-story'],
      evidence_for=['Owner-reported: the first MVP brought in 50 leads.'],evidence_against=[],
      cheapest_test='Ask every reservation-drive reserver who the storyteller is and count gifts against self-purchases.',measures=None,watch=[]),
]


def _lines(v,limit=12,n=400):
    if isinstance(v,str):v=[x.strip() for x in re.split(r'[\r\n]+',v)]
    return [str(x).strip()[:n] for x in (v or []) if str(x).strip()][:limit]


def day_words(iso):
    try:return datetime.fromisoformat(str(iso)[:10]).strftime('%b %d, %Y').replace(' 0',' ')
    except ValueError:return str(iso)


def normalize_measured(growth,product):
    """One shape for measured facts from both desks: key, label, value, unit, as_of, source, text."""
    out={}
    for f in growth:
        unit=f.get('unit') or '';value=f['value']
        shown=('$%g'%value if unit=='USD' else '%g%%'%value if unit=='%' else '%g %s'%(value,'family' if unit=='families' and value==1 else unit)).strip()
        den=f.get('denominator');source=str(f.get('source','channel math'))
        out[f['key']]={'key':f['key'],'label':f['label'],'value':value,'unit':unit,'as_of':f.get('as_of'),'source':f.get('source','Channel math'),
                       'text':f"Measured, {f.get('as_of')} ({source[0].lower()+source[1:]}): {f['label'].lower()} {shown}"+(f" ({den})." if den else '.')}
    for f in product:
        out[f['key']]={'key':f['key'],'label':f['label'],'value':f.get('percent') if f.get('denominator') else f['value'],'unit':'%' if f.get('denominator') else 'families','as_of':f.get('as_of'),
                       'source':'Beta family journal','text':f['text']}
    return out


class FactGuardRule:
    """The challenge may not introduce a number that is not in the table or the measured facts."""
    def __init__(self,allowed):self.allowed=set(allowed)
    def strangers(self,text):
        bad=[]
        for n in numbers_in(text or ''):
            v=norm(n);plain=not re.search(r'[%$]',n)  # a count up to twelve may be written out; a percentage or a dollar figure never gets that pass
            if v in self.allowed or re.fullmatch(r'(19|20)\d\d',v) or (plain and v.isdigit() and int(v)<=12):continue
            bad.append(n)
        return bad


class AssumptionCoach:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.h=FundingHunter(store);self.db.executescript(SCHEMA);self.seed()

    # ---------- the table ----------
    def seed(self):
        """Insert the deck's assumptions once; rows Bao has edited are never overwritten. New seed rows are added later on."""
        have={r['key'] for r in self.s.rows('SELECT key FROM assumptions')}
        for i,a in enumerate(SEED):
            if a['key'] in have:continue
            self.db.execute('INSERT INTO assumptions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (uid('assumption'),a['key'],a['statement'],a['number'],a['status'],a['status'],js(a['slides']),js(a.get('evidence_for',[])),js(a.get('evidence_against',[])),a['cheapest_test'],'',
                             a.get('measures'),js(a.get('watch',[])),None,None,None,i,now(),now()))

    def measured(self):
        from .growth_desk import GrowthDesk
        from .product_desk import ProductDesk
        return normalize_measured(GrowthDesk(self.s).measured_facts(),ProductDesk(self.s).measured_facts())

    def sync(self):
        """Measured numbers flow in with their dates and flip the status; when they go away the deck's status comes back. Returns the flips."""
        m=self.measured();flips=[]
        for r in self.s.rows('SELECT * FROM assumptions'):
            fact=m.get(r['measures']) if r['measures'] else None
            evidence=[m[k] for k in json.loads(r['watch_json']) if k in m]
            new_status='measured' if fact else r['seeded_status'] if r['status']=='measured' else r['status']
            measured={'fact':fact,'evidence':evidence} if (fact or evidence) else None
            if new_status!=r['status']:
                flips.append({'key':r['key'],'from':r['status'],'to':new_status,'text':fact['text'] if fact else 'The measured entries behind it were removed.'})
                self.db.execute('UPDATE assumptions SET status=?,measured_json=?,status_changed_at=?,updated_at=? WHERE id=?',(new_status,js(measured) if measured else None,now(),now(),r['id']))
                self.s.log('assumption.status_changed','assumption_coach',{'key':r['key'],'from':r['status'],'to':new_status,'as_of':fact['as_of'] if fact else None})
            elif (js(measured) if measured else None)!=r['measured_json']:
                self.db.execute('UPDATE assumptions SET measured_json=? WHERE id=?',(js(measured) if measured else None,r['id']))
        return flips

    def row(self,r):
        return {'id':r['id'],'key':r['key'],'statement':r['statement'],'number':r['number'],'status':r['status'],'status_words':STATUS_WORDS[r['status']],'seeded_status':r['seeded_status'],
                'slides':json.loads(r['slides_json']),'evidence_for':json.loads(r['evidence_for_json']),'evidence_against':json.loads(r['evidence_against_json']),
                'cheapest_test':r['cheapest_test'],'owner_note':r['owner_note'],'measures':r['measures'],'watch':json.loads(r['watch_json']),
                'measured':json.loads(r['measured_json']) if r['measured_json'] else None,'status_changed_at':r['status_changed_at'],
                'change_unseen':bool(r['status_changed_at'] and (not r['change_seen_at'] or r['change_seen_at']<r['status_changed_at'])),'updated_at':r['updated_at']}

    def items(self):
        return [self.row(r) for r in self.s.rows('SELECT * FROM assumptions ORDER BY ordinal')]

    def get(self,key):
        return self.row(self.s.one('SELECT * FROM assumptions WHERE key=?',(key,)))

    def update(self,key,fields):
        """Bao's edits: evidence lines, the cheapest test, his note, and assumed <-> modeled. Measured is only ever set by the data."""
        r=self.s.one('SELECT * FROM assumptions WHERE key=?',(key,));changes={}
        if 'evidence_for' in fields:changes['evidence_for_json']=js(_lines(fields['evidence_for']))
        if 'evidence_against' in fields:changes['evidence_against_json']=js(_lines(fields['evidence_against']))
        if 'cheapest_test' in fields:changes['cheapest_test']=str(fields['cheapest_test'] or '').strip()[:600] or r['cheapest_test']
        if 'owner_note' in fields:changes['owner_note']=str(fields['owner_note'] or '').strip()[:1000]
        if fields.get('status'):
            st=fields['status']
            if st not in ('assumed','modeled'):raise ValueError('Only the measured data can mark an assumption measured')
            if r['status']=='measured':raise ValueError('This one is measured now; the data sets its status')
            changes['status']=st;changes['seeded_status']=st
        if not changes:return self.get(key)
        sets=','.join(k+'=?' for k in changes)+',updated_at=?'
        self.db.execute(f'UPDATE assumptions SET {sets} WHERE id=?',(*changes.values(),now(),r['id']))
        self.s.log('assumption.updated','owner',{'key':key,'fields':sorted(changes)})
        return self.get(key)

    def allowed_numbers(self):
        """Fact Guard's set for the challenge: every number in the table and in the measured facts."""
        text=' '.join(' '.join([a['statement'],a['number'],a['cheapest_test'],a['owner_note'],*a['evidence_for'],*a['evidence_against']]) for a in self.items())
        text+=' '+' '.join(m['text'] for m in self.measured().values())
        return {norm(n) for n in numbers_in(text)}

    # ---------- what the agents read ----------
    def for_agents(self):
        """Compact: every assumption with its status and how to say it, weakest first. Pitch Tailor and Pitch Coach read this on every run."""
        self.sync();items=self.items();latest=self.latest_challenge()
        order={'assumed':0,'modeled':1,'measured':2};first=[w['key'] for w in (latest or {}).get('weakest',[])]
        ranked=sorted(items,key=lambda a:(a['key'] not in first,first.index(a['key']) if a['key'] in first else 99,order[a['status']],))
        def one(a):
            m=(a.get('measured') or {}).get('fact')
            return {'key':a['key'],'statement':a['statement'],'number':a['number'],'status':a['status'],'slides':a['slides'],
                    'say':('measured as of '+str(m['as_of'])+': '+m['text']) if m else SAY[a['status']],'cheapest_test':a['cheapest_test']}
        return {'items':[one(a) for a in ranked],'weakest':[a['key'] for a in ranked if a['status']!='measured'][:5],
                'rule':'Say "measured as of <date>" for measured numbers, "modeled" for modeled ones, and call assumed ones an example input or an assumption we are testing. Never present an assumed or modeled number as a result.'}

    # ---------- the weekly challenge ----------
    def latest_edition(self):
        """The newest pitch edition's script, so the Coach weighs what the pitch actually leans on. Falls back to the master deck notes."""
        from .pitch_lab import PitchLab
        lab=PitchLab(self.s)
        for w in self.s.rows("SELECT id,title,payload_json FROM work_items WHERE kind='PITCH_EDITION' ORDER BY updated_at DESC LIMIT 1"):
            script=(json.loads(w['payload_json']).get('brief') or {}).get('script') or []
            if script:return {'id':w['id'],'title':w['title'],'slides':[{'slide_id':x.get('slide_id'),'title':x.get('title'),'text':str(x.get('text',''))[:1200]} for x in script[:24]]}
        return {'id':None,'title':'Core deck (master notes)','slides':[{'slide_id':s['id'],'title':s.get('title'),'text':str(s.get('spoken',''))[:1200]} for s in lab.master_deck()['slides'] if not s.get('appendix')]}

    def context(self):
        self.sync();measured=self.measured();edition=self.latest_edition()
        return {'today':datetime.now(ET).date().isoformat(),'assumptions':[{k:a[k] for k in ('key','statement','number','status','slides','evidence_for','evidence_against','cheapest_test','owner_note')}|{'measured':(a.get('measured') or {}).get('fact')} for a in self.items()],
                'measured_facts':[m['text'] for m in measured.values()],'edition':edition,
                'task':'You are Pitch Coach for A Story, in Assumption Coach mode: a YC partner who knows this company well, kind, direct and specific. Read CONTEXT.assumptions (every number the deck depends on, with its status: assumed, modeled or measured), CONTEXT.measured_facts and CONTEXT.edition (the latest pitch script). '
                       'Name the THREE weakest assumptions this week: the ones the pitch leans on most while resting on the least. Prefer assumed over modeled over measured, and weigh how heavily the edition relies on each. For each: why_weak (two or three plain sentences a founder can act on), cheapest_test (the one test two founders with no budget can run this week, concrete enough to start Monday), judge_question (the exact question a judge or investor would ask about it). '
                       'Use only keys from CONTEXT.assumptions. Use only numbers that appear in CONTEXT; never introduce a figure, a benchmark or a rate of your own, or Fact Guard drops the item. Write " - " with spaces, never a long dash. Bao reads every field: no mention of CONTEXT, field names or these instructions.'}

    def request(self,manual=True,instant=None):
        local=(instant or datetime.now(ET)).astimezone(ET)
        key='assumptions-'+(local.strftime('%Y-%m-%dT%H%M') if manual else 'week-'+local.strftime('%G-%V'))
        return self.h.request_run(CHALLENGE_PREFIX+key,key=key)

    def researching(self):
        return bool(self.db.execute("SELECT 1 FROM hunter_requests WHERE reason LIKE ? AND state IN ('QUEUED','RUNNING')",(CHALLENGE_PREFIX+'%',)).fetchone())

    def poll(self,instant=None):
        """Every cycle: sync the measured numbers. Once a week, after Monday 7:30 Eastern, queue the challenge."""
        flips=self.sync();local=(instant or datetime.now(ET)).astimezone(ET)
        monday=(local-timedelta(days=local.weekday())).replace(hour=WEEKLY[1],minute=WEEKLY[2],second=0,microsecond=0)
        queued=False
        if local>=monday:
            before=self.db.execute('SELECT COUNT(*) FROM hunter_requests').fetchone()[0];self.request(manual=False,instant=local)
            queued=self.db.execute('SELECT COUNT(*) FROM hunter_requests').fetchone()[0]>before
        return {'flips':[f['key'] for f in flips],'queued':queued}

    def save_challenge(self,request_key,data):
        """Fact Guard: keys must exist, numbers must already be in the table. Items that fail are kept aside with the reason, never shown as advice."""
        guard=FactGuardRule(self.allowed_numbers());known={a['key']:a for a in self.items()};kept=[];rejected=[]
        for w in (data.get('weakest') or [])[:6]:
            key=str(w.get('key','')).strip()
            if key not in known:rejected.append({'key':key,'reason':'Not an assumption in the table.'});continue
            if any(x['key']==key for x in kept):continue
            fields={k:str(w.get(k,'')).strip()[:900] for k in ('why_weak','cheapest_test','judge_question')}
            strangers=sorted({n for v in fields.values() for n in guard.strangers(v)})
            if strangers:rejected.append({'key':key,'reason':'Introduced numbers not in the table: '+', '.join(strangers)+'.'});continue
            if not fields['why_weak'] or not fields['cheapest_test']:rejected.append({'key':key,'reason':'Missing the why or the test.'});continue
            kept.append({'key':key,'statement':known[key]['statement'],'status':known[key]['status'],**fields})
            if len(kept)==3:break
        if not kept:raise RuntimeError('RESEARCH_INCOMPLETE: the Assumption Coach returned no usable items ('+'; '.join(r['reason'] for r in rejected)[:300]+')')
        edition=self.latest_edition();cid=uid('challenge')
        self.db.execute('INSERT INTO assumption_challenges VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,request_key,js(kept),js(rejected),str(data.get('note',''))[:600],edition['id'],edition['title'],js([m['text'] for m in self.measured().values()]),now(),None))
        self.s.log('assumption.challenge_saved','research_worker',{'id':cid,'weakest':[k['key'] for k in kept],'rejected':len(rejected)})
        return self.challenge(cid)

    def challenge(self,cid):
        r=self.s.one('SELECT * FROM assumption_challenges WHERE id=?',(cid,))
        return {'id':r['id'],'weakest':json.loads(r['weakest_json']),'rejected':json.loads(r['rejected_json']),'note':r['note'],'edition_id':r['edition_id'],'edition_title':r['edition_title'],
                'measured':json.loads(r['measured_json']),'created_at':r['created_at'],'seen':bool(r['seen_at'])}

    def latest_challenge(self):
        r=self.db.execute('SELECT id FROM assumption_challenges ORDER BY created_at DESC LIMIT 1').fetchone()
        return self.challenge(r['id']) if r else None

    def mark_seen(self):
        t=now()
        self.db.execute('UPDATE assumption_challenges SET seen_at=? WHERE seen_at IS NULL',(t,))
        self.db.execute('UPDATE assumptions SET change_seen_at=? WHERE status_changed_at IS NOT NULL AND (change_seen_at IS NULL OR change_seen_at<status_changed_at)',(t,))
        return {'seen':True}

    # ---------- what Bao sees ----------
    def alerts(self):
        """Today: one line when a challenge is new, one per status flip Bao has not seen."""
        items=[];latest=self.latest_challenge()
        if latest and not latest['seen']:
            first=latest['weakest'][0]
            items.append({'title':'Assumption Coach: the three weakest assumptions this week','detail':(first['statement']+' '+first['why_weak'])[:160],'url':'/assumptions','link':'See the tests'})
        for a in self.items():
            if not a['change_unseen']:continue
            fact=(a.get('measured') or {}).get('fact')
            items.append({'title':('Now measured: ' if a['status']=='measured' else 'Back to '+a['status']+': ')+a['statement'][:90],'detail':(fact['text'] if fact else 'The measured entries behind it were removed; the deck’s status is back.')[:160],'url':'/assumptions','link':'Open'})
            if len(items)>=4:break
        return items

    def board(self):
        from .pitch_lab import PitchLab
        self.sync();items=self.items()
        titles={s['id']:s.get('title') for s in PitchLab(self.s).master_deck()['slides']}
        return {'assumptions':items,'counts':{s:len([a for a in items if a['status']==s]) for s in STATUSES},'challenge':self.latest_challenge(),'researching':self.researching(),
                'slide_titles':titles,'status_words':STATUS_WORDS,'measured_sources':[m['text'] for m in self.measured().values()],'today':datetime.now(ET).date().isoformat(),
                'next_challenge':'Every Monday at 7:30 AM Eastern, and whenever you ask for one.'}


def handles(reason):return reason.startswith(CHALLENGE_PREFIX)


def run(h,request,codex_json):
    """One bounded AI job, no web: the three weakest assumptions, through Fact Guard, saved as this week's challenge."""
    ac=AssumptionCoach(h.store);ctx=ac.context()
    item={'type':'object','additionalProperties':False,'properties':{'key':{'type':'string'},'why_weak':{'type':'string'},'cheapest_test':{'type':'string'},'judge_question':{'type':'string'}},'required':['key','why_weak','cheapest_test','judge_question']}
    schema={'type':'object','additionalProperties':False,'properties':{'weakest':{'type':'array','items':item},'note':{'type':'string'}},'required':['weakest','note']}
    prompt=(ctx['task']+' Return JSON matching the schema: weakest (exactly three items, weakest first) and note (one line on what changed since the measured facts, or an empty string). Do not use shell, files, web, email or any tool.\nCONTEXT:\n'+json.dumps(ctx,ensure_ascii=False))
    data,_=codex_json(h,request,prompt,schema,'assumptions')
    c=ac.save_challenge(request['request_key'],data)
    return {'challenge':c['id'],'weakest':[w['key'] for w in c['weakest']],'rejected':len(c['rejected'])}
