"""Apply the owner's Oct 23, 2026 confirmation: A Story is in Google for Startups and the Deepgram Startup Program.

Adds both to previous_programs in the owner-confirmed profile, as a new approved version with the
owner confirmation file as its source. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-23.md'
PROFILE_CLAIM='claim-8d66aa68e3949cecf35b'
ADD=['Google for Startups','Deepgram Startup Program']
NOTE='Owner told Founder OS on Oct 23, 2026 (see Owner-Confirmations-2026-10-23.md).'


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-programs-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now()
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-23')
        cur=s.one('SELECT v.id FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(PROFILE_CLAIM,))['id']
        values={r['fact_key']:json.loads(r['value_json']) for r in s.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=?',(cur,))}
        programs=list(values.get('previous_programs') or [])
        if not all(p in programs for p in ADD):
            values['previous_programs']=programs+[p for p in ADD if p not in programs]
            label=s.one('SELECT label FROM claims WHERE id=?',(PROFILE_CLAIM,))['label']  # a new version keeps its claim's label
            pv=s.propose_claim('team',label,json.dumps(values,sort_keys=True),'verified',sv,'owner chat, Oct 23 2026: Google for Startups and Deepgram',claim_id=PROFILE_CLAIM,last_verified_at=stamp)
            have={r['fact_key'] for r in s.rows('SELECT fact_key FROM company_fact_values WHERE claim_version_id=?',(pv,))}
            for k,v in values.items():
                if k not in have:h.attach_fact_value(pv,k,v)
            aid=s.request_approval('promote_claim',{'version_id':pv,'decision_needed':'Owner-confirmed programs update'},actor='founder')
            s.decide(aid,'approved',owner_confirmation=True,note=NOTE)
        mem=h.company_memory()
        print(json.dumps({'backup':str(target),'previous_programs':mem['attributes'].get('previous_programs',{}).get('value'),'conflicts':mem['conflicting_attributes']},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
