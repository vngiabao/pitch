"""Apply a sourced editorial revision as new versions; never change company truth."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.pitch_studio import PitchStudio

def apply(store):
    pack_path=ROOT/'seed-data/pitch-editorial-2026-10-09.json'
    text=pack_path.read_text(encoding='utf-8');pack=json.loads(text)
    studio=PitchStudio(store)
    source=store.import_source(pack_path,'pitch_editorial','REFERENCE',text=text,extraction='curated_working_drafts')
    result=[]
    for draft in pack['pitches']:
        old=store.db.execute('SELECT pitch_id FROM pitch_seed_keys WHERE seed_key=?',('pitch-studio-v1-'+draft['key'],)).fetchone()
        if old:
            current=studio.detail(old['pitch_id'])
            if current['body']==draft['body'] and current['notes']==draft['notes']:
                result.append({'pitch_id':current['pitch_id'],'state':'unchanged'});continue
            fields={**current,**draft,'sources':list(dict.fromkeys(current['sources']+[source])),
                    'expected_version_id':current['id'],'change_note':'Product-first editorial rewrite - 2026-10-09'}
            saved=studio.save(current['pitch_id'],fields)
        else:
            saved=studio.create({**draft,'sources':[source],'status':'draft','change_note':'Product-first editorial draft - 2026-10-09'},'pitch-editorial-2026-10-09-'+draft['key'])
        result.append({'pitch_id':saved['pitch_id'],'version_id':saved['id'],'title':saved['title'],'state':'saved'})
    return result

if __name__=='__main__':
    s=Store(ROOT/'data/founder.sqlite')
    try:
        result=apply(s)
        (ROOT/'reports/pitch-editorial-2026-10-09-manifest.json').write_text(json.dumps({'changes':result,'originals_modified':False,'canonical_facts_changed':False},indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True))
    finally:s.close()
