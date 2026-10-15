"""Daily report outbox. Gmail password lives only in Windows Credential Manager."""
import ctypes,json,smtplib,ssl
from ctypes import wintypes
from datetime import datetime,timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo
from .store import now,js,digest,PolicyError
from .application_pilot import ApplicationPilot
from .email_design import render_email
from .email_digest import render_digest,TEMPLATE_VERSION
# Owner, Oct 15 2026: no TXT attachments. Questions and prepared answers live on the website.
ATTACH_QA_TXT=False
from .owner_links import founder_url

CREDENTIAL_TARGET='AStoryFounderOS:DailyReport:gbao.n.vo@gmail.com'
OWNER_ACCOUNT='gbao.n.vo@gmail.com'
# The only mailboxes Founder OS may use. The owner Gmail password also sends the daily report.
INBOX_ACCOUNTS=(OWNER_ACCOUNT,'bao@astoryapp.com')
PENDING=('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING')

class MailNotSent(PolicyError):
    """Failed before any message data left this PC; safe to try again later."""
class Credential(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),('CredentialBlob',ctypes.POINTER(ctypes.c_byte)),('Persist',wintypes.DWORD),('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]

def credential_target(account=OWNER_ACCOUNT):
    if account not in INBOX_ACCOUNTS:raise PolicyError('Mail account is outside owner authorization')
    return CREDENTIAL_TARGET if account==OWNER_ACCOUNT else 'AStoryFounderOS:Inbox:'+account

def credential_present(account=OWNER_ACCOUNT):
    try:read_credential(account);return True
    except (PolicyError,OSError):return False

def read_credential(account=OWNER_ACCOUNT):
    target=credential_target(account)
    if not hasattr(ctypes,'WinDLL'):raise PolicyError('Windows mail credential unavailable')
    lib=ctypes.WinDLL('Advapi32.dll',use_last_error=True);ptr=ctypes.POINTER(Credential)()
    lib.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))];lib.CredReadW.restype=wintypes.BOOL
    lib.CredFree.argtypes=[ctypes.c_void_p]
    if not lib.CredReadW(target,1,0,ctypes.byref(ptr)):raise PolicyError('Connect '+account+'; no mail credential is stored')
    try:
        c=ptr.contents
        if c.UserName!=account:raise PolicyError('Mail credential does not match owner authorization')
        return ctypes.string_at(c.CredentialBlob,c.CredentialBlobSize).decode('utf-16-le')
    finally:lib.CredFree(ptr)

def store_credential(secret,account=OWNER_ACCOUNT):
    # Used only by the owner setup helpers; never exposed through the web server.
    target=credential_target(account)
    if not hasattr(ctypes,'WinDLL'):raise PolicyError('Windows Credential Manager is required')
    if len(secret.replace(' ',''))!=16 or not secret.replace(' ','').isalnum():raise PolicyError('Use a Google app password, not your Google account password')
    raw=secret.replace(' ','').encode('utf-16-le');blob=(ctypes.c_byte*len(raw)).from_buffer_copy(raw)
    c=Credential();c.Type=1;c.TargetName=target;c.CredentialBlobSize=len(raw);c.CredentialBlob=blob;c.Persist=2;c.UserName=account;c.Comment='A Story Founder OS mail ('+('daily-report sender and read-only inbox tracker' if account==OWNER_ACCOUNT else 'read-only inbox tracker')+'); this Windows user only'
    lib=ctypes.WinDLL('Advapi32.dll',use_last_error=True);lib.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD];lib.CredWriteW.restype=wintypes.BOOL
    if not lib.CredWriteW(ctypes.byref(c),0):raise PolicyError('Could not securely save the Gmail connection')

