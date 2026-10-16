"""Product desk: the beta family journal, the retention tracker and read-only metrics intake.

Bao enters the beta families and logs what each one does (first call, second call, a relative
contributing, a photo upload, an issue). The retention tracker turns those events into measured
numbers, each with its denominator, date range and source. Fact Guard reads them as "measured"
facts, preferred over owner-reported numbers where both exist. Metrics intake reads CSV exports
(App Store Connect, Stripe, RevenueCat) from data/metrics-inbox and keeps the file, its fingerprint
and the date next to every number. Nothing here writes to any outside service.
"""
import csv
import ctypes
import hashlib
import json
import re
from ctypes import wintypes
from datetime import date,datetime
from pathlib import Path
from .store import now,uid,PolicyError

EVENT_KINDS=(('first_call','First call'),('second_call','Second call'),('relative_contribution','A relative contributed'),('photo_upload','Photo upload'),('issue','Issue'))
KIND_WORDS=dict(EVENT_KINDS)
FAMILY_STATES=(('active','Active'),('paused','Paused'),('finished','Finished'),('dropped','Dropped out'))
SOURCES=('manual','import')
INBOX_SUFFIXES=('.csv','.tsv','.txt')
MAX_INBOX_BYTES=25*1024*1024
CREDENTIAL_PREFIX='AStoryFounderOS:Metrics:'

SCHEMA='''
CREATE TABLE IF NOT EXISTS beta_families(id TEXT PRIMARY KEY,label TEXT NOT NULL,storyteller TEXT NOT NULL DEFAULT '',adult_child TEXT NOT NULL DEFAULT '',
 enrolled_on TEXT,status TEXT NOT NULL DEFAULT 'active',notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS family_events(id TEXT PRIMARY KEY,family_id TEXT NOT NULL REFERENCES beta_families(id),kind TEXT NOT NULL,at TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'manual',detail TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS family_events_family ON family_events(family_id,at);
CREATE TABLE IF NOT EXISTS metrics_sources(id TEXT PRIMARY KEY,provider TEXT NOT NULL,kind TEXT NOT NULL,file_name TEXT NOT NULL,file_sha256 TEXT NOT NULL UNIQUE,
 file_path TEXT NOT NULL,imported_at TEXT NOT NULL,row_count INTEGER NOT NULL,point_count INTEGER NOT NULL,period_start TEXT,period_end TEXT,note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS metrics_points(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES metrics_sources(id),provider TEXT NOT NULL,metric TEXT NOT NULL,
 period TEXT NOT NULL,value REAL NOT NULL,unit TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS metrics_points_metric ON metrics_points(provider,metric,period);
'''


# ---------- dates and words ----------
def parse_day(value):
    """A calendar day from the formats the exports and the form use. Returns YYYY-MM-DD or None."""
    v=str(value or '').strip()
    if not v:return None
    for fmt in ('%Y-%m-%d','%Y-%m-%d %H:%M','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%m/%d/%Y','%m/%d/%y','%Y/%m/%d','%d %b %Y','%b %d, %Y'):
        try:return datetime.strptime(v,fmt).date().isoformat()
        except ValueError:pass
    try:return datetime.fromisoformat(v.replace('Z','+00:00')).date().isoformat()
    except ValueError:return None


def day_words(v):
    if not v:return ''
    d=date.fromisoformat(v);return d.strftime('%b ')+str(d.day)+d.strftime(', %Y')


def range_words(start,end):
    if not start:return 'no dates yet'
    return day_words(start) if start==end else day_words(start)+' - '+day_words(end)


def percent(n,d):
    return None if not d else round(100*n/d)


def slug(name):
    return re.sub(r'[^a-z0-9]+','_',str(name).strip().lower()).strip('_')


