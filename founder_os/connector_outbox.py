"""Durable handoff to the owner's connected Gmail tools; never extracts credentials.

The scheduled chat claims one exact message before calling Gmail, then records
its real response. SENDING/unknown messages are never automatically reclaimed.
"""
import json
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from .store import now,js,digest,PolicyError
from .application_pilot import ApplicationPilot
from .report_email import DailyReporter

OWNER='gbao.n.vo@gmail.com'
PENDING=('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING')

class ConnectorOutbox:
    def __init__(self,store):
        self.s=store;self.p=ApplicationPilot(store);self.h=self.p.h;self.db=store.db;self.reporter=DailyReporter(store);self.review=self.reporter.review

    def _message(self,kind,key):
        if kind=='report':
            r=self.s.one('SELECT * FROM daily_reports WHERE id=?',(key,));m={'id':r['id'],'recipient':r['recipient'],'subject':r['subject'],'body':r['body']};state=r['state']
            m.update(self.reporter.presentation(key))
            attachments=self.review.report_attachment(key)
            if attachments:m['attachments']=attachments
        elif kind=='preview':
            r=self.s.one('SELECT * FROM application_confirmations WHERE id=?',(key,));m=json.loads(r['email_json']);state=r['email_state']
        elif kind=='supplement':
            r=self.s.one('SELECT * FROM report_supplements WHERE id=?',(key,));m=json.loads(r['message_json']);state=r['state']
        else:raise PolicyError('Unknown mail kind')
        if 'body_html' in m and digest(m['body_html'].encode('utf-8'))!=m.get('body_html_sha256'):raise PolicyError('Email HTML integrity mismatch')
        for a in m.get('attachments',[]):
            if a['mime_type']!='text/plain' or digest(a['content'].encode('utf-8'))!=a['sha256'] or len(a['content'].encode('utf-8'))>2_000_000:raise PolicyError('Invalid question-and-answer text attachment')
        return m,state

    def _validate(self,kind,key):
        if self.h.settings().get('mail_delivery',{}).get('mode')!='gmail_connector':raise PolicyError('Connected Gmail delivery is not configured')
        if kind=='report':
            r=self.s.one('SELECT * FROM daily_reports WHERE id=?',(key,));a=self.p.authorization('daily_email_report')
            if not a or a['payload'].get('recipient')!=OWNER or r['recipient']!=OWNER:raise PolicyError('Report permission is paused or recipient changed')
            zone=ZoneInfo(self.reporter.schedule()['timezone'])
            if r['local_date']!=datetime.now(timezone.utc).astimezone(zone).date().isoformat():raise PolicyError('Only today\'s report may be sent; no backlog')
            if self.review.report_attachment(key) and a['payload'].get('question_answer_attachments') is not True:raise PolicyError('Owner text-preview attachment authorization is paused')
            return self._message(kind,key)
        if kind=='supplement':
            a=self.p.authorization('daily_email_report')
            if not a or a['payload'].get('recipient')!=OWNER or a['payload'].get('question_answer_attachments') is not True:raise PolicyError('Owner text-preview report authorization is paused')
            m,state=self._message(kind,key)
            if m['recipient']!=OWNER:raise PolicyError('Supplement recipient is outside owner scope')
            return m,state
        if kind=='preview':
            c=self.s.one('SELECT * FROM application_confirmations WHERE id=?',(key,))
            if not self.p.authorization('free_application_pilot') or c['decision']!='PENDING':raise PolicyError('Preview permission is paused or owner already decided')
            old=self.p.plan(c['plan_id']);current=self.p.build(old['opportunity_id'])
            if current['blockers'] or digest(current['payload'])!=c['payload_sha256']:raise PolicyError('Preview is stale; prepare a new exact preview')
            m=json.loads(c['email_json'])
            if m['recipient']!=OWNER:raise PolicyError('Preview destination is outside owner scope')
            return self._message(kind,key)
        raise PolicyError('Unknown mail kind')

    def pending(self,instant=None):
        instant=instant or datetime.now(timezone.utc);messages=[]
        self.p.reconcile_placeholders()
        reporter=self.reporter;schedule=reporter.schedule();local=instant.astimezone(ZoneInfo(schedule['timezone']))
        if self.p.authorization('daily_email_report') and schedule.get('enabled') and (local.hour,local.minute)>=(schedule['hour'],schedule['minute']):
            r=reporter.prepare(instant)
            if r['state'] in PENDING:messages.append({'kind':'report','id':r['id']})
        for c in self.s.rows("SELECT id FROM application_confirmations WHERE decision='PENDING' AND email_state IN ('PENDING','MAIL_CONNECTION_REQUIRED','CONNECTOR_PENDING') ORDER BY created_at"):
            try:self._validate('preview',c['id']);messages.append({'kind':'preview','id':c['id']})
            except PolicyError:continue
        for r in self.s.rows("SELECT id FROM report_supplements WHERE state='PENDING' ORDER BY created_at"):
            try:self._validate('supplement',r['id']);messages.append({'kind':'supplement','id':r['id']})
            except PolicyError:continue
        return messages

    def claim(self,kind,key):
        with self.s.transaction():
            message,state=self._validate(kind,key)
            if state not in PENDING:raise PolicyError('Message is already sent, in flight or uncertain; do not resend')
            table,column=('daily_reports','state') if kind=='report' else ('report_supplements','state') if kind=='supplement' else ('application_confirmations','email_state')
            self.db.execute(f"UPDATE {table} SET {column}='SENDING' WHERE id=?",(key,))
            if kind=='report':self.db.execute('UPDATE daily_reports SET error=NULL WHERE id=?',(key,))
            sha=digest(message)
            self.s.log('mail.connector_send_intent','gmail_connector',{'kind':kind,'id':key,'message_sha256':sha,'recipient':OWNER})
        return {'kind':kind,'id':key,'message_sha256':sha,'message':message}

    def complete(self,kind,key,sha,gmail_message_id,account):
        if account!=OWNER or not isinstance(gmail_message_id,str) or not gmail_message_id.strip():raise PolicyError('A real Gmail message ID from the authorized account is required')
        with self.s.transaction():
            # Once a send began, record its actual outcome even if scope was
            # revoked meanwhile. Revocation cannot undo an external email.
            message,state=self._message(kind,key)
            if state!='SENDING' or digest(message)!=sha:raise PolicyError('Exact in-flight message receipt mismatch')
            receipt={'accepted':True,'transport':'connected_gmail','gmail_message_id':gmail_message_id,'account':account,'recipient':OWNER,'recorded_at':now(),'inbox_delivery':'not independently confirmed'}
            if kind=='report':self.db.execute("UPDATE daily_reports SET state='SENT',sent_at=?,receipt_json=?,error=NULL WHERE id=?",(now(),js(receipt),key))
            elif kind=='supplement':self.db.execute("UPDATE report_supplements SET state='SENT',sent_at=?,receipt_json=? WHERE id=?",(now(),js(receipt),key))
            else:
                r=self.s.one('SELECT * FROM application_confirmations WHERE id=?',(key,))
                self.db.execute("UPDATE application_confirmations SET email_state='SENT',email_receipt_json=? WHERE id=?",(js(receipt),key))
                self.db.execute("UPDATE application_plans SET state='AWAITING_CONFIRMATION' WHERE id=?",(r['plan_id'],))
            self.s.log('mail.connector_sent','gmail_connector',{'kind':kind,'id':key,'message_sha256':sha,'receipt':receipt})
        return {'state':'SENT','id':key,'receipt':receipt}

    def uncertain(self,kind,key):
        table,column=('daily_reports','state') if kind=='report' else ('report_supplements','state') if kind=='supplement' else ('application_confirmations','email_state') if kind=='preview' else (None,None)
        if not table:raise PolicyError('Unknown mail kind')
        self.db.execute(f"UPDATE {table} SET {column}='DELIVERY_UNKNOWN' WHERE id=? AND {column}='SENDING'",(key,))
        self.s.log('mail.connector_unknown','gmail_connector',{'kind':kind,'id':key,'note':'No automatic resend; reconcile Gmail history'})
        return {'state':'DELIVERY_UNKNOWN','id':key}
