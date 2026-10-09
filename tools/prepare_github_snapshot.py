"""Prepare an explicit source list and consistent private recovery snapshot.

Never sends data, reads credentials, deletes originals, or changes live database facts.
"""
import argparse,base64,gzip,hashlib,json,re,sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGING=ROOT/'.deploy-staging'
SENSITIVE=re.compile(r'(?<![\w-])(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{25,}\.eyJ[A-Za-z0-9_-]{25,}\.[A-Za-z0-9_-]{25,})')

def prepare():
    STAGING.mkdir(exist_ok=True)
    paths=[]
    for folder in ['founder_os','tests','tools','examples','deploy']:
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or 'private' in p.parts:continue
            if p.suffix.lower() in {'.py','.js','.cjs','.html','.css','.sql','.ps1','.json','.md','.txt'}:paths.append(p)
    paths += sorted(p for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.md','.ps1'} or p.name in {'.gitignore','requirements.txt','funding-search-families.json'}))
    paths += sorted(p for p in (ROOT/'.impeccable').glob('*.json') if 'local' not in p.name)
    paths += sorted((ROOT/'.impeccable/surfaces').glob('*.md'))
    # The pitch starter copy is part of the source package; live data stays ignored.
    paths.append(ROOT/'data/pitch-studio-starters.json')
    entries=[]
    for p in dict.fromkeys(paths):
        content=p.read_text(encoding='utf-8-sig')
        if SENSITIVE.search(content):raise ValueError('Potential credential in source file: '+str(p.relative_to(ROOT)))
        path=str(p.relative_to(ROOT)).replace('\\','/')
        if path=='data/pitch-studio-starters.json':path='seed-data/pitch-studio-starters.json'
        entries.append({'path':path,'mode':'100644','type':'blob','content':content})
    backup=STAGING/'founder.sqlite'
    if backup.exists():raise ValueError('Staging snapshot already exists; preserve it and use another staging directory for a later release')
    with sqlite3.connect((ROOT/'data/founder.sqlite').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:
        source.backup(target)
    with sqlite3.connect(backup) as check:
        if check.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Snapshot integrity check failed')
        for name, in check.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            quoted='"'+name.replace('"','""')+'"'
            for row in check.execute('SELECT * FROM '+quoted):
                if any(isinstance(v,str) and SENSITIVE.search(v) for v in row):
                    raise ValueError('Potential credential in database table '+name+'; snapshot upload must not proceed')
    compressed=gzip.compress(backup.read_bytes(),mtime=0)
    (STAGING/'founder-2026-10-08.sqlite.gz').write_bytes(compressed)
    (STAGING/'database.base64').write_text(base64.b64encode(compressed).decode('ascii'),encoding='ascii')
    metadata={'private_repository':'vngiabao/pitch','snapshot':'private-snapshots/founder-2026-10-08.sqlite.gz','sha256':hashlib.sha256(compressed).hexdigest(),'originals_modified':False,'source_files':len(entries),'compressed_database_bytes':len(compressed),'potential_credential_matches':0,'restored_automatically':False}
    entries.append({'path':'private-snapshots/manifest.json','mode':'100644','type':'blob','content':json.dumps(metadata,indent=2)})
    (STAGING/'tree-entries.json').write_text(json.dumps(entries),encoding='utf-8')
    (STAGING/'manifest.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata))

def chunk(kind,index,size):
    if kind=='source':
        entries=json.loads((STAGING/'tree-entries.json').read_text(encoding='utf-8'))
        # Chunk count bounded by total content characters, not number of files.
        groups=[];group=[];length=0
        for e in entries:
            n=len(json.dumps(e))
            if group and length+n>size:groups.append(group);group=[];length=0
            group.append(e);length+=n
        if group:groups.append(group)
        print(json.dumps({'total_chunks':len(groups),'entries':groups[index]}))
    else:
        content=(STAGING/'database.base64').read_text(encoding='ascii')
        print(json.dumps({'total_chunks':(len(content)+size-1)//size,'content':content[index*size:(index+1)*size]}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--chunk',choices=['source','database']);parser.add_argument('--index',type=int,default=0);parser.add_argument('--size',type=int,default=16000);args=parser.parse_args()
    if args.chunk:chunk(args.chunk,args.index,args.size)
    else:prepare()
