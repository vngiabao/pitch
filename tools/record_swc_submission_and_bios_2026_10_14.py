"""Record the owner-confirmed Startup World Cup Columbus submission and approve the
owner's founder bios (Bao Vo, Daniel Hoang Nguyen) for reuse in later applications.

Both actions follow the owner's explicit instruction in chat on Oct 14, 2026:
"submitted for the world cup. and make sure to update this as the founder bio too."
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

OPPORTUNITY='opp-b7cc0e7265070cb629fa'
FORM='https://form.123formbuilder.com/6938619/usa-columbus-startup-world-cup-application'
F6S=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition\F6S-Answers-Key-Facts-2026.md')
DRAFT=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition\Powerpoint Design\For Startup World Cup\Startup-World-Cup-Columbus-Application-Draft.md')
BIOS=[
 ('Founder bio: Bao Vo, Co-founder & COO - short bio on achievements, degrees and experiences relevant to the company (max 100 words)',
  "Co-founder and COO of A Story, leading operations, customer discovery and partnerships. Chose our ten private-beta families from fifty leads after volunteering in nursing homes to learn how older adults share their stories. MS in Electrical and Computer Engineering (Integrated Circuits & VLSI), University of Michigan, 2026; BS in Materials Science and Engineering, Electrical Engineering minor, summa cum laude, 2023. Previously a project manager and consultant at miLEAD, helping early-stage life-science startups choose their markets, and a DFT/STA engineer at Faraday Technology with a top-10% performance evaluation. Track winner and Audience Choice, Ross +Tech Innovation Jam."),
 ('Founder bio: Daniel Hoang Nguyen, Co-founder & CEO - short bio on achievements, degrees and experiences relevant to the company (max 100 words)',
  "Co-founder and CEO of A Story, leading product vision, fundraising and finance. BS in Mathematics (Data Science), Bowling Green State University, 2025; incoming MS in Financial Mathematics at the University of Illinois Urbana-Champaign. Ranked #1 at BGSU in the Putnam Competition, Phi Beta Kappa, and second place at the 2025 BGSU Hackathon for an AI search framework. Led four student organizations, including the Vietnamese Student Association, and now co-leads a 300-member Vietnamese community at UIUC. Started A Story after two uncles who carried his family's history had strokes and struggled to find the words."),
]

def main():
    db_path=ROOT/'data/founder.sqlite'
    target=db_path.parent/'repair-backups'/('before-swc-submitted-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s)
        draft=s.import_source(DRAFT,'application_draft','REFERENCE',text=DRAFT.read_text(encoding='utf-8'),extraction='owner_final_wording',document_date='2026-10-14')
        f6s=s.import_source(F6S,'application_history','REFERENCE',text=F6S.read_text(encoding='utf-8'),extraction='owner_f6s_answers_summary',document_date='2026-09-27')
        with s.transaction():
            outcome=h.outcome(OPPORTUNITY,'Applied','Owner confirmed in chat on Oct 14, 2026 that the Startup World Cup Columbus application was submitted. No organizer receipt captured.',source_version_id=draft)
        aid=h.start_application(OPPORTUNITY)
        bios=[]
        for i,(prompt,body) in enumerate(BIOS,6):
            qid=s.add_question(aid,i,prompt,draft,FORM+' (Team Members page, read 2026-10-14)',100,'words',checked=True)
            vid=s.add_answer(qid,body,[draft,f6s],provenance='owner_written')
            pending=[a for a in s.rows("SELECT id,payload_json FROM approvals WHERE action='approve_answer' AND state='pending'") if json.loads(a['payload_json']).get('version_id')==vid]
            review=s.one('SELECT status FROM answer_reviews WHERE version_id=?',(vid,))['status']
            if review!='approved':
                appr=pending[0]['id'] if pending else s.request_approval('approve_answer',{'version_id':vid,'decision_needed':'Owner instructed: use this as the founder bio.'})
                s.decide(appr,'approved',owner_confirmation=True,note='Owner in chat, Oct 14 2026: "make sure to update this as the founder bio too."')
            bios.append({'bio':prompt.split(' - ')[0],'answer_version':vid,'status':s.one('SELECT status FROM answer_reviews WHERE version_id=?',(vid,))['status']})
        print(json.dumps({'backup':str(target),'outcome':outcome,'recommendation_now':h.detail(OPPORTUNITY)['recommendation'],'bios':bios},indent=2))
    finally:s.close()

if __name__=='__main__':main()
