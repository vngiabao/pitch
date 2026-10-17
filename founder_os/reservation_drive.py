"""Reservation drive: the $1 reservation push to the leads and beta families before November 2, 2026.

Bao supplies the people as a CSV; nothing here invents a name. Each person becomes a contact tagged with the
campaign key, due today, so the Follow-up drafter writes one note per worker cycle with a drive-specific task:
leads get a personal note about the $1 reservation (15 percent off the first year of Individual), beta families
get a thank-you with one referral ask. Every note passes Fact Guard and Bao's Voice like any growth draft.
Bao copies and sends each note from his own email, then records what happened. Nothing here emails anyone.
"""
import csv
import io
from datetime import date,timedelta
from .store import now,uid
from .growth_agents import Growth,today,text

CAMPAIGN='reservation-2026'
DEADLINE=date(2026,11,2)
NUDGE_DAYS=(date(2026,10,26),date(2026,10,30),date(2026,11,1))
KINDS={'lead':'Lead','beta':'Beta family'}
KIND_ALIASES={'lead':'lead','leads':'lead','beta':'beta','beta family':'beta','beta families':'beta','family':'beta','beta_family':'beta','beta-family':'beta'}
STATES=('NEW','SENT','REPLIED','RESERVED')
STATE_WORDS={'NEW':'Not yet written','READY':'Note ready','SENT':'Sent','REPLIED':'Replied','RESERVED':'Reserved'}
ROW_LIMIT=500

SCHEMA='''
CREATE TABLE IF NOT EXISTS drive_members(id TEXT PRIMARY KEY,campaign TEXT NOT NULL,contact_id TEXT NOT NULL REFERENCES contacts(id),kind TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'NEW',sent_on TEXT,replied_on TEXT,reserved_on TEXT,referrals INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(campaign,contact_id));
'''


def days_left(on=None):return (DEADLINE-(on or today())).days


def _table_exists(db):return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='drive_members'").fetchone())


def member_ids(store):
    """Contacts in the drive, so the generic follow-up alert leaves them to the drive's own nudges. Safe before the table exists."""
    if not _table_exists(store.db):return set()
    return {r[0] for r in store.db.execute('SELECT contact_id FROM drive_members WHERE campaign=?',(CAMPAIGN,))}


