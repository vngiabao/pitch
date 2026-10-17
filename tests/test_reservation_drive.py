import os
import unittest
from datetime import date,timedelta
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os.growth_agents import Growth,FOLLOWUP_PREFIX,today
from founder_os.growth_desk import GrowthDesk
from founder_os.reservation_drive import ReservationDrive,CAMPAIGN,DEADLINE,NUDGE_DAYS,drive_task,member_ids

CSV='''name,email,context,kind
Linh Pham,linh@example.com,Signed up after the Columbus demo night,Lead
Minh Le,MINH@example.com,Asked about pricing for his mother,lead
The Tran family,tran@example.com,Beta since September,Beta family
Linh Pham again,linh@example.com,duplicate email,Lead
No Email,,no address,Lead
Odd Kind,odd@example.com,unknown group,Investor
'''


class ReservationDriveTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown

    def drive(self):return ReservationDrive(self.s)

    def test_loader_tags_people_and_skips_duplicates_by_email(self):
        d=self.drive();r=d.import_csv(CSV)
        self.assertEqual((r['created'],r['enrolled'],r['skipped'],len(r['rejected']),r['rows']),(3,0,1,2,6))
        self.assertEqual({x['reason'] for x in r['rejected']},{'no usable email','kind must be Lead or Beta family'})
        members=d.members()
        self.assertEqual([(m['name'],m['kind'],m['shown']) for m in members],[('The Tran family','beta','NEW'),('Linh Pham','lead','NEW'),('Minh Le','lead','NEW')])
        self.assertTrue(all(m['campaign']==CAMPAIGN for m in members))
        # Every contact is a Customer, due today, so the Follow-up drafter picks it up one per cycle.
        g=Growth(self.s)
        for m in members:
            c=g.contact(m['contact_id']);self.assertEqual((c['kind'],c['next_followup_on'],c['due']),('Customer',today().isoformat(),True))
        # Loading the same file again creates nothing and copies no one.
        r=d.import_csv(CSV);self.assertEqual((r['created'],r['enrolled'],r['skipped']),(0,0,4))
        self.assertEqual(len(d.members()),3);self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],3)
        # A person already in People with that email is enrolled, not duplicated.
        known=g.add_contact({'name':'Hope Nguyen','kind':'Mentor','email':'hope@example.com'})
        r=d.import_csv('Name,Email,Kind\nHope Nguyen,hope@example.com,Beta family\n')
        self.assertEqual((r['created'],r['enrolled']),(0,1));self.assertEqual(d.member(known['id'])['kind'],'beta')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],4)
        with self.assertRaises(ValueError):d.import_csv('name,context\nSomeone,no email column\n')
        with self.assertRaises(ValueError):d.import_csv('   ')

    def test_states_count_from_drafts_and_what_bao_records(self):
        d=self.drive();d.import_csv(CSV);g=Growth(self.s);desk=GrowthDesk(self.s)
        lead=next(m for m in d.members() if m['name']=='Linh Pham');beta=next(m for m in d.members() if m['kind']=='beta');other=next(m for m in d.members() if m['name']=='Minh Le')
        self.assertEqual(d.counts(),{'not_written':3,'ready':0,'sent':0,'replied':0,'reserved':0,'total':3,'unsent':3,'referrals':0,'leads':2,'beta':1})
        # The drafter writes one note per cycle; a saved draft makes the note ready.
        self.assertEqual(g.poll(limit=1)['drafts_queued'],1)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM hunter_requests WHERE reason LIKE ?',(FOLLOWUP_PREFIX+'%',)).fetchone()[0],1)
        g.save_draft('contact',lead['contact_id'],'Hold your spot for $1','Hi Linh, ...');g.save_draft('contact',beta['contact_id'],'Thank you','Hi, ...')
        c=d.counts();self.assertEqual((c['not_written'],c['ready'],c['unsent']),(1,2,3))
        self.assertEqual(d.member(lead['contact_id'])['shown'],'READY')
        # "I sent it" logs a touch, retires the draft and schedules the reminder before the deadline.
        m=d.mark_sent(lead['contact_id'])
        self.assertEqual((m['shown'],m['sent_on'],m['draft']),('SENT',today().isoformat(),None))
        self.assertEqual(m['touches'][0]['summary'],'Sent the reservation note.')
        nxt=date.fromisoformat(g.contact(lead['contact_id'])['next_followup_on']);self.assertTrue(nxt>today() and (nxt<=DEADLINE-timedelta(days=3) or today()>=DEADLINE-timedelta(days=3)))
        m=d.mark_sent(beta['contact_id']);self.assertEqual(m['touches'][0]['summary'],'Sent the thank-you note with the referral ask.')
        self.assertEqual((d.counts()['sent'],d.counts()['unsent']),(2,1))
        # Replied, reserved and referred: each is logged on the person and the last two reach channel math.
        m=d.mark_replied(lead['contact_id'],'Wants to reserve for her mom.');self.assertEqual(m['shown'],'REPLIED');self.assertIn('Wants to reserve',m['touches'][0]['summary'])
        m=d.mark_reserved(lead['contact_id']);self.assertEqual((m['shown'],m['reserved_on']),('RESERVED',today().isoformat()))
        self.assertEqual(d.mark_reserved(lead['contact_id'])['shown'],'RESERVED','recording twice adds nothing')
        m=d.mark_referred(beta['contact_id'],'her sister in Troy');self.assertEqual((m['shown'],m['referrals']),('REPLIED',1));self.assertIn('her sister in Troy',m['touches'][0]['summary'])
        m=d.mark_referred(other['contact_id']);self.assertEqual((m['shown'],m['referrals']),('REPLIED',1),'a referral from someone not yet written to still counts as a reply')
        c=d.counts();self.assertEqual((c['sent'],c['replied'],c['reserved'],c['referrals'],c['unsent']),(0,2,1,2,0))
        math=desk.math();by={x['channel']:x for x in math['channels']}
        self.assertEqual((by['email']['purchases'],by['email']['revenue_usd'],by['referrals']['signups'],math['totals']['purchases']),(1,1.0,2,1))
        week=(today()-timedelta(days=today().weekday())).isoformat()
        self.assertTrue(all(e['week_start']==week and e['source']=='reservation_drive' for e in math['entries']))
        self.assertEqual(len(d.board()['entries']),3)
        with self.assertRaises(ValueError):d.mark_sent('contact-nobody')

    def test_nudges_on_the_three_days_and_ready_notes_any_day(self):
        d=self.drive();d.import_csv(CSV);g=Growth(self.s)
        quiet=date(2026,10,27)
        self.assertEqual(d.alerts(on=quiet),[],'nothing ready, not a nudge day: Today stays quiet')
        [a]=d.alerts(on=NUDGE_DAYS[0])
        self.assertEqual((a['title'],a['url']),('Reservation drive: 3 notes still unsent, 7 days to November 2','/drive'));self.assertIn('3 still being written',a['detail'])
        members=d.members();g.save_draft('contact',members[0]['contact_id'],'Subject','Body')
        [a]=d.alerts(on=quiet);self.assertEqual(a['title'],'1 reservation note ready to send');self.assertIn('6 days to November 2',a['detail'])
        [a]=d.alerts(on=NUDGE_DAYS[2]);self.assertEqual(a['title'],'Reservation drive: 3 notes still unsent, 1 day to November 2')
        for m in members:
            g.save_draft('contact',m['contact_id'],'Subject','Body');d.mark_sent(m['contact_id'])
        self.assertEqual(d.alerts(on=NUDGE_DAYS[1]),[],'everything sent: no nudge')
        self.assertEqual(d.alerts(on=DEADLINE+timedelta(days=1)),[],'after the deadline the drive is silent')
        # The generic follow-up alert leaves drive members alone, but still covers everyone else.
        g.add_contact({'name':'Hope College','kind':'Partner','next_followup_on':today().isoformat()})
        titles=[x['title'] for x in g.alerts()]
        self.assertTrue(any(t=='Follow up with Hope College' for t in titles),titles)
        self.assertFalse(any('Linh Pham' in t or 'Tran' in t for t in titles))

    def test_drafter_gets_the_drive_task_and_everyone_else_the_usual_one(self):
        d=self.drive();d.import_csv(CSV);g=Growth(self.s)
        lead=next(m for m in d.members() if m['kind']=='lead');beta=next(m for m in d.members() if m['kind']=='beta')
        task=g.followup_context(lead['contact_id'])['task']
        self.assertIn('reserve the Individual plan for $1',task);self.assertIn('15 percent off the first year',task);self.assertIn('November 2',task);self.assertNotIn('thank-you',task)
        task=g.followup_context(beta['contact_id'])['task']
        self.assertIn('thank-you note',task);self.assertIn('exactly one referral ask',task);self.assertIn('never invent what happened on their calls',task)
        g.save_draft('contact',lead['contact_id'],'S','B');d.mark_sent(lead['contact_id'])
        self.assertIn('reminder',g.followup_context(lead['contact_id'])['task'])
        g.save_draft('contact',beta['contact_id'],'S','B');d.mark_sent(beta['contact_id'])
        self.assertIsNone(drive_task(self.s,beta['contact_id']),'a thanked family goes back to the usual follow-up')
        plain=g.add_contact({'name':'Hope College','kind':'Partner'})
        self.assertTrue(g.followup_context(plain['id'])['task'].startswith('Write a short follow-up email'))
        self.assertEqual(member_ids(self.s),{m['contact_id'] for m in d.members()})


if __name__=='__main__':unittest.main()
