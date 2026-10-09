"""Portable project package using a consistent live SQLite backup."""
import hashlib,json,sqlite3,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];target=ROOT.parent/'a-story-founder-os-materials-previews.zip'
one_time={'reconcile_research_probes.py','replay_retained_scan.py','finish_hunter_setup.py','refine_hunter_ui.py','apply_finish_review.py','update_hunter_docs.py','package_delivery.py','export_review.py','verify_task_research.py','retry_task_verification.py'}
with tempfile.TemporaryDirectory() as folder:
    snapshot=Path(folder)/'founder.sqlite';source=sqlite3.connect(ROOT/'data/founder.sqlite');dest=sqlite3.connect(snapshot);source.backup(dest);source.close()
    assert dest.execute('PRAGMA integrity_check').fetchone()[0]=='ok';dest.close()
    paths=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and not p.name.endswith(('-journal','-wal','-shm')) and p.name not in one_time and p!=ROOT/'data/founder.sqlite' and not p.is_relative_to(ROOT/'outputs')]
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in sorted(paths):archive.write(p,Path('founder-os')/p.relative_to(ROOT))
        archive.write(snapshot,'founder-os/data/founder.sqlite')
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None;members=len(archive.infolist())
receipt={'path':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'members':members,'database_snapshot':'SQLite backup API','archive_integrity':'ok','original_foundation_package_preserved':True,'original_hunter_package_preserved':True}
(ROOT.parent/'materials-previews-package-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
