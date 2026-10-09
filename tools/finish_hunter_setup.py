"""Persist verified scheduler metadata, without touching company facts."""
import json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,js,now
from founder_os.funding_hunter import FundingHunter
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s)
receipt=json.loads((ROOT/'reports/scheduler.json').read_text(encoding='utf-8-sig'))
h.set_runner({'type':'windows_scheduled_task_codex_cli','status':'connected','task_name':receipt['TaskName'],'cli_executable':shutil.which('codex'),'description':'Uses your existing ChatGPT sign-in. This PC must be awake and your Windows user signed in; the Codex app can be closed.','connected_at':h.settings()['runner'].get('connected_at') or now(),'api_key_required':False})
# Historical unverified records join the next broad scan, avoiding an immediate
# duplicate scan on every scheduler installation.
s.db.execute("UPDATE funding_intelligence SET next_check=? WHERE last_verified IS NULL AND next_check<=?",('2026-10-05T12:00:00+00:00',now()))
s.log('funding.scheduler_connected','setup',receipt);s.close()
print(json.dumps({'runner':'connected','api_key_required':False,'schedule':receipt['ResearchSchedule']}))
