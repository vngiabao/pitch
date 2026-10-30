"""Apply the owner's Oct 28, 2026 confirmations (business résumé + MBC application).

- Traction: "over 10" students paid $1 at the Oct 17 campus event (was "about 10"); B2B is in progress with
  funeral homes, senior living is a separate channel.
- Team: Nhi Tran's MBC role is brand design, pitch design and product positioning; she presents the MBC pitch.
  Origin wording for applications: "Bao and Daniel started building A Story in 2026."

Daniel's degree status is left unchanged until the owner confirms it. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-28.md'
NOTE='Owner told Founder OS on Oct 28, 2026 (see Owner-Confirmations-2026-10-28.md).'
EDITS={
    'claim-e45f7ffc6e5dd908d85a':[
        ('about 10 students reserved A Story for $1 each','over 10 students reserved A Story for $1 each'),
        ('the Hope College sales are the first payments.',
         'the Hope College sales are the first payments. B2B is in progress: A Story is in conversations with funeral homes, and senior living is a separate channel. Funeral homes are leads, not partnerships.'),
    ],
    'claim-7d629a57720f34672314':[
        ('Nhi Tran is listed as CMO only for the Michigan Business Challenge; other applications name the two founders.',
         'Nhi Tran is listed as CMO only for the Michigan Business Challenge, leading brand design, pitch design and product positioning, and she presents the MBC pitch; other applications name the two founders. In applications, say "Bao and Daniel started building A Story in 2026"; Daniel incorporated the Delaware C-Corp in June 2026.'),
    ],
}


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-oct28-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now();done={}
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-28')
        for cid,edits in EDITS.items():
            c=s.one('SELECT c.topic,c.label,v.body FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(cid,))
            body=c['body']
            for old,new in edits:
                if new in body:continue
                assert old in body,f'{cid}: expected text not found: {old[:60]}'
                body=body.replace(old,new,1)
            if body==c['body']:done[cid]='already current';continue
            vid=s.propose_claim(c['topic'],c['label'],body,'verified',sv,'owner chat, Oct 28 2026',claim_id=cid,last_verified_at=stamp)
            aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':'Owner-confirmed update, Oct 28 2026'},actor='founder')
            s.decide(aid,'approved',owner_confirmation=True,note=NOTE)
            done[cid]='updated'
        mem=h.company_memory()
        bodies=[x['body'] for x in mem['canonical_claims']]
        print(json.dumps({'backup':str(target),'result':done,
                          'traction_ok':any('over 10 students' in b for b in bodies),
                          'team_ok':any('pitch design and product positioning' in b for b in bodies)},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
