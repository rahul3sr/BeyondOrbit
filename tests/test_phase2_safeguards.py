"""Pure/unit and mock-transport release-gate tests. No real upload occurs."""
import copy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from beyond_orbit.approval import Authenticator,PublicationGate,Principal
from beyond_orbit.campaigns import eligibility,forecast,now,validate,fingerprint,identity
from beyond_orbit.operations import campaign_fixture,assumptions
from beyond_orbit.engine import write,manifest,digest,render
from beyond_orbit.store import Store,UploadUncertain
from integrations.social import YouTubeMock
from integrations.youtube_protocol import RecordingTransport,YouTubeProtocol


def real_shaped_campaign():
    c=campaign_fixture();c['fixture']=False;c['fields']['active']['value']=True
    c['restrictions']={'min_account_age_days':30,'min_age_years':18}
    c['manual_terms_review']={'complete':True,'reviewer':'UNIT TEST ONLY','checked_at':now().isoformat()}
    return c


def unit_artifact(path,source_sha='source-unit-sha',destination=None):
    path.mkdir()
    (path/'video.mp4').write_bytes(b'NON-MEDIA UNIT TEST FIXTURE')
    (path/'captions.srt').write_text('unit fixture');(path/'captions.ass').write_text('unit fixture')
    (path/'rights-document.txt').write_text('Unit-test evidence, not a real campaign authorization')
    dest=destination or {'platform':'youtube','channel_id':'UC_UNIT_TEST','privacy':'private'}
    write(path/'metadata.json',{'title':'Unit fixture','description':'Unit test only','destination':dest})
    write(path/'spec.json',{'source_sha256':source_sha})
    write(path/'report.json',{'qc':{'passed':True},'fixture':'pure unit; no real-media verification claimed'})
    write(path/'manifest.json',manifest(path))
    return dest

class CampaignRepair(unittest.TestCase):
    def setUp(self):
        self.c=real_shaped_campaign();self.a={'followers':100,'country':'US','platform':'youtube','account_age_days':60,'age_years':30}
    def test_expired_and_stale_material_terms(self):
        self.c['fields']['deadline']['value']=(now()-timedelta(seconds=1)).isoformat()
        self.assertFalse(eligibility(self.c,self.a)['eligible'])
        self.c=real_shaped_campaign();self.c['fields']['fee_fraction']['checked_at']=(now()-timedelta(days=2)).isoformat()
        self.assertFalse(eligibility(self.c,self.a)['eligible'])
        with self.assertRaises(ValueError):forecast(self.c,assumptions())
    def test_age_follower_location_and_account_age(self):
        for field,value in [('followers',-1),('country','XX'),('account_age_days',0),('age_years',17)]:
            a=dict(self.a);a[field]=value
            self.assertFalse(eligibility(self.c,a)['eligible'])
    def test_unknown_rights_and_unreviewed_terms(self):
        self.c['fields']['usage_rights']['value']={'commercial_clipping':False}
        self.assertFalse(eligibility(self.c,self.a)['eligible'])
        self.c=real_shaped_campaign();self.c.pop('manual_terms_review')
        self.assertFalse(eligibility(self.c,self.a)['eligible'])
    def test_typed_countries_and_platforms(self):
        for key in ('countries','platforms'):
            c=copy.deepcopy(self.c);c['fields'][key]['value']='US'
            with self.assertRaises(ValueError):validate(c)
    def test_fixture_never_active(self):
        c=campaign_fixture();self.assertFalse(c['fields']['active']['value'])
        c['fields']['active']['value']=True
        with self.assertRaises(ValueError):validate(c)
    def test_no_slideshow_or_flite_production_fallback(self):
        with self.assertRaises(ValueError):render({},'UNUSED')
        from beyond_orbit.narration import narrate
        with self.assertRaises(ValueError):narrate([],8,Path('UNUSED'))
        from beyond_orbit.operations import demo
        with self.assertRaises(ValueError):demo('UNUSED')

