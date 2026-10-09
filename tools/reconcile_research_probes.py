"""Replay retained live observations after validator repairs; no repeated searches."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.funding_hunter import FundingHunter
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s)
for stem in ('research-d6a356d724df6fc0','research-f52c6e18fd5da198'):
    path=ROOT/'reports/runs'/f'{stem}-observations.json'
    batch=json.loads(path.read_text(encoding='utf-8'))
    result=h.runFundingHunter(batch,'validated-replay-'+stem+'-v4')
    print(json.dumps({'run_id':result['run_id'],'created':result['records_created'],'updated':result['records_updated'],'errors':result['errors']}))
    if result['records_created'] or result['records_updated']:
        if batch.get('request_id'):s.db.execute("UPDATE hunter_requests SET state='COMPLETE',run_id=?,last_error=NULL WHERE id=?",(result['run_id'],batch['request_id']))
s.close()