# ---------- retention: pure functions over family_events rows ----------
def retention(events,start=None,end=None):
    """Measured retention from journal events (dicts with family_id, kind, at, source).

    Every number carries its numerator, denominator, the date range of the events it used and
    the sources they came from. A rate with an empty denominator is None, never 0.
    """
    rows=[e for e in events if (not start or e['at']>=start) and (not end or e['at']<=end)]
    by_family={}
    for e in rows:by_family.setdefault(e['family_id'],[]).append(e)
    def families_with(kind):return {f for f,es in by_family.items() if any(e['kind']==kind for e in es)}
    first=families_with('first_call');second=families_with('second_call');contributed=families_with('relative_contribution')
    after=set();calls_after=0
    for f in contributed:
        es=by_family[f];first_contribution=min(e['at'] for e in es if e['kind']=='relative_contribution')
        later=[e for e in es if e['kind'] in ('first_call','second_call') and e['at']>first_contribution]
        if later:after.add(f);calls_after+=len(later)
    dates=sorted(e['at'] for e in rows);sources=sorted({e['source'] for e in rows})
    def metric(key,label,n,d,num_label,den_label,extra=None):
        return {'key':key,'label':label,'numerator':n,'denominator':d,'rate':(n/d if d else None),'percent':percent(n,d),'numerator_label':num_label,'denominator_label':den_label,
                'measurable':bool(d),'range':{'start':dates[0] if dates else None,'end':dates[-1] if dates else None},'sources':sources,**(extra or {})}
    return {'as_of':dates[-1] if dates else None,'range':{'start':dates[0] if dates else None,'end':dates[-1] if dates else None},'sources':sources,
            'families_with_events':len(by_family),'events':len(rows),
            'metrics':[metric('second_call_rate','Second-call rate',len(second&first),len(first),'families with a second call','families with a first call'),
                       metric('relatives_contributing','Relatives contributing',len(contributed&first),len(first),'families where a relative contributed','families with a first call'),
                       metric('calls_after_contribution','Calls that followed a contribution',len(after),len(contributed),'families that called again after a relative contributed','families with a contribution',{'calls':calls_after})]}


def measured_facts(result,families_enrolled=None):
    """Plain statements for Fact Guard and the drafters, each labelled measured with its as-of date."""
    facts=[];as_of=result['as_of']
    if families_enrolled is not None and families_enrolled>0:
        facts.append({'key':'beta_families','label':'Beta families enrolled','value':families_enrolled,'numerator':families_enrolled,'denominator':None,'percent':None,'as_of':as_of or date.today().isoformat(),'source':'measured',
                      'text':f'Measured as of {day_words(as_of or date.today().isoformat())}: {families_enrolled} beta '+('family' if families_enrolled==1 else 'families')+' in the journal.'})
    for m in result['metrics']:
        if not m['measurable']:continue
        n,d=m['numerator'],m['denominator']
        text=f"Measured as of {day_words(as_of)} ({range_words(m['range']['start'],m['range']['end'])}, {' and '.join(m['sources'])} entries): {n} of {d} {m['denominator_label']} "
        text+={'second_call_rate':'had a second call','relatives_contributing':'had a relative contribute','calls_after_contribution':'called again after that contribution'}[m['key']]
        text+=f" ({m['percent']}%)."
        facts.append({'key':m['key'],'label':m['label'],'value':m['rate'],'numerator':n,'denominator':d,'percent':m['percent'],'as_of':as_of,'source':'measured','text':text})
    return facts


def measured_numbers(facts):
    """Every number a measured fact licenses, in Fact Guard's normalised form, mapped to the fact's text."""
    out={}
    for f in facts:
        values=[f['numerator'],f['denominator'],f['percent']]
        if f['value'] is not None and f['denominator']:values.append(round(100*f['value'],1))
        for v in values:
            if v is None:continue
            out['%g'%float(v)]=f['text']
    return out


# ---------- CSV adapters (read-only) ----------
# Column aliases per provider: export column -> (metric, unit). Unknown numeric columns are kept under their slug.
ALIASES={
 'app_store_connect':{'units':('app_units','count'),'app units':('app_units','count'),'downloads':('downloads','count'),'total downloads':('downloads','count'),'first-time downloads':('first_time_downloads','count'),
                      'redownloads':('redownloads','count'),'impressions':('impressions','count'),'product page views':('product_page_views','count'),'installations':('installations','count'),
                      'sessions':('sessions','count'),'active devices':('active_devices','count'),'deletions':('deletions','count'),'developer proceeds':('proceeds','usd'),'proceeds':('proceeds','usd'),
                      'conversion rate':('conversion_rate','percent'),'crashes':('crashes','count'),'paying users':('paying_users','count'),'sales':('sales','usd')},
 'revenuecat':{'active subscriptions':('active_subscriptions','count'),'active trials':('active_trials','count'),'mrr':('mrr','usd'),'revenue':('revenue','usd'),'new customers':('new_customers','count'),
               'new paid subscriptions':('new_paid_subscriptions','count'),'new trials':('new_trials','count'),'churn':('churn','percent'),'churn rate':('churn','percent'),'active users':('active_users','count'),
               'trial conversion rate':('trial_conversion_rate','percent'),'refunds':('refunds','count'),'cancellations':('cancellations','count')},
 'stripe':{}}
DATE_COLUMNS=('date','day','begin date','created (utc)','created date (utc)','created','period','report date','start date')
PROVIDERS={'app_store_connect':'App Store Connect','stripe':'Stripe','revenuecat':'RevenueCat'}


