"""Record owner-reported application outcomes and propose company facts from the
A Story meeting notes (Sep 20 - Oct 14, 2026).

Outcomes are owner-reported history from the founder's own notes. Company facts are
PROPOSED only; they stay unknown until the owner approves each one under Decisions.
Takes a consistent database backup first. Never writes to the source folder.
"""
import json,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

NOTES=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition\Powerpoint Design\AStory Meeting Notes.pdf')
SEPT30='2026-09-30T18:00:00-04:00'

OUTCOMES=[
    ('opp-9ffd0692de45f6559044','Rejected','Sep 30 meeting notes: ElevenLabs submitted, then rejected. Team suspects overlap with Kinlily, a past grant recipient.'),
    ('opp-efc2a72f531f997a50a3','Applied','Sep 30 meeting notes: F6S $150K University Pitch Competition submitted. Team expects non-selection because the app was not yet published.'),
    ('opp-6e16bafa138dd6827405','Applied','Sep 30 meeting notes: NVIDIA Inception submitted.'),
    ('opp-59702300e70697137549','Applied','Sep 30 meeting notes: Runway submitted.'),
]

PROPOSALS=[
    {'topic':'product_description','label':'Product stage and AI use - October 14, 2026','evidence_status':'reported',
     'locator':'Oct 14 notes, Slide 3 brainstorm (Traction); Sep 30 notes (App Store)',
     'body':'A Story is a consumer AI product: an AI biographer that calls family members, records their stories in their own voice and builds a shared family archive. The core product works end to end (AI-guided calls, shared archive, photo contributions, billing). Ten families are in a private beta; the App Store release was pending review on Sep 30.',
     'attributes':{'uses_ai':True,'product_stage':'private_beta','customer_type':'B2C','business_type':'consumer_subscription','industry':'consumer_ai'},
     'decision_needed':'Approve if these attributes are current. They let the Funding Hunter check AI, consumer and stage eligibility instead of leaving them unknown.'},
    {'topic':'team','label':'Incorporation and founding team - October 14, 2026','evidence_status':'reported',
     'locator':'Approved company name (A Story Technologies, Inc.); Sep 30 notes (new A Story bank account); Oct 14 notes, Slide 3 (Team)',
     'body':'A Story Technologies, Inc. is a US company with its own bank account. The Oct 14 notes describe a three-person founding team: Daniel (CEO: product vision, fundraising, finance), Bao (COO: operations, customer discovery, partnerships) and Nhi (CMO: brand, acquisition, go-to-market). This conflicts with the approved team size of 4 and with F6S, which listed Nhi as an employee; resolve team size separately.',
     'attributes':{'incorporated':True,'us_company':True},
     'decision_needed':'Approve only if A Story Technologies, Inc. is actually incorporated in the US. Team size is not changed by this proposal.'},
    {'topic':'pricing','label':'Pricing direction - October 14, 2026','evidence_status':'hypothesis',
     'locator':'Sep 30 notes ($1 and $30 plan rollout); Oct 14 notes, Slide 3 (Business model)',
     'body':'Two pricing directions conflict. Sep 30: a $1 and $30 plan rollout on astoryapp.com. Oct 14 slide brainstorm: Individual $119/year, Family $229/year, printed books from $69, family contributors free. Pick one before any application states prices.',
     'attributes':{},
     'decision_needed':'Choose the current price list. Applications and pitches will not state prices until one is approved.'},
]


def backup(db_path):
    target=db_path.parent/'repair-backups'/('before-meeting-notes-'+now()[:19].replace(':','')+'.sqlite')
    target.parent.mkdir(exist_ok=True)
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close();return target


def main():
    db_path=ROOT/'data/founder.sqlite'
    saved=backup(db_path)
    text=subprocess.run(['pdftotext','-layout',str(NOTES),'-'],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout or None
    s=Store(db_path)
    try:
        h=FundingHunter(s)
        vid=s.import_source(NOTES,'meeting_notes','REFERENCE',text=text,extraction='pdftotext' if text else 'reference_only',document_date='2026-10-14')
        recorded=[]
        for oid,outcome,note in OUTCOMES:
            with s.transaction():recorded.append(h.outcome(oid,outcome,note,source_version_id=vid,occurred_at=SEPT30))
        proposals=[]
        for p in PROPOSALS:
            cv=s.propose_claim(p['topic'],p['label'],p['body'],p['evidence_status'],vid,p['locator'])
            existing={r['key'] for r in s.rows('SELECT fact_key key FROM company_fact_values WHERE claim_version_id=?',(cv,))}
            for k,v in p['attributes'].items():
                if k not in existing:h.attach_fact_value(cv,k,v)
            pending=[a for a in s.rows("SELECT id,payload_json FROM approvals WHERE action='promote_claim' AND state='pending'") if json.loads(a['payload_json']).get('version_id')==cv]
            aid=pending[0]['id'] if pending else s.request_approval('promote_claim',{'version_id':cv,'decision_needed':p['decision_needed']},actor='funding_hunter')
            proposals.append({'label':p['label'],'approval_id':aid})
        print(json.dumps({'backup':str(saved),'source_version':vid,'outcomes':recorded,'proposals':proposals,'canonical_facts_changed':0},indent=2))
    finally:s.close()


if __name__=='__main__':main()
