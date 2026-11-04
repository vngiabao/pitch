"""Owner-only Cloudflare Worker; durable commits precede successful responses."""
import base64,gzip,hashlib,hmac,io,json,secrets,sqlite3,sys,time,zipfile,zlib
from pathlib import Path
from urllib.parse import urlsplit,quote
from workers import WorkerEntrypoint,Response,DurableObject,fetch
from pyodide.ffi import to_js as _to_js
from js import Object,Uint8Array,crypto
from app_bundle import ARCHIVE
ROOT=Path('/tmp/pitch-cloud');ROOT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE))) as archive:archive.extractall(ROOT)
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'timezones.zip'))
import zoneinfo
zoneinfo.reset_tzpath([])
from cloud_adapter import dispatch
ISSUER='https://astoryapp.cloudflareaccess.com'
AUDIENCE='31a9f790dee8455b1ed8591943c3cd0ac020e55bcc7832c22afc0fa54be96aa9'
OWNER='gbao.n.vo@gmail.com';CHUNK=65536;BACKUP_PREFIX='data/repair-backups/cloud-before-refresh-'
_keys={};_keys_until=0
def js(v):return _to_js(v,dict_converter=Object.fromEntries)
def raw(v):return bytes(Uint8Array.new(v).to_py())
def decode(v):return base64.urlsafe_b64decode(v+'='*(-len(v)%4))
def error(status,message):return Response.json({'error':message},status=status,headers={'Cache-Control':'no-store'})
def normalized_path(url):
    u=urlsplit(url);p=u.path
    if p.startswith('/__cloud/'):p=p[len('/__cloud'):]
    return p+('?'+u.query if u.query else '')
async def verified_owner(request,env):
    global _keys,_keys_until
    if getattr(env,'LOCAL_TEST','')=='1' and urlsplit(request.url).hostname in ('localhost','127.0.0.1') and request.headers.get('X-Pitch-Local-Test')=='1':return True
    token=request.headers.get('Cf-Access-Jwt-Assertion','')
    if not token or len(token)>16384:return False
    try:
        a,b,c=token.split('.');head=json.loads(decode(a));claims=json.loads(decode(b));now=time.time()
        if head.get('alg')!='RS256' or not head.get('kid'):return False
        if any(k not in claims for k in ('exp','iat','iss','aud','sub','email')):return False
        aud=claims['aud'] if isinstance(claims['aud'],list) else [claims['aud']]
        if claims['iss']!=ISSUER or AUDIENCE not in aud or claims['email'].lower()!=OWNER:return False
        if not claims['sub'] or not isinstance(claims['exp'],(int,float)) or claims['exp']<=now:return False
        if not isinstance(claims['iat'],(int,float)) or claims['iat']>now or claims.get('nbf',0)>now:return False
        if now>=_keys_until or head['kid'] not in _keys:
            r=await fetch(ISSUER+'/cdn-cgi/access/certs')
            if r.status!=200:return False
            data=await r.json();_keys={k['kid']:k for k in data['keys'] if k.get('kty')=='RSA'};_keys_until=now+300
        kd=_keys.get(head['kid'])
        if not kd:return False
        key=await crypto.subtle.importKey('jwk',js(kd),js({'name':'RSASSA-PKCS1-v1_5','hash':'SHA-256'}),False,js(['verify']))
        valid=bool(await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,js(decode(c)),js((a+'.'+b).encode())))
        return valid
    except Exception:
        return False
def migration_allowed(request,env):
    secret=getattr(env,'MIGRATION_KEY','');supplied=request.headers.get('X-Pitch-Migration-Key','')
    return bool(secret and supplied and hmac.compare_digest(secret,supplied))
