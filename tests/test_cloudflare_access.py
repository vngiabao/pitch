import http.client,json,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from founder_os.cloudflare_access import AccessIdentity
from founder_os.server import FounderServer


class AccessValidationTests(unittest.TestCase):
    def setUp(self):
        self.access=AccessIdentity('pitch.gbaonvo.com','fixture.cloudflareaccess.com','a'*64,'gbao.n.vo@gmail.com')
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.access.keys=SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=self.key.public_key()))
        self.claims={'iss':self.access.issuer,'aud':['a'*64],'email':'gbao.n.vo@gmail.com','sub':'owner','iat':int(time.time()),'exp':int(time.time())+300}
    def sign(self,changes=None,key=None):
        return jwt.encode({**self.claims,**(changes or {})},key or self.key,algorithm='RS256',headers={'kid':'fixture'})
    def test_exact_owner_valid_signature_required(self):
        self.assertTrue(self.access.authorized(self.sign()))
        for changes in [{'email':'other@gmail.com'},{'aud':['b'*64]},{'iss':'https://evil.example'},{'exp':int(time.time())-1},{'nbf':int(time.time())+300}]:
            self.assertFalse(self.access.authorized(self.sign(changes)))
        other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.assertFalse(self.access.authorized(self.sign(key=other)))
    def test_missing_claim_unsigned_wrong_algorithm_and_key_outage_deny(self):
        for field in ['exp','iat','iss','aud','sub','email']:
            claims={k:v for k,v in self.claims.items() if k!=field}
            self.assertFalse(self.access.authorized(jwt.encode(claims,self.key,algorithm='RS256',headers={'kid':'fixture'})))
        for token in [None,'','bad',jwt.encode(self.claims,'not-a-secret-but-long-enough-for-a-test',algorithm='HS256',headers={'kid':'fixture'}),jwt.encode(self.claims,key=None,algorithm='none')]:
            self.assertFalse(self.access.authorized(token))
        self.access.keys=Mock();self.access.keys.get_signing_key_from_jwt.side_effect=OSError('offline')
        self.assertFalse(self.access.authorized(self.sign()))
    def test_configuration_rejects_untrusted_key_url_or_missing_audience(self):
        for domain in ['evil.example','fixture.cloudflareaccess.com/evil','https://fixture.cloudflareaccess.com','fixture.cloudflareaccess.com@evil.example']:
            with self.assertRaises(ValueError):AccessIdentity('pitch.gbaonvo.com',domain,'a'*64,'gbao.n.vo@gmail.com')
        with self.assertRaises(ValueError):AccessIdentity('pitch.gbaonvo.com','fixture.cloudflareaccess.com','','gbao.n.vo@gmail.com')


class RemoteOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        # HTTP wiring fixture; the real cryptographic validator is tested separately above.
        self.access=SimpleNamespace(hostname='pitch.gbaonvo.com',authorized=lambda token:token=='fixture-valid-owner')
        self.server=FounderServer(str(Path(self.tmp.name)/'test.sqlite'),0,self.access)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.thread.join();self.server.server_close();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        c.request(method,path,body,headers or {});r=c.getresponse();result=(r.status,r.read(),dict(r.getheaders()));c.close();return result
    def headers(self):return {'Host':self.access.hostname,'Cf-Access-Jwt-Assertion':'fixture-valid-owner'}
    def test_every_route_denies_missing_identity_and_local_host(self):
        for route in ['/','/pitches','/app.js','/api/dashboard','/api/materials-manifest']:
            self.assertEqual(self.request('GET',route,headers={'Host':self.access.hostname})[0],403)
        self.assertEqual(self.request('GET','/',headers={'Host':self.access.hostname,'Cf-Access-Jwt-Assertion':'spoofed','Cf-Access-Authenticated-User-Email':'gbao.n.vo@gmail.com'})[0],403)
        self.assertEqual(self.request('GET','/',headers={'Cf-Access-Jwt-Assertion':'fixture-valid-owner'})[0],403)
    def test_remote_cookie_and_https_origin_keep_csrf(self):
        code,_,headers=self.request('GET','/',headers=self.headers());self.assertEqual(code,200)
        for value in ['Secure','HttpOnly','SameSite=Strict']:self.assertIn(value,headers['Set-Cookie'])
        h={**self.headers(),'Cookie':'founder_session='+self.server.token,'X-Founder-CSRF':self.server.token,'Origin':'https://pitch.gbaonvo.com','Content-Type':'application/json'}
        body=json.dumps({'title':'Remote fixture','body':'Fixture draft','duration_seconds':60})
        self.assertEqual(self.request('POST','/api/pitches',body,h)[0],200)
        for changes in [{'Origin':'https://evil.example'},{'Origin':'http://pitch.gbaonvo.com'},{'X-Founder-CSRF':''},{'Cf-Access-Jwt-Assertion':''}]:
            self.assertEqual(self.request('POST','/api/pitches',body,{**h,**changes})[0],403)

if __name__=='__main__':unittest.main()
