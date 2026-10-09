"""Recover an observation batch already researched; never repeat model work."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,js,now
from founder_os.funding_hunter import FundingHunter
from tools.research_worker import normalize_observations
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s)
files=sorted((ROOT/'reports/runs').glob('*-observations.json'),key=lambda p:p.stat().st_mtime)
path=files[-1];batch=normalize_observations(json.loads(path.read_text(encoding='utf-8')));schema=path.with_name(path.name.replace('-observations.json','-schema.json'))
batch['research_started_at']=datetime.fromtimestamp(schema.stat().st_mtime,timezone.utc).isoformat()
key='retained-broad-scan-'+path.stem+'-v2'
report=h.runFundingHunter(batch,key)
if report['records_created'] or report['records_updated']:
    s.db.execute("UPDATE hunter_requests SET state='COMPLETE',run_id=?,last_error=NULL WHERE id=?",(report['run_id'],batch['request_id']))
for r in s.rows("SELECT id FROM funding_runs WHERE state='RUNNING' AND request_key!=?",(key,)):
    failure={'run_id':r['id'],'errors':[{'state':'RESEARCH_INCOMPLETE','message':'Interrupted during validator repair; retained observations replayed in '+report['run_id']}],'records_created':0,'records_updated':0}
    s.db.execute("UPDATE funding_runs SET state='FAILED',completed_at=?,lease_until=NULL,report_json=? WHERE id=?",(now(),js(failure),r['id']))
(ROOT/'reports/first-broad-run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('run_id','candidates_discovered','new_programs','verified','records_created','records_updated','errors')}));s.close()
