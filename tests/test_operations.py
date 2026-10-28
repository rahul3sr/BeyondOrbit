import copy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import http.cookiejar
from beyond_orbit import skills
from beyond_orbit.campaigns import eligibility,forecast,now,validate
from beyond_orbit.engine import manifest,read,render,write
from beyond_orbit.operations import campaign_fixture,assumptions,scheduled_daily
from beyond_orbit.store import Store,authorize
from beyond_orbit.review import server
from integrations.social import YouTubeMock,InstagramMock,TikTokMock,LivePlatform

class Campaigns(unittest.TestCase):
    def setUp(self):
        self.c=campaign_fixture()
        self.account={'followers':0,'country':'US','platform':'youtube'}
    def test_fixture_not_live_eligible(self):
        self.assertFalse(eligibility(self.c,self.account)['eligible'])
        self.assertTrue(eligibility(self.c,self.account,allow_fixture=True)['eligible'])
    def test_unknown_rights_country_and_expiry(self):
        self.c['fields']['usage_rights']['status']='unconfirmed'
        self.assertFalse(eligibility(self.c,self.account,allow_fixture=True)['eligible'])
        self.c=campaign_fixture();self.account['country']='ZZ'
        self.assertFalse(eligibility(self.c,self.account,allow_fixture=True)['eligible'])
        self.account['country']='US'
        self.c['fields']['deadline']['value']=(now()-timedelta(seconds=1)).isoformat()
        self.assertFalse(eligibility(self.c,self.account,allow_fixture=True)['eligible'])
    def test_stale_evidence(self):
        self.assertFalse(eligibility(self.c,self.account,now()+timedelta(days=2),True)['eligible'])
    def test_explicit_missing_field(self):
        del self.c['fields']['payment_timing']
        with self.assertRaises(ValueError):validate(self.c)
    def test_financial_math_caps_fees_probability(self):
        f=forecast(self.c,assumptions())
        base=f['scenarios']['base']
        self.assertEqual(base['forecast_gross_usd'],8)
        self.assertEqual(base['risk_adjusted_net_usd'],4.32)
        self.assertEqual(base['estimated_collectible_usd'],0)
        self.assertEqual(base['estimated_contribution_usd'],1.72)
        self.assertEqual(f['scenarios']['best']['forecast_gross_usd'],48)
        self.assertIsNone(f['cash_received_usd'])
    def test_budget_cap(self):
        self.c['fields']['remaining_budget']['value']=1
        self.assertEqual(forecast(self.c,assumptions())['scenarios']['best']['forecast_gross_usd'],1)
    def test_nan_negative_unknown_terms(self):
        for v in (float('nan'),-2,True):
            a=assumptions();a['base']['views']=v
            with self.assertRaises(ValueError):forecast(self.c,a)
        self.c['fields']['fee_fraction']['status']='unconfirmed'
        with self.assertRaises(ValueError):forecast(self.c,assumptions())

