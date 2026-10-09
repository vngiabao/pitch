"""Package the closed local foundation; exclude caches and transient journals."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
target = root.parent / 'a-story-founder-os-foundation.zip'
paths = [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and not p.name.endswith(('-journal','-wal','-shm'))]
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(paths):
        z.write(p,Path(root.name) / p.relative_to(root))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    count = len(z.infolist())
receipt = {'path':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'members':count,'archive_integrity':'ok'}
(root.parent / 'founder-os-package-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
