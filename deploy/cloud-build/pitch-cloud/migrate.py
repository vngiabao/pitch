"""Consistent private snapshot transfer; credential never appears in output.
Pass --replace <sha256 of the current cloud copy> to refresh a workspace that was already imported.
The cloud keeps the replaced copy under data/repair-backups/."""
import argparse,base64,gzip,hashlib,json,sqlite3,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('--replace');args=p.parse_args()
out=root/'migration';out.mkdir(exist_ok=True)
snapshot=out/('local-test.sqlite' if '127.0.0.1' in args.base else 'cloud-cutover.sqlite')
with sqlite3.connect(root.parent/'pitch/data/founder.sqlite') as src,sqlite3.connect(snapshot) as dst:src.backup(dst)
data=snapshot.read_bytes();sha=hashlib.sha256(data).hexdigest()
payload={'database_gzip':base64.b64encode(gzip.compress(data)).decode(),'sha256':sha}
if args.replace:payload['replace_sha256']=args.replace
body=json.dumps(payload).encode()
req=urllib.request.Request(args.base.rstrip('/')+'/api/cloud/import',data=body,headers={'User-Agent':'Pitch-Cloud-Migration/1.0','Content-Type':'application/json','X-Pitch-Migration-Key':(root/'.migration-key').read_text().strip()},method='POST')
try:
    with urllib.request.urlopen(req,timeout=180) as r:result=json.load(r)
except urllib.error.HTTPError as e:
    print(e.code,e.read().decode()[:2000]);raise SystemExit(1)
print(json.dumps(result))
(out/'last-transfer.json').write_text(json.dumps({'base':args.base,'sha256':sha,'database_bytes':len(data),'result':result},indent=2))
