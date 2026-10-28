import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit,parse_qs
from integrations.google_oauth import GoogleOAuth,save_tokens
from integrations.youtube_protocol import YouTubeProtocol

class OAuthProtocol(unittest.TestCase):
    def test_pkce_and_state_single_use(self):
        flow=GoogleOAuth('test-client','http://127.0.0.1:9000/callback')
        q=parse_qs(urlsplit(flow.authorization_url()).query)
        self.assertEqual(q['code_challenge_method'],['S256'])
        self.assertNotEqual(q['code_challenge'][0],flow.verifier)
        calls=[]
        def mock(*args):calls.append(args);return {'access_token':'synthetic-fixture-only'}
        with self.assertRaises(ValueError):flow.exchange('code','bad-state',mock)
        self.assertEqual(calls,[])
        flow.exchange('test-code',flow.state,mock)
        with self.assertRaises(ValueError):flow.exchange('test-code',flow.state,mock)
        self.assertEqual(len(calls),1)
    def test_credentials_permissions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'credentials/test.json'
            save_tokens(p,{'access_token':'synthetic-fixture-only'})
            self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):save_tokens(p,{})
    def test_private_resumable_upload_mock(self):
        calls=[]
        def mock(method,url,headers,body):
            calls.append((method,url,headers,body))
            return {'location':'https://www.googleapis.com/upload/youtube/v3/videos?upload_id=fixture'} if method=='POST' else {'id':'mock-id'}
        client=YouTubeProtocol(mock)
        m={'title':'Fixture','description':'Fixture only','destination':{'platform':'youtube','privacy':'private'}}
        self.assertEqual(client.private_upload(b'not-a-real-video',m,'synthetic-fixture-only')['id'],'mock-id')
        self.assertEqual(json.loads(calls[0][3])['status']['privacyStatus'],'private')
        m['destination']['privacy']='public'
        with self.assertRaises(ValueError):client.private_upload(b'',m,'synthetic-fixture-only')
    def test_upload_redirect_exfiltration_rejected(self):
        client=YouTubeProtocol(lambda *a:{'location':'https://attacker.invalid/session'})
        with self.assertRaises(ValueError):client.private_upload(b'',{'title':'t','description':'d','destination':{'platform':'youtube','privacy':'private'}},'synthetic-fixture-only')
    def test_analytics_mock(self):
        calls=[]
        client=YouTubeProtocol(lambda *a:calls.append(a) or {'rows':[]})
        self.assertEqual(client.analytics('synthetic-fixture-only','2026-01-01','2026-01-02'),{'rows':[]})
        self.assertTrue(calls[0][1].startswith('https://youtubeanalytics.googleapis.com/'))