class Vendor(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        self.srt=self.root/'input.srt'
        self.srt.write_text('\n\n'.join(f'{i+1}\n00:00:{i*6:02},000 --> 00:00:{i*6+5:02},000\nCan you finish 1 small step?' for i in range(9)))
    def tearDown(self):self.t.cleanup()
    def test_integrity_and_hook(self):
        self.assertEqual(skills.verify_vendor(),'a2feb2104981a375ffd4f87ee04f4f5344ac43c6')
        self.assertIn('verdict',skills.hook('Can you finish 1 small step?')[0])
    def test_packaging(self):
        self.assertIn('score',skills.package('3 small steps','START HERE')[0])
    def test_edit_and_chapters(self):
        r=skills.edit(self.srt)
        self.assertGreaterEqual(r['out'],0)
        c=skills.run('chapters',self.srt)
        self.assertTrue(c['valid'])
        self.assertGreaterEqual(len(c['chapters']),3)
    def test_retention_percent_fixture(self):
        p=self.root/'retention.csv';p.write_text('percent,watching\n'+''.join(f'{i*10},{100-i*5}\n' for i in range(11)))
        r=skills.run('retention',p,'--duration','200')
        self.assertEqual(r['points'],11)
        self.assertEqual(r['hook_leak'],5)
    def test_outliers(self):
        p=self.root/'views.json'
        write(p,[{'channel':'synthetic','title':'3 small steps','views':v} for v in (100,100,100,1000)])
        r=skills.run('outliers',p)
        self.assertEqual(r['outliers'][0]['multiple'],10)
    def test_json_list_parser_quarantined(self):
        with self.assertRaises(ValueError):skills.edit(self.root/'unsupported.json')

class State(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory()
        cls.original=Path(cls.shared.name)/'original'
        spec=read(Path(__file__).resolve().parents[1]/'examples/original.json')
        render(spec,cls.original,fixture=True)
    @classmethod
    def tearDownClass(cls):cls.shared.cleanup()
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        self.store=Store(self.root/'db.sqlite')
        self.c=campaign_fixture();self.imported=self.store.import_campaign(self.c)
        self.asset=self.root/'asset';shutil.copytree(self.original,self.asset)
        write(self.asset/'context.json',{'campaign_id':self.imported['id'],'fingerprint':self.imported['fingerprint']})
        write(self.asset/'manifest.json',manifest(self.asset))
        self.key=self.store.register(self.asset,self.imported['id'])
        self.owner={'id':'test-owner','role':'OWNER','minor':False}
    def tearDown(self):self.t.cleanup()
    def approve(self):self.store.decide(self.key,'approved',self.owner)
    def test_import_dedup_and_material_revision(self):
        self.assertEqual(self.store.import_campaign(self.c)['event'],'unchanged')
        self.c['fields']['remaining_budget']['value']=90
        self.assertEqual(self.store.import_campaign(self.c)['event'],'terms_changed')
    def test_pending_blocks(self):
        with self.assertRaises(ValueError):self.store.enqueue_mock(self.key)
    def test_roles_and_minors(self):
        for p in [{'id':'child','role':'APPROVER','minor':True},{'id':'editor','role':'EDITOR'}]:
            with self.assertRaises(PermissionError):self.store.decide(self.key,'approved',p)
    def test_job_once_only(self):
        self.approve();a=self.store.enqueue_mock(self.key);b=self.store.enqueue_mock(self.key)
        self.assertEqual(a,b)
        adapter=YouTubeMock()
        r=self.store.work_mock(adapter)
        self.assertFalse(r['publicly_published'])
        self.assertIsNone(self.store.work_mock(adapter))
        self.assertEqual(len(adapter.calls),1)
    def test_global_duplicate_prevention(self):
        self.approve();job=self.store.enqueue_mock(self.key)
        p=self.root/'copy';shutil.copytree(self.asset,p)
        other=self.store.register(p,self.imported['id']);self.store.decide(other,'approved',self.owner)
        self.assertEqual(job,self.store.enqueue_mock(other))
    def test_changes_after_approval_and_queue(self):
        self.approve();self.store.enqueue_mock(self.key)
        (self.asset/'metadata.json').write_text('{}')
        self.assertIsNone(self.store.work_mock(YouTubeMock()))
        self.assertEqual(self.store.dashboard()['jobs'][0]['state'],'blocked')
    def test_changed_terms_and_rejected_decision(self):
        self.approve();self.store.decide(self.key,'rejected',self.owner)
        with self.assertRaises(ValueError):self.store.enqueue_mock(self.key)
        self.approve();self.c['fields']['fee_fraction']['value']=.2;self.store.import_campaign(self.c)
        with self.assertRaises(ValueError):self.store.enqueue_mock(self.key)
    def test_live_adapter_blocked(self):
        with self.assertRaises(ValueError):self.store.work_mock(LivePlatform('youtube'))
    def test_mock_platforms(self):
        m=read(self.asset/'metadata.json')
        for adapter in (InstagramMock(),TikTokMock()):
            m['destination']['platform']=adapter.platform
            self.assertEqual(adapter.upload(self.asset/'video.mp4',m,'test')['mode'],'mock')
    def test_cost_limit(self):
        self.approve();self.store.enqueue_mock(self.key)
        a=YouTubeMock();a.cost_usd=1
        with self.assertRaises(ValueError):self.store.work_mock(a,0)
    def test_retry_revalidates_approval(self):
        class TimeoutMock(YouTubeMock):
            def upload(self,*a):raise TimeoutError()
        self.approve();self.store.enqueue_mock(self.key)
        with self.assertRaises(TimeoutError):self.store.work_mock(TimeoutMock())
        with self.store.tx() as c:c.execute("UPDATE jobs SET due='2000-01-01'")
        self.store.decide(self.key,'changes_requested',self.owner)
        self.assertIsNone(self.store.work_mock(YouTubeMock()))
        self.assertEqual(self.store.dashboard()['jobs'][0]['state'],'blocked')
    def test_daily_dedup_and_schedule(self):
        inbox=self.root/'inbox';inbox.mkdir();write(inbox/'campaign.json',self.c)
        r=scheduled_daily(self.store,inbox)
        self.assertEqual(r['events'][0]['event'],'unchanged')
        self.assertEqual(scheduled_daily(self.store,inbox)['state'],'already_claimed')
    def test_dashboard_no_invented_metrics(self):
        self.assertEqual(self.store.dashboard()['metrics'],[])
        self.assertEqual(self.store.dashboard()['finances'],[])
    def test_http_review_csrf_roles_and_preview(self):
        credential=secrets.token_urlsafe(32)
        srv=server(self.store,[dict(self.owner,credential=credential)])
        th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
        base=f'http://127.0.0.1:{srv.server_port}'
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def req(path,body=None,headers=None):
            data=json.dumps(body).encode() if body is not None else None
            return opener.open(urllib.request.Request(base+path,data=data,headers=headers or {}),timeout=10)
        try:
            with self.assertRaises(urllib.error.HTTPError):req('/api/dashboard')
            with req('/session',{'credential':credential}) as r:self.assertEqual(r.status,200)
            with req('/api/dashboard') as r:data=json.load(r)
            with req('/media/'+self.key) as r:self.assertTrue(r.headers['Content-Type'].startswith('video/mp4'))
            body={'asset':self.key,'decision':'approved','expected_sha':manifest(self.asset)['sha256']}
            with self.assertRaises(urllib.error.HTTPError):req('/api/decision',body)
            with req('/api/decision',body,{'X-CSRF':data['csrf']}) as r:self.assertFalse(json.load(r)['uploaded'])
            self.assertTrue(self.store.enqueue_mock(self.key))
            with self.assertRaises(urllib.error.HTTPError):req('/api/dashboard',headers={'Origin':'https://attacker.invalid'})
        finally:srv.shutdown();srv.server_close();th.join()

class Ranking(unittest.TestCase):
    def test_fixtures_not_ranked_as_real_opportunities(self):
        from beyond_orbit.campaigns import rank_opportunities
        r=rank_opportunities([campaign_fixture()],{'followers':0,'country':'US','platform':'youtube'}, {})
        self.assertEqual(r['ranked'],[])
        self.assertEqual(len(r['blocked']),1)
    def test_assumptions_and_relevance_change_rank(self):
        from beyond_orbit.campaigns import rank_opportunities,identity
        # Synthetic test data only, never imported into the real demo DB.
        c=campaign_fixture();c['fixture']=False;c['fields']['active']['value']=True
        c['restrictions']={'min_account_age_days':0,'min_age_years':18}
        c['manual_terms_review']={'complete':True,'reviewer':'TEST','checked_at':now().isoformat()}
        r=rank_opportunities([c],{'followers':0,'country':'US','platform':'youtube','account_age_days':1,'age_years':30},{identity(c):assumptions()})
        self.assertEqual(len(r['ranked']),1)
        a=assumptions();a['base']['audience_relevance']=0
        self.assertLess(forecast(c,a)['scenarios']['base']['estimated_contribution_usd'],0)
