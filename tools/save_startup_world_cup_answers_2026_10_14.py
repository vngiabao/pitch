"""Store the owner's Startup World Cup Columbus 2026 answers as draft answer versions.

Questions were read from the live official form on Oct 14, 2026. Answers are the
owner's own final wording. Nothing is submitted or approved; the outcome is
recorded separately once the owner confirms submission.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

OPPORTUNITY='opp-b7cc0e7265070cb629fa'
FORM='https://form.123formbuilder.com/6938619/usa-columbus-startup-world-cup-application'
DRAFT=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition\Powerpoint Design\For Startup World Cup\Startup-World-Cup-Columbus-Application-Draft.md')
QUESTIONS=[
 ('Company One-Liner',250,'characters','drafted',"A Story is an AI biographer that calls your parents and grandparents, helps them tell their life stories in their own voice, and lets the whole family add photos and memories to one living archive."),
 ('What is your current revenue to date? If none, how do you plan to generate revenue?',50,'words','owner_written',"Pre-revenue. Families will pay a yearly subscription for the ongoing interviews: $119 for an individual or $229 for a family. We also offer printed books starting at $69. Five beta families are waiting to pay at our public launch, and Hope College has shown interest in gifting A Story to students' grandparents for Thanksgiving gifts."),
 ('Summarize the problem you are trying to solve, and who is your target customer?',50,'words','owner_written',"Our customers are adult children wanting to know their parents beyond the milestones, but distance, work, and not knowing what to ask get in the way. Photo albums keep the faces, not the stories. Memoir products often turn a meaningful gift into homework for the parent, ending with one book."),
 ('Summarize the solution you are building and why your target customer is willing to pay for it?',50,'words','owner_written',"A Story calls on a schedule and does the asking, so storytelling becomes an easy habit. It remembers past conversations and lets each memory shape the next question. Relatives add their own perspectives, turning one autobiography into a family documentary in original voices. Families pay to keep that story growing."),
 ('What is your competitive advantage?',50,'words','owner_written',"Unlike Storyworth and Remento, A Story doesn't end with a book. Scheduled calls build the habit, and every photo, memory, or relative's perspective gives the next interview a reason to happen. As more family members contribute, their connected stories and original voices make the archive harder to leave behind, and the network itself brings in new customers."),
]
UNRESOLVED={'What is your competitive advantage?':['Network-driven acquisition is a growth hypothesis, not a measured result.'],
 'What is your current revenue to date? If none, how do you plan to generate revenue?':['Prices, waiting families and Hope College interest are owner-reported; pricing proposal pending approval.']}

def main():
    db_path=ROOT/'data/founder.sqlite'
    target=db_path.parent/'repair-backups'/('before-swc-answers-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s)
        vid=s.import_source(DRAFT,'application_draft','REFERENCE',text=DRAFT.read_text(encoding='utf-8'),extraction='owner_final_wording',document_date='2026-10-14')
        aid=h.start_application(OPPORTUNITY)
        saved=[]
        for i,(prompt,limit,unit,prov,body) in enumerate(QUESTIONS,1):
            qid=s.add_question(aid,i,prompt,vid,FORM+' (read 2026-10-14)',limit,unit,checked=True)
            saved.append({'question':prompt[:60],'answer_version':s.add_answer(qid,body,[vid],unresolved=UNRESOLVED.get(prompt,()),provenance=prov)})
        print(json.dumps({'backup':str(target),'application_id':aid,'source_version':vid,'answers':saved,'submitted':False},indent=2))
    finally:s.close()

if __name__=='__main__':main()
