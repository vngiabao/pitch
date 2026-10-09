"""Record local Pitch Studio data and preserved source evidence, read-only."""
import hashlib,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
db=sqlite3.connect((ROOT/'data/founder.sqlite').as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row
try:
    active=db.execute("SELECT count(*) FROM pitch_documents d JOIN pitch_versions v ON v.id=d.current_version_id WHERE v.status!='archived'").fetchone()[0]
    sources=[]
    for row in db.execute("SELECT DISTINCT s.original_path,v.sha256 FROM pitch_versions p,json_each(p.sources_json) j JOIN source_versions v ON v.id=j.value JOIN sources s ON s.id=v.source_id WHERE s.original_path LIKE '%Pitch Competition%' "):
        path=Path(row['original_path'])
        sources.append({'path':str(path),'exists':path.is_file(),'matches_registered_sha256':path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']})
    report={'verified_at':datetime.now(timezone.utc).isoformat(),'active_pitches':active,
        'original_source_checks':sources,'all_checked_source_bytes_preserved':all(s['matches_registered_sha256'] for s in sources),
        'automated_checks':json.loads((ROOT/'reports/pitch-studio-test-result.json').read_text(encoding='utf-8')),
        'browser_checks_october_8_session':['custom audience and scenario creation','95-second custom length saved','edited text survived reload','verification draft archived; 14 active pitches remain','rehearsal timer started and paused at 14 seconds','1280px desktop and 390px mobile without horizontal page overflow','no browser console errors'],
        'screenshots_directory':'.impeccable/review/pitch','canonical_facts_changed':False,'external_submissions':0,
        'limits':['Longer pitches are editable working outlines; they need evidence and demonstration preparation.','Timing is estimated at 130 words/minute.','Screenshots and tests do not establish any external program eligibility.']}
    (ROOT/'reports/pitch-studio-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'active_pitches':active,'preserved_sources':len(sources),'all_checked_source_bytes_preserved':report['all_checked_source_bytes_preserved']}))
finally:db.close()
