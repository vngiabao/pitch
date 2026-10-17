import json,unittest
import test_funding_hunter as fixtures
from founder_os.founder_profile import FounderProfile,match_key,mask,MASK
from founder_os.application_drafter import ApplicationDrafter


class MappingTests(unittest.TestCase):
    def test_synonyms_reach_the_right_key(self):
        cases={'EIN':'ein','Tax ID':'ein','Employer Identification Number':'ein','Federal Tax ID number':'ein',
               'Company address':'legal_address','Street address':'legal_address','Address line 1':'legal_address','Mailing address':'mailing_address',
               'Registered business address':'legal_address','LinkedIn profile (URL)':'linkedin_url','Startup LinkedIn Profile':'company_linkedin_url',
               'Team member 2 LinkedIn':'cofounder_linkedin_url','Video Pitch Link':'demo_video_link','Multimedia URL':'demo_video_link','Pitch Deck Link':'deck_link',
               'When was your company incorporated?':'incorporation_date','Incorporated on':'incorporation_date','Date founded':'incorporation_date',
               'State of incorporation':'incorporation_state','Phone Number':'phone','Primary Contact Phone':'phone','Preferred Pronouns':'pronouns',
               'Date of birth':'founder_dob','Team member 2 date of birth':'cofounder_dob','Are you a U.S. citizen or permanent resident?':'founder_citizenship',
               'Company Twitter Profile':'company_twitter_url','Crunchbase URL':'crunchbase_url','Company website':'company_website',
               'Total revenue to date':'revenue_to_date','Total funding raised':'funding_to_date','How much are you expecting to fundraise in your next round?':'next_round_target',
               'Number of employees':'employees','City':'city','ZIP code':'zip_code','Country':'country'}
        for label,key in cases.items():
            self.assertEqual(match_key(label),key,label)

    def test_look_alikes_are_left_alone(self):
        for label in ('Email address','Phone Type','Email Type','Describe your revenue model','What does your company do?','Do you consent to video recording?',
                      'Country of incorporation','Initial','Suffix','How did you hear about us?','Deepgram Project UUID'):
            self.assertIsNone(match_key(label),label)
        self.assertIsNone(match_key(''))

    def test_masking_hides_everything(self):
        self.assertEqual(mask('12-3456789'),MASK);self.assertEqual(mask(''),'')
        self.assertNotIn('3456789',mask('12-3456789'))


class VaultTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record
    approve_fact=fixtures.HunterTests.approve_fact

    def audit(self):
        return [json.loads(r['payload_json']) for r in self.s.db.execute("SELECT payload_json FROM audit WHERE event LIKE 'founder_profile.%'")]

    def test_sensitive_values_never_leave_masked(self):
        v=FounderProfile(self.s);v.save('ein','12-3456789');v.save('linkedin_url','https://www.linkedin.com/in/bao')
        page=json.dumps(v.board())
        self.assertNotIn('3456789',page);self.assertIn('linkedin.com/in/bao',page)
        ein=[f for f in v.fields() if f['key']=='ein'][0]
        self.assertTrue(ein['set']);self.assertIsNone(ein['value']);self.assertEqual(ein['masked'],MASK);self.assertTrue(ein['sensitive'])
        self.assertEqual(v.reveal('ein')['value'],'12-3456789')
        self.assertNotIn('ein',v.public_values());self.assertIn('linkedin_url',v.public_values())
        for payload in self.audit():self.assertNotIn('3456789',json.dumps(payload))
        self.assertIn({'key':'ein'},self.audit())

    def test_bank_fields_are_refused_and_custom_fields_match_by_words(self):
        v=FounderProfile(self.s)
        with self.assertRaisesRegex(ValueError,'Bank'):v.save('','1234','Bank account number')
        with self.assertRaisesRegex(ValueError,'Bank'):v.save('','1234','Routing number')
        r=v.save('','proj-123','Deepgram project UUID',sensitive=True)
        self.assertEqual(r['key'],'deepgram_project_uuid')
        self.assertEqual(v.match('Deepgram Project UUID'),'deepgram_project_uuid');self.assertIsNone(v.match('Project UUID for Runware'))
        custom=[f for f in v.fields() if f['custom']][0]
        self.assertEqual(custom['group'],'Other');self.assertIsNone(custom['value']);self.assertTrue(custom['sensitive'])
        v.delete('deepgram_project_uuid');self.assertFalse([f for f in v.fields() if f['custom']])
        with self.assertRaises(ValueError):v.delete('ein')

    def application(self,prompts):
        oid=self.h.upsert(self.record())['opportunity_id'];aid=self.h.start_application(oid)
        for i,prompt in enumerate(prompts,1):self.s.add_question(aid,i,prompt,self.src,'form | type='+('select' if '[' in prompt else 'text'),checked=True)
        self.s.db.execute("INSERT INTO form_inspections VALUES(?,?,?,?,?,?,?)",(oid,'https://example.org/apply','QUESTIONS_READ','ok',len(prompts),aid,'2026-10-16T00:00:00+00:00'))
        return aid

    def answers(self,aid):
        return {q['prompt']:self.s.db.execute('SELECT body,provenance FROM answer_versions WHERE question_id=? ORDER BY created_at DESC',(q['id'],)).fetchone() for q in self.s.rows('SELECT * FROM questions WHERE application_id=?',(aid,))}

    def test_form_filler_uses_vault_and_leaves_the_rest_to_bao(self):
        d=ApplicationDrafter(self.s);aid=self.application(['EIN','LinkedIn profile (URL)','Phone Number','Pitch Deck Link','What does your company do?'])
        for qid in self.s.rows('SELECT id FROM questions WHERE application_id=?',(aid,)):
            self.s.db.execute("INSERT INTO draft_notes VALUES(?,?,?)",(qid['id'],'Not provided.','2026-10-16T00:00:00+00:00'))
        self.assertEqual(d.fill_known(aid),0)
        v=FounderProfile(self.s);v.save('ein','12-3456789');v.save('linkedin_url','https://www.linkedin.com/in/bao')
        self.assertEqual(d.refill_all(),{aid:2})
        a=self.answers(aid)
        self.assertEqual(tuple(a['EIN']),('12-3456789','founder_profile'));self.assertEqual(a['LinkedIn profile (URL)'][0],'https://www.linkedin.com/in/bao')
        self.assertIsNone(a['Phone Number']);self.assertIsNone(a['Pitch Deck Link']);self.assertIsNone(a['What does your company do?'])
        view=self.h.application_view(aid);by={q['prompt']:q for q in view['questions']}
        self.assertIsNone(by['EIN']['needs_you']);self.assertEqual(by['Phone Number']['needs_you'],'Not provided.')
        self.assertEqual(len([q for q in d.open_questions(aid)]),3)
        self.assertEqual(d.refill_all(),{aid:0})
        for row in self.s.db.execute("SELECT payload_json FROM audit"):self.assertNotIn('3456789',row[0])

    def test_approved_facts_win_and_choices_need_a_matching_option(self):
        self.approve_fact('team_size',2);self.approve_fact('headquarters','4932 West Campus Drive, Allendale, Michigan 49401')
        v=FounderProfile(self.s);v.save('team_size','9');v.save('country','United States');v.save('employees','0')
        d=ApplicationDrafter(self.s);aid=self.application(['How many people are on your team?','Company address','Country [Canada, Mexico]','Headcount [0, 1-10, 11+]'])
        d.fill_known(aid);a=self.answers(aid)
        self.assertEqual(tuple(a['How many people are on your team?']),('2','auto_filled'))
        self.assertEqual(tuple(a['Company address']),('4932 West Campus Drive, Allendale, Michigan 49401','founder_profile'))
        self.assertIsNone(a['Country [Canada, Mexico]'])
        self.assertEqual(a['Headcount [0, 1-10, 11+]'][0],'0')

    def test_ai_context_excludes_sensitive_values(self):
        v=FounderProfile(self.s);v.save('ein','12-3456789');v.save('founder_dob','1999-01-01');v.save('deck_link','https://example.org/deck')
        d=ApplicationDrafter(self.s);aid=self.application(['Tell us about your traction'])
        ctx=json.dumps(d.draft_context(aid))
        self.assertNotIn('3456789',ctx);self.assertNotIn('1999-01-01',ctx);self.assertIn('example.org/deck',ctx)


if __name__=='__main__':unittest.main()
