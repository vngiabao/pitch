"""Fail-closed Cloudflare Access identity validation for the tunnel origin."""
import re


class AccessIdentity:
    def __init__(self, hostname, team_domain, audience, email):
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', hostname):
            raise ValueError('An exact public hostname is required')
        if not re.fullmatch(r'[a-z0-9-]+\.cloudflareaccess\.com', team_domain):
            raise ValueError('Use the Cloudflare Access team domain, without a scheme or path')
        if not re.fullmatch(r'[a-fA-F0-9]{64}', audience):
            raise ValueError('The exact Access application audience is required')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('An exact owner email is required')
        import jwt
        self.jwt=jwt;self.hostname=hostname;self.email=email.lower()
        self.issuer='https://'+team_domain;self.audience=audience
        self.keys=jwt.PyJWKClient(self.issuer+'/cdn-cgi/access/certs',cache_keys=True,timeout=5)

    def authorized(self, token):
        if not isinstance(token,str) or not token or len(token)>16384:return False
        try:
            header=self.jwt.get_unverified_header(token)
            if header.get('alg')!='RS256' or not header.get('kid'):return False
            key=self.keys.get_signing_key_from_jwt(token).key
            claims=self.jwt.decode(token,key,algorithms=['RS256'],audience=self.audience,issuer=self.issuer,
                options={'require':['exp','iat','iss','aud','sub','email']})
            return isinstance(claims.get('email'),str) and claims['email'].lower()==self.email
        except Exception:
            # Key-fetch outages, expired tokens, bad signatures and wrong claims all deny.
            # Never include the token or credential content in a log or response.
            return False
