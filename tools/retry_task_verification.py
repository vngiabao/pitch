"""Retry the one task proof after allowing valid direct official-source checks."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
s=Store(ROOT/'data/founder.sqlite')
s.db.execute("UPDATE hunter_requests SET next_attempt=? WHERE request_key='windows-task-authenticated-research-proof-001' AND state='QUEUED'",(now(),))
s.close();print('Retained targeted verification queued for immediate corrected retry')
