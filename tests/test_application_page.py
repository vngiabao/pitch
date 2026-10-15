import unittest
import test_funding_hunter as fixtures
from test_opportunity_curation import brief


class ApplicationPageTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    record=fixtures.HunterTests.record

    def opportunity(self,name='Example Competition'):
        d=self.record(name);d['founder_brief']=brief(d['official_url'])
        return self.h.upsert(d)['opportunity_id']

    def test_owner_marks_submitted_with_attested_source(self):
        oid=self.opportunity();aid=self.h.start_application(oid)
        r=self.h.owner_outcome(oid,'Applied','Submitted tonight',application_id=aid)
        self.assertEqual(r['recommendation'],'ALREADY APPLIED')
        row=self.s.one('SELECT o.application_id,s.kind FROM funding_outcomes o JOIN source_versions v ON v.id=o.source_version_id JOIN sources s ON s.id=v.source_id WHERE o.id=?',(r['outcome_id'],))
        self.assertEqual(row['application_id'],aid);self.assertEqual(row['kind'],'owner_attestation')
        self.assertTrue((self.path/'owner-attestations').is_dir())

    def test_unknown_outcome_rejected(self):
        oid=self.opportunity()
        with self.assertRaises(ValueError):self.h.owner_outcome(oid,'Maybe')

    def test_application_view_returns_questions_answers_and_outcomes(self):
        oid=self.opportunity();aid=self.h.start_application(oid)
        qid=self.s.add_question(aid,1,'What is your competitive advantage?',self.src,'form',50,'words',checked=True)
        self.s.add_answer(qid,'We keep the whole family story.',[self.src],provenance='owner_written')
        self.h.owner_outcome(oid,'Applied',application_id=aid)
        v=self.h.application_view(aid)
        self.assertEqual(v['program'],'Example Competition');self.assertEqual(v['questions'][0]['limit'],50)
        self.assertEqual(v['questions'][0]['answer']['body'],'We keep the whole family story.')
        self.assertEqual(v['outcomes'][0]['outcome'],'Applied')

    def test_money_board_separates_waiting_from_decided(self):
        waiting=self.opportunity('Waiting Prize');decided=self.opportunity('Decided Prize')
        self.h.owner_outcome(waiting,'Applied');self.h.owner_outcome(decided,'Rejected')
        tracked={t['canonical_name']:t for t in self.h.dashboard()['money_board']['tracked']}
        self.assertTrue(tracked['Waiting Prize']['waiting']);self.assertFalse(tracked['Decided Prize']['waiting'])
        self.assertIn('next_date',tracked['Waiting Prize'])


if __name__=='__main__':unittest.main()
