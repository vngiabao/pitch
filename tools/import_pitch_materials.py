"""Non-destructive, repeatable folder ingestion; copy text, reference large assets.

No cloud uploads, no cleanup, no canonical company promotions. Every candidate
is checked against the specified root. Cached inventory hashes are used only
when size and modification time match; extracted documents are freshly hashed.
"""
import argparse,hashlib,json,os,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,digest,now
from founder_os.funding_hunter import FundingHunter
from founder_os.materials_library import MaterialsLibrary

EXT={'.pptx':'deck','.ppt':'deck','.pdf':'pdf','.docx':'document','.doc':'document','.md':'document','.txt':'document','.xlsx':'financials','.xls':'financials','.csv':'financials','.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.svg':'image','.mp4':'video','.mov':'video','.mp3':'audio','.wav':'audio','.m4a':'audio','.fig':'design'}
SKIP={'node_modules','.git','.next','.venv','site-packages','vendor','venv','__pycache__'}

def extract(p):
    ext=p.suffix.lower()
    if ext in ('.md','.txt','.csv'):return p.read_text(encoding='utf-8-sig',errors='replace'),'text'
    if ext=='.pdf':
        from pypdf import PdfReader
        pages=PdfReader(p).pages
        return '\n\n'.join('[PAGE '+str(i+1)+']\n'+(page.extract_text() or '') for i,page in enumerate(pages)),'pdf_pages'
    if ext in ('.pptx','.docx','.xlsx'):
        with zipfile.ZipFile(p) as z:
            if ext=='.pptx':names=[n for n in z.namelist() if n.startswith(('ppt/slides/slide','ppt/notesSlides/notesSlide')) and n.endswith('.xml')]
            elif ext=='.docx':names=[n for n in z.namelist() if n in ('word/document.xml','word/footnotes.xml','word/endnotes.xml')]
            else:names=[n for n in z.namelist() if n=='xl/sharedStrings.xml' or n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
            out=[]
            for name in sorted(names):
                if z.getinfo(name).file_size>8_000_000:raise ValueError('Oversized embedded XML; reference retained')
                tree=ET.fromstring(z.read(name));texts=[el.text for el in tree.iter() if el.tag.rsplit('}',1)[-1] in ('t','v') and el.text]
                out.append('['+name+']\n'+'\n'.join(texts))
            return '\n\n'.join(out), 'office_xml_text_and_notes'
    return None,'reference_only'

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--inventory');args=a.parse_args();root=Path(args.root).resolve()
    if not root.is_dir():raise ValueError('Source folder unavailable')
    cached={}
    if args.inventory:
        for r in json.loads(Path(args.inventory).read_text(encoding='utf-8-sig')):
            cached[str(Path(r['source_path']).resolve()).lower()]=r
    s=Store(ROOT/'data/founder.sqlite');FundingHunter(s);library=MaterialsLibrary(s);errors=[];seen=[];texts={};processed=0
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d.lower() not in SKIP]
        for name in sorted(files):
            p=(Path(folder)/name).resolve();ext=p.suffix.lower();rel=p.relative_to(root);parts={x.lower() for x in rel.parts}
            if ext not in EXT or not p.is_relative_to(root):continue
            if 'pitch-os' in parts:continue # Legacy application database is migrated separately; these are source-code assets.
            if any(t in name.lower() for t in ('license','token','credential','secret','package-lock')):continue
            if name.lower() in ('readme.md','build.md','agents.md'):continue
            stat=p.stat();old=cached.get(str(p).lower());cat=old['category'] if old else 'KEEP'
            if cat=='IGNORE':continue
            if parts.intersection({'qa','previews','renders','rendered','screenshots','.codex-build'}) or any(t in name.lower() for t in ('contact-sheet','contact_sheet','qa-report','pass-report')):cat='ARCHIVE'
            key='material-'+digest(str(p))[:24];existing=s.db.execute('SELECT * FROM material_library WHERE id=?',(key,)).fetchone()
            if existing and existing['size_bytes']==stat.st_size and existing['modified_ns']==stat.st_mtime_ns:
                seen.append(key);continue
            sha=None;body=None;version=None;extraction='reference_only'
            if old and old['size_bytes']==stat.st_size:
                modified=datetime.fromtimestamp(stat.st_mtime,timezone.utc)
                recorded=datetime.fromisoformat(old['modified_utc'].replace('Z','+00:00'))
                if abs((modified-recorded).total_seconds())<0.002:sha=old.get('sha256')
            if ext in ('.md','.txt','.pdf','.pptx','.docx','.xlsx','.csv') and stat.st_size<=70_000_000:
                try:
                    actual=hashlib.sha256(p.read_bytes()).hexdigest();sha=actual
                    if sha in texts:body,extraction=texts[sha]
                    else:
                        body,extraction=extract(p)
                        if body is not None:body=body[:1_000_000] # Explicit bounded indexed excerpt for large documents.
                        texts[sha]=(body,extraction)
                    if body:
                        version=s.import_source(p,EXT[ext],cat,expected_sha256=sha,text=body,extraction=extraction,document_date=datetime.fromtimestamp(stat.st_mtime,timezone.utc).date().isoformat())
                        mid='registered-material-'+digest([version,EXT[ext]])[:24]
                        s.db.execute("INSERT OR IGNORE INTO material_registry VALUES(?,?,?,?,'reference','{}',?)",(mid,version,EXT[ext],name,now()))
                except Exception as e:extraction='EXTRACTION_FAILED';errors.append({'path':str(p),'error':str(e)[:250]})
            s.db.execute('''INSERT INTO material_library VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,category=excluded.category,size_bytes=excluded.size_bytes,sha256=excluded.sha256,modified_ns=excluded.modified_ns,source_version_id=excluded.source_version_id,body=excluded.body,extraction=excluded.extraction,duplicate_of=NULL,registered_at=excluded.registered_at''',(key,str(p),str(rel),str(root),EXT[ext],cat,stat.st_size,sha,stat.st_mtime_ns,version,body,extraction,None,now()))
            seen.append(key);processed+=1
    # Stable representative selection: keep core user files ahead of generated/archived copies.
    canonical={}
    for r in s.rows("SELECT id,sha256 FROM material_library ORDER BY category='ARCHIVE',length(relative_path),relative_path"):
        if r['sha256']:
            first=canonical.setdefault(r['sha256'],r['id']);s.db.execute('UPDATE material_library SET duplicate_of=? WHERE id=?',(None if first==r['id'] else first,r['id']))
    manifest=library.manifest();(ROOT/'reports'/'pitch-materials-manifest.json').write_text(manifest,encoding='utf-8')
    receipt={'source_root':str(root),'completed_at':now(),'stats':library.stats(),'current_files_seen':len(seen),'registered_or_refreshed':processed,'extraction_errors':errors,'originals_modified':0,'mode':'Searchable extracted text and local original references; no bulk binary cloud copy','history_policy':'Reference only; not canonical or approved answers'}
    (ROOT/'reports'/'pitch-materials-import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');s.log('materials.folder_catalogued','ingestion',receipt);s.close();print(json.dumps(receipt,ensure_ascii=True))
if __name__=='__main__':main()
