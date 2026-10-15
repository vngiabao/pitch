"""Read-only inbox tracker for the owner's two application inboxes.

Finds program emails (received, advanced, accepted, rejected) and PROPOSES outcomes.
Nothing is recorded until the owner confirms each one. The mailbox is opened with
EXAMINE (read-only) and bodies are fetched with BODY.PEEK, so nothing is sent,
deleted, moved, labelled or marked read. Passwords stay in Windows Credential Manager.
"""
import csv,email,html,imaplib,io,json,re,ssl
from datetime import datetime,timedelta,timezone
from email.header import decode_header,make_header
from email.utils import parseaddr,parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from .store import now,js,digest,PolicyError
from .report_email import INBOX_ACCOUNTS,read_credential,credential_present
from .owner_links import founder_url

SCHEMA='''CREATE TABLE IF NOT EXISTS inbox_messages(
 id TEXT PRIMARY KEY, account TEXT NOT NULL, message_id TEXT NOT NULL,
 sender TEXT NOT NULL, sender_domain TEXT NOT NULL, subject TEXT NOT NULL, received_at TEXT NOT NULL,
 snippet TEXT NOT NULL, opportunity_id TEXT, proposed_outcome TEXT, state TEXT NOT NULL, reason TEXT,
 source_version_id TEXT, outcome_id TEXT, created_at TEXT NOT NULL, decided_at TEXT,
 UNIQUE(account,message_id));'''

OUTCOMES=('Applied','Advanced','Finalist','Accepted','Rejected')
RANK={'Applied':1,'Advanced':2,'Finalist':3,'Accepted':4,'Won':4,'Rejected':4,'Withdrawn':4}
# Checked in order: a rejection that congratulates other teams is still a rejection.
RULES=[('Rejected',(r'unfortunately',r'not (?:been )?selected',r'regret to inform',r'unable to (?:offer|accept|move forward)',r'(?:not|won.t) (?:be )?moving forward',r'decided not to (?:move|proceed|accept|select)',r'was not accepted',r'application (?:was|has been) declined')),
       ('Accepted',(r'congratulations',r'you(?:.ve| have) been (?:accepted|approved|selected)',r'you.re in\b',r'accepted (?:in)?to',r'(?:application|account) (?:has been|is) approved',r'approved for',r'credits (?:have been|are|were) (?:added|applied|granted|issued)')),
       ('Finalist',(r'\bfinalists?\b',)),
       ('Advanced',(r'next round',r'semi-?finalist',r'shortlisted',r'invite you to (?:an? )?(?:interview|pitch)',r'advanced? to the')),
       ('Applied',(r'application (?:has been |was )?received',r'thanks? (?:you )?for (?:your )?appl',r'received your application',r'application (?:has been |was )?submitted',r'confirm(?:s|ing)? (?:your|receipt of your) (?:application|submission)'))]
WEAK_ACCEPT=r'\bwelcome to\b'
# Unmatched senders are only worth a look when the email is about startup funding,
# not a job application or a shop's "congratulations".
PROGRAM_WORDS=r'\b(?:grant|accelerator|incubator|program(?:me)?|competition|fund|fellowship|credits|startup|cohort|pitch|investment|founders?)\b'
# Shared senders (mail platforms, form tools, the university): match by program name only.
SHARED=('gmail.com','googlemail.com','google.com','outlook.com','hotmail.com','yahoo.com','icloud.com','typeform.com','airtable.com','hubspot.com','hubspotemail.net','hs-email.net','mailchimp.com','mcsv.net','mcdlv.net','sendgrid.net','amazonses.com','mailgun.org','f6s.com','forms.gle','notion.so','calendly.com','zoom.us','docusign.net','umich.edu','linkedin.com','substack.com','beehiiv.com','luma-mail.com','lu.ma')
SECOND_LEVEL=('co','com','org','net','ac','edu','gov')
HEADER_LIMIT=1500;BODY_LIMIT=80;BODY_MAX_BYTES=2_000_000


def registrable(host):
    parts=[p for p in (host or '').lower().strip('.').split('.') if p]
    if len(parts)>=3 and len(parts[-1])==2 and parts[-2] in SECOND_LEVEL:return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def header_text(value):
    try:return str(make_header(decode_header(value or ''))).strip()
    except (UnicodeError,LookupError):return (value or '').strip()


