"""CPython harness for entry.py's import/refresh route (Wrangler's local Python runtime fails on Windows).
Stubs the Workers runtime, keeps Durable Object storage in a real SQLite file, and checks:
first import, refusal without the current copy's hash, refusal with a wrong hash, refresh with a backup,
state surviving a fresh Durable Object instance, and the owner's Skip decisions hiding programs.
Usage: py -X utf8 test_entry_refresh.py <old.sqlite> <new.sqlite>"""
import asyncio,base64,gzip,hashlib,json,shutil,sqlite3,sys,types
from pathlib import Path
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here))

class Row:
    def __init__(self,d):self.__dict__.update(d)
class Cursor:
    def __init__(self,rows):self.rows=rows
    def toArray(self):return self.rows
class Sql:
    def __init__(self,path):self.db=sqlite3.connect(path,isolation_level=None)
    def exec(self,q,*args):
        cur=self.db.execute(q,args);names=[c[0] for c in cur.description or []]
        return Cursor([Row(dict(zip(names,r))) for r in cur.fetchall()])
class Storage:
    def __init__(self,path):self.sql=Sql(path)
    def transactionSync(self,fn):fn()
class Ctx:
    def __init__(self,path):self.storage=Storage(path)
class Response:
    def __init__(self,body,status=200,headers=None):self.body=body;self.status=status;self.headers=headers or {}
    @classmethod
    def json(cls,data,status=200,headers=None):return cls(json.dumps(data),status,headers)
class DurableObject:
    def __init__(self,ctx,env):self.ctx=ctx;self.env=env
class Uint8:
    def __init__(self,v):self.v=v
    def to_py(self):return bytes(self.v)
workers=types.ModuleType('workers');workers.WorkerEntrypoint=object;workers.Response=Response;workers.DurableObject=DurableObject;workers.fetch=None
pyodide=types.ModuleType('pyodide');ffi=types.ModuleType('pyodide.ffi');ffi.to_js=lambda v,**k:v;pyodide.ffi=ffi
jsmod=types.ModuleType('js');jsmod.Object=types.SimpleNamespace(fromEntries=dict);jsmod.Uint8Array=types.SimpleNamespace(new=Uint8);jsmod.crypto=None
sys.modules.update({'workers':workers,'pyodide':pyodide,'pyodide.ffi':ffi,'js':jsmod})
import entry
shutil.rmtree(entry.ROOT/'data',ignore_errors=True)

class Headers(dict):
    def get(self,k,d=None):return next((v for kk,v in self.items() if kk.lower()==k.lower()),d)
class Request:
    def __init__(self,url,method='GET',headers=None,body=None):self.url=url;self.method=method;self.headers=Headers(headers or {});self._body=body
    async def json(self):return json.loads(self._body)
    async def text(self):return self._body or ''
    async def bytes(self):return (self._body or '').encode()

env=types.SimpleNamespace(MIGRATION_KEY='test-key',LOCAL_TEST='1')
store=here/'migration'/'harness-do.sqlite';store.parent.mkdir(exist_ok=True);store.unlink(missing_ok=True)
def workspace():
    shutil.rmtree(entry.ROOT/'data',ignore_errors=True)  # a fresh isolate starts with an empty /tmp
    return entry.PitchWorkspace(Ctx(str(store)),env)
async def send(ws,path,replace=None):
    data=Path(path).read_bytes();sha=hashlib.sha256(data).hexdigest()
    p={'database_gzip':base64.b64encode(gzip.compress(data)).decode(),'sha256':sha}
    if replace:p['replace_sha256']=replace
    req=Request('http://127.0.0.1/api/cloud/import','POST',{'X-Pitch-Migration-Key':'test-key'},json.dumps(p));del p,data
    import tracemalloc;tracemalloc.start()  # server side only: the upload text already exists, as it would in the isolate
    r=await ws.fetch(req);send.peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    return r.status,json.loads(r.body),sha
cookie={}
async def get(ws,path):
    h={'X-Pitch-Local-Test':'1'}
    if cookie:h['Cookie']=cookie['v']
    r=await ws.fetch(Request('http://127.0.0.1'+path,headers=h))
    sc=next((v for k,v in r.headers.items() if k.lower()=='set-cookie'),None)
    if sc:cookie['v']=sc.split(';')[0]
    return r.status,r.body
async def main(old,new):
    ws=workspace()
    s1=await send(ws,old);assert s1[0]==200,s1;print('first import ok')
    s2=await send(ws,new);assert s2[0]==409 and s1[2] in s2[1]['error'],s2;print('refused without current hash')
    s3=await send(ws,new,'wrong');assert s3[0]==409,s3;print('refused with wrong hash')
    st,_=await get(ws,'/');assert st==200  # warm isolate: the old copy is loaded in /tmp, as on the live site
    s4=await send(ws,new,s1[2])
    assert s4[0]==200 and s4[1]['replaced']==s1[2],s4;print('refresh ok, new Python memory used while refreshing %.0f MB'%(send.peak/2**20))
    rows=ws.ctx.storage.sql.db.execute('SELECT data FROM pitch_files WHERE name=? ORDER BY part',(s4[1]['backup'],)).fetchall()
    assert hashlib.sha256(b''.join(r[0] for r in rows)).hexdigest()==s1[2];print('old copy kept in storage as',s4[1]['backup'])
    ws2=workspace()  # new isolate: state must come back from Durable Object storage
    st,body=await get(ws2,'/api/cloud/status');assert st==200,(st,body[:300]);b=json.loads(body)
    assert b['seeded_sha256']==s4[2],b;print('after restart, cloud holds the new copy:',b['counts'])
    assert not (entry.ROOT/s4[1]['backup']).exists();print('backup stays in storage, not loaded into memory')
    assert hashlib.sha256(entry.ROOT.joinpath('data/founder.sqlite').read_bytes()).hexdigest()==s4[2];print('restored database matches the new copy byte for byte')
    st,_=await get(ws2,'/');assert st==200 and cookie,st
    st,body=await get(ws2,'/api/opportunities?view=Recommended');assert st==200,(st,body[:300])
    names=[x['data']['canonical_name'] for x in json.loads(body)];print('recommended now:',len(names),names)
    for gone in ('Michigan Business Challenge','Next Era Founders Fellowship','TechRise Pitch Competitions','MTank','Fuel'):assert gone not in names,gone
    print('ALL CHECKS PASSED')
if __name__=='__main__':asyncio.run(main(sys.argv[1],sys.argv[2]))
