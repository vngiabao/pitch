"""Idempotently add sourced working pitches. Never writes to the source folder."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.pitch_studio import PitchStudio

def main():
    path=ROOT/'data/pitch-studio-starters.json'
    if not path.exists():path=ROOT/'seed-data/pitch-studio-starters.json'
    text=path.read_text(encoding='utf-8');batch=json.loads(text);s=Store(ROOT/'data/founder.sqlite')
    try:
        studio=PitchStudio(s);studio.sync_legacy()
        sources=[]
        for term in batch['source_terms']:
            for row in s.rows('SELECT source_version_id FROM material_library WHERE relative_path LIKE ? AND duplicate_of IS NULL AND source_version_id IS NOT NULL',('%'+term,)):
                sources.append(row['source_version_id'])
        if not sources:raise ValueError('Pitch source material is unavailable; no starter drafts added')
        generated=s.import_source(path,'pitch_studio_starters','REFERENCE',text=text,extraction='curated_working_drafts')
        fact_sources=s.rows("SELECT v.source_version_id,v.id FROM claim_versions v JOIN claims c ON c.canonical_version_id=v.id JOIN claim_reviews r ON r.version_id=v.id WHERE r.status='approved' AND c.label LIKE '%funding%' LIMIT 1")
        sources=list(dict.fromkeys(sources+[generated]+[r['source_version_id'] for r in fact_sources]))
        manifest=[]
        for draft in batch['pitches']:
            fields={**draft,'speaker':'','status':'draft','sources':sources,'claim_versions':[r['id'] for r in fact_sources],
                'notes':batch['draft_note'],'change_note':'Sourced starter draft'}
            record=studio.create(fields,'pitch-studio-v'+str(batch['version'])+'-'+draft['key']);manifest.append({'pitch_id':record['pitch_id'],'version_id':record['id'],'title':record['title'],'source_versions':record['sources']})
        (ROOT/'reports/pitch-studio-manifest.json').write_text(json.dumps({'source_folder':r'C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition','originals_modified':False,'drafts':manifest},indent=2),encoding='utf-8')
        print(json.dumps({'starter_drafts':len(manifest),'total_pitches':len(studio.list()['items']),'originals_modified':False}))
    finally:s.close()
if __name__=='__main__':main()
