"""Apply the owner's Oct 18, 2026 confirmation: Bao Vo is Co-founder, COO and CTO.

Updates the owner-confirmed profile (founder_role) and the team statement, each as a new approved version
with the owner confirmation file as its source. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-18.md'
PROFILE_CLAIM='claim-8d66aa68e3949cecf35b'
TEAM_CLAIM='claim-7d629a57720f34672314'
ROLE='Co-founder, COO & CTO'
NOTE='Owner told Founder OS on Oct 18, 2026: "im also the cto now" (see Owner-Confirmations-2026-10-18.md).'


def approve(s,vid,why):
    aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':why},actor='founder')
    s.decide(aid,'approved',owner_confirmation=True,note=NOTE);return aid


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-role-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now()
        sv=s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-18')
        # 1. The structured profile: founder_role.
        cur=s.one('SELECT v.id FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(PROFILE_CLAIM,))['id']
        values={r['fact_key']:json.loads(r['value_json']) for r in s.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=?',(cur,))}
        if values.get('founder_role')!=ROLE:
            values['founder_role']=ROLE
            label=lambda cid:s.one('SELECT label FROM claims WHERE id=?',(cid,))['label']  # a new version keeps its claim's label
            pv=s.propose_claim('team',label(PROFILE_CLAIM),json.dumps(values,sort_keys=True),'verified',sv,'owner chat, Oct 18 2026: Bao is also CTO',claim_id=PROFILE_CLAIM,last_verified_at=stamp)
            have={r['fact_key'] for r in s.rows('SELECT fact_key FROM company_fact_values WHERE claim_version_id=?',(pv,))}
            for k,v in values.items():
                if k not in have:h.attach_fact_value(pv,k,v)
            approve(s,pv,'Owner-confirmed role update')
        # 2. The team statement the drafters quote.
        body=s.one('SELECT v.body FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(TEAM_CLAIM,))['body']
        if 'COO and CTO' not in body:
            new=body.replace('Bao Vo (COO)','Bao Vo (COO and CTO)',1)
            assert new!=body,'team statement no longer names Bao Vo (COO)'
            tv=s.propose_claim('team',s.one('SELECT label FROM claims WHERE id=?',(TEAM_CLAIM,))['label'],new,'verified',sv,'owner chat, Oct 18 2026',claim_id=TEAM_CLAIM,last_verified_at=stamp)
            approve(s,tv,'Owner-confirmed role update')
        mem=h.company_memory()
        print(json.dumps({'backup':str(target),'founder_role':mem['attributes'].get('founder_role',{}).get('value'),'cofounder_role':mem['attributes'].get('cofounder_role',{}).get('value'),
                          'team_statement':next((c['body'][:120] for c in mem['canonical_claims'] if c['body'].startswith('A Story has two founders')),None),'conflicts':mem['conflicting_attributes']},indent=2,ensure_ascii=False))
    finally:s.close()


if __name__=='__main__':main()
