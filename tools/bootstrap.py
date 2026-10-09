"""Create an isolated foundation from an explicit source index and supplied drafts.

Does not execute source scripts, copy source directories, approve claims, or submit.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from founder_os.store import Store, digest, js
from founder_os.agents import Founder


def locate(text, phrase):
    for i,line in enumerate(text.splitlines()):
        if phrase.casefold() in line.casefold():return 'line '+str(i+1)
    raise ValueError('Expected source passage missing: '+phrase)


def taxonomy(row):
    p=row['relative_path'].lower();kind=row['content_type'];tags=[]
    if row.get('exact_duplicate_group') and row.get('canonical_source_id')!=row['source_id']:
        return 'DUPLICATE',['retain original','exact byte match']
    if kind=='Dependencies and generated runtime' or kind=='External reference deck':return 'UNRELATED',['excluded from A Story company memory']
    if 'mbc resources' in p and not p.endswith('.zip'):return 'STALE',['historical 2025-2026 requirements','reusable prompt structure']
    if kind in ('Research and pitch narrative','Research and feedback analysis','Evidence and claim review','Financial model and research source'):return 'RAW RESEARCH',['unapproved','claim-level reconciliation required']
    if kind in ('Image or design asset','Design and brand material','Rendered deck derivative'):return 'MEDIA/ASSETS',['reference only']
    if row['category']=='ARCHIVE':
        if kind=='Deck version':tags=['possible submission material; submission unconfirmed']
        return 'ARCHIVE',tags
    return 'USEFUL REFERENCE',['not canonical']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',type=Path,required=True);ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--prompt',type=Path,required=True);ap.add_argument('--essay',type=Path,required=True);ap.add_argument('--db',type=Path,default=ROOT/'data'/'founder.sqlite');args=ap.parse_args()
    s=Store(args.db);f=Founder(s);versions={};source_index=json.loads(args.index.read_text(encoding='utf-8'))
    for row in source_index:
        path=Path(row['source_path']);ext=path.suffix.lower();text=path.read_text(encoding='utf-8-sig') if ext in {'.md','.txt'} else None
        classification='RAW RESEARCH' if text is not None and ('research' in row['content_type'].lower() or 'claim' in row['content_type'].lower()) else 'USEFUL REFERENCE'
        versions[row['relative_path']]=s.import_source(path,'pilot_reference',classification,row.get('sha256'),text,'verbatim UTF-8 text' if text is not None else 'hash and original path; binary/code not ingested')
    prompt_sv=s.import_source(args.prompt,'user_instructions','USEFUL REFERENCE',extraction='provenance only; instructions implemented from user request')
    essay_text=args.essay.read_text(encoding='utf-8-sig')
    essay_sv=s.import_source(args.essay,'unfinalized_essay','USEFUL REFERENCE',text=essay_text,extraction='verbatim UTF-8 draft snapshot; no implied approval')
    drafts=json.loads((ROOT/'draft-answers.json').read_text(encoding='utf-8'))
    lines=essay_text.splitlines();found=[]
    for draft in drafts:
        idx=next(i for i,line in enumerate(lines) if line.startswith(draft['heading']))
        found.append((idx,draft))
    if found!=sorted(found,key=lambda x:x[0]):raise ValueError('Question order changed')
    opp=s.upsert_opportunity('Organizer identity pending confirmation','$150K University Pitch Competition #15','saved 2026 application, current intake unverified',essay_sv,state='historical_application_draft',terms={'prize':'$150K in draft title; form/terms need reconciliation','dilution':'unverified'})
    app=s.create_application(opp,'F6S draft essay review')
    claim_specs=[
        ('product_description','Short product description','An AI interviewer that helps families record stories by phone.','hypothesis','An AI biographer'),
        ('positioning','Family context differentiation','Family contributions may improve subsequent interviews; retention and defensibility remain hypotheses.','hypothesis','Our long-term advantage'),
        ('pricing','Current plan and bundle prices','Draft lists $119/year Individual, $229/year Family, $19.99/month, $79 Express, books from $69 and a $154 bundle. Reconcile before approval.','reported','Our current paid plans'),
        ('traction','Pilot families and waiting buyers','Draft reports 10 pilot families and five families waiting to pay; no verified payment or usage logs supplied.','reported','So far, 10 pilot families'),
        ('features','Beta and feature readiness','Draft reports an end-to-end beta, TestFlight distribution and App Store review; release state and demonstrated features need verification.','reported','The core product works end to end'),
        ('team','Founders and outside commitments','Draft reports CEO/COO roles, part-time tutoring and future finance study; current responsibilities and dates need confirmation.','reported','Daniel will begin'),
        ('customer_evidence','Hope College interest','Draft reports interest in a holiday gifting program; no agreement or completed program established.','reported','Hope College'),
        ('fundraising','Runway not established','Editorial suggestion to replace three months with twelve is not financial evidence. Derive runway from current cash, commitments and burn.','unknown','3 months runway'),
        ('market','Revenue scale arithmetic','100,000 paying families at an assumed $150 annual revenue per family yields $15M; one-time book revenue must not be called ARR.','model','100,000 paying families'),
        ('competitors','Competitor exclusivity claim','Blanket claim that competitors end in one book needs rejection or current feature-specific substantiation.','unknown','Competitors end in one book'),
        ('approved_language','No approved language imported','All supplied essay variants are drafts; wording approval remains a separate owner decision.','unknown','not rely on this completely'),
        ('rejected_language','Permanence promise needs review','Do not carry the draft forever commitment into application copy without an approved service policy.','unknown','forever'),
    ]
    by_topic={}
    for topic,label,body,status,phrase in claim_specs:
        vid=s.propose_claim(topic,label,body,status,essay_sv,locate(essay_text,phrase));by_topic.setdefault(topic,[]).append(vid)
    decisions=[
        ('pricing','Confirm the current offer','Reconcile plan prices, included minutes, monthly/annual billing, Express and book bundles before any canonical pricing change.'),
        ('traction','Reconcile pilots and payments','Confirm dated leads, participating families, completed calls, waiting buyers and actual revenue. Waiting to pay is not a payment.'),
        ('features','Verify the demonstrated product','Provide a dated end-to-end demonstration and current beta/App Store status; retain live-versus-proposed distinctions.'),
        ('team','Confirm founder roles and outside obligations','Confirm roles, full-time commitments, part-time tutoring, degree dates and future enrollment; verify IP/contributor statements.'),
        ('fundraising','Calculate runway from records','Do not change three months to twelve for presentation. Confirm current cash, recurring burn and committed costs.'),
    ]
    for topic,title,detail in decisions:
        s.issue('confirmation',title,detail,[essay_sv])
        vid=by_topic[topic][0]
        if not s.db.execute('SELECT 1 FROM approvals WHERE action=\'promote_claim\' AND payload_json LIKE ?',('%'+vid+'%',)).fetchone():
            s.request_approval('promote_claim',{'version_id':vid,'decision_needed':detail},actor='consistency_truth')
    s.issue('positioning','Demonstrate differentiation before claiming a moat','Lead with recording stories by phone. Show the family-context loop. Do not assert competitors lack archives, family calls or repeat use without current evidence.',[essay_sv])
    s.issue('consent','Confirm use of the family origin story','Confirm wording, relative relationships, timing and permission before using a sensitive family medical story in public materials.',[essay_sv])
    s.issue('evidence','Verify institutional interest','Interest from Hope College is not a signed partnership, revenue or proof a holiday program ran.',[essay_sv])
    answer_ids=[]
    for n,(start,draft) in enumerate(found):
        heading=lines[start];limit=re.search(r'([\d,]+) characters',heading)
        maxchars=int(limit.group(1).replace(',','')) if limit else None
        end=found[n+1][0] if n+1<len(found) else next(i for i in range(start+1,len(lines)) if lines[i].startswith('15. Pitch deck'))
        q=s.add_question(app,n+1,heading.strip(),essay_sv,f'line {start+1}',maxchars,'characters' if maxchars else None,False)
        raw='\n'.join(lines[start+1:end]).strip()
        s.add_answer(q,raw,[essay_sv],unresolved=['Raw source contains alternative drafts and editorial notes; not a final answer.'],provenance=f'verbatim draft variants; lines {start+2}-{end}')
        facts=[vid for topic in draft['topics'] for vid in by_topic.get(topic,[])]
        aid=s.add_answer(q,draft['body'],[essay_sv],facts,draft['unresolved'],'revised by assistant from unfinalized essay; internal review draft')
        if maxchars and len(draft['body'])>maxchars:raise ValueError('Revised draft exceeds its source limit: '+draft['key'])
        answer_ids.append(aid)
    for capability,payload in [
        ('opportunity_scout',{'opportunities':[{'organizer':'Michigan Business Challenge','program':'Michigan Business Challenge','cycle':'2025-2026 historical materials','source_version_id':versions['MBC Resources\\Intent to Compete MBC 2026.docx'],'criteria':{}},{'organizer':'ElevenLabs','program':'Startup Grants','cycle':'2026 materials, current cycle unverified','source_version_id':versions['Grant and Investor Research - 2026-09-29\\01-Research-and-Rejection-Audit.md'],'criteria':{}}]}),
        ('application',{'application_id':app}),
        ('research',{'query':'traction pricing hypothesis revenue'}),
        ('consistency_truth',{'check_source_changes':True}),
        ('follow_up',{'days':30}),
        ('customer_evidence',{'items':[{'kind':'product_learning','body':'Unfinalized essay reports reducing setup and first-call friction after pilots. Outcome not independently measured.','source_version_id':essay_sv,'locator':locate(essay_text,'The first beta exposed'),'permission_status':'internal_only_unverified'}]}),
        ('pitch',{'duration_seconds':30,'audience':'general','body':'A Story is being built to help families record the stories they keep meaning to ask about. A willing parent or grandparent talks by phone, while the family helps organize the memories around them. We are testing how relatives’ photos and recollections can improve later interviews. The aim is a family record that keeps each person’s voice and perspective.','source_version_id':essay_sv,'claim_versions':by_topic['product_description']+by_topic['positioning']})
    ]:f.enqueue(capability,payload,'bootstrap-v1-'+capability)
    while f.run_one() is not None:pass
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    (reports/'import-ledger.json').write_text(json.dumps(s.export_ledger(),ensure_ascii=False,indent=2),encoding='utf-8')
    (reports/'answer-review.json').write_text(json.dumps([s.answer_readiness(a) for a in answer_ids],ensure_ascii=False,indent=2),encoding='utf-8')
    counts={k:0 for k in ['CANONICAL KNOWLEDGE','USEFUL REFERENCE','HISTORICAL SUBMISSION','RAW RESEARCH','MEDIA/ASSETS','DUPLICATE','STALE','UNRELATED','ARCHIVE']}
    with zipfile.ZipFile(args.inventory) as archive,gzip.open(reports/'founder-taxonomy.jsonl.gz','wt',encoding='utf-8') as dest:
        with archive.open('manifest.jsonl') as src:
            for line in src:
                row=json.loads(line);primary,tags=taxonomy(row);counts[primary]+=1
                dest.write(js({'source_id':row['source_id'],'original_path':row['source_path'],'relative_path':row['relative_path'],'sha256':row.get('sha256'),'hash_status':row['hash_status'],'old_disposition':row['category'],'classification':primary,'secondary_tags':tags,'canonical_approved':False,'submitted_confirmed':False})+'\n')
    summary={'inventory_paths':sum(counts.values()),'taxonomy_counts':counts,'pilot_sources_registered':len(versions),'attachments_registered':2,'source_versions':s.db.execute('SELECT count(*) FROM source_versions').fetchone()[0],'claims_proposed':s.db.execute('SELECT count(*) FROM claims').fetchone()[0],'canonical_claims':0,'questions':len(found),'revised_answers':len(answer_ids),'application_id':app,'essay_source_version':essay_sv,'prompt_source_version':prompt_sv,'jobs':s.rows('SELECT capability,state,error FROM jobs'),'submissions':0,'source_files_modified':0,'live_model_connected':False,'scheduler_installed':False}
    (reports/'migration-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    s.close();print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