def body_text(msg):
    plain=[];rich=[]
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition()=='attachment':continue
        kind=part.get_content_type()
        if kind not in ('text/plain','text/html'):continue
        try:raw=part.get_payload(decode=True) or b'';text=raw.decode(part.get_content_charset() or 'utf-8',errors='replace')
        except LookupError:text=raw.decode('utf-8',errors='replace')
        (plain if kind=='text/plain' else rich).append(text)
    text='\n'.join(plain) if plain else html.unescape(re.sub(r'(?is)<(script|style).*?</\1>|<[^>]+>',' ','\n'.join(rich)))
    return re.sub(r'\s+',' ',text).strip()


def classify(subject,body,bulk=False):
    text=subject+' \n '+body[:4000]
    for outcome,patterns in RULES:
        if any(re.search(p,text,re.I) for p in patterns):return outcome
    # "Welcome to ..." from a mailing list is usually a newsletter, not an acceptance.
    if not bulk and re.search(WEAK_ACCEPT,subject,re.I):return 'Accepted'
    return None


class ImapInbox:
    """Gmail / Google Workspace over IMAP, strictly read-only."""
    def __init__(self,account):
        if account not in INBOX_ACCOUNTS:raise PolicyError('Mailbox is outside owner authorization')
        self.account=account
    def available(self):return credential_present(self.account)
    def _mailbox(self,m):
        typ,rows=m.list()
        for row in rows or []:
            line=row.decode('utf-8','replace') if isinstance(row,bytes) else str(row)
            if '\\All' in line:return line.rsplit(' "/" ',1)[-1].strip()
        return 'INBOX'
    def fetch(self,since,prefilter):
        secret=read_credential(self.account)
        m=imaplib.IMAP4_SSL('imap.gmail.com',993,ssl_context=ssl.create_default_context(),timeout=30)
        try:
            try:m.login(self.account,secret)
            finally:del secret
            typ,_=m.select(self._mailbox(m),readonly=True)
            if typ!='OK':raise PolicyError('Mailbox could not be opened read-only')
            typ,data=m.search(None,'SINCE',since.strftime('%d-%b-%Y'))
            ids=(data[0] or b'').split()[-HEADER_LIMIT:] if typ=='OK' else []
            heads=[]
            for i in range(0,len(ids),200):
                typ,rows=m.fetch(b','.join(ids[i:i+200]),'(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID LIST-UNSUBSCRIBE)])')
                for row in rows or []:
                    if not isinstance(row,tuple):continue
                    size=re.search(rb'RFC822\.SIZE (\d+)',row[0]);num=row[0].split()[0]
                    heads.append((num,int(size.group(1)) if size else 0,email.message_from_bytes(row[1])))
            picked=[h for h in heads if prefilter(h[2])][-BODY_LIMIT:]
            out=[]
            for num,size,head in picked:
                msg=head
                if size<=BODY_MAX_BYTES:
                    typ,rows=m.fetch(num,'(BODY.PEEK[])')
                    full=[r for r in rows or [] if isinstance(r,tuple)]
                    if typ=='OK' and full:msg=email.message_from_bytes(full[0][1])
                out.append(msg)
            return out
        finally:
            try:m.logout()
            except (OSError,imaplib.IMAP4.error):pass


