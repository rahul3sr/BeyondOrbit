import tempfile
from pathlib import Path
import unittest
from beyond_orbit.analytics import import_evidence,summarize
from beyond_orbit.store import Store
from beyond_orbit.campaigns import now

class Evidence(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.s=Store(Path(self.t.name)/'db.sqlite')
        self.d={'type':'financial','kind':'accrued_revenue','currency':'USD','value':10,
                'status':'verified','fixture':False,'source_url':'https://example.invalid/test-only',
                'evidence_id':'UNIT-TEST','checked_at':now().isoformat()}
    def tearDown(self):self.t.cleanup()
    def test_forecasts_do_not_become_cash(self):
        self.assertEqual(import_evidence(self.s,self.d),'imported')
        self.assertEqual(import_evidence(self.s,self.d),'duplicate')
        r=summarize(self.s.dashboard())
        self.assertEqual(r['financials']['accrued_revenue_usd'],10)
        self.assertIsNone(r['financials']['cash_received_usd'])
        self.assertIsNone(r['financials']['contribution_usd'])
    def test_fixture_import_blocked(self):
        self.d['fixture']=True
        with self.assertRaises(ValueError):import_evidence(self.s,self.d)

    def test_future_evidence_rejected(self):
        from datetime import timedelta
        self.d['checked_at']=(now()+timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):import_evidence(self.s,self.d)
