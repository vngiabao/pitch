import unittest
import test_funding_hunter as fixtures
from founder_os.form_reader import parse
from founder_os.application_drafter import ApplicationDrafter,choose_option,access_status,DRAFT_PREFIX

FORM='''<html><body><form>
<div aria-labelledby="l1"><label id="l1">Company name *</label><input type="text" name="company"></div>
<label for="em">Work email</label><input id="em" type="email" name="email" required>
<div aria-labelledby="l2"><label id="l2">Number of employees</label><select name="size"><option>Please Select</option><option>1-10</option><option>11-50</option></select></div>
<div aria-labelledby="l3"><label id="l3">Have you incorporated your company yet?</label>
<label><input type="radio" name="inc" value="Yes">Yes</label><label><input type="radio" name="inc" value="No">No</label></div>
<label for="q">What does your company do? (Max. 50 words)</label><textarea id="q" name="does"></textarea>
<input type="hidden" name="csrf" value="x"><button type="submit">Send</button></form></body></html>'''


class FakeReader:
    def __init__(self,result):self.result=result
    def read(self,url):return self.result


class DrafterTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record
    approve_fact=fixtures.HunterTests.approve_fact

    def test_parser_reads_labels_options_limits(self):
        r=parse(FORM);q={x['label']:x for x in r['questions']}
        self.assertEqual(r['state'],'QUESTIONS_READ')
        self.assertIn('Company name',q);self.assertEqual(q['Number of employees']['options'],['1-10','11-50'])
        self.assertEqual(q['Have you incorporated your company yet?']['options'],['Yes','No'])
        self.assertEqual((q['What does your company do? (Max. 50 words)']['limit'],q['What does your company do? (Max. 50 words)']['unit']),(50,'words'))
        self.assertNotIn('csrf',str(r['questions']))

    def test_login_wall_is_blocked_not_bypassed(self):
        r=parse('<form><label for="e">Email</label><input id="e" type="email"><input type="password" name="pw"></form>')
        self.assertEqual(r['state'],'LOGIN_REQUIRED');self.assertEqual(r['questions'],[])

    def test_choose_option_maps_facts_to_form_text(self):
        self.assertEqual(choose_option(2,['1-10','11-50']),'1-10')
        self.assertEqual(choose_option(0,['< $1M','$1-5M']),'< $1M')
        self.assertEqual(choose_option(True,['Yes','No']),'Yes')
        self.assertEqual(choose_option('Bootstrapped',['Bootstrapped','Seed']),'Bootstrapped')
        self.assertIsNone(choose_option(7,['A','B']))

    def test_read_form_fills_facts_and_queues_open_questions(self):
        for k,v in (('company_name','A Story Technologies, Inc.'),('team_size',2),('incorporated',True)):self.approve_fact(k,v)
        oid=self.h.upsert(self.record())['opportunity_id']
        d=ApplicationDrafter(self.s,FakeReader(parse(FORM)));r=d.read_form(oid)
        self.assertEqual(r['state'],'QUESTIONS_READ');self.assertGreaterEqual(r['filled'],3);self.assertTrue(r['draft_queued'])
        answers={q['prompt'].split(' [')[0]:self.s.db.execute('SELECT body FROM answer_versions WHERE question_id=?',(q['id'],)).fetchone() for q in self.s.rows('SELECT * FROM questions WHERE application_id=?',(r['application_id'],))}
        self.assertEqual(answers['Number of employees'][0],'1-10');self.assertEqual(answers['Have you incorporated your company yet?'][0],'Yes')
        self.assertIsNone(answers['What does your company do? (Max. 50 words)'])
        self.assertEqual(access_status(self.s,oid,'REVIEW')['level'],'DRAFTING')
        saved=d.save_drafts(r['application_id'],[{'question_id':q['id'],'answer':'An AI biographer that calls families.','note':''} for q in d.open_questions(r['application_id']) if 'company do' in q['prompt']])
        self.assertEqual(saved,1)

    def test_blocked_and_unread_states_are_explicit(self):
        oid=self.h.upsert(self.record())['opportunity_id']
        self.assertEqual(access_status(self.s,oid,'REVIEW')['level'],'NOT_CHECKED')
        ApplicationDrafter(self.s,FakeReader({'state':'LOGIN_REQUIRED','reason':'Sign in first.','questions':[]})).read_form(oid)
        self.assertEqual(access_status(self.s,oid,'REVIEW')['label'],'Blocked: needs your login')
        self.assertEqual(access_status(self.s,oid,'ALREADY APPLIED','Applied')['level'],'FINISHED')


if __name__=='__main__':unittest.main()
