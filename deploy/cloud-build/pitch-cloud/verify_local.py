import http.cookiejar,json,re,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8789'
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
session_cookie=''
def request(path,payload=None,authorized=True,csrf=''):
    headers={'X-Pitch-Local-Test':'1'} if authorized else {}
    if session_cookie:headers['Cookie']=session_cookie
    data=None
    if payload is not None:
        data=json.dumps(payload).encode();headers.update({'Content-Type':'application/json','Origin':'https://pitch.gbaonvo.com','X-Founder-CSRF':csrf})
    try:
        with client.open(urllib.request.Request(BASE+path,data=data,headers=headers),timeout=30) as r:return r.status,r.read(),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
status,html,headers=request('/')
assert status==200,(status,html[:300])
session_cookie=headers['Set-Cookie'].split(';')[0]
csrf=re.search(rb'name="founder-csrf" content="([^"]+)"',html)
if not csrf:csrf=re.search(rb'__CSRF__',html)
print('home',status,'bytes',len(html))
for path in ['/api/dashboard','/api/pitches','/api/materials','/api/answers','/api/opportunities','/api/application-list','/api/autonomy','/api/product','/api/founder-profile','/api/growth','/api/drive','/api/money','/api/lab','/api/assumptions','/api/stack','/api/scouts','/api/plans']:
    status,data,_=request(path)
    print(path,status,len(data))
    if status!=200:print(data[:400].decode(errors='replace'))
    assert status==200,path
assert request('/api/cloud/status',authorized=False)[0]==403
print('unauthenticated access denied')
assert csrf and csrf.group(1)
payload={'title':'Cloud migration local QA','body':'Disposable local persistence check.','duration_seconds':60,'status':'archived'}
assert request('/api/pitches',payload=payload,csrf='incorrect')[0]==403
status,data,_=request('/api/pitches',payload=payload,csrf=csrf.group(1).decode())
assert status==200,(status,data[:300])
pitch=json.loads(data);pid=pitch['pitch_id']
payload.update(expected_version_id=pitch['id'],body='Saved cloud persistence check.')
status,data,_=request('/api/pitch/'+pid,payload=payload,csrf=csrf.group(1).decode())
assert status==200,(status,data[:300])
assert request('/api/pitch/'+pid,payload=payload,csrf=csrf.group(1).decode())[0]==409
Path('migration/persistence-test.json').write_text(json.dumps({'pitch_id':pid,'body':'Saved cloud persistence check.'}))
print('create/save, CSRF denial and stale-version protection passed; restart check prepared')
