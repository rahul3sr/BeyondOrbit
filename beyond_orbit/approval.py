"""Authenticated, version-bound publication authority. Live dispatch remains disabled."""
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
from .engine import manifest,read,digest
from .campaigns import eligibility,now

@dataclass(frozen=True)
class Principal:
    identity:str
    role:str
    minor:bool
    proof:str

class Authenticator:
    def __init__(self,users,key=None):
        self.key=key or secrets.token_bytes(32)
        self.users=users
        if len({u['credential'] for u in users})!=len(users):raise ValueError('Individual credentials must be unique')
        if len({u['id'] for u in users})!=len(users):raise ValueError('Individual identities must be unique')
        if any(len(u['credential'])<24 for u in users):raise ValueError('Credential too short')
    def sign(self,data):
        return hmac.new(self.key,json.dumps(data,sort_keys=True).encode(),hashlib.sha256).hexdigest()
    def authenticate(self,credential):
        user=next((u for u in self.users if hmac.compare_digest(credential,u['credential'])),None)
        if not user:raise PermissionError('Authentication failed')
        data=[user['id'],user['role'],bool(user.get('minor'))]
        return Principal(*data,self.sign(data))
    def require(self,p,roles=('OWNER','APPROVER')):
        if not isinstance(p,Principal) or not hmac.compare_digest(p.proof,self.sign([p.identity,p.role,p.minor])):
            raise PermissionError('Authenticated reviewer required')
        if p.role not in roles or p.minor:raise PermissionError('Adult authorized reviewer required')

