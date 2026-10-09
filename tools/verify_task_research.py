"""Queue one bounded known-program check to exercise Windows task authentication."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.funding_hunter import FundingHunter
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s)
r=s.one("SELECT i.opportunity_id FROM funding_intelligence i JOIN funding_programs p ON p.id=i.program_id WHERE p.canonical_name='NVIDIA Inception'")
request=h.request_run('Research opportunity '+r['opportunity_id'],'windows-task-authenticated-research-proof-001')
print(json.dumps(request));s.close()
