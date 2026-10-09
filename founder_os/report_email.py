"""Daily report outbox. Gmail password lives only in Windows Credential Manager."""
import ctypes,json,smtplib,ssl
from ctypes import wintypes
from datetime import datetime,timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo
from .store import now,js,digest,PolicyError
from .application_pilot import ApplicationPilot
from .email_design import render_email,TEMPLATE_VERSION
from .owner_links import founder_url

CREDENTIAL_TARGET='AStoryFounderOS:DailyReport:gbao.n.vo@gmail.com'
class Credential(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),('CredentialBlob',ctypes.POINTER(ctypes.c_byte)),('Persist',wintypes.DWORD),('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]

def credential_present():
    try:read_credential();return True
    except (PolicyError,OSError):return False

def read_credential():
    if not hasattr(ctypes,'WinDLL'):raise PolicyError('Windows mail credential unavailable')
    lib=ctypes.WinDLL('Advapi32.dll',use_last_error=True);ptr=ctypes.POINTER(Credential)()
    lib.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))];lib.CredReadW.restype=wintypes.BOOL
    lib.CredFree.argtypes=[ctypes.c_void_p]
    if not lib.CredReadW(CREDENTIAL_TARGET,1,0,ctypes.byref(ptr)):raise PolicyError('Connect Gmail for scheduled reports; no mail credential is stored')
    try:
        c=ptr.contents
        if c.UserName!='gbao.n.vo@gmail.com':raise PolicyError('Report mail account does not match owner authorization')
        return ctypes.string_at(c.CredentialBlob,c.CredentialBlobSize).decode('utf-16-le')
    finally:lib.CredFree(ptr)

def store_credential(secret):
    # Used only by the owner setup helper; never exposed through the web server.
    if not hasattr(ctypes,'WinDLL'):raise PolicyError('Windows Credential Manager is required')
    if len(secret.replace(' ',''))!=16 or not secret.replace(' ','').isalnum():raise PolicyError('Use a Google app password, not your Google account password')
    raw=secret.replace(' ','').encode('utf-16-le');blob=(ctypes.c_byte*len(raw)).from_buffer_copy(raw)
    c=Credential();c.Type=1;c.TargetName=CREDENTIAL_TARGET;c.CredentialBlobSize=len(raw);c.CredentialBlob=blob;c.Persist=2;c.UserName='gbao.n.vo@gmail.com';c.Comment='A Story daily-report sender; this Windows user only'
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
        with smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=30,context=ssl.create_default_context()) as smtp:
            smtp.login('gbao.n.vo@gmail.com',secret);refused=smtp.send_message(message)
        del secret
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
        if not selected:lines+=['No sufficiently researched, relevant opportunities to recommend today. The agent will continue verification; no generic review backlog is being handed to you.','']
        elif len(selected)<5:lines+=['Showing fewer than five because the remaining records do not meet the research and relevance checks.','']
        dash=self.h.dashboard();auto=self.p.dashboard();runs=dash['agent_activity']
        lines+=['AGENT STATUS',str(len(dash['opportunities']))+' tracked; '+str(sum(p['state']=='SUBMITTED' for p in auto['plans']))+' confirmed submissions.',
                'Last research: '+(runs[0]['state']+' at '+runs[0]['started_at'] if runs else 'No completed run yet'),
                'As of '+local.strftime('%I:%M %p %Z')+'. Each source retains its own verification date.',
                'Applications are drafts until you approve an exact emailed preview. This report does not authorize any submission.']
        auth=self.p.authorization('daily_email_report')
        if auth and auth['payload'].get('question_answer_attachments') is True:
            lines.append('Your private question-and-answer text preview is attached. It includes unfinished work and saved draft essays; it is not submission approval.')
        html=render_email(day,cards,' '.join(lines[lines.index('AGENT STATUS')+1:lines.index('AGENT STATUS')+4]),bool(auth and auth['payload'].get('question_answer_attachments') is True),sample)
        return {'local_date':day,'body':'\n'.join(lines),'body_html':html,'body_html_sha256':digest(html.encode('utf-8')),'template_version':TEMPLATE_VERSION,'shortlist':[d['opportunity_id'] for d in selected]}

    def prepare_sample(self,instant=None):
        auth=self.p.authorization('daily_email_report')
        if not auth or auth['payload'].get('recipient')!='gbao.n.vo@gmail.com':raise PolicyError('Owner report permission is paused')
        rendered=self.render(instant,sample=True)
        message={'recipient':auth['payload']['recipient'],'subject':'A Story - your opportunity brief (design sample) - '+rendered['local_date'],'body':rendered['body'],**{k:rendered[k] for k in ('body_html','body_html_sha256','template_version')}}
        if auth['payload'].get('question_answer_attachments') is True:message['attachments']=[self.review.snapshot()]
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
        include=auth['payload'].get('question_answer_attachments') is True
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
        if transport is None and self.h.settings().get('mail_delivery',{}).get('mode')=='gmail_connector':
            self.db.execute("UPDATE daily_reports SET state='CONNECTOR_PENDING',error='Queued for the connected Gmail scheduled sender' WHERE id=?",(rid,));return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
        transport=transport or GmailTransport()
        if not transport.available():
            self.db.execute("UPDATE daily_reports SET state='MAIL_CONNECTION_REQUIRED',error='Connect the local Gmail sender; report saved, no email sent' WHERE id=?",(rid,));return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))
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
        except Exception:
            self.db.execute("UPDATE daily_reports SET state='DELIVERY_UNKNOWN',error='Mail transmission failed or was uncertain; no automatic resend' WHERE id=?",(rid,))
        return self.store.one('SELECT * FROM daily_reports WHERE id=?',(rid,))

    def poll(self,instant=None):
        instant=instant or datetime.now(timezone.utc);schedule=self.schedule();auth=self.p.authorization('daily_email_report')
        if not auth or not schedule.get('enabled'):return {'paused':True}
        local=instant.astimezone(ZoneInfo(schedule['timezone']))
        if (local.hour,local.minute)<(schedule['hour'],schedule['minute']):return {'waiting':True}
        r=self.prepare(instant)
        # Rebuild a blocked draft from current state after the mail account is connected.
        # Never send a backlog; only today's report is considered on each poll.
        return self.send(r['id'])
