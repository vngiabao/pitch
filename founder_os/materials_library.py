"""Private, searchable source library. Originals stay in the owner's folder."""
import json
from pathlib import Path
from .store import digest,now,PolicyError

SCHEMA='''
CREATE TABLE IF NOT EXISTS material_library(
 id TEXT PRIMARY KEY, source_path TEXT NOT NULL UNIQUE, relative_path TEXT NOT NULL,
 source_root TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL,
 size_bytes INTEGER NOT NULL, sha256 TEXT, modified_ns INTEGER NOT NULL,
 source_version_id TEXT REFERENCES source_versions(id), body TEXT,
 extraction TEXT NOT NULL, duplicate_of TEXT, registered_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS material_library_kind ON material_library(kind,category);
'''

class MaterialsLibrary:
    def __init__(self,store):
        self.s=store;self.db=store.db;self.db.executescript(SCHEMA)

    def stats(self):
        r=self.s.one('SELECT count(*) total,count(DISTINCT coalesce(sha256,id)) unique_files,sum(body IS NOT NULL) searchable_text,sum(size_bytes) referenced_bytes FROM material_library')
        r['kinds']=self.s.rows('SELECT kind,count(*) count FROM material_library GROUP BY kind ORDER BY kind')
        return r

    def search(self,q='',kind='',category='',offset=0,limit=40,duplicates=False):
        offset=max(0,int(offset));limit=min(100,max(1,int(limit)));where=[];values=[]
        if q:
            escaped=q[:300].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            where.append("(relative_path LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')");values+=['%'+escaped+'%']*2
        if kind:where.append('kind=?');values.append(kind)
        if category=='all':pass
        elif category:where.append('category=?');values.append(category)
        else:where.append("category!='ARCHIVE'")
        if not duplicates:where.append('duplicate_of IS NULL')
        clause=' WHERE '+' AND '.join(where) if where else ''
        count=self.s.one('SELECT count(*) total FROM material_library'+clause,values)['total']
        rows=self.s.rows('SELECT id,source_path,relative_path,kind,category,size_bytes,sha256,source_version_id,extraction,duplicate_of,(SELECT count(*) FROM material_library b WHERE b.duplicate_of=material_library.id) duplicates FROM material_library'+clause+' ORDER BY CASE kind WHEN \'deck\' THEN 0 WHEN \'document\' THEN 1 WHEN \'pdf\' THEN 2 ELSE 3 END,relative_path LIMIT ? OFFSET ?',values+[limit,offset])
        return {'items':rows,'total':count,'offset':offset,'limit':limit,'stats':self.stats()}

    def detail(self,key):
        r=self.s.one('SELECT * FROM material_library WHERE id=?',(key,))
        r['aliases']=self.s.rows('SELECT id,source_path,relative_path FROM material_library WHERE duplicate_of=?',(key,))
        return r

    def original(self,key):
        r=self.detail(key);p=Path(r['source_path']).resolve();root=Path(r['source_root']).resolve()
        if not p.is_relative_to(root) or not p.is_file():raise PolicyError('Original is unavailable on this PC; its source reference is retained')
        stat=p.stat()
        if stat.st_size!=r['size_bytes'] or stat.st_mtime_ns!=r['modified_ns']:raise PolicyError('Original changed since registration; refresh the library before opening this version')
        return p

    def manifest(self):
        rows=self.s.rows('SELECT id,source_path,relative_path,kind,category,sha256,size_bytes,source_version_id,extraction,duplicate_of FROM material_library ORDER BY relative_path')
        return json.dumps({'generated_at':now(),'mode':'Original files referenced; extracted text stored privately. Historical content is not canonical truth.','items':rows},ensure_ascii=False,indent=2)