def drive_task(store,cid):
    """The drafter's task for a drive member, or None so the generic follow-up task applies."""
    if not _table_exists(store.db):return None
    m=store.db.execute('SELECT kind,state FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid)).fetchone()
    if not m or today()>DEADLINE:return None
    offer=('The pre-launch offer, exactly as pricing states it: reserve the Individual plan for $1 at astoryapp.com by November 2 and hold 15 percent off the first year. '
           'Name the date; do not count days. Use prices only from CONTEXT.pricing.')
    if m['kind']=='lead':
        if m['state']=='NEW':
            return ('Write a short personal note from Bao to this lead, who showed interest in the first version of A Story (see context). Pick up from what they told us, say the app is nearly ready, and explain the one easy step: reserve for $1. '
                    +offer+' Under 120 words. Give a subject line in title.')
        if m['state']=='SENT':
            return ('Write a short, kind reminder from Bao to this lead, who already received a note about the $1 reservation (see conversation_log). No guilt, no pressure words. One line on where the app stands from the approved statements, then the one step: reserve for $1 before November 2. '
                    +offer+' Under 90 words. Give a subject line in title.')
        return None
    if m['state']=='NEW':
        return ('Write a short thank-you note from Bao to this beta family for being part of the private beta. Thank them for something concrete from context when it is given; never invent what happened on their calls. '
                'Then make exactly one referral ask: do they know one family who would want this for a parent or grandparent before the holidays? Mention the reservation offer as the reason to pass it on now. '
                +offer+' Under 120 words. Give a subject line in title.')
    return None


class ReservationDrive:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.g=Growth(store)
        for statement in SCHEMA.split(';'):
            if statement.strip():self.db.execute(statement)

    # ---------- the loader ----------
    def import_csv(self,raw):
        """Rows of name, email, context, kind (Lead or Beta family). Duplicates by email are skipped; a known contact is enrolled, not copied."""
        raw=(raw or '').lstrip('﻿')
        if not raw.strip():raise ValueError('Paste or choose a CSV with a header row: name, email, context, kind')
        reader=csv.reader(io.StringIO(raw))
        try:header=[h.strip().lower().lstrip('﻿') for h in next(reader)]
        except StopIteration:raise ValueError('The CSV is empty')
        col={}
        for i,h in enumerate(header):
            key={'name':'name','full name':'name','email':'email','e-mail':'email','email address':'email','context':'context','notes':'context','note':'context','kind':'kind','type':'kind','group':'kind'}.get(h)
            if key and key not in col:col[key]=i
        if 'name' not in col or 'email' not in col:raise ValueError('The header row needs name and email columns (context and kind are optional)')
        report={'created':0,'enrolled':0,'skipped':0,'rejected':[],'rows':0};seen=set()
        for n,row in enumerate(reader,start=2):
            if not any(cell.strip() for cell in row):continue
            report['rows']+=1
            if report['rows']>ROW_LIMIT:raise ValueError('At most '+str(ROW_LIMIT)+' rows per file')
            cell=lambda k:row[col[k]].strip() if k in col and col[k]<len(row) else ''
            name,email,context=cell('name')[:120],cell('email')[:200],cell('context')[:2000]
            kind=KIND_ALIASES.get(cell('kind').lower() or 'lead')
            if not name:report['rejected'].append({'row':n,'reason':'no name'});continue
            if '@' not in email or ' ' in email:report['rejected'].append({'row':n,'reason':'no usable email','name':name});continue
            if not kind:report['rejected'].append({'row':n,'reason':'kind must be Lead or Beta family','name':name});continue
            if email.lower() in seen:report['skipped']+=1;continue
            seen.add(email.lower())
            existing=self.db.execute('SELECT id FROM contacts WHERE lower(email)=?',(email.lower(),)).fetchone()
            if existing:
                if self.db.execute('SELECT 1 FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,existing['id'])).fetchone():report['skipped']+=1;continue
                self.db.execute("UPDATE contacts SET next_followup_on=COALESCE(next_followup_on,?),state='ACTIVE',updated_at=? WHERE id=?",(today().isoformat(),now(),existing['id']))
                self._enroll(existing['id'],kind);report['enrolled']+=1;continue
            c=self.g.add_contact({'name':name,'kind':'Customer','email':email,'context':context,'next_followup_on':today().isoformat(),'cadence_days':7})
            self._enroll(c['id'],kind);report['created']+=1
        self.s.log('drive.imported','owner',{'campaign':CAMPAIGN,**{k:v for k,v in report.items() if k!='rejected'},'rejected':len(report['rejected'])})
        return report

    def _enroll(self,cid,kind):
        self.db.execute('INSERT INTO drive_members(id,campaign,contact_id,kind,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(uid('drive'),CAMPAIGN,cid,kind,'NEW',now(),now()))

    # ---------- the people in it ----------
    def member(self,cid):
        m=self.s.one('SELECT * FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid))
        c=self.g.contact(cid)
        shown='READY' if m['state']=='NEW' and c['draft'] else m['state']
        return {**m,'name':c['name'],'email':c['email'],'context':c['context'],'kind_words':KINDS[m['kind']],'draft':c['draft'],'drafting':c['drafting'],'touches':c['touches'],
                'shown':shown,'state_words':STATE_WORDS[shown],'contact_state':c['state']}

    def members(self):
        ids=[r['contact_id'] for r in self.s.rows('SELECT m.contact_id FROM drive_members m JOIN contacts c ON c.id=m.contact_id WHERE m.campaign=? ORDER BY m.kind,c.name',(CAMPAIGN,))]
        return [self.member(i) for i in ids]

    def counts(self,members=None):
        members=self.members() if members is None else members
        out={k:0 for k in ('not_written','ready','sent','replied','reserved')}
        for m in members:out[{'NEW':'not_written','READY':'ready','SENT':'sent','REPLIED':'replied','RESERVED':'reserved'}[m['shown']]]+=1
        out['total']=len(members);out['unsent']=out['not_written']+out['ready'];out['referrals']=sum(m['referrals'] for m in members)
        out['leads']=len([m for m in members if m['kind']=='lead']);out['beta']=len([m for m in members if m['kind']=='beta'])
        return out

    # ---------- what Bao records ----------
    def _set(self,cid,**fields):
        fields['updated_at']=now()
        self.db.execute('UPDATE drive_members SET '+','.join(k+'=?' for k in fields)+' WHERE campaign=? AND contact_id=?',(*fields.values(),CAMPAIGN,cid))

    def mark_sent(self,cid):
        """Bao sent the note from his own email. Logs the touch (which retires the draft) and schedules the next look."""
        m=self.s.one('SELECT * FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid));t=today()
        if m['kind']=='lead':nxt=min(t+timedelta(days=7),DEADLINE-timedelta(days=3)) if t<DEADLINE-timedelta(days=3) else DEADLINE+timedelta(days=8)
        else:nxt=t+timedelta(days=30)
        summary='Sent the reservation note.' if m['kind']=='lead' else 'Sent the thank-you note with the referral ask.'
        self.g.log_touch(cid,{'summary':summary,'next_followup_on':nxt.isoformat()})
        if m['state']=='NEW':self._set(cid,state='SENT',sent_on=t.isoformat())
        self.s.log('drive.sent','owner',{'contact_id':cid,'kind':m['kind']})
        return self.member(cid)

    def mark_replied(self,cid,note=''):
        m=self.s.one('SELECT * FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid))
        self.g.log_touch(cid,{'summary':('They replied. '+text(note,1000,'Note')).strip(),'next_followup_on':(today()+timedelta(days=3)).isoformat()})
        if m['state'] in ('NEW','SENT'):self._set(cid,state='REPLIED',replied_on=today().isoformat())
        return self.member(cid)

    def mark_reserved(self,cid):
        """They reserved for $1. One purchase for the email channel this week, so channel math sees the drive."""
        m=self.s.one('SELECT * FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid))
        if m['state']=='RESERVED':return self.member(cid)
        name=self.s.one('SELECT name FROM contacts WHERE id=?',(cid,))['name']
        self.g.log_touch(cid,{'summary':'Reserved A Story for $1 (15 percent off the first year).','next_followup_on':(DEADLINE+timedelta(days=8)).isoformat()})
        self._channel_entry('email',purchases=1,revenue=1.0,note='Reservation drive: '+name+' reserved')
        self._set(cid,state='RESERVED',reserved_on=today().isoformat())
        self.s.log('drive.reserved','owner',{'contact_id':cid,'kind':m['kind']})
        return self.member(cid)

    def mark_referred(self,cid,who=''):
        """They referred someone. One signup for the referrals channel this week. The referred family is not added unless Bao adds them."""
        m=self.s.one('SELECT * FROM drive_members WHERE campaign=? AND contact_id=?',(CAMPAIGN,cid))
        who=text(who,200,'Who they referred');name=self.s.one('SELECT name FROM contacts WHERE id=?',(cid,))['name']
        self.g.log_touch(cid,{'summary':'Referred someone to A Story'+(': '+who if who else '')+'.','next_followup_on':(today()+timedelta(days=14)).isoformat()})
        self._channel_entry('referrals',signups=1,note='Reservation drive: referral from '+name+(' ('+who+')' if who else ''))
        fields={'referrals':m['referrals']+1}
        if m['state'] in ('NEW','SENT'):fields.update(state='REPLIED',replied_on=today().isoformat())
        self._set(cid,**fields)
        self.s.log('drive.referred','owner',{'contact_id':cid,'kind':m['kind']})
        return self.member(cid)

    def _channel_entry(self,channel,signups=0,purchases=0,revenue=0.0,note=''):
        from .growth_desk import GrowthDesk
        GrowthDesk(self.s)  # makes sure channel_entries exists
        week=(today()-timedelta(days=today().weekday())).isoformat()
        self.db.execute('INSERT INTO channel_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',(uid('entry'),channel,week,0,signups,purchases,0.0,revenue,'reservation_drive',note[:300],now()))

    # ---------- the page, Today and the daily email ----------
    def board(self):
        members=self.members();c=self.counts(members);left=days_left()
        return {'campaign':CAMPAIGN,'deadline':DEADLINE.isoformat(),'days_left':left,'today':today().isoformat(),'counts':c,'members':members,
                'states':[{'key':k,'label':STATE_WORDS[k]} for k in ('NEW','READY','SENT','REPLIED','RESERVED')],'kinds':[{'key':k,'label':v} for k,v in KINDS.items()],
                'entries':self.s.rows("SELECT channel,week_start,signups,purchases,revenue_usd,note,created_at FROM channel_entries WHERE source='reservation_drive' ORDER BY created_at DESC LIMIT 40") if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='channel_entries'").fetchone() else [],
                'nudge_days':[d.isoformat() for d in NUDGE_DAYS]}

    def alerts(self,on=None):
        """Notes ready to send any day; on October 26, October 30 and November 1 a count of what is still unsent."""
        on=on or today();items=[]
        if on>DEADLINE:return items
        c=self.counts();left=days_left(on);when=str(left)+(' day' if left==1 else ' days')+' to November 2' if left>0 else 'the reservation closes today'
        if on in NUDGE_DAYS and c['unsent']:
            items.append({'title':'Reservation drive: '+str(c['unsent'])+(' note' if c['unsent']==1 else ' notes')+' still unsent, '+when,
                          'detail':(str(c['ready'])+' ready to copy, '+str(c['not_written'])+' still being written. ' if c['not_written'] else str(c['ready'])+' ready to copy. ')+str(c['reserved'])+' reserved and '+str(c['referrals'])+' referrals so far.','url':'/drive','link':'Open the drive'})
        elif c['ready']:
            items.append({'title':str(c['ready'])+(' reservation note' if c['ready']==1 else ' reservation notes')+' ready to send','detail':'Copy each one and send it from your own email, then press "I sent it". '+when[0].upper()+when[1:]+'.','url':'/drive','link':'Open the drive'})
        return items
