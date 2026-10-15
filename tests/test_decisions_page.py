import unittest
from founder_os.store import now,PolicyError
import test_funding_hunter as fixtures


class DecisionsPageTests(unittest.TestCase):
    setUp=fixtures.HunterTests.setUp
    tearDown=fixtures.HunterTests.tearDown
    approve_fact=fixtures.HunterTests.approve_fact

    def propose(self,label,body,status,values=None,verified=False):
        v=self.s.propose_claim('team',label,body,status,self.src,'line 1',last_verified_at=now() if verified else None)
        for k,val in (values or {}).items():self.h.attach_fact_value(v,k,val)
        return self.s.request_approval('promote_claim',{'version_id':v})

    def card(self,aid):
        return next(p['card'] for p in self.h.dashboard()['needs_decision'] if p['id']==aid)

    def test_suggestion_follows_evidence(self):
        verified=self.propose('Incorporation','A Story is incorporated.','verified',{'incorporated':True},verified=True)
        reported=self.propose('Traction','Ten beta families.','reported')
        reminder=self.propose('Runway','Runway not established.','unknown')
        self.assertEqual(self.card(verified)['kind'],'APPROVE')
        self.assertIn('programs that require a legal entity',self.card(verified)['unlocks'])
        self.assertEqual(self.card(reported)['kind'],'CHECK')
        self.assertEqual(self.card(reminder)['kind'],'REMINDER')

    def test_card_shows_what_it_replaces(self):
        self.approve_fact('team_size',4)
        aid=self.propose('Team','Two founders.','verified',{'team_size':2},verified=True)
        self.assertEqual(self.card(aid)['replaces'],[{'fact':'team_size','current':4,'proposed':2}])

    def test_owner_edit_saves_verified_fact_and_retires_original(self):
        aid=self.propose('Product stage','Draft says beta; verify.','reported',{'product_stage':'private_beta'})
        r=self.h.owner_edit_claim(aid,'A Story is in private beta on TestFlight.')
        self.assertEqual(self.s.one('SELECT state FROM approvals WHERE id=?',(aid,))['state'],'rejected')
        v=self.s.one('SELECT body,evidence_status FROM claim_versions WHERE id=?',(r['claim_version_id'],))
        self.assertEqual((v['body'],v['evidence_status']),('A Story is in private beta on TestFlight.','verified'))
        self.assertEqual(self.h.company_memory()['attributes']['product_stage']['value'],'private_beta')
        self.assertEqual(self.h.dashboard()['recent_decisions'][0]['state'],'approved')

    def test_edit_rejects_empty_or_decided(self):
        aid=self.propose('Team','Two founders.','reported')
        with self.assertRaises(ValueError):self.h.owner_edit_claim(aid,'  ')
        self.s.decide(aid,'rejected',True)
        with self.assertRaises(PolicyError):self.h.owner_edit_claim(aid,'Two founders.')


if __name__=='__main__':unittest.main()