def read_table(text):
    """Rows from a CSV or TSV export, skipping any preamble before the header line with the date column."""
    lines=text.lstrip('﻿').splitlines()
    for i,line in enumerate(lines):
        if not line.strip():continue
        delimiter='\t' if line.count('\t')>=line.count(',') and '\t' in line else ','
        header=[h.strip().lower() for h in next(csv.reader([line],delimiter=delimiter))]
        if any(h in DATE_COLUMNS for h in header):
            rows=[r for r in csv.DictReader(lines[i+1:],fieldnames=header,delimiter=delimiter) if any((v or '').strip() for v in r.values())]
            return header,rows
    raise ValueError('No header with a date column was found in this export')


def date_column(header):
    return next(h for h in DATE_COLUMNS if h in header)


def number(v):
    t=str(v or '').strip().replace(',','').replace('$','').replace('%','')
    if t in ('','-','—'):return None
    try:return float(t)
    except ValueError:return None


def daily_table(provider,header,rows):
    """Daily metric tables (App Store Connect analytics and sales reports, RevenueCat charts): one point per metric per day."""
    dcol=date_column(header);aliases=ALIASES.get(provider,{});totals={}
    for r in rows:
        day=parse_day(r.get(dcol))
        if not day:continue
        for col in header:
            if col==dcol or not col:continue
            v=number(r.get(col))
            if v is None:continue
            metric,unit=aliases.get(col,(slug(col),'count'))
            if unit=='percent' or metric in ('active_subscriptions','active_trials','mrr','active_devices','active_users'):totals[(metric,day)]=(v,unit,'latest value that day')
            else:
                old=totals.get((metric,day),(0.0,unit,'summed across rows that day'));totals[(metric,day)]=(old[0]+v,unit,old[2])
    return [{'metric':m,'period':d,'value':v,'unit':u,'detail':note} for (m,d),(v,u,note) in sorted(totals.items())]


def stripe_payments(header,rows):
    """Stripe payments export: succeeded payments and refunds per day, in the export's currency."""
    dcol=date_column(header);amount=next((h for h in ('amount','converted amount') if h in header),None)
    if not amount:raise ValueError('Stripe export needs an Amount column')
    totals={}
    for r in rows:
        day=parse_day(r.get(dcol));status=(r.get('status') or '').strip().lower();v=number(r.get(amount));currency=(r.get('currency') or r.get('converted currency') or 'usd').strip().lower()
        if not day or v is None:continue
        if status in ('succeeded','paid','') :
            p=totals.setdefault(('payments',day),[0,'count',currency]);p[0]+=1
            rv=totals.setdefault(('revenue',day),[0.0,currency,currency]);rv[0]+=v
        refunded=number(r.get('amount refunded'))
        if refunded:
            rf=totals.setdefault(('refunds',day),[0.0,currency,currency]);rf[0]+=refunded
    return [{'metric':m,'period':d,'value':v,'unit':u,'detail':'from payments with status succeeded' if m!='refunds' else 'amount refunded'} for (m,d),(v,u,_) in sorted(totals.items())]


def parse_export(provider,text):
    if provider not in PROVIDERS:raise ValueError('Unknown metrics provider')
    header,rows=read_table(text)
    points=stripe_payments(header,rows) if provider=='stripe' else daily_table(provider,header,rows)
    if not points:raise ValueError('The export has no numbers the adapter understands')
    return {'rows':len(rows),'points':points}


# ---------- API pulls: a documented stub ----------
def credential_present(provider):
    """True when a metrics key is stored in Windows Credential Manager under AStoryFounderOS:Metrics:<provider>.

    The secret itself never leaves this function: only its presence is reported. Keys are added by the owner
    with Credential Manager (generic credential, this Windows user only), never through the web server.
    """
    if provider not in PROVIDERS:raise PolicyError('Unknown metrics provider')
    if not hasattr(ctypes,'WinDLL'):return False
    lib=ctypes.WinDLL('Advapi32.dll',use_last_error=True);ptr=ctypes.c_void_p()
    lib.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p)];lib.CredReadW.restype=wintypes.BOOL
    lib.CredFree.argtypes=[ctypes.c_void_p]
    if not lib.CredReadW(CREDENTIAL_PREFIX+provider,1,0,ctypes.byref(ptr)):return False
    lib.CredFree(ptr);return True


