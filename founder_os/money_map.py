"""Money map: every route to money in one place - programs by category with their pitch and application
status, plus the owner's own money moves (sales, pilots, freelance work) as a checklist."""
from .store import now,uid
from .funding_hunter import FundingHunter

CATEGORIES=[
 ('big_pitch','Big pitch competitions','Large cash prizes on a yearly calendar. Miss the window and it is a year away.'),
 ('local_pitch','Local pitch nights','Small, fast prizes and practice close to home.'),
 ('grants','Grants and SBIR','Non-dilutive money with longer applications.'),
 ('founder','Money for the founders','Fellowships, stipends and grants paid to Bao or Daniel.'),
 ('agetech','AgeTech and aging','Programs for products that serve older adults and families.'),
 ('accelerators','Accelerators and investment','Cash for equity or a SAFE. Always investment, never a grant.'),
 ('hackathons','Hackathons','Prize money for building fast with voice and AI.'),
 ('credits','Credits','Not cash. They cut what A Story pays for voice and AI.'),
 ('other','Everything else','Programs the agents track that fit no group above.')]
LOCAL=('michigan','5x5','pitch night','grand rapids','ann arbor','detroit','kalamazoo','muskegon','gvsu','start garden')
AGE=('agetech','aarp','aging','older adult','longevity','national institute on aging','caregiv','dementia')
MOVES=[
 ('holiday-gifting','Sell now','Holiday gifting push','Gift the $79 Express pass and the $119 plan for the holidays. Every gift sale is revenue no judge has to approve.'),
 ('reservations','Sell now','Follow up on the $1 reservations','Personal note to each of the 50 leads before November 2. Ask the 10 beta families for one referral each.'),
 ('b2b-pilots','Sell now','Paid pilots with organizations','Senior living, hospices, funeral homes, genealogy societies and churches: $500 to $2,000 for 10 to 20 storytellers.'),
 ('freelance','Founder income','Freelance AI voice and agent builds','Small businesses pay $2,000 to $10,000 for voice or agent workflows. Uses what you already built.'),
 ('licensing','Founder income','License the interviewer','Museums, libraries, universities and oral-history projects need guided recorded interviews.'),
 ('sbir-partner','Grants','Find a University of Michigan aging researcher','For an NIA SBIR or STTR application on the next NIH date.'),
 ('smartzone','Investment','SmartZone referral to Michigan Rise','Pre-seed of up to $250,000, reached through your local SmartZone.')]
RANK={m[0]:i for i,m in enumerate(MOVES)}
SCHEMA='''CREATE TABLE IF NOT EXISTS money_moves(id TEXT PRIMARY KEY,key TEXT NOT NULL UNIQUE,grp TEXT NOT NULL,title TEXT NOT NULL,detail TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'TODO',updated_at TEXT NOT NULL);'''


def classify(d):
    data=d['data'];money=d['analysis']['money'];t=str(data.get('opportunity_type') or '').lower()
    text=' '.join(str(data.get(k) or '') for k in ('canonical_name','organizer','notes','opportunity_type')).lower()
    if money['kind']=='CREDITS' or 'credit' in t:return 'credits'
    if 'hackathon' in text:return 'hackathons'
    if any(k in text for k in AGE):return 'agetech'
    if t in ('fellowship','founder_fellowship') or 'fellow' in text or 'emergent ventures' in text:return 'founder'
    if t in ('accelerator','incubator') or money['kind']=='INVESTMENT':return 'accelerators'
    if t in ('grant','sbir') or 'grant' in text or 'sbir' in text:return 'grants'
    if t in ('pitch_competition','competition','award','prize','pitch_night') or 'pitch' in text or 'challenge' in text or 'competition' in text:
        cash=money.get('cash_max')
        if cash and cash>=25000:return 'big_pitch'
        return 'local_pitch' if any(k in text for k in LOCAL) or (cash and cash<25000) else 'big_pitch'
    return 'other'


class MoneyMap:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA);self.h=FundingHunter(store)
        for key,grp,title,detail in MOVES:
            self.db.execute('INSERT OR IGNORE INTO money_moves VALUES(?,?,?,?,?,?,?)',(uid('move'),key,grp,title,detail,'TODO',now()))

    def board(self):
        from .application_drafter import application_list
        apps={a['opportunity_id']:a for a in application_list(self.s)}
        editions={}
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE name='work_items'").fetchone():
            for w in self.s.rows("SELECT id,opportunity_id,stage,title FROM work_items WHERE kind='PITCH_EDITION' ORDER BY updated_at"):editions[w['opportunity_id']]=w
        groups={k:[] for k,_,_ in CATEGORIES};seen=set()
        for d in self.h.list('All'):
            name=d['data']['canonical_name'].strip().lower()
            if name in seen:continue
            seen.add(name);m=d['analysis']['money'];days=d['analysis']['scoring']['dates']['days_remaining']
            outcome=self.db.execute('SELECT outcome FROM funding_outcomes WHERE opportunity_id=? ORDER BY occurred_at DESC,created_at DESC LIMIT 1',(d['opportunity_id'],)).fetchone()
            app=apps.get(d['opportunity_id']);ed=editions.get(d['opportunity_id'])
            amount=('Up to $'+format(int(m['cash_max']),',')) if m.get('cash_max') else (('$'+format(int(m['credits_face_value']),',')+' credits') if m.get('credits_face_value') else '')
            groups[classify(d)].append({'id':d['opportunity_id'],'name':d['data']['canonical_name'],'amount':amount,'kind':m['kind'],'deadline':d['data']['dates'].get('deadline'),
                'days':days,'rolling':d['data'].get('cycle_kind')=='rolling','recommendation':d['recommendation'],'outcome':outcome['outcome'] if outcome else None,
                'access':app['access'] if app else None,'application_id':app['application_id'] if app and app.get('questions') else None,
                'edition':{'id':ed['id'],'stage':ed['stage']} if ed else None})
        def order(r):
            closed=r['outcome'] in ('Rejected','Withdrawn','Accepted','Won') or r['recommendation'] in ('EXPIRED','SKIP','REJECTED')
            return (closed,r['days'] if r['days'] is not None and r['days']>=0 else 9999,r['name'])
        return {'categories':[{'key':k,'title':t,'note':n,'programs':sorted(groups[k],key=order)} for k,t,n in CATEGORIES],
                'moves':sorted(self.s.rows('SELECT * FROM money_moves'),key=lambda m:RANK.get(m['key'],len(RANK)))}

    def set_move(self,mid,state):
        if state not in ('TODO','DOING','DONE'):raise ValueError('Unknown state')
        self.s.one('SELECT id FROM money_moves WHERE id=?',(mid,))
        self.db.execute('UPDATE money_moves SET state=?,updated_at=? WHERE id=?',(state,now(),mid));return {'id':mid,'state':state}
