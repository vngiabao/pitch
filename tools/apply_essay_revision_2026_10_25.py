"""Save the October 25, 2026 essay revision into Founder OS.

Every revised answer becomes a new draft version that supersedes the one it replaces, so the old
versions stay in history. Answers with [Bao: ...] placeholders carry them as unresolved items, which
blocks approval until Bao fills them. Also adds the Y Combinator application (questions plus the
short answers) and fixes stale job titles. Takes a consistent backup first. Run it once; re-running
skips answers that already exist.
"""
import json,re,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
BANK=FOLDER/'Answer-Bank-2026-10-25.md'
APPS=FOLDER/'Essay-Revision-2026-10-25.json'
YC_OPP='opp-304e4645eaaf1e02115a'
PROVENANCE='revised Oct 25, 2026 from the Answer Bank: current facts, Bao voice'
TITLE='Co-founder, COO & CTO'
TITLE_FIELDS={'Runware Grant Program application':3,'TechRise Pitch Competitions application':6,'AgeTech Collaborative January Open Mic Challenge application':4}


def placeholders(text):return re.findall(r'\[Bao:[^\]]*\]',text)


def latest(s,qid):
    r=s.db.execute('SELECT id,body FROM answer_versions WHERE question_id=? ORDER BY created_at DESC LIMIT 1',(qid,)).fetchone()
    return (r[0],r[1]) if r else (None,None)


def save(s,sv,qid,text,counts):
    old,body=latest(s,qid)
    if body==text:counts['unchanged']+=1;return
    s.add_answer(qid,text,[sv],unresolved=placeholders(text),provenance=PROVENANCE,supersedes=old)
    counts['saved']+=1


def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-essay-revision-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path);counts={'saved':0,'unchanged':0}
    try:
        sv=s.import_source(BANK,'answer_bank','REFERENCE',text=BANK.read_text(encoding='utf-8'),extraction='assistant_draft',document_date='2026-10-25')
        payload=json.loads(APPS.read_text(encoding='utf-8'))
        # 1. Open applications: new versions over the old drafts.
        for item in payload['applications']:
            save(s,sv,item['id'],item['text'],counts)
        # 2. Stale job titles.
        for app,ordinal in TITLE_FIELDS.items():
            q=s.one('SELECT q.id FROM questions q JOIN applications a ON a.id=q.application_id WHERE a.title=? AND q.ordinal=?',(app,ordinal))
            save(s,sv,q['id'],TITLE,counts)
        # 3. The Y Combinator application with its short answers.
        aid=s.create_application(YC_OPP,'Y Combinator application')
        for i,item in enumerate(payload['yc'],start=1):
            qid=s.add_question(aid,i,item['prompt'],sv,'YC application questions as of Oct 2026 (re-check on apply.ycombinator.com)',item.get('limit'),item.get('unit'))
            save(s,sv,qid,item['text'],counts)
        print(json.dumps({'backup':str(target),'source_version':sv,'yc_application':aid,**counts},indent=2))
    finally:s.close()


if __name__=='__main__':main()
