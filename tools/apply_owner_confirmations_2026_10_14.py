"""Apply the owner's Oct 14, 2026 answers to the 8 pending decisions.

The old proposals were 'reported' notes (some only reminders), which can never become
eligibility facts. They are rejected and replaced with clean, owner-verified facts.
Team size is changed inside the existing owner-confirmed profile so it does not
conflict with a second team_size value. Takes a consistent backup first.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter

FOLDER=Path(r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition')
CONFIRM=FOLDER/'Owner-Confirmations-2026-10-14.md'
PRICING=FOLDER/'astoryapp-pricing-2026-10-14.md'
PROFILE_CLAIM='claim-8d66aa68e3949cecf35b'
OLD=['approval-7e988106379c44398dbf43b08be8c5be','approval-369ca076d283408ca61098e069306548','approval-d1e27bc5a6e24802bbb5ba1e518129a6',
     'approval-2598b9090a7a4cf4ba78ad5eacadbc8c','approval-dd44c635ca2e431c89317ff4a4ea9f7d','approval-24cb02f33b214350b6b38e1d09f83753',
     'approval-ec374edfac4640068f8d604f73985448','approval-caaa71bb3c4a4610b76558cb83dec0cd']
NOTE='Owner answered on Oct 14, 2026; replaced by a clean owner-verified fact (see Owner-Confirmations-2026-10-14.md).'

FACTS=[
 ('product_description','Product and stage - confirmed Oct 14, 2026','confirm',
  'A Story is a consumer AI product: an AI biographer that calls family members, records their stories in their own voice and builds a shared family archive. It is in private beta on TestFlight; the App Store release is in review.',
  {'uses_ai':True,'product_stage':'private_beta','customer_type':'B2C','business_type':'consumer_subscription','industry':'consumer_ai'}),
 ('team','Incorporation - confirmed Oct 14, 2026','confirm',
  'A Story Technologies, Inc. is a Delaware C-Corporation, incorporated in June 2026.',
  {'incorporated':True,'us_company':True,'incorporation_date':'2026-06'}),
 ('traction','Beta traction - confirmed Oct 14, 2026','confirm',
  'Owner-reported: the first MVP brought in 50 leads; 10 families were selected for the private beta; 5 more families are waiting to join as paying customers once the redesigned release ships. No payment records verify this yet.',{}),
 ('features','Product readiness - confirmed Oct 14, 2026','confirm',
  'The core product works end to end: scheduled AI-guided phone interviews, transcription, the family archive, relative invitations, photo contributions and billing. The private beta runs on TestFlight and the App Store release is in review.',{}),
 ('team','Founders and commitments - confirmed Oct 14, 2026','confirm',
  'A Story has two founders: Daniel Hoang Nguyen (CEO) and Bao Vo (COO). Daniel works on A Story full time, tutors part time (unrelated to A Story) and starts an MS in Financial Mathematics at UIUC in 2027. Bao has finished graduate school and works on A Story full time. Nhi Tran is listed as CMO only for the Michigan Business Challenge; other applications name the two founders.',{}),
 ('pricing','Pricing - astoryapp.com, Oct 14, 2026','pricing',
  'Free $0 (three guided questions a day, no calls); Express $79 one-time (about 30 days, 140 call minutes); Individual $119/year (one storyteller, 90 call minutes a month, a Classic Hardcover each year); Family $229/year (up to three storytellers, 200 shared minutes a month, a hardcover per storyteller); Monthly $19.99/month. Books: Digital $19, Softcover $39, Classic Hardcover $69, Heirloom $149, Full-Service Legacy $499. Relatives read and contribute free. Pre-launch: reserve Individual for $1 by November 2 for 15% off the first year.',{}),
 ('fundraising','Funding and runway - confirmed Oct 14, 2026','confirm',
  'A Story is bootstrapped from founder money with no outside investment. There is no fixed runway; when a form requires a number, use 8 months.',
  {'self_funded':True,'institutional_equity_funding':False}),
]

def approve(s,vid,why):
    aid=s.request_approval('promote_claim',{'version_id':vid,'decision_needed':why},actor='founder')
    s.decide(aid,'approved',owner_confirmation=True,note=NOTE);return aid

def main():
    db_path=ROOT/'data/founder.sqlite'
    (db_path.parent/'repair-backups').mkdir(exist_ok=True)
    target=db_path.parent/'repair-backups'/('before-owner-confirmations-'+now()[:19].replace(':','')+'.sqlite')
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close()
    s=Store(db_path)
    try:
        h=FundingHunter(s);stamp=now()
        sv={'confirm':s.import_source(CONFIRM,'owner_confirmation','CANONICAL',text=CONFIRM.read_text(encoding='utf-8'),extraction='owner_statement',document_date='2026-10-14'),
            'pricing':s.import_source(PRICING,'official_pricing_capture','REFERENCE',text=PRICING.read_text(encoding='utf-8'),extraction='site_capture',document_date='2026-10-14')}
        rejected=[]
        for aid in OLD:
            if s.one('SELECT state FROM approvals WHERE id=?',(aid,))['state']=='pending':
                s.decide(aid,'rejected',owner_confirmation=True,note=NOTE);rejected.append(aid)
        saved=[]
        for topic,label,source,body,attrs in FACTS:
            vid=s.propose_claim(topic,label,body,'verified',sv[source],'owner answers, Oct 14 2026',last_verified_at=stamp)
            have={r['fact_key'] for r in s.rows('SELECT fact_key FROM company_fact_values WHERE claim_version_id=?',(vid,))}
            for k,v in attrs.items():
                if k not in have:h.attach_fact_value(vid,k,v)
            if s.one('SELECT status FROM claim_reviews WHERE version_id=?',(vid,))['status']!='approved':approve(s,vid,'Owner-confirmed fact')
            saved.append(label)
        # Update the approved profile itself: two founders, full CEO name, accepted programs.
        cur=s.one('SELECT v.id FROM claims c JOIN claim_versions v ON v.id=c.canonical_version_id WHERE c.id=?',(PROFILE_CLAIM,))['id']
        values={r['fact_key']:json.loads(r['value_json']) for r in s.rows('SELECT fact_key,value_json FROM company_fact_values WHERE claim_version_id=?',(cur,))}
        values.update(team_size=2,cofounder_name='Daniel Hoang Nguyen',previous_programs=['NVIDIA Inception Program','Cartesia Startups Grant','AssemblyAI Startup Program'])
        pv=s.propose_claim('team','Owner-confirmed company profile — October 6, 2026',json.dumps(values,sort_keys=True),'verified',sv['confirm'],'owner answers, Oct 14 2026: team of two founders; accepted programs',claim_id=PROFILE_CLAIM,last_verified_at=stamp)
        if s.one('SELECT status FROM claim_reviews WHERE version_id=?',(pv,))['status']!='approved':
            have={r['fact_key'] for r in s.rows('SELECT fact_key FROM company_fact_values WHERE claim_version_id=?',(pv,))}
            for k,v in values.items():
                if k not in have:h.attach_fact_value(pv,k,v)
            approve(s,pv,'Owner-confirmed profile update')
        mem=h.company_memory()
        print(json.dumps({'backup':str(target),'rejected':len(rejected),'facts_saved':saved,'profile_version':pv,
                          'active_attributes':len(mem['attributes']),'conflicts':mem['conflicting_attributes'],
                          'pending_left':s.one("SELECT count(*) n FROM approvals WHERE state='pending'")['n'],
                          'key_values':{k:mem['attributes'][k]['value'] for k in ('team_size','incorporated','uses_ai','product_stage','self_funded','previous_programs') if k in mem['attributes']}},indent=2,ensure_ascii=False))
    finally:s.close()

if __name__=='__main__':main()
