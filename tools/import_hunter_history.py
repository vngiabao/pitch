"""Index historical intelligence and unapproved assets without copying originals."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,digest,js
from founder_os.funding_hunter import FundingHunter
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s)
programs=[('Michigan Business Challenge','Zell Lurie Institute, University of Michigan',r'\bMBC\b|Michigan Business Challenge','https://zli.umich.edu/program/michigan-business-challenge/'),('ElevenLabs Startup Grants','ElevenLabs',r'ElevenLabs','https://elevenlabs.io/startup-grants'),('NVIDIA Inception','NVIDIA',r'NVIDIA|Inception','https://www.nvidia.com/en-us/startups/'),('AWS Activate','Amazon Web Services',r'AWS Activate','https://aws.amazon.com/startups/credits/'),('Google for Startups Cloud Program','Google',r'Google for Startups','https://cloud.google.com/startup/'),('Microsoft for Startups','Microsoft',r'Microsoft for Startups|Founders Hub','https://www.microsoft.com/en-us/startups/'),('Y Combinator','Y Combinator',r'Y Combinator','https://www.ycombinator.com/'),('Techstars','Techstars',r'Techstars','https://www.techstars.com/'),('University Pitch Competition #15','F6S',r'University Pitch Competition|F6S','https://www.f6s.com/'),('Honors Fund','Honors Fund',r'Honors Fund',None)]
rows=s.rows('SELECT s.*,v.id version_id,v.body text FROM sources s JOIN source_versions v ON v.source_id=s.id')
history=[];materials=[]
for r in rows:
    name=Path(r['original_path']).name;lower=name.lower();text=r['text'] or ''
    if '.codex' in r['original_path'] and '150' not in text[:200]:continue
    for canonical,organizer,pattern,url in programs:
        match=re.search(pattern,text,re.I)
        if not match and not re.search(pattern,name,re.I):continue
        line=text[:match.start()].count('\n')+1 if match else None
        locator=f'first program mention, extracted text line {line}' if line else 'filename only; content unverified'
        pid=h._program(canonical,organizer,url)
        kind='analyst_memo' if 'audit' in lower or 'research' in lower else 'saved_material'
        note='Historical reference only. Does not establish current eligibility, terms, a submission, rejection, acceptance or other outcome.'
        record_id='history-'+digest([pid,r['original_path'],locator,kind])[:20]
        s.db.execute('INSERT OR IGNORE INTO program_history VALUES(?,?,NULL,?,?,?,?,?)',(record_id,pid,r['version_id'],r['original_path'],locator,kind,note))
        existing=s.db.execute("SELECT 1 FROM imports WHERE destination_type='program_history' AND destination_id=?",(record_id,)).fetchone()
        if not existing:s.import_receipt(r['version_id'],'program_history',record_id,locator,'Indexed historical program mention without inferring outcome')
        history.append({'id':record_id,'program_id':pid,'source_version_id':r['version_id'],'original_path':r['original_path'],'locator':locator,'kind':kind})
    kinds=[]
    if 'pitch deck' in lower and Path(name).suffix.lower() in ('.pdf','.pptx','.fig'):kinds.append('deck')
    elif 'deck' in lower:kinds.append('pitch_script')
    if 'financial' in lower:kinds.append('financials')
    if 'market' in lower:kinds.extend(['market','competitors'])
    if 'brief' in lower or 'writing' in text[:200].lower() or 'finalized' in text[:200].lower():kinds.extend(['product_description','founder_bio','traction'])
    if 'overview' in lower:kinds.append('product_description')
    for kind in sorted(set(kinds)):
        record_id='material-'+digest([r['version_id'],kind])[:20]
        s.db.execute("INSERT OR IGNORE INTO material_registry VALUES(?,?,?,?,'reference','[]',NULL)",(record_id,r['version_id'],kind,name))
        if not s.db.execute("SELECT 1 FROM imports WHERE destination_type='material_registry' AND destination_id=?",(record_id,)).fetchone():s.import_receipt(r['version_id'],'material_registry',record_id,'entire file / filename-based material type','Reference classification only; requires current-truth validation and owner approval')
        materials.append({'id':record_id,'kind':kind,'source_version_id':r['version_id'],'original_path':r['original_path'],'status':'reference'})
report={'historical_references':history,'material_references':materials,'original_files_modified':0,'outcomes_inferred':0,'canonical_claims_changed':0,'coverage':'Selected registered migration sources; full manifest remains linked metadata. Program mentions are references, not application evidence.'}
(ROOT/'reports/hunter-history-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
ledger=s.rows('SELECT i.*,s.original_path,v.sha256 FROM imports i JOIN source_versions v ON v.id=i.source_version_id JOIN sources s ON s.id=v.source_id')
(ROOT/'reports/import-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'history_references':len(history),'material_references':len(materials),'original_files_modified':0,'outcomes_inferred':0}));s.close()