class GmailTransport:
    def available(self):return credential_present()
    def send(self,report):
        if report['recipient']!='gbao.n.vo@gmail.com':raise PolicyError('Only the owner daily-report recipient is authorized')
        secret=read_credential();message=EmailMessage();message['From']='gbao.n.vo@gmail.com';message['To']=report['recipient'];message['Subject']=report['subject'];message['Message-ID']='<'+report['id']+'@astoryapp.com>';message.set_content(report['body'])
        if report.get('body_html'):
            if digest(report['body_html'].encode('utf-8'))!=report['body_html_sha256']:raise PolicyError('Email HTML integrity mismatch')
            message.add_alternative(report['body_html'],subtype='html')
        for a in report.get('attachments',[]):
            if digest(a['content'].encode('utf-8'))!=a['sha256']:raise PolicyError('Attachment integrity mismatch')
            message.add_attachment(a['content'],subtype='plain',filename=a['filename'])
        try:
            smtp=smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=30,context=ssl.create_default_context())
            try:smtp.login('gbao.n.vo@gmail.com',secret)
            except BaseException:smtp.close();raise
        except smtplib.SMTPAuthenticationError:raise
        except (OSError,smtplib.SMTPException) as e:raise MailNotSent('Gmail was unreachable before sending') from e
        finally:del secret
        # From here on, a failure leaves transmission uncertain.
        with smtp as conn:refused=conn.send_message(message)
        if refused:raise PolicyError('The report recipient was refused')
        return {'accepted':True,'transport':'gmail_smtp_tls','message_id':message['Message-ID'],'recipient':report['recipient'],'delivery_note':'Gmail accepted the message; inbox delivery is not independently confirmed'}

