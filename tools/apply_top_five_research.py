"""One-time source-grounded curation of the owner's requested sample.

Provider observations were read from official pages on October 7, 2026.
This is an ingestion artifact, not provider-specific logic in the agent.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now,js
from founder_os.funding_hunter import FundingHunter
from founder_os.report_email import DailyReporter

s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s);checked=now();items=[]

def load(oid,url,summary):
    d=h.detail(oid)['data']
    d['sources'].append({'url':url,'role':'official_program','checked_at':checked,'excerpt':summary})
    return d

def field(d,key,value,url):
    if '.' in key:
        section,k=key.split('.',1);d[section][k]=value
    else:d[key]=value
    d['field_sources'][key]=[url]

def curate(d,url,why,help,angle,next_step,owner,priority='CORE_PRODUCT',basis='conditional',facts=()):
    d['founder_brief']={'why_applicable':why,'how_it_helps':help,'application_angle':angle,
        'agent_next_step':next_step,'owner_decisions':owner,'company_fact_keys':list(facts),
        'source_urls':[url],'priority':priority,'basis':basis}
    d['why_fit']=[why];items.append(d)

url='https://runway.com/product/builders'
d=load('opp-59702300e70697137549',url,'Builders overview/benefits/application: Seed to Series C positioning; up to 500k API credit units, Tier 5, Characters access and builder community. Nine form questions include a funding-stage dropdown. No Builders closing date published; adjacent October 31 banner is an enterprise promotion.')
field(d,'funding.other_benefits','Up to 500,000 API credit units, Tier 5 limits, Characters access and builder support.',url)
field(d,'eligibility.company_stage','Marketing targets Seed to Series C; live form allows Bootstrapped. Bootstrapped acceptance needs verification.',url)
field(d,'eligibility.other_restrictions','Business email and company website/LinkedIn; describe avatar use and current visual models.',url)
field(d,'credit_benefits.tier','Builders',url)
d['risks']=['Seed-to-Series-C positioning differs from the Bootstrapped form option; acceptance is not confirmed.']
curate(d,url,'Directly matches the personalized visual interviewer you described.','Credits and Characters access could fund a web/mobile avatar experiment while phone calls remain the core experience.',
       'Position A Story as a persistent family interviewer with memory-controlled questions and personalized appearance, voice and personality.',
       'Keep the filled draft on hold; verify bootstrapped acceptance and API terms.',
       ['None now - you instructed us not to send the Runway application.'],facts=['funding_stage'])

url='https://elevenlabs.io/startup-grants'
d=load('opp-9ffd0692de45f6559044',url,'Benefits and eligibility FAQ: 33M text characters over 12 months, rolling; fewer than 25 employees, business email, long-term monetized AI voice product. Excludes enterprise customers, agencies, minor-targeted products and repeated company applications. Free-plan conversion unless another option was selected.')
field(d,'funding.other_benefits','33 million text characters over 12 months plus startup support.',url)
d['risks']=['Eligibility excludes products built for children aged 18 or under; family use alone does not establish eligibility.']
curate(d,url,'Your proposed family interviewer has a clear voice use case; the confirmed four-member team is below the published size cap.',
       'Could reduce voice-generation cost for interviews and narration if ElevenLabs fits the chosen stack.',
       'Emphasize ongoing family interviews, natural voice interaction and a sustainable business model.',
       'Inspect the official application, reuse the existing ElevenLabs deck and validate its claims against current memory.',
       ['Confirm prior grant applications, enterprise-account status and whether the product is intended for minors.'],facts=['team_size'])

url='https://www.cartesia.ai/startups'
d=load('opp-1d317459817ff1acf725',url,'Startup grant benefits and FAQs: 12 months of Scale, 8M shared Sonic/Ink credits monthly, $299/month Managed Agents credits. Any startup stage, rolling. Marketing/logo and requested social-post terms. After year one $299/month Scale; overage is optional pay-as-you-go.')
field(d,'funding.other_benefits','96 million Sonic/Ink usage credits per year plus $299/month Managed Agents credits for 12 months.',url)
field(d,'credit_benefits.renewal_behavior','After 12 months the Scale plan costs $299/month; cancel or downgrade to avoid renewal charges.',url)
field(d,'credit_benefits.eligible_products','Sonic speech generation, Ink transcription and Managed Agents.',url)
field(d,'eligibility.other_restrictions','Logo/name marketing rights and social posts if requested; review terms before acceptance.',url)
d['risks']=['Included credits do not cover optional usage overages.']
curate(d,url,'Accepts startups at any stage; its speech and transcription stack could serve your proposed family interviewer.',
       'Could subsidize a year of voice experiments and a transcription comparison before committing to a provider.',
       'Explain persistent family conversations and why natural speech and accurate transcription matter to the interview experience.',
       'Inspect questions and plan a small benchmark; flag renewal and publicity terms in the eventual exact preview.',
       ['Decide whether the publicity obligations and paid renewal risk are acceptable.'],facts=['funding_stage'])

url='https://aws.amazon.com/startups/credits'
d=load('opp-6b33ae9d69285932dc3f',url,'Credit tier table and how-to-apply: Founders for self-funded startups starts at $1,000; selected participants up to $5,000. Pre-Series-B, founded within ten years, Paid Tier account and prior-credit limits. Portfolio maximum needs a provider Org ID. Professional email/Builder ID and AWS account linking. Existing standing intake is tracked as rolling; no closing date stated.')
field(d,'credit_benefits.tier','Founders: starts at $1,000; selected participants may receive up to $5,000',url)
field(d,'funding.credits_value',5000,url)
field(d,'funding.currency','USD',url)
field(d,'eligibility.company_stage','Pre-Series B; Founders accepts bootstrapped/self-funded startups.',url)
field(d,'eligibility.age_requirement','Founded within ten years.',url)
field(d,'eligibility.other_restrictions','Paid Tier AWS account; must be new to Activate or request more credits than previously received.',url)
d['risks']=['Paid Tier account and usage beyond credits can create charges; usable savings need a compatible workload.']
curate(d,url,'The Founders tier explicitly accepts self-funded startups, matching A Story\'s confirmed bootstrapped stage.',
       'Could offset hosting or eligible AI workloads if they already run on AWS or a small migration is worthwhile.',
       'Lead with the supported company/product description and a concrete eligible workload; do not claim the partner-tier maximum.',
       'Verify account and prior-credit conditions, inspect questions and compare benefit with integration effort.',
       ['Confirm whether you have a Paid Tier AWS account and any previous Activate credits.'],priority='COST_SAVINGS',basis='approved_memory',facts=['funding_stage'])

url='https://cloud.google.com/startup/pre-funded'
d=load('opp-cb3e8eb7372841b12251',url,'Pre-funded selection criteria/benefits: $2,000 credit tier, 12-month validity, digital-native technology startup with working MVP/business model and plans for venture funding, founded within 24 months, no credits beyond trial, billing account ID. Proprietary Google models covered; third-party models billed separately. General benefits page differs on age, so review is required.')
field(d,'funding.credits_value',2000,url);field(d,'funding.currency','USD',url)
field(d,'credit_benefits.tier','Pre-funded Start tier',url)
field(d,'credit_benefits.expiration_months',12,url)
field(d,'credit_benefits.excluded_products','Third-party models are billed separately and are not covered by these program credits.',url)
field(d,'eligibility.company_stage','Technology startup with working MVP, clear business model and plans to seek venture funding.',url)
field(d,'eligibility.age_requirement','Pre-funded page says founded within 24 months; general benefits page differs. Verify tier-specific rules.',url)
field(d,'eligibility.other_restrictions','No Google Cloud credits beyond the free trial; billing account ID required; excluded business categories apply.',url)
d['eligibility_complete']=False
d['risks']=['Current Google workload and usable savings are unknown; third-party model spend is excluded.']
curate(d,url,'The pre-funded tier is the relevant lead for a bootstrapped company; the confirmed June 2026 founding date is within the stricter published age window.',
       'Could cover $2,000 of compatible cloud or Google-model experiments without pursuing the funded-tier headline award.',
       'Describe a real MVP and intended eligible workload; keep venture-funding plans and provider use accurate.',
       'Resolve tier-rule discrepancies and inspect the form before drafting; do not invent a deadline.',
       ['Confirm working MVP, venture-funding plans, billing account and prior Google credits.'],priority='COST_SAVINGS',facts=['funding_stage','founded_date'])

batch={'queries':['site:cloud.google.com startup Start tier eligibility'],
       'candidates':[{'title':d['canonical_name'],'url':d['official_url'],'family':'owner_requested_curation','state':'VERIFIED_SOURCE','note':'Existing lead rechecked for a founder decision brief.'} for d in items],
       'opportunities':items,'errors':[],
       'usage':{'runner':'owner-requested live official research','model_api_cost':None,'api_key_used':False}}
path=ROOT/'reports/top-five-2026-10-07-research.json';path.write_text(json.dumps(batch,ensure_ascii=False,indent=2),encoding='utf-8')
report=h.runFundingHunter(batch,'owner-top-five-curation-2026-10-07-v2')
if report['errors']:raise RuntimeError(json.dumps(report['errors']))
sample=DailyReporter(s).render(sample=True)
(ROOT/'reports/top-five-sample-2026-10-07.txt').write_text(sample['body'],encoding='utf-8')
key=DailyReporter(s).prepare_sample()
(ROOT/'reports/top-five-sample-outbox.json').write_text(json.dumps({'kind':'supplement','id':key,'shortlist':sample['shortlist']},indent=2),encoding='utf-8')
print(json.dumps({'report_id':report['run_id'],'sample_id':key,'shortlist':sample['shortlist']}))
s.close()
