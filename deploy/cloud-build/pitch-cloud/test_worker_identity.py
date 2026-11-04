import json,time,urllib.request,urllib.error
from pathlib import Path
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
root=Path(__file__).resolve().parent;base='http://127.0.0.1:8789'
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk['kid']='worker-fixture'
data=json.dumps({'keys':[jwk]}).encode()
req=urllib.request.Request(base+'/__local_auth_fixture',data=data,headers={'Content-Type':'application/json','X-Pitch-Migration-Key':(root/'.migration-key').read_text()})
with urllib.request.urlopen(req) as r:assert json.load(r)['fixture_ready']
claims={'iss':'https://astoryapp.cloudflareaccess.com','aud':['31a9f790dee8455b1ed8591943c3cd0ac020e55bcc7832c22afc0fa54be96aa9'],'sub':'fixture-owner','email':'gbao.n.vo@gmail.com','iat':int(time.time()),'exp':int(time.time())+120}
def check(changes=None,other_key=None):
    token=jwt.encode({**claims,**(changes or {})},other_key or key,algorithm='RS256',headers={'kid':'worker-fixture'})
    try:
        with urllib.request.urlopen(urllib.request.Request(base+'/api/cloud/status',headers={'Cf-Access-Jwt-Assertion':token})) as r:return r.status
    except urllib.error.HTTPError as e:return e.code
assert check()==200,'Correct signed identity rejected'
for changes in [{'email':'other@gmail.com'},{'aud':['wrong']},{'iss':'https://invalid.example'},{'exp':int(time.time())-30},{'iat':int(time.time())+300}]:assert check(changes)==403
assert check(other_key=rsa.generate_private_key(public_exponent=65537,key_size=2048))==403
print('Python Worker WebCrypto validates owner signature and denies wrong email, audience, issuer, time and signing key.')