class ApprovalRepair(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.credential=secrets.token_urlsafe(32)
        self.auth=Authenticator([{'id':'UNIT-OWNER','role':'OWNER','credential':self.credential}])
        self.owner=self.auth.authenticate(self.credential)
        self.gate=PublicationGate(self.root/'db.sqlite',self.root/'snapshots',self.auth)
        self.asset=self.root/'asset';self.dest=unit_artifact(self.asset)
        self.rights={'owner':'UNIT TEST','source_sha256':'source-unit-sha','document_reference':'unit fixture',
            'document_sha256':digest(self.asset/'rights-document.txt'),'verified_by':'UNIT TEST','verified_at':now().isoformat(),
            'commercial_use':True,'editing_allowed':True,'audio_reuse':True,'destinations':[self.dest],'attribution':[],'disclosures':[]}
        self.source={'sha256':'source-unit-sha','fixture':False,'rights':self.rights}
        self.proof=self.gate.attest_destination(self.owner,'UC_UNIT_TEST','unit-account','unit official-response fixture')
    def tearDown(self):self.temp.cleanup()
    def register(self):return self.gate.register(self.asset,self.source,None,{},self.dest,self.proof,self.owner)
    def approve(self,key,publish=True):self.gate.decide(key,self.owner,'approved',publish,manifest(self.asset)['sha256'])
    def test_authentication_and_forged_identity(self):
        with self.assertRaises(PermissionError):self.auth.authenticate('wrong')
        key=self.register()
        with self.assertRaises(PermissionError):self.gate.decide(key,replace(self.owner,identity='FORGED'),'approved',True,manifest(self.asset)['sha256'])
    def test_missing_explicit_authorization(self):
        key=self.register();self.approve(key,False)
        t=RecordingTransport()
        with self.assertRaises(PermissionError):self.gate.dispatch(key,t,'unit-account')
        self.assertEqual(t.calls,[])
    def test_exact_payload_and_one_time_dispatch(self):
        key=self.register();self.approve(key);t=RecordingTransport()
        self.gate.dispatch(key,t,'unit-account')
        self.assertEqual(t.calls[-1][3],(self.asset/'video.mp4').read_bytes())
        with self.assertRaises(PermissionError):self.gate.dispatch(key,t,'unit-account')
    def test_unknown_wrong_and_stale_destination(self):
        self.proof['channel_id']='UC_WRONG'
        with self.assertRaises(ValueError):self.register()
        self.proof=self.gate.attest_destination(self.owner,'UC_UNIT_TEST','unit-account','unit')
        self.proof['checked_at']=(now()-timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):self.register()
    def test_destination_evidence_must_be_authenticated(self):
        self.proof['account_subject']='FORGED'
        with self.assertRaises(ValueError):self.register()
    def test_oauth_account_must_match(self):
        key=self.register();self.approve(key);t=RecordingTransport()
        with self.assertRaises(PermissionError):self.gate.dispatch(key,t,'wrong-account')
        self.assertFalse(t.calls)
    def test_media_mutation_invalidates_dispatch(self):
        key=self.register();self.approve(key)
        with self.gate.connect() as c:row=c.execute('SELECT path FROM publication_reviews WHERE id=?',(key,)).fetchone()
        p=Path(row[0])/'video.mp4';p.chmod(0o644);p.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_metadata_mutation_invalidates_dispatch(self):
        key=self.register();self.approve(key)
        with self.gate.connect() as c:row=c.execute('SELECT path FROM publication_reviews WHERE id=?',(key,)).fetchone()
        p=Path(row[0])/'metadata.json';p.chmod(0o644);p.write_text('{}')
        with self.assertRaises(ValueError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_stale_rights_rejected(self):
        self.rights['verified_at']=(now()-timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):self.register()
    def test_mismatched_source_rejected(self):
        self.source['sha256']='WRONG'
        with self.assertRaises(ValueError):self.register()
    def test_direct_upload_paths_blocked(self):
        with self.assertRaises(PermissionError):YouTubeProtocol(RecordingTransport()).private_upload(b'',{},'unit')
        with self.assertRaises(PermissionError):YouTubeProtocol(lambda *a:{}).simulate_private_upload(b'',{},'unit')
    def test_rejected_and_changed_requests_cannot_dispatch(self):
        key=self.register();self.approve(key)
        self.gate.decide(key,self.owner,'changes_requested',False,manifest(self.asset)['sha256'])
        with self.assertRaises(PermissionError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_copied_approval_seal_cannot_authorize_other_version(self):
        key=self.register();self.approve(key)
        with self.gate.connect() as c:c.execute("UPDATE publication_reviews SET publish_authorized=0 WHERE id=?",(key,))
        with self.assertRaises(PermissionError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_expiry_revalidated_immediately_before_dispatch(self):
        from unittest.mock import patch
        c=real_shaped_campaign();c['fields']['source_footage']['value']=self.source['sha256']
        c['fields']['deadline']['value']=(now()+timedelta(seconds=1)).isoformat()
        write(self.asset/'context.json',{'campaign_id':identity(c),'fingerprint':fingerprint(c)})
        write(self.asset/'manifest.json',manifest(self.asset))
        account={'followers':100,'country':'US','platform':'youtube','account_age_days':60,'age_years':30}
        key=self.gate.register(self.asset,self.source,c,account,self.dest,self.proof,self.owner);self.approve(key)
        with patch('beyond_orbit.campaigns.now',return_value=now()+timedelta(seconds=10)):
            with self.assertRaises(ValueError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_changed_campaign_registry_blocks_dispatch(self):
        c=real_shaped_campaign();c['fields']['source_footage']['value']=self.source['sha256']
        store=Store(self.root/'db.sqlite');store.import_campaign(c)
        write(self.asset/'context.json',{'campaign_id':identity(c),'fingerprint':fingerprint(c)})
        write(self.asset/'manifest.json',manifest(self.asset))
        account={'followers':100,'country':'US','platform':'youtube','account_age_days':60,'age_years':30}
        key=self.gate.register(self.asset,self.source,c,account,self.dest,self.proof,self.owner);self.approve(key)
        c['fields']['fee_fraction']['value']=.3;store.import_campaign(c)
        with self.assertRaises(ValueError):self.gate.dispatch(key,RecordingTransport(),'unit-account')
    def test_fixture_source_denied_publication_authority(self):
        self.source['fixture']=True
        with self.assertRaises(ValueError):self.register()
    def test_minor_and_unprivileged_reviewer_blocked(self):
        users=[{'id':'child','role':'APPROVER','minor':True,'credential':secrets.token_urlsafe(32)},
               {'id':'editor','role':'EDITOR','credential':secrets.token_urlsafe(32)}]
        auth=Authenticator(users,self.auth.key)
        key=self.register()
        for u in users:
            with self.assertRaises(PermissionError):self.gate.decide(key,auth.authenticate(u['credential']),'approved',True,manifest(self.asset)['sha256'])
    def test_live_transport_remains_disabled(self):
        key=self.register();self.approve(key)
        with self.assertRaises(PermissionError):self.gate.dispatch(key,lambda *a:{},'unit-account')

class QueueRepair(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.s=Store(self.root/'db.sqlite')
        self.owner={'id':'UNIT TEST','role':'OWNER'}
        self.c=campaign_fixture();self.imported=self.s.import_campaign(self.c)
        for i in range(2):
            p=self.root/str(i);unit_artifact(p);(p/'video.mp4').write_bytes(f'UNIT {i}'.encode())
            write(p/'context.json',{'campaign_id':self.imported['id'],'fingerprint':self.imported['fingerprint']})
            write(p/'manifest.json',manifest(p))
        self.a=self.s.register(self.root/'0',self.imported['id']);self.b=self.s.register(self.root/'1')
        for a in (self.a,self.b):self.s.decide(a,'approved',self.owner);self.s.enqueue_mock(a)
    def tearDown(self):self.temp.cleanup()
    def test_invalid_first_job_does_not_starve_valid_second(self):
        self.c['fields']['fee_fraction']['value']=.2;self.s.import_campaign(self.c)
        t=YouTubeMock();self.assertIsNotNone(self.s.work_mock(t))
        self.assertEqual([j['state'] for j in self.s.dashboard()['jobs']],['blocked','completed'])
        self.assertEqual(len(t.calls),1)
    def test_uncertain_upload_never_blindly_retried(self):
        class Uncertain(YouTubeMock):
            def upload(self,*a):raise UploadUncertain()
        with self.assertRaises(UploadUncertain):self.s.work_mock(Uncertain())
        self.assertEqual(self.s.dashboard()['jobs'][0]['state'],'uncertain_upload')
        t=YouTubeMock();self.s.work_mock(t);self.assertEqual(len(t.calls),1)
        job=self.s.dashboard()['jobs'][0]['id']
        with self.assertRaises(ValueError):self.s.reconcile(job,self.owner,'retry')
        self.s.reconcile(job,self.owner,'retry',confirmed_not_uploaded=True)
    def test_wrong_campaign_binding_rejected(self):
        p=self.root/'wrong';unit_artifact(p)
        with self.assertRaises(ValueError):self.s.register(p,self.imported['id'])
