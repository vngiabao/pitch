"""Apply the owner's second Oct 23, 2026 confirmation: relatives can add videos and voice messages today.

Adds a new approved version of the product readiness statement with the owner confirmation file as
its source. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-23b.md'
FEATURES_CLAIM='claim-2e4b51226c984860e4a0'
OLD='photo contributions'
NEW='photo, video and voice-message contributions from relatives'
NOTE='Owner told Founder OS on Oct 23, 2026 (see Owner-Confirmations-2026-10-23b.md).'


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-media-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now()
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-23')
        c=s.one('SELECT c.topic,c.label,v.body FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(FEATURES_CLAIM,))
        if NEW not in c['body']:
            body=c['body'].replace(OLD,NEW,1)
            assert body!=c['body'],'readiness statement no longer says "photo contributions"'
            vid=s.propose_claim(c['topic'],c['label'],body,'verified',sv,'owner chat, Oct 23 2026: videos and voice messages',claim_id=FEATURES_CLAIM,last_verified_at=stamp)
            aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':'Owner-confirmed feature update'},actor='founder')
            s.decide(aid,'approved',owner_confirmation=True,note=NOTE)
        mem=h.company_memory()
        print(json.dumps({'backup':str(target),'features':next((x['body'] for x in mem['canonical_claims'] if x['body'].startswith('The core product works end to end')),None)},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