class InboxTracker:
    def __init__(self,store,hunter=None,inboxes=None):
        from .funding_hunter import FundingHunter
        self.s=store;self.db=store.db;self.h=hunter or FundingHunter(store);self.db.executescript(SCHEMA)
        self.inboxes=inboxes
        self.db.execute('INSERT OR IGNORE INTO hunter_settings VALUES(?,?)',('inbox_tracker',js({'enabled':True,'accounts':list(INBOX_ACCOUNTS),'interval_minutes':30,'first_lookback_days':90,'state':{}})))

    def settings(self):return self.h.settings().get('inbox_tracker',{})
    def _save(self,cfg):self.db.execute("UPDATE hunter_settings SET value_json=? WHERE key='inbox_tracker'",(js(cfg),))
    def inbox(self,account):return (self.inboxes or {}).get(account) or ImapInbox(account)

    # ---- program index -------------------------------------------------
    def programs(self):
        superseded=set()
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='opportunity_supersessions'").fetchone():
            superseded={r['superseded_id'] for r in self.s.rows('SELECT superseded_id FROM opportunity_supersessions')}
        aliases={}
        for a in self.s.rows('SELECT program_id,alias FROM program_aliases'):aliases.setdefault(a['program_id'],set()).add(a['alias'])
        best={}
        for r in self.s.rows('SELECT i.opportunity_id,i.program_id,i.last_checked,i.data_json,p.canonical_name,(SELECT count(*) FROM funding_outcomes o WHERE o.opportunity_id=i.opportunity_id) outcomes FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id'):
            if r['opportunity_id'] in superseded:continue
            old=best.get(r['program_id'])
            if old and (old['outcomes'],old['last_checked'] or '')>=(r['outcomes'],r['last_checked'] or ''):continue
            best[r['program_id']]=r
        out=[]
        for pid,r in best.items():
            data=json.loads(r['data_json'])
            domains={registrable(urlsplit(u).hostname or '') for u in (data.get('official_url'),data.get('application_url')) if u}
            names={r['canonical_name'],*(data.get('aliases') or []),*aliases.get(pid,())}
            out.append({'opportunity_id':r['opportunity_id'],'program_id':pid,'name':r['canonical_name'],'domains':{d for d in domains if d and d not in SHARED},'patterns':self._patterns(names)})
        return out

    @staticmethod
    def _patterns(names):
        pats=[]
        for name in names:
            name=re.sub(r'\(.*?\)|#\s*\d+','',str(name or '')).strip()
            for piece in {name,re.split(r'\s+[—–-]\s+|:\s',name)[0].strip()}:
                if len(piece)>=6:pats.append(re.compile(r'(?<![\w])'+re.escape(piece)+r'(?![\w])',re.I))
            words=[w for w in re.findall(r'[A-Za-z][\w&]*',name) if w[0].isupper()]
            if len(words)>=3:pats.append(re.compile(r'\b'+''.join(w[0] for w in words)+r'\b'))
        return pats

    def match(self,programs,domain,text):
        by_domain=[p for p in programs if domain in p['domains']]
        named=lambda pool:[p for p in pool if any(x.search(text) for x in p['patterns'])]
        if len(by_domain)==1:return by_domain[0],None
        if by_domain:
            hit=named(by_domain)
            return (hit[0],None) if len(hit)==1 else (None,'Sender matches several tracked programs')
        hit=named(programs)
        if len(hit)==1:return hit[0],None
        return None,('Mentions several tracked programs' if hit else 'Sender is not a tracked program')

    # ---- scanning --------------------------------------------------------
    def prefilter(self,programs):
        domains=set().union(*(p['domains'] for p in programs)) if programs else set()
        def keep(head):
            sender=parseaddr(header_text(head.get('From')))[1].lower()
            if sender in INBOX_ACCOUNTS:return False
            subject=header_text(head.get('Subject'))
            if registrable(sender.rpartition('@')[2]) in domains:return True
            if classify(subject,'',bool(head.get('List-Unsubscribe'))):return True
            return any(x.search(subject) for p in programs for x in p['patterns'])
        return keep

    def ingest(self,account,msg,programs):
        if account not in INBOX_ACCOUNTS:raise PolicyError('Mailbox is outside owner authorization')
        sender=parseaddr(header_text(msg.get('From')))[1].lower()
        if not sender or sender in INBOX_ACCOUNTS:return None
        message_id=(msg.get('Message-ID') or '').strip() or 'no-id-'+digest([sender,msg.get('Date'),msg.get('Subject')])[:24]
        mid='inbox-'+digest([account,message_id])[:24]
        if self.db.execute('SELECT 1 FROM inbox_messages WHERE id=?',(mid,)).fetchone():return None
        subject=header_text(msg.get('Subject'))[:300];body=body_text(msg)
        outcome=classify(subject,body,bool(msg.get('List-Unsubscribe')))
        if not outcome:return None
        domain=registrable(sender.rpartition('@')[2])
        program,why=self.match(programs,domain,subject+' \n '+body[:4000])
        if not program and (msg.get('List-Unsubscribe') or not re.search(PROGRAM_WORDS,subject+' '+body[:1000],re.I)):return None
        try:received=parsedate_to_datetime(msg.get('Date')).astimezone(timezone.utc).isoformat()
        except (TypeError,ValueError,IndexError):received=now()
        state,reason='REVIEW',why
        if program:
            state,reason=self._compare(program['opportunity_id'],outcome,received)
        self.db.execute('INSERT INTO inbox_messages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,NULL)',(mid,account,message_id,sender,domain,subject,received,body[:600],program and program['opportunity_id'],outcome,state,reason,now()))
        return {'id':mid,'state':state,'outcome':outcome,'program':program and program['name']}

    def _compare(self,oid,outcome,received):
        from .funding_hunter import stamp
        cur=self.db.execute('SELECT outcome,occurred_at FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC LIMIT 1',(oid,)).fetchone()
        if self.db.execute("SELECT 1 FROM inbox_messages WHERE opportunity_id=? AND proposed_outcome=? AND state='PROPOSED'",(oid,outcome)).fetchone():
            return 'ALREADY_TRACKED','Another email already proposes this outcome'
        if cur:
            if cur['outcome']==outcome:return 'ALREADY_TRACKED','Matches the recorded outcome'
            if RANK[outcome]<RANK.get(cur['outcome'],0):return 'ALREADY_TRACKED','Earlier stage than the recorded '+cur['outcome']
            if RANK[outcome]==RANK.get(cur['outcome'],0) and stamp(received)<=stamp(cur['occurred_at']):
                return 'REVIEW','Email says '+outcome+' but '+cur['outcome']+' is recorded'
        return 'PROPOSED',None

    def poll(self,instant=None,force=False):
        instant=instant or datetime.now(timezone.utc);cfg=self.settings()
        if not cfg.get('enabled'):return {'paused':True}
        programs=self.programs();report={}
        for account in cfg.get('accounts',[]):
            if account not in INBOX_ACCOUNTS:continue
            state=cfg.setdefault('state',{}).setdefault(account,{})
            last=state.get('last_checked')
            if not force and last and datetime.fromisoformat(last)>instant-timedelta(minutes=int(cfg.get('interval_minutes',30))):
                report[account]={'waiting':True};continue
            inbox=self.inbox(account)
            if not inbox.available():
                state.update(connected=False,last_error='Not connected; run Connect-Inbox.ps1');report[account]={'connected':False};continue
            since=datetime.fromisoformat(state['scanned_through'])-timedelta(days=2) if state.get('scanned_through') else instant-timedelta(days=int(cfg.get('first_lookback_days',90)))
            try:
                found=[r for r in (self.ingest(account,m,programs) for m in inbox.fetch(since,self.prefilter(programs))) if r]
            except Exception as e:
                state.update(connected=True,last_error=type(e).__name__+': could not read this inbox; nothing was changed in it')
                self.s.log('inbox.scan_failed','inbox_tracker',{'account':account,'error_type':type(e).__name__});report[account]={'error':type(e).__name__};continue
            state.update(connected=True,last_checked=instant.isoformat(),scanned_through=instant.isoformat(),last_error=None)
            self.s.log('inbox.scanned','inbox_tracker',{'account':account,'new':len(found),'proposed':sum(r['state']=='PROPOSED' for r in found),'read_only':True})
            report[account]={'new':len(found)}
        self._save(cfg)
        return report

    # ---- owner decisions -------------------------------------------------
    def decide(self,mid,decision,outcome=None,actor='owner'):
        if actor!='owner':raise PolicyError('Only the owner can confirm an inbox outcome')
        m=self.s.one('SELECT * FROM inbox_messages WHERE id=?',(mid,))
        if m['state'] not in ('PROPOSED','REVIEW'):raise PolicyError('This email was already decided')
        if decision=='dismiss':
            self.db.execute("UPDATE inbox_messages SET state='DISMISSED',decided_at=? WHERE id=? AND state IN ('PROPOSED','REVIEW')",(now(),mid))
            self.s.log('inbox.dismissed',actor,{'id':mid});return {'state':'DISMISSED'}
        if decision!='confirm':raise ValueError('Unknown decision')
        outcome=outcome or m['proposed_outcome']
        if outcome not in OUTCOMES:raise ValueError('Unknown outcome')
        if not m['opportunity_id']:raise PolicyError('Open the program and record the outcome there; this email is not matched to a program')
        name=self.h.detail(m['opportunity_id'])['data']['canonical_name']
        folder=Path(self.s.path).parent/'inbox-evidence';folder.mkdir(exist_ok=True)
        path=folder/(mid+'.txt')
        statement=(f'Email evidence confirmed by the owner on {now()}\nInbox: {m["account"]}\nFrom: {m["sender"]}\nDate: {m["received_at"]}\n'
                   f'Subject: {m["subject"]}\nMessage-ID: {m["message_id"]}\nProgram: {name} ({m["opportunity_id"]})\nOutcome: {outcome}\n\nExcerpt:\n{m["snippet"]}\n')
        path.write_text(statement,encoding='utf-8')
        vid=self.s.import_source(path,'email','REFERENCE',text=statement,extraction='inbox_tracker',document_date=m['received_at'][:10])
        with self.s.transaction():
            eid=self.h.outcome(m['opportunity_id'],outcome,'Email from '+m['sender']+' to '+m['account']+': "'+m['subject']+'"',source_version_id=vid,occurred_at=m['received_at'])
            self.db.execute("UPDATE inbox_messages SET state='CONFIRMED',proposed_outcome=?,source_version_id=?,outcome_id=?,decided_at=? WHERE id=?",(outcome,vid,eid,now(),mid))
            self.s.log('inbox.outcome_confirmed',actor,{'id':mid,'opportunity_id':m['opportunity_id'],'outcome':outcome,'outcome_id':eid})
        return {'state':'CONFIRMED','outcome_id':eid,'recommendation':self.h.detail(m['opportunity_id'])['recommendation']}

    # ---- views -----------------------------------------------------------
    def dashboard(self):
        cfg=self.settings();accounts=[]
        for a in INBOX_ACCOUNTS:
            st=(cfg.get('state') or {}).get(a,{})
            accounts.append({'account':a,'connected':credential_present(a),'last_checked':st.get('last_checked'),'last_error':st.get('last_error')})
        pending=self.s.rows("SELECT m.*,p.canonical_name program FROM inbox_messages m LEFT JOIN funding_intelligence i ON i.opportunity_id=m.opportunity_id LEFT JOIN funding_programs p ON p.id=i.program_id WHERE m.state IN ('PROPOSED','REVIEW') ORDER BY m.state,m.received_at DESC")
        return {'enabled':bool(cfg.get('enabled')),'accounts':accounts,'pending':pending,'proposed':sum(p['state']=='PROPOSED' for p in pending),'review':sum(p['state']=='REVIEW' for p in pending)}

    def export_csv(self):
        """One row per tracked program: latest status, first application date and evidence."""
        board=self.h.money_board(self.h.list('All'))
        kinds={'meeting_notes':'Meeting notes','owner_attestation':'Owner statement','email':'Email'}
        out=io.StringIO();w=csv.writer(out)
        w.writerow(['Program','Organizer','Status','Status date','First applied','Money type','Advertised value','Evidence','Inbox','Email subject','Email date','Pending email proposal','Official URL','Founder OS'])
        for t in board['tracked']:
            d=self.h.detail(t['opportunity_id']);data=d['data'];fund=data['funding']
            first=self.db.execute("SELECT min(occurred_at) v FROM funding_outcomes WHERE opportunity_id=? AND outcome='Applied'",(t['opportunity_id'],)).fetchone()['v']
            src=self.db.execute('SELECT s.kind FROM funding_outcomes o JOIN source_versions v ON v.id=o.source_version_id JOIN sources s ON s.id=v.source_id WHERE o.opportunity_id=? ORDER BY o.occurred_at DESC,o.created_at DESC LIMIT 1',(t['opportunity_id'],)).fetchone()
            mail=self.db.execute("SELECT account,subject,received_at FROM inbox_messages WHERE opportunity_id=? AND state IN ('CONFIRMED','ALREADY_TRACKED') ORDER BY received_at DESC LIMIT 1",(t['opportunity_id'],)).fetchone()
            pending=self.db.execute("SELECT proposed_outcome FROM inbox_messages WHERE opportunity_id=? AND state='PROPOSED' ORDER BY received_at DESC LIMIT 1",(t['opportunity_id'],)).fetchone()
            value=('Cash up to '+format(fund['cash_prize_max'],',g')+' '+(fund.get('currency') or '')) if fund.get('cash_prize_max') is not None else ('Credits '+format(fund['credits_value'],',g')+' '+(fund.get('currency') or '')) if fund.get('credits_value') is not None else (fund.get('other_benefits') or '')
            w.writerow([t['canonical_name'],data.get('organizer') or '',t['outcome'],(t['occurred_at'] or '')[:10],(first or '')[:10],d['analysis'].get('money',{}).get('kind',''),value.strip(),kinds.get(src['kind'],src['kind']) if src else 'Recorded',
                        mail['account'] if mail else '',mail['subject'] if mail else '',(mail['received_at'] or '')[:10] if mail else '',pending['proposed_outcome'] if pending else '',data.get('official_url') or '',founder_url('/opportunity/'+t['opportunity_id'])])
        return '﻿'+out.getvalue()