class PublicationGate:
    def __init__(self,db,root,auth):
        self.db=str(db);self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.auth=auth
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS publication_reviews(
                id TEXT PRIMARY KEY,path TEXT,manifest TEXT,source TEXT,campaign TEXT,account TEXT,
                destination TEXT,destination_proof TEXT,decision TEXT,reviewer TEXT,publish_authorized INTEGER DEFAULT 0,seal TEXT);
                CREATE TABLE IF NOT EXISTS publication_events(id INTEGER PRIMARY KEY,review TEXT,event TEXT,at TEXT);
                CREATE UNIQUE INDEX IF NOT EXISTS one_dispatch ON publication_events(review) WHERE event='dispatch_claimed';''')
    def connect(self):
        c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row;return c
    def attest_destination(self,principal,channel_id,account_subject,evidence_reference):
        self.auth.require(principal,('OWNER',))
        if not channel_id.startswith('UC') or not account_subject or not evidence_reference:
            raise ValueError('Official channel/account evidence required')
        proof={'channel_id':channel_id,'account_subject':account_subject,'evidence_reference':evidence_reference,
               'checked_at':now().isoformat(),'method':'owner_verified_official_channel_evidence','reviewer':principal.identity}
        proof['seal']=self.auth.sign(proof)
        return proof

    def register(self,path,source,campaign,account,destination,channel_verification,principal):
        self.auth.require(principal,('OWNER',))
        if source.get('fixture') or (campaign and campaign.get('fixture')):raise ValueError('Fixtures cannot enter publication authority')
        from .production import validate_rights
        validate_rights(source['rights'],source['sha256'],destination)
        if not (Path(path)/'rights-document.txt').is_file() or digest(Path(path)/'rights-document.txt')!=source['rights']['document_sha256']:raise ValueError('Original rights document missing or mismatched')
        if manifest(path)!=read(Path(path)/'manifest.json'):raise ValueError('Artifact manifest mismatch')
        if not read(Path(path)/'report.json')['qc']['passed']:raise ValueError('Technical QA failed')
        spec=read(Path(path)/'spec.json')
        if spec.get('source_sha256')!=source['sha256']:raise ValueError('Wrong source association')
        if campaign:
            if campaign['fields']['source_footage']['value']!=source['sha256']:raise ValueError('Campaign authorizes a different source')
            from .campaigns import fingerprint,identity
            context=read(Path(path)/'context.json')
            if context.get('campaign_id')!=identity(campaign) or context.get('fingerprint')!=fingerprint(campaign):
                raise ValueError('Wrong campaign association')
            if not eligibility(campaign,account)['eligible']:raise ValueError('Campaign not eligible')
        if destination.get('platform')!='youtube' or destination.get('privacy')!='private':raise ValueError('Only reviewed private YouTube destinations are supported')
        meta=read(Path(path)/'metadata.json')
        if meta['destination']!=destination:raise ValueError('Metadata destination mismatch')
        if not channel_verification or channel_verification.get('channel_id')!=destination.get('channel_id'):
            raise ValueError('Verified destination channel required')
        from .campaigns import when
        if not 0<=(now()-when(channel_verification['checked_at'])).total_seconds()<=86400:raise ValueError('Stale destination verification')
        unsigned={k:v for k,v in channel_verification.items() if k!='seal'}
        if not hmac.compare_digest(channel_verification.get('seal',''),self.auth.sign(unsigned)):raise ValueError('Unauthenticated destination verification')
        if channel_verification.get('method')!='owner_verified_official_channel_evidence' or not channel_verification.get('account_subject'):
            raise ValueError('Official account/channel verification required')
        key=secrets.token_hex(16);target=self.root/key
        shutil.copytree(path,target,symlinks=False)
        hashes=manifest(target)
        if hashes!=read(target/'manifest.json'):raise ValueError('Snapshot changed during copy')
        for f in target.rglob('*'):
            if f.is_file():f.chmod(0o444)
        target.chmod(0o555)
        with self.connect() as c:
            c.execute('INSERT INTO publication_reviews(id,path,manifest,source,campaign,account,destination,destination_proof,decision) VALUES(?,?,?,?,?,?,?,?,?)',
                (key,str(target),hashes['sha256'],json.dumps(source),json.dumps(campaign),json.dumps(account),json.dumps(destination),json.dumps(channel_verification),'pending'))
        return key
    def _validate(self,row):
        path=Path(row['path']);m=manifest(path)
        if m!=read(path/'manifest.json') or m['sha256']!=row['manifest']:raise ValueError('Immutable snapshot changed')
        source=json.loads(row['source']);destination=json.loads(row['destination']);campaign=json.loads(row['campaign'])
        from .production import validate_rights
        validate_rights(source['rights'],source['sha256'],destination)
        if campaign and not eligibility(campaign,json.loads(row['account']))['eligible']:raise ValueError('Campaign expired or ineligible')
        # Updated campaign terms must also be checked against the campaign registry at dispatch.
        from .campaigns import identity,fingerprint,when
        if campaign:
            with self.connect() as c:
                if c.execute("SELECT 1 FROM sqlite_master WHERE name='campaigns'").fetchone():
                    current=c.execute('SELECT data FROM campaigns WHERE id=?',(identity(campaign),)).fetchone()
                    if not current or fingerprint(json.loads(current[0]))!=fingerprint(campaign):raise ValueError('Campaign terms changed')
                    if not eligibility(json.loads(current[0]),json.loads(row['account']))['eligible']:raise ValueError('Current campaign evidence stale or eligibility changed')
        proof=json.loads(row['destination_proof'])
        if not 0<=(now()-when(proof['checked_at'])).total_seconds()<=86400:raise ValueError('Destination verification expired or future-dated')
        if proof.get('channel_id')!=destination.get('channel_id'):raise ValueError('Destination differs from verified channel')
        unsigned={k:v for k,v in proof.items() if k!='seal'}
        if not hmac.compare_digest(proof.get('seal',''),self.auth.sign(unsigned)):raise ValueError('Destination verification tampered')
        return path,m
    def decide(self,key,principal,decision,publish_authorized=False,expected_manifest=None):
        self.auth.require(principal)
        if decision not in {'approved','rejected','changes_requested'}:raise ValueError('Unknown review decision')
        with self.connect() as c:
            row=c.execute('SELECT * FROM publication_reviews WHERE id=?',(key,)).fetchone()
            if not row:raise ValueError('Unknown review')
            self._validate(row)
            if expected_manifest!=row['manifest']:raise ValueError('Displayed version differs')
            payload=[key,row['manifest'],row['source'],row['campaign'],row['account'],row['destination'],row['destination_proof'],principal.identity,decision,bool(publish_authorized)]
            seal=self.auth.sign(payload)
            c.execute('UPDATE publication_reviews SET decision=?,reviewer=?,publish_authorized=?,seal=? WHERE id=?',
                (decision,principal.identity,int(publish_authorized),seal,key))
            c.execute('INSERT INTO publication_events(review,event,at) VALUES(?,?,?)',(key,decision,now().isoformat()))
    def dispatch(self,key,transport,account_subject):
        # No caller can turn on live dispatch with a CLI flag in Phase 2.
        from integrations.youtube_protocol import RecordingTransport
        if type(transport) is not RecordingTransport:raise PermissionError('Live publication is disabled; account authorization has not been connected')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM publication_reviews WHERE id=?',(key,)).fetchone()
            if not row or row['decision']!='approved' or not row['publish_authorized']:raise PermissionError('Explicit publication approval required')
            payload=[key,row['manifest'],row['source'],row['campaign'],row['account'],row['destination'],row['destination_proof'],row['reviewer'],row['decision'],bool(row['publish_authorized'])]
            if not hmac.compare_digest(row['seal'] or '',self.auth.sign(payload)):raise PermissionError('Approval integrity invalid')
            if c.execute("SELECT 1 FROM publication_events WHERE review=? AND event='dispatch_claimed'",(key,)).fetchone():raise PermissionError('Publication already claimed; reconcile instead of retrying')
            path,m=self._validate(row)
            if account_subject!=json.loads(row['destination_proof'])['account_subject']:raise PermissionError('OAuth account differs from approved destination')
            video=(path/'video.mp4').read_bytes();metadata=(path/'metadata.json').read_bytes()
            if hashlib.sha256(video).hexdigest()!=m['files']['video.mp4'] or hashlib.sha256(metadata).hexdigest()!=m['files']['metadata.json']:
                raise ValueError('Payload changed before dispatch')
            c.execute("INSERT INTO publication_events(review,event,at) VALUES(?,'dispatch_claimed',?)",(key,now().isoformat()))
            c.commit()
            from integrations.youtube_protocol import _private_upload
            return _private_upload(transport,video,json.loads(metadata),'MOCK-ONLY')
