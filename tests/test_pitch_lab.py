import json
import os
import unittest
import zipfile
import io
# Slide QA launches a real browser; only the dedicated test below turns it on.
os.environ.setdefault('FOUNDER_OS_SLIDE_QA','off')
import test_funding_hunter as fixtures
from founder_os.pitch_lab import PitchLab,FactGuard,PIPELINE_PREFIX
from founder_os.money_map import MoneyMap,classify
from founder_os import slide_deck


def brief(text_by_slide,minutes=3):
    script=[{'slide_id':k,'title':k.replace('-',' ').title(),'seconds':30,'text':v} for k,v in text_by_slide.items()]
    return {'rules':{'minutes':minutes,'slide_limit':None,'format':'Live pitch','judging_criteria':['Team','Market'],'required_sections':[],'prize':'$5,000','equity':'Non-dilutive','deadline':None,'source_urls':[]},
            'strategy':'Lead with the legacy gap.','slide_plan':[{'slide_id':k,'action':'keep','change':'','why':''} for k in text_by_slide],'script':script,
            'ask':'Funds the launch.','materials':['Deck PDF'],'open_questions':['Ask amount?'],'answers_to_feedback':[]}


def coach(score):
    return {'summary':'Clear story.','scores':[{'criterion':c,'score':score,'why':'ok','fix':'tighten'} for c in ('Clarity','Problem urgency','Insight','Why now','Evidence','Business','Defensibility','Team','The ask','Delivery')],
            'hard_questions':[{'question':'Why won’t Storyworth copy this?','answer':'Family input shapes the next call.','gap':'Retention data'}],'top_fixes':['Lead with retention'],'verdict':'PASS' if score>=4 else 'REVISE'}


class Runner:
    """Plays the model: a queue of answers per stage."""
    def __init__(self,**answers):self.answers={k:list(v) for k,v in answers.items()};self.calls=[]
    def __call__(self,prompt,schema,stem,search):
        self.calls.append((stem,search));return self.answers[stem].pop(0)


class PitchLabTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record

    def lab(self):return PitchLab(self.s)

    def run_ai(self,lab,iid,runner):
        req=self.s.db.execute('SELECT * FROM hunter_requests WHERE reason=? AND state=\'QUEUED\'',(PIPELINE_PREFIX+iid,)).fetchone()
        self.assertIsNotNone(req,'stage was not queued')
        # Like the real worker: the request stays RUNNING while the stage runs and the item advances.
        self.s.db.execute("UPDATE hunter_requests SET state='RUNNING' WHERE id=?",(req['id'],))
        it=lab.run_ai_stage(iid,runner)
        self.s.db.execute("UPDATE hunter_requests SET state='COMPLETE' WHERE id=?",(req['id'],))
        return lab.item(iid)

    def test_fact_guard_rules(self):
        g=FactGuard(self.lab(),'Startup World Cup')
        r=g.check([{'key':'traction','text':'We have 5 paying customers and 4,321 users — growing fast.'}],'PITCH_EDITION')
        rules={i['rule'] for i in r['issues']}
        self.assertIn('traction',rules);self.assertIn('unverified_number',rules);self.assertIn('dash',rules)
        self.assertNotIn('—',r['segments'][0]['text'])
        ok=g.check([{'key':'traction','text':'5 families are waiting to join as paying customers. 79% want to know more.'}],'PITCH_EDITION')
        self.assertEqual(ok['blocking'],0)
        self.assertTrue(any(i['rule']=='team' for i in g.check([{'key':'team','text':'Nhi leads brand.'}],'PITCH_EDITION')['issues']))
        self.assertFalse(any(i['rule']=='team' for i in FactGuard(self.lab(),'Michigan Business Challenge').check([{'key':'team','text':'Nhi leads brand.'}],'PITCH_EDITION')['issues']))
        self.assertTrue(any(i['rule']=='price_placement' for i in g.check([{'key':'meet-a-story','text':'Only $119 a year.'}],'PITCH_EDITION')['issues']))
        self.assertFalse(any(i['rule']=='price_placement' for i in g.check([{'key':'business','text':'Only $119 a year.'}],'PITCH_EDITION')['issues']))
        self.assertTrue(any(i['rule']=='hope_college' for i in g.check([{'key':'x','text':'Our partnership with Hope College is signed.'}],'PITCH_EDITION')['issues']))
        # Spoken rounding of an approved number is fine: $24.12 said as "about $24".
        r=g.check([{'key':'business','text':'About $24 per account at half use, minus about $9 at full use.'}],'PITCH_EDITION')
        self.assertFalse(any(i['rule']=='unverified_number' for i in r['issues']))
        r=g.check([{'key':'next','text':'A test from January 29–March 25, 2027, using 2023–2025 data.'}],'PITCH_EDITION')
        self.assertIn('January 29 - March 25',r['segments'][0]['text']);self.assertIn('2023–2025',r['segments'][0]['text'])

    def test_edition_runs_the_full_line_with_revisions(self):
        oid=self.h.upsert(self.record('Startup World Cup'))['opportunity_id'];lab=self.lab()
        it=lab.start_edition(oid,3)
        self.assertEqual(it['stage'],'TAILOR');self.assertTrue(it['queued'])
        clean={'legacy-gap':'Eighty years of a life, remembered by two dates and a folder of photos.','business':'Families pay $119 a year to keep the story growing.'}
        runner=Runner(tailor=[brief(clean),brief(clean),brief(clean)],
                      voice=[{'segments':[{'key':'legacy-gap','text':'Eighty years of a life, and 4,321 photos.','changed':True}],'notes':['plainer']},{'segments':[],'notes':[]},{'segments':[],'notes':[]}],
                      coach=[coach(3),coach(3),coach(3)])
        it=self.run_ai(lab,it['id'],runner)
        self.assertTrue(runner.calls[0][1],'first Tailor round may read the official rules')
        self.assertEqual(it['stage'],'VOICE')
        it=self.run_ai(lab,it['id'],runner)
        # Voice tried to add a number; the recheck restores the original wording.
        self.assertNotIn('4,321',json.dumps(it['payload']['brief']['script']))
        self.assertEqual(it['stage'],'COACH')
        it=self.run_ai(lab,it['id'],runner)
        self.assertEqual((it['stage'],it['round']),('TAILOR',2))
        self.assertEqual(it['payload']['feedback']['from'],'Pitch Coach')
        for _ in range(3):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual((it['stage'],it['round']),('TAILOR',3))
        self.assertFalse(runner.calls[3][1],'revisions never search the web')
        for _ in range(3):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual(it['stage'],'READY');self.assertEqual(it['round'],3)
        self.assertEqual(len([r for r in it['reviews'] if r['agent']=='COACH']),3)
        saved=lab.save_to_studio(it['id'])
        from founder_os.pitch_studio import PitchStudio
        p=PitchStudio(self.s).detail(saved['pitch_id'])
        self.assertIn('SLIDE 1',p['body']);self.assertIn('PITCH COACH',p['notes'])
        # Bao edits the saved pitch: his edit becomes a voice example.
        PitchStudio(self.s).save(saved['pitch_id'],{**{k:p[k] for k in ('title','audience','scenario','speaker','notes','format','status','duration_seconds','sources','claim_versions')},'body':p['body']+' My own line.','change_note':'Bao edit','expected_version_id':p['id']})
        self.assertEqual(lab.harvest_voice(),1)

    def test_last_round_block_reaches_bao_flagged(self):
        oid=self.h.upsert(self.record('Startup World Cup'))['opportunity_id'];lab=self.lab()
        bad=brief({'legacy-gap':'We already have 4,321 families.'});bad['ask']='Test from January 29—March 25.'
        runner=Runner(tailor=[bad,bad,bad],voice=[{'segments':[],'notes':[]}],coach=[coach(5)])
        it=lab.start_edition(oid,3)
        for _ in range(3):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual((it['stage'],it['round']),('VOICE',3))
        for _ in range(2):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual(it['stage'],'READY')
        self.assertTrue(any('4,321' in u['text'] for u in it['payload']['unresolved']))
        self.assertNotIn('—',it['payload']['brief']['ask'])
        self.assertTrue(any('need your eyes' in a['title'] for a in lab.alerts()))

    def test_last_round_block_that_voice_fixed_is_not_left_open(self):
        oid=self.h.upsert(self.record('Startup World Cup'))['opportunity_id'];lab=self.lab()
        bad=brief({'traction':'Hope College is our first partner campaign.'})
        fixed=[{'key':'traction','text':'Many Hope College students want to preorder or join our mailing list.','changed':True}]
        runner=Runner(tailor=[bad,bad,bad],voice=[{'segments':fixed,'notes':[]}],coach=[coach(5)])
        it=lab.start_edition(oid,3)
        for _ in range(5):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual(it['stage'],'READY')
        self.assertNotIn('unresolved',it['payload'])
        self.assertEqual([r['verdict'] for r in it['reviews'] if r['agent']=='FACT_GUARD'][-2:],['BLOCK','PASS'])

    def test_format_check_sends_long_scripts_back(self):
        oid=self.h.upsert(self.record('Five By Five Night'))['opportunity_id'];lab=self.lab()
        long={'legacy-gap':' '.join(['story']*400)}
        runner=Runner(tailor=[brief(long,1)],voice=[{'segments':[],'notes':[]}],coach=[coach(5)])
        it=lab.start_edition(oid,1)
        for _ in range(3):it=self.run_ai(lab,it['id'],runner)
        self.assertEqual((it['stage'],it['round']),('TAILOR',2))
        self.assertEqual(it['payload']['feedback']['from'],'Format Check')

    def test_application_review_suggests_without_touching_answers(self):
        from test_application_drafter import FakeReader,FORM
        from founder_os.form_reader import parse
        from founder_os.application_drafter import ApplicationDrafter
        oid=self.h.upsert(self.record())['opportunity_id'];d=ApplicationDrafter(self.s,FakeReader(parse(FORM)));r=d.read_form(oid)
        q=[x for x in d.open_questions(r['application_id']) if 'company do' in x['prompt']][0]
        d.save_drafts(r['application_id'],[{'question_id':q['id'],'answer':'A Story leverages AI to call families.','note':''}])
        before=self.s.db.execute('SELECT COUNT(*) FROM answer_versions').fetchone()[0]
        lab=self.lab();it=lab.start_application(r['application_id'])
        self.assertEqual(it['stage'],'VOICE')
        runner=Runner(voice=[{'segments':[{'key':q['id'],'text':'A Story calls families and does the asking.','changed':True}],'notes':[]}],coach=[coach(4)])
        it=self.run_ai(lab,it['id'],runner);it=self.run_ai(lab,it['id'],runner)
        self.assertEqual(it['stage'],'READY')
        sug=[a for a in it['payload']['answers'] if a['question_id']==q['id']][0]
        self.assertEqual(sug['suggested'],'A Story calls families and does the asking.')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM answer_versions').fetchone()[0],before)
        self.assertEqual(lab.start_application(r['application_id'])['id'],it['id'],'same answers are reviewed once')

    def test_results_become_lessons_bao_approves(self):
        oid=self.h.upsert(self.record('Startup World Cup'))['opportunity_id'];lab=self.lab();lab.poll()
        self.h.owner_outcome(oid,'Rejected','Judges wanted traction numbers.')
        lab.poll()
        item=[x for x in lab.items() if x['kind']=='OUTCOME_LESSON'][0]
        runner=Runner(learn=[{'lessons':[{'lesson':'Lead with the 50 / 10 / 5 numbers for investor-judged competitions.','applies_to':'TAILOR','evidence':'Rejected; judges asked for traction.'}]}])
        self.run_ai(lab,item['id'],runner)
        proposed=lab.lessons('PROPOSED');self.assertEqual(len(proposed),1)
        self.assertEqual(lab.approved_lessons('TAILOR'),[])
        self.assertTrue(any('lesson' in a['title'] for a in lab.alerts()),'pending lessons reach Today and the daily email')
        lab.decide_lesson(proposed[0]['id'],'APPROVED')
        self.assertIn('Lead with the 50 / 10 / 5 numbers',lab.approved_lessons('TAILOR')[0])
        self.assertFalse(any('lesson' in a['title'] for a in lab.alerts()))

    def test_money_map_categories_and_moves(self):
        rec=self.record('Michigan 5x5 Night');rec['funding']['cash_prize_max']=5000
        self.h.upsert(rec)
        big=self.record('National Venture Cup');big['funding']['cash_prize_max']=500000;self.h.upsert(big)
        m=MoneyMap(self.s);b=m.board()
        cats={c['key']:[p['name'] for p in c['programs']] for c in b['categories']}
        self.assertIn('Michigan 5x5 Night',cats['local_pitch']);self.assertIn('National Venture Cup',cats['big_pitch'])
        move=b['moves'][0];m.set_move(move['id'],'DONE')
        self.assertEqual([x for x in m.board()['moves'] if x['id']==move['id']][0]['state'],'DONE')


