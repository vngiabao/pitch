"""Idempotently add the October 14 three-minute competition pitch as a new editable draft."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.pitch_studio import PitchStudio

def main():
    batch=json.loads((ROOT/'seed-data/pitch-mbc-3min-2026-10-14.json').read_text(encoding='utf-8'))
    s=Store(ROOT/'data/founder.sqlite')
    try:
        sources=[r['id'] for term in batch['source_terms'] for r in s.rows('SELECT v.id FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE s.original_path LIKE ? ORDER BY v.captured_at DESC LIMIT 1',('%'+term,))]
        if not sources:raise ValueError('Run tools/apply_meeting_notes_2026_10_14.py first; the meeting notes source is not registered')
        record=PitchStudio(s).create({**batch['pitch'],'sources':sources},batch['seed_key'])
        print(json.dumps({'pitch_id':record['pitch_id'],'version_id':record['id'],'title':record['title'],'sources':record['sources']}))
    finally:s.close()
if __name__=='__main__':main()
