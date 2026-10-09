import json,sqlite3,tempfile,unittest
from pathlib import Path
from founder_os.store import Store
from founder_os.pitch_studio import PitchStudio,PitchConflict
from test_hunter_runtime import ServerSecurityTests

class PitchStudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'studio.sqlite');self.studio=PitchStudio(self.s)
        p=Path(self.tmp.name)/'original.txt';p.write_text('Original pitch',encoding='utf-8');self.src=self.s.import_source(p,'pitch','KEEP',text='Original pitch')
        self.fields={'title':'Family introduction','body':'A family story begins with a question. [Add real evidence.]','audience':'Families & customers','scenario':'Customer conversation','duration_seconds':60,'sources':[self.src]}
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_edits_and_restore_preserve_versions_and_source(self):
        r=self.studio.create(self.fields);original=r['id'];p={**r,'body':'Revised wording','expected_version_id':original};new=self.studio.save(r['pitch_id'],p)
        self.assertEqual(len(new['history']),2);self.assertEqual(self.studio.export(r['pitch_id'],original).count(self.fields['body']),1)
        restored=self.studio.restore(r['pitch_id'],original,new['id']);self.assertEqual(restored['body'],self.fields['body']);self.assertEqual(len(restored['history']),3)
        self.assertEqual(restored['sources'],[self.src]);self.assertEqual(self.s.one('SELECT body FROM pitches WHERE id=?',(r['pitch_id'],))['body'],self.fields['body'])
        self.assertEqual(Path(self.tmp.name,'original.txt').read_text(),'Original pitch')
        self.assertEqual(self.s.one('SELECT count(*) n FROM claim_versions')['n'],0)
        for sql in ('UPDATE pitch_versions SET body=\'changed\' WHERE id=?','DELETE FROM pitch_versions WHERE id=?'):
            with self.assertRaises(sqlite3.IntegrityError):self.s.db.execute(sql,(original,))
    def test_stale_editor_cannot_overwrite_newer_work(self):
        r=self.studio.create(self.fields);updated=self.studio.save(r['pitch_id'],{**r,'body':'First editor','expected_version_id':r['id']})
        with self.assertRaises(PitchConflict):self.studio.save(r['pitch_id'],{**r,'body':'Second editor','expected_version_id':r['id']})
        self.assertEqual(self.studio.detail(r['pitch_id'])['body'],updated['body'])
    def test_custom_choices_archived_filters_and_seed_idempotence(self):
        fields={**self.fields,'audience':'Donors','scenario':'Dinner conversation','duration_seconds':95}
        first=self.studio.create(fields,'seed');again=self.studio.create(fields,'seed');self.assertEqual(first['pitch_id'],again['pitch_id'])
        options=self.studio.list();self.assertIn('Donors',options['audiences']);self.assertIn(95,options['lengths']);self.assertEqual(len(self.studio.list(audience='Donors',duration='95')['items']),1)
        self.studio.save(first['pitch_id'],{**first,'status':'archived','expected_version_id':first['id']})
        self.assertEqual(self.studio.list()['items'],[]);self.assertEqual(len(self.studio.list(archived=True)['items']),1)
    def test_invalid_source_duration_and_cross_pitch_restore_rejected(self):
        for change in [{'sources':['nonexistent']},{'duration_seconds':True},{'duration_seconds':0},{'body':''}]:
            with self.assertRaises(ValueError):self.studio.create({**self.fields,**change})
        a=self.studio.create(self.fields);b=self.studio.create(self.fields)
        with self.assertRaises(ValueError):self.studio.restore(a['pitch_id'],b['id'],a['id'])
    def test_new_legacy_agent_pitch_is_included_without_rewriting(self):
        self.s.db.execute("INSERT INTO pitches VALUES('legacy',30,'general','Preserved body','[]','draft','now',?)",(self.src,))
        self.studio.list();self.studio.list();r=self.studio.detail('legacy')
        self.assertEqual(r['body'],'Preserved body');self.assertEqual(len(r['history']),1)
        self.assertEqual(len(self.s.rows("SELECT * FROM imports WHERE destination_type='pitch_version'")),1)

class PitchHttpTests(ServerSecurityTests):
    def test_editor_route_and_save_require_owner_session(self):
        self.assertEqual(self.request('GET','/pitches')[0],200)
        self.assertEqual(self.request('POST','/api/pitches','{}')[0],403)
        headers={'Cookie':'founder_session='+self.server.token,'X-Founder-CSRF':self.server.token,'Origin':'http://'+self.host,'Content-Type':'application/json'}
        fields={'title':'Test','body':'Test script','duration_seconds':60}
        code,data,_=self.request('POST','/api/pitches',json.dumps(fields),headers);self.assertEqual(code,200);r=json.loads(data)
        fields['expected_version_id']='old';code,data,_=self.request('POST','/api/pitch/'+r['pitch_id'],json.dumps(fields),headers);self.assertEqual(code,409)
        code,data,h=self.request('GET','/api/pitch/'+r['pitch_id']+'/export',headers=headers);self.assertEqual(code,200);self.assertIn(b'Test script',data);self.assertIn('attachment',h['Content-Disposition'])

if __name__=='__main__':unittest.main()
