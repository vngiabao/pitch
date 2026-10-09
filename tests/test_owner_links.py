import json,tempfile,unittest
from pathlib import Path
from founder_os.owner_links import founder_url,public_site_enabled

class OwnerLinksTests(unittest.TestCase):
    def test_public_links_require_verified_owner_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cloudflare.json'
            self.assertEqual(founder_url('/pitches',p),'http://127.0.0.1:8765/pitches')
            c={'hostname':'pitch.gbaonvo.com','team_domain':'astoryapp.cloudflareaccess.com','audience':'a'*64,'email':'gbao.n.vo@gmail.com'}
            p.write_text(json.dumps(c))
            self.assertFalse(public_site_enabled(p))
            c['report_links_enabled']=True;p.write_text(json.dumps(c))
            self.assertEqual(founder_url('/applications#preview',p),'https://pitch.gbaonvo.com/applications#preview')
            for key,value in [('email','another@example.com'),('hostname','example.com'),('audience','unknown'),('report_links_enabled','true')]:
                bad=dict(c);bad[key]=value;p.write_text(json.dumps(bad))
                self.assertFalse(public_site_enabled(p))
            p.write_text('{broken')
            self.assertFalse(public_site_enabled(p))
            p.write_text('[]')
            self.assertFalse(public_site_enabled(p))
    def test_links_cannot_redirect_to_another_origin(self):
        for path in ['https://example.com','//example.com',None]:
            with self.assertRaises(ValueError):founder_url(path)

if __name__=='__main__':unittest.main()