if __name__=='__main__':unittest.main()


class EditionBuilderTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record
    run_ai=PitchLabTests.run_ai

    def ready_edition(self,script):
        oid=self.h.upsert(self.record('Startup World Cup'))['opportunity_id'];lab=PitchLab(self.s)
        b=brief(script);b['script'].append({'slide_id':'new-2','title':'The ask','seconds':20,'text':'Here is what we are raising.'});b['ask']='We are raising a pre-seed round. It funds the retention proof.'
        runner=Runner(tailor=[b],voice=[{'segments':[],'notes':[]}],coach=[coach(5)])
        it=lab.start_edition(oid,3)
        for _ in range(3):it=self.run_ai(lab,it['id'],runner)
        return lab,it

    def test_edition_is_built_from_core_slides_in_order(self):
        lab,it=self.ready_edition({'legacy-gap':'Eighty years of a life.','business':'Families pay $119 a year to keep the story growing.'})
        self.assertEqual(it['stage'],'READY')
        self.assertEqual([r['agent'] for r in it['reviews']][-2:],['BUILDER','SLIDE_QA'])
        e=it['payload']['edition'];self.assertEqual([s['id'] for s in e['slides']],['legacy-gap','business','new-2']);self.assertEqual(e['new_slides'],['new-2'])
        m=lab.edition_manifest(it);out,slides=slide_deck.edition_files(m)
        deck=json.loads((out/'deck.json').read_text(encoding='utf-8'))
        self.assertEqual(deck['order'],['legacy-gap','business','new-2']);self.assertEqual(deck['cover'],'legacy-gap')
        self.assertTrue(all(v['start'] in deck['order'] for v in deck['sections'].values()))
        # Core design untouched: same markup as the frozen slide apart from notes and page number.
        _,_,core=slide_deck.load_core()
        strip=lambda h:slide_deck.PAGE_NO.sub('',slide_deck.ASIDE.sub('',h))
        self.assertEqual(strip(slides['business']),strip(core['business']))
        self.assertIn('<aside>~0:30 · Families pay $119 a year',slides['business'])
        self.assertRegex(slides['business'],r'bottom:\s*40px[^"]*">02</p>')
        self.assertIn('data-draft="true"',slides['new-2']);self.assertIn('We are raising a pre-seed round.',slides['new-2'])
        self.assertEqual(it['payload']['slide_qa']['available'],False)
        z=zipfile.ZipFile(io.BytesIO(slide_deck.edition_zip(m)))
        names=z.namelist();self.assertIn('project/deck.json',names);self.assertIn('project/slides/business.html',names)
        self.assertTrue(any(n.startswith('assets/') for n in names),'images travel with the deck')
        page=slide_deck.preview_page(m,it['payload']['slide_qa'],it['title'])
        self.assertIn('/edition-asset/',page);self.assertNotIn('/_blob/',page);self.assertIn('/vendor/gsap.min.js',page)

    def test_a_designed_new_slide_survives_a_rebuild(self):
        lab,it=self.ready_edition({'legacy-gap':'Eighty years of a life.'})
        d=slide_deck.editions_root(self.s)/it['id']/'designed';d.mkdir(parents=True)
        (d/'new-2.html').write_text('<section id="new-2" style="background:#f3ebde"><h2>Our ask</h2><p style="position:absolute; bottom:40px; right:64px">09</p><aside>old</aside></section>',encoding='utf-8')
        it=lab.build_now(it['id']);m=lab.edition_manifest(it);_,slides=slide_deck.edition_files(m)
        self.assertIn('<h2>Our ask</h2>',slides['new-2']);self.assertNotIn('data-draft',slides['new-2'])
        self.assertIn('>02</p>',slides['new-2']);self.assertIn('<aside>~0:20 · Here is what we are raising.',slides['new-2'])
        self.assertEqual(it['payload']['edition']['new_slides'],[])

    def test_build_now_keeps_an_approved_editions_stage(self):
        lab,it=self.ready_edition({'legacy-gap':'Eighty years of a life.'})
        lab.approve(it['id']);p=lab.item(it['id'])['payload'];p.pop('edition');lab._save(it['id'],payload=p)
        it=lab.build_now(it['id'])
        self.assertEqual(it['stage'],'APPROVED');self.assertEqual(it['payload']['edition']['slides'][0]['id'],'legacy-gap')
        with self.assertRaises(ValueError):lab.build_now(lab.create('GROWTH_DRAFT','x',{'body':'Hello','title':'x'})['id'])

    @unittest.skipUnless(slide_deck.find_browser(),'needs Edge or Chrome')
    def test_slide_qa_catches_broken_layouts(self):
        lab,it=self.ready_edition({'legacy-gap':'Eighty years of a life.','business':'Families pay $119 a year.'})
        m=lab.edition_manifest(it);out=__import__('pathlib').Path(m['dir'])
        bad=('<section id="business" style="background:#f3ebde">'
             '<p style="position:absolute; top:100px; left:100px; width:900px; font-size:60px; font-weight:800">Two lines that collide with each other here</p>'
             '<p style="position:absolute; top:110px; left:120px; width:900px; font-size:60px; font-weight:800">Another title placed on top of it</p>'
             '<div style="position:absolute; top:400px; left:100px; width:500px; height:80px; background:#2e5163"></div>'
             '<p style="position:absolute; top:410px; left:120px; width:460px; font-size:40px; color:#fff">This text is far too long for the small box it sits in</p>'
             '<p style="position:absolute; top:900px; left:1700px; width:400px; font-size:40px">Runs off the slide</p><aside>notes</aside></section>')
        (out/'slides'/'business.html').write_text(bad,encoding='utf-8')
        os.environ['FOUNDER_OS_SLIDE_QA']='on'
        try:qa=slide_deck.run_qa(m)
        finally:os.environ['FOUNDER_OS_SLIDE_QA']='off'
        self.assertTrue(qa['available'],qa.get('reason'))
        by={s['id']:{i['rule'] for i in s['issues'] if i['severity']=='block'} for s in qa['slides']}
        self.assertEqual(by['legacy-gap'],set(),'an approved core slide passes')
        self.assertTrue({'TEXT_OVERLAP','TEXT_SPILL','OFF_SLIDE'}<=by['business'],by['business'])
        self.assertTrue(any(i['rule']=='NEW_SLIDE' for s in qa['slides'] for i in s['issues']))
