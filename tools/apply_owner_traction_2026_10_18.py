"""Apply the owner's second Oct 18, 2026 confirmation: Hope College on-site results and Bao's full responsibilities.

Adds the first sales as a new approved traction version, adds Bao's responsibilities to the team statement,
logs the field day in channel math, and closes the one-day campaign. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-18b.md'
TRACTION_CLAIM='claim-e45f7ffc6e5dd908d85a'
TEAM_CLAIM='claim-7d629a57720f34672314'
FIRST_SALES=(' First sales, owner-reported: on October 17, 2026, at a Hope College on-site table (cold approach), about 10 students reserved A Story for $1 each '
             'and one bought a $29 book. Payment records are not yet reconciled. These are individual students, not a college partnership.')
ROLES=(' Bao leads technology, fundraising and strategy, and runs all partnerships, web design, client-facing work and traction. '
       'Daniel leads product and the product roadmap.')
NOTE='Owner told Founder OS on Oct 18, 2026 (see Owner-Confirmations-2026-10-18b.md).'


def approve(s,vid,why):
    aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':why},actor='founder')
    s.decide(aid,'approved',owner_confirmation=True,note=NOTE);return aid


def extend(s,sv,cid,addition,marker,stamp):
    c=s.one('SELECT c.label,v.body FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(cid,))
    if marker in c['body']:return False
    vid=s.propose_claim(s.one('SELECT topic FROM claims WHERE id=?',(cid,))['topic'],c['label'],c['body'].rstrip()+addition,'verified',sv,'owner chat, Oct 18 2026',claim_id=cid,last_verified_at=stamp)
    approve(s,vid,'Owner-confirmed update');return True


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-traction-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now()
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-18')
        traction=extend(s,sv,TRACTION_CLAIM,FIRST_SALES,'First sales, owner-reported',stamp)
        team=extend(s,sv,TEAM_CLAIM,ROLES,'runs all partnerships',stamp)
        logged=False
        from founder_os.growth_desk import GrowthDesk
        desk=GrowthDesk(s);key='hope-college-onsite-2026-10-17'
        if not desk.field_days(key)['entries']:
            desk.log_field_day(key,{'approached':0,'conversations':0,'emails':0,'reservations':10,'on':'2026-10-17','note':'Owner-reported: about 10 $1 reservations; approached count not recorded'})
            desk.add_entry({'channel':'events','week_start':'2026-10-12','purchases':1,'revenue_usd':29,'note':'Hope College on site Oct 17: one $29 book (owner-reported)'})
            desk.set_campaign_state(key,'DONE');logged=True
        mem=h.company_memory()
        print(json.dumps({'backup':str(target),'traction_updated':traction,'team_updated':team,'field_day_logged':logged,
                          'traction':next((c['body'] for c in mem['canonical_claims'] if c['body'].startswith('Owner-reported: the first MVP')),None),
                          'channel_totals':{k:desk.math()['totals'][k] for k in ('purchases','revenue_usd')}},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
