import tempfile,unittest
from pathlib import Path
from founder_os.store import Store
from founder_os.materials_library import MaterialsLibrary
from tools.curate_pitches import apply

class WorkspaceRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'workspace.sqlite');self.lib=MaterialsLibrary(self.s)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def material(self,key,path,body='',kind='document'):
        self.s.db.execute("INSERT INTO material_library(id,source_path,relative_path,source_root,kind,category,size_bytes,modified_ns,body,extraction,registered_at) VALUES(?,?,?,?,?,'KEEP',0,0,?,'text','2026-10-09')",(key,str(Path(self.tmp.name)/path),path,self.tmp.name,kind,body))
    def test_generated_files_stay_retrievable_without_crowding_default_results(self):
        self.material('deck','ElevenLabs/exports/A Story.pptx',kind='deck')
        self.material('build',r'ElevenLabs\build\candidate.pptx',kind='deck')
        self.material('page',r'ElevenLabs\exports\pages\01.pdf',kind='pdf')
        self.assertEqual([r['id'] for r in self.lib.search('ElevenLabs')['items']],['deck'])
        self.assertEqual({r['id'] for r in self.lib.search('ElevenLabs',category='ARCHIVE')['items']},{'build','page'})
        self.assertEqual(self.lib.search('ElevenLabs',category='all')['total'],3)
        self.assertEqual(self.lib.detail('build')['category'],'KEEP')
    def test_search_prioritizes_named_sources_and_escapes_literal_search(self):
        self.material('body','A unrelated deck.pptx','ElevenLabs',kind='deck')
        self.material('name','ElevenLabs notes.txt')
        self.material('literal','100%_notes.txt')
        self.assertEqual(self.lib.search('ElevenLabs')['items'][0]['id'],'name')
        self.assertEqual([r['id'] for r in self.lib.search('%_')['items']],['literal'])
    def test_editorial_replay_preserves_history_and_does_not_promote_company_facts(self):
        first=apply(self.s);second=apply(self.s)
        self.assertEqual([r['pitch_id'] for r in first],[r['pitch_id'] for r in second])
        self.assertEqual(self.s.one('SELECT count(*) n FROM pitch_versions')['n'],15)
        self.assertEqual(self.s.one('SELECT count(*) n FROM claim_versions')['n'],0)

if __name__=='__main__':unittest.main()
