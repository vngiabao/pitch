"""Track the ZLCF and Higgsfield applications from the Sep 30 meeting notes.

The Funding Hunter had no program records for them. Run once to take a consistent
backup and queue targeted research; run again after the research worker finishes
to record the owner-reported 'Applied' outcomes against the official records.
Idempotent: fixed request keys and outcome ids. Never submits or contacts anyone.
"""
import json,re,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

NOTES_VERSION='sv-1b76fde33120181e0d735432'
SEPT30='2026-09-30T18:00:00-04:00'

PROGRAMS=[
    {'key':'owner-applied-zlcf-2026-09-30','match':r'zell lurie commercialization|\bzlcf\b',
     'reason':'Research program: Zell Lurie Commercialization Fund (ZLCF) | Zell Lurie Institute for Entrepreneurial Studies, University of Michigan Ross School of Business',
     'note':'Sep 30 meeting notes (Application process): ZLCF submitted.'},
    {'key':'owner-applied-higgsfield-2026-09-30','match':r'higgsfield',
     'reason':'Research program: Higgsfield | Higgsfield AI, generative video platform; its startup, creator or grant program',
     'note':'Sep 30 meeting notes (Application process): Higgsfield submitted. The notes do not name the Higgsfield program; matched to the program research found. Owner to confirm.'},
]


def backup(db_path):
    target=db_path.parent/'repair-backups'/('before-untracked-applications-'+now()[:19].replace(':','')+'.sqlite')
    target.parent.mkdir(exist_ok=True)
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close();return target


def find(s,pattern):
    rx=re.compile(pattern,re.I)
    rows=s.rows('SELECT i.opportunity_id,i.program_id,i.last_checked,p.canonical_name FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id')
    aliases={}
    for a in s.rows('SELECT program_id,alias FROM program_aliases'):aliases.setdefault(a['program_id'],[]).append(a['alias'])
    hits=[r for r in rows if rx.search(r['canonical_name']) or any(rx.search(a) for a in aliases.get(r['program_id'],[]))]
    return hits


def main():
    db_path=ROOT/'data/founder.sqlite'
    saved=backup(db_path)
    s=Store(db_path)
    try:
        h=FundingHunter(s);s.one('SELECT id FROM source_versions WHERE id=?',(NOTES_VERSION,))
        result=[]
        for p in PROGRAMS:
            hits=find(s,p['match'])
            programs={r['program_id'] for r in hits}
            if not hits:
                with s.transaction():queued=h.request_run(p['reason'],key=p['key'])
                state=s.one('SELECT state,last_error FROM hunter_requests WHERE id=?',(queued['request_id'],))
                result.append({'program':p['reason'],'record':None,'research_request':queued['request_id'],'request_state':state['state'],'last_error':state['last_error']})
                continue
            if len(programs)>1:
                result.append({'program':p['reason'],'ambiguous':[r['canonical_name'] for r in hits],'recorded':False});continue
            # One outcome on the program's most recently checked record is enough for the tracker.
            oid=sorted(hits,key=lambda r:r['last_checked'] or '')[-1]['opportunity_id']
            with s.transaction():eid=h.outcome(oid,'Applied',p['note'],source_version_id=NOTES_VERSION,occurred_at=SEPT30)
            result.append({'program':hits[0]['canonical_name'],'opportunity_id':oid,'outcome_id':eid,'recorded':True})
        print(json.dumps({'backup':str(saved),'source_version':NOTES_VERSION,'results':result},indent=2))
    finally:s.close()


if __name__=='__main__':main()