def api_pull(provider):
    """Stub for read-only API pulls. Not switched on; documents the design so the next step is small.

    Design: each pull is a GET with a key read from Credential Manager at call time (App Store Connect:
    an API key id, issuer id and .p8 private key signed into a JWT; Stripe: a restricted key with read-only
    scopes; RevenueCat: a v2 secret key with read scopes). The response is normalised into the same point
    shape the CSV adapters produce and saved as a metrics_sources row with kind 'api', the request date as
    its as-of date and the endpoint as file_name. No key is ever logged, returned or stored in the database.
    """
    present=credential_present(provider)
    return {'provider':provider,'credential_present':present,'status':'not_switched_on','credential_target':CREDENTIAL_PREFIX+provider,
            'note':('A key is stored; API pulls still need code and Bao\'s go-ahead.' if present else 'No key is stored for this provider. CSV exports keep working.')}


class ProductDesk:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA)
        self.inbox=Path(store.path).resolve().parent/'metrics-inbox'

    # ---------- beta family journal ----------
    def add_family(self,p):
        label=str(p.get('label') or '').strip()
        if not label:raise ValueError('Give the family a name or label')
        enrolled=parse_day(p.get('enrolled_on')) if p.get('enrolled_on') else None
        if p.get('enrolled_on') and not enrolled:raise ValueError('Enrolled date must be a calendar day')
        status=str(p.get('status') or 'active')
        if status not in dict(FAMILY_STATES):raise ValueError('Unknown family status')
        fid=uid('family');t=now()
        self.db.execute('INSERT INTO beta_families VALUES(?,?,?,?,?,?,?,?,?)',(fid,label[:120],str(p.get('storyteller') or '').strip()[:120],str(p.get('adult_child') or '').strip()[:120],enrolled,status,str(p.get('notes') or '').strip()[:2000],t,t))
        self.s.log('family.added','owner',{'id':fid,'label':label});return self.family(fid)

    def update_family(self,fid,p):
        f=self.s.one('SELECT * FROM beta_families WHERE id=?',(fid,))
        fields={}
        for k in ('label','storyteller','adult_child','notes'):
            if k in p:fields[k]=str(p[k] or '').strip()[:2000 if k=='notes' else 120]
        if 'label' in fields and not fields['label']:raise ValueError('Give the family a name or label')
        if 'status' in p:
            if p['status'] not in dict(FAMILY_STATES):raise ValueError('Unknown family status')
            fields['status']=p['status']
        if 'enrolled_on' in p:
            d=parse_day(p['enrolled_on']) if p['enrolled_on'] else None
            if p['enrolled_on'] and not d:raise ValueError('Enrolled date must be a calendar day')
            fields['enrolled_on']=d
        if fields:
            self.db.execute('UPDATE beta_families SET '+','.join(k+'=?' for k in fields)+',updated_at=? WHERE id=?',(*fields.values(),now(),f['id']))
        return self.family(fid)

    def log_event(self,p):
        fid=p.get('family_id');self.s.one('SELECT id FROM beta_families WHERE id=?',(fid,))
        kind=p.get('kind')
        if kind not in KIND_WORDS:raise ValueError('Unknown event kind')
        at=parse_day(p.get('at'))
        if not at:raise ValueError('The event needs a calendar day')
        if at>date.today().isoformat():raise ValueError('The journal records what happened, not what is planned')
        source=p.get('source') or 'manual'
        if source not in SOURCES:raise ValueError('Unknown event source')
        eid=uid('event')
        self.db.execute('INSERT INTO family_events VALUES(?,?,?,?,?,?,?)',(eid,fid,kind,at,source,str(p.get('detail') or '').strip()[:1000],now()))
        self.s.log('family.event','owner' if source=='manual' else 'import',{'id':eid,'family_id':fid,'kind':kind,'at':at});return self.s.one('SELECT * FROM family_events WHERE id=?',(eid,))

    def delete_event(self,eid):
        e=self.s.one('SELECT * FROM family_events WHERE id=?',(eid,))
        self.db.execute('DELETE FROM family_events WHERE id=?',(eid,));self.s.log('family.event_removed','owner',{'id':eid,'family_id':e['family_id'],'kind':e['kind'],'at':e['at']})
        return {'deleted':eid}

    def events(self):
        return self.s.rows('SELECT * FROM family_events ORDER BY at,created_at')

    def family(self,fid):
        f=self.s.one('SELECT * FROM beta_families WHERE id=?',(fid,))
        es=self.s.rows('SELECT * FROM family_events WHERE family_id=? ORDER BY at,created_at',(fid,))
        counts={k:0 for k,_ in EVENT_KINDS}
        for e in es:counts[e['kind']]=counts.get(e['kind'],0)+1
        return {**f,'events':[{**e,'kind_words':KIND_WORDS.get(e['kind'],e['kind'])} for e in es],'counts':counts,'last_event':es[-1]['at'] if es else None,'status_words':dict(FAMILY_STATES).get(f['status'],f['status'])}

    def families(self):
        return [self.family(r['id']) for r in self.s.rows('SELECT id FROM beta_families ORDER BY enrolled_on IS NULL,enrolled_on,created_at')]

    def retention(self,start=None,end=None):
        return retention(self.events(),start,end)

    def measured_facts(self):
        enrolled=self.db.execute("SELECT COUNT(*) FROM beta_families WHERE status IN ('active','paused','finished')").fetchone()[0]
        return measured_facts(self.retention(),enrolled)

    # ---------- metrics intake ----------
    def inbox_files(self):
        if not self.inbox.exists():return []
        out=[]
        for f in sorted(self.inbox.iterdir()):
            if not f.is_file() or f.suffix.lower() not in INBOX_SUFFIXES:continue
            sha=hashlib.sha256(f.read_bytes()).hexdigest();done=self.db.execute('SELECT id,provider,imported_at FROM metrics_sources WHERE file_sha256=?',(sha,)).fetchone()
            out.append({'name':f.name,'size':f.stat().st_size,'modified':datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec='minutes'),'imported':dict(done) if done else None})
        return out

    def import_file(self,name,provider,note=''):
        """Import one export from data/metrics-inbox by file name. The file is read, never moved or changed."""
        if provider not in PROVIDERS:raise ValueError('Choose App Store Connect, Stripe or RevenueCat')
        safe=Path(str(name or '')).name
        if not safe or safe!=str(name) or safe.startswith('.'):raise ValueError('Name a file in the metrics inbox, without a path')
        f=self.inbox/safe
        if not f.is_file() or f.suffix.lower() not in INBOX_SUFFIXES:raise ValueError('No such export in data/metrics-inbox')
        if f.stat().st_size>MAX_INBOX_BYTES:raise ValueError('Export is larger than 25 MB')
        raw=f.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        existing=self.db.execute('SELECT id FROM metrics_sources WHERE file_sha256=?',(sha,)).fetchone()
        if existing:raise ValueError('This exact file was already imported as '+existing['id'])
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:text=raw.decode('latin-1')
        parsed=parse_export(provider,text);points=parsed['points'];sid=uid('metrics');days=sorted(p['period'] for p in points)
        with self.s.transaction():
            self.db.execute('INSERT INTO metrics_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(sid,provider,'csv',safe,sha,str(f),now(),parsed['rows'],len(points),days[0],days[-1],str(note or '')[:500]))
            for p in points:
                self.db.execute('INSERT INTO metrics_points VALUES(?,?,?,?,?,?,?,?)',(uid('point'),sid,provider,p['metric'],p['period'],p['value'],p['unit'],p['detail']))
        self.s.log('metrics.imported','owner',{'id':sid,'provider':provider,'file':safe,'sha256':sha,'points':len(points)})
        return self.source(sid)

    def source(self,sid):
        return self.s.one('SELECT * FROM metrics_sources WHERE id=?',(sid,))

    def sources(self):
        return self.s.rows('SELECT * FROM metrics_sources ORDER BY imported_at DESC')

    def latest_points(self):
        """The newest value of every imported metric, with the file and day it came from."""
        return self.s.rows('''SELECT p.provider,p.metric,p.period,p.value,p.unit,p.detail,s.file_name,s.imported_at FROM metrics_points p JOIN metrics_sources s ON s.id=p.source_id
                              WHERE p.period=(SELECT MAX(period) FROM metrics_points q WHERE q.provider=p.provider AND q.metric=p.metric) ORDER BY p.provider,p.metric''')

    def api_status(self):
        out=[]
        for key,name in PROVIDERS.items():
            try:out.append({**api_pull(key),'name':name})
            except PolicyError as e:out.append({'provider':key,'name':name,'credential_present':False,'status':'error','note':str(e)})
        return out

    def board(self):
        fams=self.families();r=self.retention()
        return {'families':fams,'retention':r,'measured':self.measured_facts(),'event_kinds':[list(k) for k in EVENT_KINDS],'family_states':[list(s) for s in FAMILY_STATES],
                'counts':{'families':len(fams),'first_calls':sum(1 for f in fams if f['counts']['first_call']),'second_calls':sum(1 for f in fams if f['counts']['second_call']),
                          'contributing':sum(1 for f in fams if f['counts']['relative_contribution']),'issues':sum(f['counts']['issue'] for f in fams)},
                'intake':{'inbox':str(self.inbox),'files':self.inbox_files(),'sources':self.sources(),'latest':self.latest_points(),'providers':PROVIDERS,'api':self.api_status()}}