class PitchWorkspace(DurableObject):
    def __init__(self,ctx,env):
        super().__init__(ctx,env);self.sql=self.ctx.storage.sql
        ROOT.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE))) as archive:archive.extractall(ROOT)
        self.sql.exec('CREATE TABLE IF NOT EXISTS pitch_files(name TEXT NOT NULL,part INTEGER NOT NULL,data BLOB NOT NULL,PRIMARY KEY(name,part))')
        self.sql.exec('CREATE TABLE IF NOT EXISTS pitch_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        rows=self.sql.exec("SELECT value FROM pitch_meta WHERE key='csrf'").toArray()
        self.token=rows[0].value if len(rows) else secrets.token_urlsafe(32)
        if not len(rows):self.sql.exec("INSERT INTO pitch_meta VALUES('csrf',?)",self.token)
        self.loaded=False;self.digests={};self.dbpath=ROOT/'data/founder.sqlite'
    def load(self):
        if self.loaded:return
        # Refresh backups stay in storage only; loading them would double the isolate's memory.
        rows=self.sql.exec('SELECT name,part,data FROM pitch_files WHERE substr(name,1,?)!=? ORDER BY name,part',len(BACKUP_PREFIX),BACKUP_PREFIX).toArray();handles={}
        try:
            for row in rows:
                name=row.name
                if name not in handles:
                    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);handles[name]=p.open('wb')
                data=raw(row.data);handles[name].write(data);self.digests[(name,row.part)]=hashlib.sha256(data).digest()
        finally:
            for f in handles.values():f.close()
        self.loaded=True
    def persist(self):
        changes=[];present=set()
        for folder in ('data','reports','outputs'):
            parent=ROOT/folder
            if not parent.exists():continue
            for p in parent.rglob('*'):
                if not p.is_file() or p.name.endswith(('-journal','-wal','-shm','.pyc')) or '__pycache__' in p.parts:continue
                name=p.relative_to(ROOT).as_posix()
                with p.open('rb') as f:
                    part=0
                    while True:
                        data=f.read(CHUNK)
                        if not data:break
                        key=(name,part);present.add(key);digest=hashlib.sha256(data).digest()
                        if self.digests.get(key)!=digest:changes.append((name,part,data,digest))
                        part+=1
        removed=set(self.digests)-present
        def commit():
            for name,part,data,digest in changes:self.sql.exec('INSERT INTO pitch_files(name,part,data) VALUES(?,?,?) ON CONFLICT(name,part) DO UPDATE SET data=excluded.data',name,part,js(data))
            for name,part in removed:self.sql.exec('DELETE FROM pitch_files WHERE name=? AND part=?',name,part)
        if changes or removed:self.ctx.storage.transactionSync(commit)
        for name,part,data,digest in changes:self.digests[(name,part)]=digest
        for key in removed:self.digests.pop(key,None)
    async def fetch(self,request):
        path=normalized_path(request.url).split('?')[0]
        if path=='/api/cloud/import' and request.method=='POST' and migration_allowed(request,self.env):
            payload=await request.json()
            seeded=self.sql.exec("SELECT value FROM pitch_meta WHERE key='seeded'").toArray()
            # A refresh must name the copy it replaces, so a stale or repeated transfer can't overwrite newer work.
            if len(seeded) and payload.get('replace_sha256')!=seeded[0].value:return error(409,'Workspace already imported; a refresh must name the current copy in replace_sha256: '+seeded[0].value)
            # Memory stays near one database copy (isolates have 128 MB): drop the request text early, never hold
            # the old copy in /tmp, and make the backup inside Durable Object storage with SQL.
            expected=payload['sha256'];gz=base64.b64decode(payload.pop('database_gzip'));del payload
            self.loaded=False;self.digests={}
            self.dbpath.parent.mkdir(parents=True,exist_ok=True)
            if self.dbpath.exists():self.dbpath.write_bytes(b'')  # free the old copy first (truncate works even while open)
            unpack=zlib.decompressobj(16+zlib.MAX_WBITS);digest=hashlib.sha256();size=0
            with self.dbpath.open('wb') as f:  # unpack in 1 MB steps so the whole database is never in memory twice
                for i in range(0,len(gz)+1,1<<20):
                    out=unpack.decompress(gz[i:i+(1<<20)]) if i<len(gz) else unpack.flush()
                    size+=len(out);digest.update(out);f.write(out)
                    if size>64*1024*1024:break
            del gz
            ok=size<=64*1024*1024 and digest.hexdigest()==expected
            if ok:
                with sqlite3.connect(self.dbpath) as check:ok=check.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            if not ok:
                self.dbpath.write_bytes(b'');return error(400,'Database checksum or integrity check failed; the previous copy was kept')
            name=self.dbpath.relative_to(ROOT).as_posix();backup=BACKUP_PREFIX+(seeded[0].value[:12] if len(seeded) else '')+'.sqlite'
            def commit():
                if len(seeded):
                    self.sql.exec('DELETE FROM pitch_files WHERE name=?',backup)
                    self.sql.exec('INSERT INTO pitch_files(name,part,data) SELECT ?,part,data FROM pitch_files WHERE name=?',backup,name)
                self.sql.exec('DELETE FROM pitch_files WHERE name=?',name)
                with self.dbpath.open('rb') as f:
                    part=0
                    while chunk:=f.read(CHUNK):
                        self.sql.exec('INSERT INTO pitch_files(name,part,data) VALUES(?,?,?)',name,part,js(chunk));part+=1
                self.sql.exec("INSERT INTO pitch_meta VALUES('seeded',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",expected)
            self.ctx.storage.transactionSync(commit)
            return Response.json({'imported':True,'sha256':expected,'replaced':seeded[0].value if len(seeded) else None,'backup':backup if len(seeded) else None})
        if not await verified_owner(request,self.env):return error(403,'Verified owner sign-in required')
        self.load()
        if not self.dbpath.exists():return error(503,'Cloud workspace is being migrated')
        fullpath=normalized_path(request.url)
        if path=='/api/cloud/status':
            with sqlite3.connect(self.dbpath) as db:
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('pitch_documents','material_library','opportunities','applications') if t in tables}
            seeded=self.sql.exec("SELECT value FROM pitch_meta WHERE key='seeded'").toArray()
            return Response.json({'hosting':'cloudflare','durable':True,'counts':counts,'seeded_sha256':seeded[0].value if len(seeded) else None,'desktop_required_for_workspace':False,'research_automation_connected':False})
        if path.startswith('/api/cloud/material-meta/'):
            key=path.rsplit('/',1)[1]
            with sqlite3.connect(self.dbpath) as db:row=db.execute('SELECT sha256,relative_path,size_bytes FROM material_library WHERE id=?',(key,)).fetchone()
            if not row or not row[0]:return error(404,'Material not found')
            return Response.json({'sha256':row[0],'name':row[1].replace(chr(92),'/').split('/')[-1],'size':row[2]},headers={'Cache-Control':'no-store'})
        if path.startswith('/api/material/') and path.endswith('/file'):
            with sqlite3.connect(self.dbpath) as db:row=db.execute('SELECT sha256,relative_path FROM material_library WHERE id=?',(path.split('/')[3],)).fetchone()
            if not row or not row[0]:return error(404,'Material not found')
            return error(404,'Open original files through the protected website.')
        if request.method=='POST' and int(request.headers.get('Content-Length','0') or '0')>65536:return error(413,'Request too large')
        body=(await request.text()).encode() if request.method=='POST' else b''
        if len(body)>65536:return error(413,'Request too large')
        headers={k:request.headers.get(k,'') for k in ('Cookie','Content-Type','X-Founder-CSRF','Origin')}
        try:
            status,headers,response=dispatch(self.dbpath,self.token,request.method,fullpath,headers,body);self.persist()
            return Response(response,status=status,headers=headers)
        except Exception as exc:
            print('Cloud dispatch error:',type(exc).__name__,str(exc))
            self.loaded=False
            return error(500,'The cloud request failed. Previously saved state is retained.')
class Default(WorkerEntrypoint):
    async def fetch(self,request):
        return await self.env.PITCH.get(self.env.PITCH.idFromName('owner')).fetch(request)
