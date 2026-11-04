"""Refresh the funding pipeline (Bao, Nov 4, 2026: "do a fresh check and remove grants that are expired for now").

Every program still under REVIEW was rechecked on its official page on Nov 4, 2026. This records the owner's
cleanup: expired, closed, ineligible and duplicate entries are skipped with the reason, and programs already
applied to are marked Applied. Nothing is deleted and nothing is submitted. Takes a consistent backup first.
Plan file: JSON list of {"id", "action": "SKIP"|"WATCH"|"Applied", "reason"}.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter


def main(plan_path):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-pipeline-refresh-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path);done=[]
    try:
        h=FundingHunter(s)
        for p in plan:
            if p['action']=='Applied':h.owner_outcome(p['id'],'Applied',p['reason'])
            else:h.decide(p['id'],p['action'],p['reason'])
            done.append((p['id'],p['action'],h.detail(p['id'])['recommendation']))
        left=h.list('Recommended',{})
        left=left if isinstance(left,list) else left.get('items',[])
        print(json.dumps({'backup':str(target),'applied':done,'still_recommended':[x['data']['canonical_name'] for x in left]},indent=1,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main(sys.argv[1])
