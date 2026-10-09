"""Read-only integrity and provenance checks for the delivered pilot."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
db = sqlite3.connect((root / 'data/founder.sqlite').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not db.execute('PRAGMA foreign_key_check').fetchall()
sources = list(db.execute('SELECT s.original_path,v.sha256 FROM sources s JOIN source_versions v ON v.source_id=s.id'))
source_checks = []
for row in sources:
    h = hashlib.sha256()
    with Path(row['original_path']).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    assert h.hexdigest() == row['sha256'], row['original_path']
    source_checks.append(dict(row))
mapping = {'source_version':'source_versions','claim_version':'claim_versions','question':'questions','answer_version':'answer_versions','evidence':'evidence','pitch':'pitches','program_history':'program_history','material_registry':'material_registry'}
imports = list(db.execute('SELECT * FROM imports'))
for row in imports:
    table = mapping[row['destination_type']]
    assert db.execute(f'SELECT 1 FROM {table} WHERE id=?', (row['destination_id'],)).fetchone(), dict(row)
    assert row['locator'] and row['transformation']
with gzip.open(root / 'reports/founder-taxonomy.jsonl.gz','rt',encoding='utf-8') as f:
    taxonomy = [json.loads(line) for line in f]
assert len(taxonomy) == 103159
counts = {table:db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ('sources','source_versions','imports','claims','questions','answer_versions','approvals','jobs','submissions')}
canonical = db.execute('SELECT count(*) FROM claims WHERE canonical_version_id IS NOT NULL').fetchone()[0]
assert canonical == 1 and counts['submissions'] == 0
assert counts['sources'] >= 26 and counts['questions'] == 9 and counts['answer_versions'] == 18
assert db.execute("SELECT count(*) FROM approvals WHERE action='promote_claim' AND state='pending'").fetchone()[0] == 5
assert db.execute("SELECT label FROM claims WHERE canonical_version_id IS NOT NULL").fetchone()[0] == 'Owner-confirmed company profile — October 6, 2026'
db.close()
report = {'verified_at':datetime.now(timezone.utc).isoformat(),'database_integrity':'ok','foreign_key_errors':0,'registered_source_hashes_rechecked':len(sources),'changed_registered_sources':0,'valid_import_destinations':len(imports),'manifest_records':len(taxonomy),'counts':counts,'canonical_claims':canonical,'source_checks':source_checks,'scope_note':'Rechecked all registered source versions, including the expanded pitch document library and the owner-confirmation source. Binary library assets are local references with cached inventory hashes, not newly rehashed content. This is not a second full-tree hash audit. Original files were read only. One owner-confirmed profile is canonical; five essay proposals remain pending.'}
(root / 'reports/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k != 'source_checks'}))