class DailyReporter:
    def __init__(self,store):
        from .application_review import ApplicationReview
        self.store=store;self.p=ApplicationPilot(store);self.h=self.p.h;self.db=store.db;self.review=ApplicationReview(store)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS report_presentations (
            report_id TEXT PRIMARY KEY REFERENCES daily_reports(id),body_html TEXT NOT NULL,html_sha256 TEXT NOT NULL,template_version TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS report_html_frozen_update BEFORE UPDATE ON report_presentations
            WHEN (SELECT state FROM daily_reports WHERE id=OLD.report_id) IN ('SENDING','SENT','DELIVERY_UNKNOWN')
            BEGIN SELECT RAISE(ABORT,'Sent or in-flight email HTML is immutable'); END;
            CREATE TRIGGER IF NOT EXISTS report_html_frozen_delete BEFORE DELETE ON report_presentations
            WHEN (SELECT state FROM daily_reports WHERE id=OLD.report_id) IN ('SENDING','SENT','DELIVERY_UNKNOWN')
            BEGIN SELECT RAISE(ABORT,'Sent or in-flight email HTML is immutable'); END;
            CREATE TRIGGER IF NOT EXISTS report_html_frozen_insert BEFORE INSERT ON report_presentations
            WHEN (SELECT state FROM daily_reports WHERE id=NEW.report_id) IN ('SENDING','SENT','DELIVERY_UNKNOWN')
            BEGIN SELECT RAISE(ABORT,'Sent or in-flight email HTML is immutable'); END;''')
    def presentation(self,rid):
        r=self.db.execute('SELECT * FROM report_presentations WHERE report_id=?',(rid,)).fetchone()
        if not r:return {}
        if digest(r['body_html'].encode('utf-8'))!=r['html_sha256']:raise PolicyError('Email HTML integrity mismatch')
        return {'body_html':r['body_html'],'body_html_sha256':r['html_sha256'],'template_version':r['template_version']}
    def schedule(self):
        return self.h.settings().get('daily_report',{'hour':9,'minute':0,'timezone':'America/New_York','enabled':True})
    def render(self,instant=None,sample=False):
        """Same agent-curated decision brief for daily delivery and owner samples."""
        instant=instant or datetime.now(timezone.utc)
        local=instant.astimezone(ZoneInfo(self.schedule()['timezone']));day=local.date().isoformat()
        selected=self.h.daily_shortlist(instant)
        cards=[]
        lines=['A Story - '+('sample report' if sample else 'daily opportunities')+' - '+day,'',
               'TODAY\'S TOP '+str(len(selected))+' OPPORTUNITIES',
               'Prioritized from current saved research, including existing leads. Conditional options are marked REVIEW; they are not confirmed eligible or guaranteed awards.','']
        for n,d in enumerate(selected,1):
            start=len(lines)
            data=d['data'];a=d['analysis'];b=a['founder_brief'];fund=data['funding'];credits=data.get('credit_benefits',{})
            lines += [str(n)+'. '+data['canonical_name']+' - '+d['recommendation'],
                      'Why applicable: '+b['why_applicable'],
                      'How it helps A Story: '+b['how_it_helps']]
            value=credits.get('tier') or ''
            if fund.get('credits_value') is not None:
                value+=('; ' if value else '')+format(fund['credits_value'],',g')+' advertised credits'+(' ('+fund['currency']+')' if fund.get('currency') else ' (units/currency not established)')
            elif fund.get('cash_prize_max') is not None:
                value+=('; ' if value else '')+format(fund['cash_prize_max'],',g')+' cash ceiling'+(' '+fund['currency'] if fund.get('currency') else '')
            if fund.get('other_benefits'):value+=('; ' if value else '')+fund['other_benefits']
            lines.append('Benefit / tier: '+(value.rstrip('. ') or 'Amount not verified; see practical benefit above')+'. Advertised credits are not cash or guaranteed savings.')
            date=data['dates'];days=a['scoring']['dates']['days_remaining']
            deadline=date['deadline']
            if deadline:
                lines.append('Deadline: '+deadline+(' | '+str(days)+' days remaining' if days is not None else '')+' | '+(date['timezone'] or 'closing time / timezone UNKNOWN'))
            else:
                lines.append('Deadline: '+('Rolling applications; no fixed deadline published' if data['cycle_kind']=='rolling' else 'UNKNOWN - no verified closing date'))
            requirements=[v for v in data['eligibility'].values() if v]
            assets=[r.get('label',r['kind']) for r in data['requirements']]
            lines.append('Requirements: '+(' '.join(str(v) for v in requirements) or 'Complete official requirements still being verified.'))
            if assets:lines.append('Application materials: '+', '.join(assets))
            conditions=[credits[k] for k in ('renewal_behavior','stacking_restrictions') if credits.get(k)]
            if data['risks']:conditions+=data['risks'][:2]
            if conditions:lines.append('Costs / catches: '+' '.join(conditions))
            ready=a['materials'];hours=ready['estimated_hours'];pct=ready['percentage']
            draft=self.store.one('''SELECT count(q.id) total,sum(EXISTS(SELECT 1 FROM answer_versions v WHERE v.question_id=q.id AND length(trim(v.body))>0)) filled
                FROM questions q JOIN applications ap ON ap.id=q.application_id WHERE ap.opportunity_id=?''',(d['opportunity_id'],))
            progress=(str(draft['filled'] or 0)+'/'+str(draft['total'])+' saved draft answers; ' if draft['total'] else '')
            effort=str(hours)+' hours (planning estimate)' if hours is not None and data['questions_known'] is True else 'full application time not yet estimated'+(' (drafting baseline '+str(hours)+' hours)' if hours is not None else '')
            lines.append('Effort / readiness: '+progress+effort+'; '+(str(pct)+'% approved material reuse for known requirements' if pct is not None else 'reuse not yet verified'))
            lines.append('Application angle: '+b['application_angle'])
            lines.append('Agent next: '+b['agent_next_step'])
            lines.append('Your decision: '+('; '.join(b['owner_decisions']) if b['owner_decisions'] else 'None yet - agent research/preparation continues.'))
            lines.append('Eligibility: '+a['eligibility']['status']+' | Fit: '+(str(d['fit_score'])+'/100' if d['fit_score'] is not None else 'not established; no optimistic score assigned'))
            lines += ['Sources (checked '+d['last_verified'][:10]+'): '+', '.join(b['source_urls']),
                      'Open in Founder OS: '+founder_url('/opportunity/'+d['opportunity_id']),'']
            cards.append({'name':data['canonical_name'],'recommendation':d['recommendation'],'priority':b['priority'],
                          'fields':dict(line.split(': ',1) for line in lines[start:] if ': ' in line),
                          'checked':d['last_verified'][:10],'sources':b['source_urls'],
                          'os_url':founder_url('/opportunity/'+d['opportunity_id'])})
        dash=self.h.dashboard();auto=self.p.dashboard()
        d=self.digest(instant,local,dash,auto)
        html=render_digest(d,sample)
        body='\n'.join(self.digest_text(d))
        return {'local_date':day,'body':body,'body_html':html,'body_html_sha256':digest(html.encode('utf-8')),'template_version':TEMPLATE_VERSION,'shortlist':[x['opportunity_id'] for x in selected]}

    def digest(self,instant,local,dash,auto):
        """Structured daily brief: actions first, money rows, explicit access, waiting results."""
        from .application_drafter import application_list,access_status
        apps=application_list(self.store);by_opp={x['opportunity_id']:x for x in apps};board=dash['money_board']
        def when(d):
            days=d['analysis']['scoring']['dates']['days_remaining'];dl=d['data']['dates']['deadline']
            if days is None:return 'Rolling, no deadline' if d['data'].get('cycle_kind')=='rolling' else ('Deadline time unverified' if dl else 'No deadline published')
            if days<0:return 'Closed'
            if days==0:return 'Closes today'
            if days==1:return 'Closes tomorrow'
            return 'Closes in '+str(days)+' days'
        def row(d):
            m=d['analysis']['money'];oid=d['opportunity_id'];app=by_opp.get(oid)
            amount=('Up to $'+format(int(m['cash_max']),',')) if m.get('cash_max') else (('$'+format(int(m['credits_face_value']),',')+' credits') if m.get('credits_face_value') else ('Value unknown' if m['kind']=='CREDITS' else 'Amount unknown'))
            url=founder_url('/application/'+app['application_id']) if app and app['questions'] else founder_url('/opportunity/'+oid)
            return {'name':d['data']['canonical_name'],'amount':amount,'amount_known':bool(m.get('cash_max') or m.get('credits_face_value')),'when':when(d),
                    'access':app['access'] if app else access_status(self.store,oid,d['recommendation']),'url':url,'days':d['analysis']['scoring']['dates']['days_remaining']}
        cash=[row(d) for d in board['cash'][:6]];credits=[row(d) for d in board['credits'][:6]]
        closing=[r for r in cash+credits if r['days'] is not None and 0<=r['days']<=7]
        needs=[]
        if dash['needs_decision']:
            n=len(dash['needs_decision']);needs.append({'title':f'Confirm {n} company fact'+('s' if n!=1 else ''),'detail':'They decide which programs you qualify for.','url':founder_url('/decisions'),'link':'Review'})
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='inbox_messages'").fetchone():
            n=self.db.execute("SELECT COUNT(*) FROM inbox_messages WHERE state IN ('PROPOSED','REVIEW')").fetchone()[0]
            if n:needs.append({'title':f'Confirm {n} result'+('s' if n!=1 else '')+' found in your inbox','detail':'Acceptances, rejections or receipts from programs you applied to.','url':founder_url('/decisions'),'link':'Confirm'})
        for c in auto.get('confirmations',[]):
            if c.get('decision')=='PENDING':needs.append({'title':'Approve a filled application preview','detail':'The agent filled a simple form and is waiting for your exact approval.','url':founder_url('/applications'),'link':'Review'})
        for x in apps:
            if x['access']['level']=='READY' and x['questions'] and x['answered']<x['questions']:
                needs.append({'title':f"{x['program']}: {x['answered']} of {x['questions']} answers ready",'detail':f"{x['questions']-x['answered']} need you (things only you know, like IDs or links). Copy the rest and submit.",'url':founder_url('/application/'+x['application_id']),'link':'Open answers'})
        for r in closing:needs.append({'title':f"{r['name']}: {r['when'].lower()}",'detail':r['access']['label']+'.','url':r['url'],'link':'Open'})
        needs=needs[:6]
        tz=local.tzinfo
        waiting=[{'name':t['canonical_name'],'status':t['outcome']+' '+datetime.fromisoformat(t['occurred_at'].replace('Z','+00:00')).astimezone(tz).strftime('%b %d').replace(' 0',' ')} for t in board['tracked'] if t.get('waiting')]
        reach=[{'name':x['program'],'detail':f"{x['answered']} of {x['questions']} answers ready",'url':founder_url('/application/'+x['application_id'])} for x in apps if x['access']['level'] in ('READY','DRAFTING') and x['questions']]
        blocked=[{'name':x['program'],'detail':x['access']['label']} for x in apps if x['access']['level']=='BLOCKED']
        not_checked=[x['program'] for x in apps if x['access']['level']=='NOT_CHECKED']
        runs=dash['agent_activity'];forms=self.db.execute("SELECT COUNT(*) FROM form_inspections WHERE state='QUESTIONS_READ'").fetchone()[0] if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='form_inspections'").fetchone() else 0
        summary=((f"{len(needs)} thing{'s' if len(needs)!=1 else ''} need{'' if len(needs)!=1 else 's'} you. " if needs else 'Nothing needs you today. ')+f"{len(cash)} cash program{'s are' if len(cash)!=1 else ' is'} open"
                 +(f", {len(closing)} closing this week" if closing else '')+f". The agent can reach {len(reach)} application form{'s' if len(reach)!=1 else ''}; {len(blocked)} {'are' if len(blocked)!=1 else 'is'} blocked.")
        return {'date_label':local.strftime('%a %b %d').replace(' 0',' '),'headline':local.strftime('%A, %B %d').replace(' 0',' '),'summary':summary,'preheader':summary,
                'needs_you':needs,'cash':cash,'credits':credits,'closing_soon':len(closing),'waiting':waiting,
                'access':{'reach':reach,'blocked':blocked,'not_checked':not_checked},
                'agent_status':'Last research: '+((runs[0]['state'].lower()+' at '+runs[0]['started_at'][11:16]+' UTC on '+runs[0]['started_at'][:10]) if runs else 'none yet')+f'. Forms read so far: {forms}. As of '+local.strftime('%I:%M %p %Z').lstrip('0')+'.',
                'os_url':founder_url('/')}

    @staticmethod
    def digest_text(d):
        lines=['A Story - daily brief - '+d['headline'],'',d['summary'],'','NEEDS YOU TODAY']
        lines+=[f"{i}. {x['title']} - {x['detail']} {x['url']}" for i,x in enumerate(d['needs_you'],1)] or ['Nothing needs you today.']
        for title,rows in (('CASH ON THE TABLE',d['cash']),('CREDITS WORTH CLAIMING',d['credits'])):
            lines+=['',title]+([f"- {r['name']}: {r['amount']} | {r['when']} | {r['access']['label']}" for r in rows] or ['None right now.'])
        lines+=['','ACCESS REPORT','Agent can reach: '+(', '.join(f"{x['name']} ({x['detail']})" for x in d['access']['reach']) or 'none yet'),
                'Blocked: '+(', '.join(f"{x['name']} ({x['detail']})" for x in d['access']['blocked']) or 'nothing'),
                'Not checked yet: '+(', '.join(d['access']['not_checked']) or 'none'),'','WAITING ON RESULTS']
        lines+=[f"- {w['name']}: {w['status']}" for w in d['waiting']] or ['Nothing pending.']
        lines+=['',d['agent_status'],'Nothing is submitted for you. Questions and prepared answers are on the website.','Open Founder OS: '+d['os_url']]
        return lines

    def prepare_sample(self,instant=None):
        auth=self.p.authorization('daily_email_report')
        if not auth or auth['payload'].get('recipient')!='gbao.n.vo@gmail.com':raise PolicyError('Owner report permission is paused')
        rendered=self.render(instant,sample=True)
        message={'recipient':auth['payload']['recipient'],'subject':'A Story - your opportunity brief (design sample) - '+rendered['local_date'],'body':rendered['body'],**{k:rendered[k] for k in ('body_html','body_html_sha256','template_version')}}
        if ATTACH_QA_TXT:message['attachments']=[self.review.snapshot()]
        key='report-supplement-'+digest(message)[:24];message['id']=key
        self.db.execute("INSERT OR IGNORE INTO report_supplements VALUES(?,?,'PENDING',?,NULL,NULL)",(key,js(message),now()))
        self.store.log('report.sample_prepared','daily_reporter',{'id':key,'shortlist':rendered['shortlist'],'submitted':False})
        return key

    def prepare(self,instant=None):
        auth=self.p.authorization('daily_email_report')
        if not auth:raise PolicyError('Daily reporting is paused')
        instant=instant or datetime.now(timezone.utc);day=instant.astimezone(ZoneInfo(self.schedule()['timezone'])).date().isoformat()
        old=self.db.execute('SELECT * FROM daily_reports WHERE local_date=?',(day,)).fetchone()
        if old and old['state'] in ('SENT','SENDING','DELIVERY_UNKNOWN'):return dict(old)
        rendered=self.render(instant)
        include=ATTACH_QA_TXT
        rid='daily-report-'+digest(day)[:24];recipient=auth['payload']['recipient']
        if recipient!='gbao.n.vo@gmail.com':raise PolicyError('Report recipient is outside the authorized scope')
        self.db.execute("INSERT INTO daily_reports VALUES(?,?,?,?,?,'PENDING',?,NULL,NULL,NULL) ON CONFLICT(local_date) DO UPDATE SET subject=excluded.subject,body=excluded.body WHERE daily_reports.state IN ('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING')",(rid,day,recipient,'A Story - daily opportunity shortlist - '+day,rendered['body'],now()))
        self.db.execute('INSERT INTO report_presentations VALUES(?,?,?,?) ON CONFLICT(report_id) DO UPDATE SET body_html=excluded.body_html,html_sha256=excluded.html_sha256,template_version=excluded.template_version',(rid,rendered['body_html'],rendered['body_html_sha256'],TEMPLATE_VERSION))
        if include:
            attachment=self.review.snapshot()
            self.db.execute('INSERT INTO report_attachments VALUES(?,?) ON CONFLICT(report_id) DO UPDATE SET artifact_id=excluded.artifact_id',(rid,attachment['artifact_id']))
        return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))

    def send(self,rid,transport=None):
        auth=self.p.authorization('daily_email_report');r=self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        if not auth or r['recipient']!=auth['payload']['recipient']:raise PolicyError('Daily-report authorization is paused or changed')
        if r['state'] in ('SENT','SENDING','DELIVERY_UNKNOWN'):return r
        # State guards: the connector may claim between the read above and these writes.
        if transport is None and self.h.settings().get('mail_delivery',{}).get('mode')=='gmail_connector':
            self.db.execute("UPDATE daily_reports SET state='CONNECTOR_PENDING',error='Queued for the connected Gmail scheduled sender' WHERE id=? AND state IN "+str(PENDING),(rid,));return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        transport=transport or GmailTransport()
        if not transport.available():
            self.db.execute("UPDATE daily_reports SET state='MAIL_CONNECTION_REQUIRED',error='Connect the local Gmail sender; report saved, no email sent' WHERE id=? AND state IN "+str(PENDING),(rid,));return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        with self.store.transaction():
            changed=self.db.execute("UPDATE daily_reports SET state='SENDING',error=NULL WHERE id=? AND state IN ('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING')",(rid,)).rowcount
            if not changed:return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
            self.store.log('report.send_intent','daily_reporter',{'report_id':rid,'recipient':r['recipient'],'authorization_id':auth['id']})
        try:
            receipt=transport.send({**r,**self.presentation(rid),'attachments':self.review.report_attachment(rid)})
            if receipt.get('accepted') is not True:raise PolicyError('No confirmed mail-transport acceptance')
            self.db.execute("UPDATE daily_reports SET state='SENT',sent_at=?,receipt_json=?,error=NULL WHERE id=?",(now(),js(receipt),rid));self.store.log('report.sent','daily_reporter',{'report_id':rid,'receipt':receipt})
        except smtplib.SMTPAuthenticationError:
            self.db.execute("UPDATE daily_reports SET state='MAIL_CONNECTION_REQUIRED',error='Gmail rejected the connection. Reconnect the local sender; no message was sent' WHERE id=?",(rid,))
            self.store.log('report.smtp_auth_failed','daily_reporter',{'report_id':rid})
        except MailNotSent:
            self.db.execute("UPDATE daily_reports SET state=?,error='Gmail was unreachable before sending; no message was sent. Will try again.' WHERE id=?",(r['state'],rid))
        except Exception:
            self.db.execute("UPDATE daily_reports SET state='DELIVERY_UNKNOWN',error='Mail transmission failed or was uncertain; no automatic resend' WHERE id=?",(rid,))
        return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))

    def fallback_due(self,instant):
        """Owner-approved SMTP fallback for days the connected Gmail sender never claimed."""
        fb=self.h.settings().get('mail_delivery',{}).get('smtp_fallback') or {}
        if fb.get('enabled') is not True:return False
        schedule=self.schedule();local=instant.astimezone(ZoneInfo(schedule['timezone']))
        return local.hour*60+local.minute>=schedule['hour']*60+schedule['minute']+int(fb.get('after_minutes',30))

    def fallback(self,rid,transport=None):
        """Send a never-claimed report locally. Claimed, sent or uncertain reports are left alone."""
        r=self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        if r['state']!='CONNECTOR_PENDING':return r
        # One rejected app password stops the fallback for that day; no lockout loop.
        if self.db.execute("SELECT 1 FROM audit WHERE event='report.smtp_auth_failed' AND json_extract(payload_json,'$.report_id')=?",(rid,)).fetchone():return r
        transport=transport or GmailTransport()
        if not transport.available():
            self.db.execute("UPDATE daily_reports SET error='Connected Gmail sender has not sent yet; local fallback not connected (run Connect-Report-Email.ps1). No email sent.' WHERE id=? AND state='CONNECTOR_PENDING'",(rid,))
            return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        self.store.log('report.smtp_fallback','daily_reporter',{'report_id':rid,'reason':'connected Gmail sender had not claimed by the fallback time'})
        return self.send(rid,transport)

    def supersede(self,rid,reason,actor='owner'):
        """Close a past day's never-claimed report without sending it."""
        if actor!='owner' or not reason.strip():raise PolicyError('Only the owner can supersede a report, with a reason')
        r=self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        today=datetime.now(timezone.utc).astimezone(ZoneInfo(self.schedule()['timezone'])).date().isoformat()
        if r['local_date']>=today:raise PolicyError('Only a past day report can be superseded')
        with self.store.transaction():
            if not self.db.execute("UPDATE daily_reports SET state='SUPERSEDED',error=? WHERE id=? AND state IN "+str(PENDING),('Not sent: '+reason,rid)).rowcount:
                raise PolicyError('Report was claimed, sent or is uncertain; it cannot be superseded')
            self.store.log('report.superseded',actor,{'report_id':rid,'local_date':r['local_date'],'reason':reason,'sent':False})
        return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))

    def poll(self,instant=None):
        instant=instant or datetime.now(timezone.utc);schedule=self.schedule();auth=self.p.authorization('daily_email_report')
        if not auth or not schedule.get('enabled'):return {'paused':True}
        local=instant.astimezone(ZoneInfo(schedule['timezone']))
        if (local.hour,local.minute)<(schedule['hour'],schedule['minute']):return {'waiting':True}
        r=self.prepare(instant)
        # Rebuild a blocked draft from current state after the mail account is connected.
        # Never send a backlog; only today's report is considered on each poll.
        r=self.send(r['id'])
        if r['state']=='CONNECTOR_PENDING' and self.fallback_due(instant):r=self.fallback(r['id'])
        return r
