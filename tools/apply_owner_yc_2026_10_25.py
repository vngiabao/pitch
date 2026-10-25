"""Apply the owner's Oct 25, 2026 YC answers to the approved facts.

Adds new approved versions of four statements (traction, product readiness, founders, funding) with
the owner confirmation file as their source. Takes a consistent backup first. Safe to re-run.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-25.md'
NOTE='Owner answered the YC questions in chat on Oct 25, 2026 (see Owner-Confirmations-2026-10-25.md).'
# claim id -> (text to replace or None to append, replacement or addition, marker showing it is done)
EDITS={
 'claim-e45f7ffc6e5dd908d85a':[('and one bought a $29 book.','and one paid $29 to preorder a book.','to preorder a book'),
                               (None,' The 10 private-beta families use A Story free during the beta; the Hope College sales are the first payments.','free during the beta')],
 'claim-2e4b51226c984860e4a0':[(None,' Stack: OpenAI GPT models run the interviewer; the iOS app is React Native (Expo); Cartesia for voice, AssemblyAI for transcription, Supabase for the backend; the founders build with Claude Code and Codex.','React Native (Expo)')],
 'claim-7d629a57720f34672314':[(None,' Both founders write code, and an early engineer also contributed code under a signed IP assignment. Both have worked on A Story full time since June 2026. The founders live in Allendale, Michigan; after YC the company would be based in San Francisco. Equity: 9,000,000 shares each (50% each of issued stock), with 2,000,000 more shares unassigned; no one else holds stock.','9,000,000 shares each')],
 'claim-2ac25703d81abbfdcd18':[(None,' Not raising yet; the plan is to raise after YC.','raise after YC')]}


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-yc-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path);changed=[]
    try:
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-25')
        stamp=now()
        for cid,edits in EDITS.items():
            c=s.one('SELECT c.topic,c.label,v.body FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(cid,))
            body=c['body']
            for old,new,marker in edits:
                if marker in body:continue
                if old:
                    assert old in body,(cid,old);body=body.replace(old,new,1)
                else:body=body.rstrip()+new
            if body==c['body']:continue
            vid=s.propose_claim(c['topic'],c['label'],body,'verified',sv,'owner chat, Oct 25 2026: YC answers',claim_id=cid,last_verified_at=stamp)
            aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':'Owner-confirmed YC facts'},actor='founder')
            s.decide(aid,'approved',owner_confirmation=True,note=NOTE);changed.append(c['label'])
        print(json.dumps({'backup':str(target),'updated':changed},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
