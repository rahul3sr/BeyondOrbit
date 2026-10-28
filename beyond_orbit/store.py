"""Transactional local state. This is a single-host SQLite deployment."""
from contextlib import contextmanager
from datetime import timedelta
import json
import hashlib
from pathlib import Path
import sqlite3
import uuid
from .campaigns import validate, identity, fingerprint, now
from .engine import manifest, read

ROLES={'OWNER':{'read','create','approve','analytics'},'CREATOR':{'read','create'},
       'EDITOR':{'read','create'},'APPROVER':{'read','approve'},'ANALYST':{'read','analytics'}}


def authorize(principal, capability):
    if capability not in ROLES.get(principal.get('role'),set()): raise PermissionError('Role denied')
    if principal.get('minor') and capability=='approve': raise PermissionError('Adult approval required')
    if not principal.get('id'): raise PermissionError('Individual identity required')


class Store:
    def __init__(self,path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY, fingerprint TEXT, data TEXT, seen_at TEXT);
            CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY, campaign TEXT, event TEXT, fingerprint TEXT, at TEXT);
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,path TEXT UNIQUE,sha TEXT,campaign TEXT,terms TEXT,state TEXT);
            CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY,asset TEXT,sha TEXT,terms TEXT,decision TEXT,reviewer TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,asset TEXT,sha TEXT,mode TEXT,state TEXT,attempts INTEGER DEFAULT 0,
                due TEXT,error TEXT,result TEXT,upload_key TEXT UNIQUE,UNIQUE(asset,sha,mode));
            CREATE TABLE IF NOT EXISTS finances(id INTEGER PRIMARY KEY,kind TEXT,amount REAL,asset TEXT,note TEXT,at TEXT);
            CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY,platform TEXT,video TEXT,name TEXT,value REAL,source TEXT,at TEXT);
            ''')

    def connect(self):
        c=sqlite3.connect(self.path,timeout=20)
        c.row_factory=sqlite3.Row
        return c

    @contextmanager
    def tx(self):
        c=self.connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except BaseException:
            c.rollback();raise
        finally:c.close()

    def import_campaign(self,data):
        validate(data)
        key=identity(data);fp=fingerprint(data);stamp=now().isoformat()
        with self.tx() as c:
            old=c.execute('SELECT fingerprint FROM campaigns WHERE id=?',(key,)).fetchone()
            event='new' if old is None else ('unchanged' if old[0]==fp else 'terms_changed')
            c.execute('INSERT OR REPLACE INTO campaigns VALUES(?,?,?,?)',(key,fp,json.dumps(data),stamp))
            if event!='unchanged': c.execute('INSERT INTO revisions(campaign,event,fingerprint,at) VALUES(?,?,?,?)',(key,event,fp,stamp))
        return {'id':key,'event':event,'fingerprint':fp}

    def register(self,path,campaign=None):
        path=Path(path).resolve()
        if manifest(path)!=read(path/'manifest.json'): raise ValueError('Invalid artifact manifest')
        if not read(path/'report.json')['qc']['passed']: raise ValueError('QC failed')
        sha=manifest(path)['sha256'];key=uuid.uuid4().hex
        with self.tx() as c:
            terms=None
            if campaign:
                row=c.execute('SELECT fingerprint FROM campaigns WHERE id=?',(campaign,)).fetchone()
                if row is None:raise ValueError('Unknown campaign')
                terms=row[0]
            c.execute('INSERT INTO assets VALUES(?,?,?,?,?,?)',(key,str(path),sha,campaign,terms,'pending'))
        return key

    def _current(self,c,key):
        a=c.execute('SELECT * FROM assets WHERE id=?',(key,)).fetchone()
        if not a:raise ValueError('Unknown asset')
        m=manifest(a['path'])
        if m!=read(Path(a['path'])/'manifest.json') or m['sha256']!=a['sha']:
            raise ValueError('Asset changed: register a new version and reapprove')
        if a['campaign']:
            row=c.execute('SELECT fingerprint FROM campaigns WHERE id=?',(a['campaign'],)).fetchone()
            if not row or row[0]!=a['terms']:raise ValueError('Campaign terms changed: re-review required')
        return a

    def decide(self,key,decision,principal):
        authorize(principal,'approve')
        if decision not in {'approved','rejected','changes_requested'}:raise ValueError('Unknown decision')
        with self.tx() as c:
            a=self._current(c,key)
            c.execute('INSERT INTO approvals(asset,sha,terms,decision,reviewer,at) VALUES(?,?,?,?,?,?)',
                      (key,a['sha'],a['terms'],decision,principal['id'],now().isoformat()))
            c.execute('UPDATE assets SET state=? WHERE id=?',(decision,key))

    def enqueue_mock(self,key):
        # No production/live mode accepted anywhere in this queue.
        with self.tx() as c:
            a=self._current(c,key)
            self._approved(c,a)
            job=uuid.uuid4().hex
            m=manifest(a['path'])
            upload_key=hashlib.sha256((m['files']['video.mp4']+m['files']['metadata.json']+'mock').encode()).hexdigest()
            c.execute('INSERT OR IGNORE INTO jobs(id,asset,sha,mode,state,due,upload_key) VALUES(?,?,?,?,?,?,?)',
                      (job,key,a['sha'],'mock','queued',now().isoformat(),upload_key))
            return c.execute('SELECT id FROM jobs WHERE upload_key=?',(upload_key,)).fetchone()[0]

    def _approved(self,c,a):
        row=c.execute('SELECT * FROM approvals WHERE asset=? ORDER BY id DESC LIMIT 1',(a['id'],)).fetchone()
        if not row or row['decision']!='approved' or row['sha']!=a['sha'] or row['terms']!=a['terms']:
            raise ValueError('Exact-version human approval required')

    def work_mock(self,adapter,max_cost_usd=0):
        # Take an atomic claim, then revalidate before the side effect. Crashed in-flight jobs
        # stay running/uncertain for reconciliation, never automatically re-upload.
        from .campaigns import number
        number(max_cost_usd)
        if getattr(adapter,'mode',None)!='mock':raise ValueError('Only mock adapters are enabled')
        with self.tx() as c:
            j=c.execute("SELECT * FROM jobs WHERE state IN ('queued','retry') AND due<=? ORDER BY due LIMIT 1",(now().isoformat(),)).fetchone()
            if not j:return None
            a=self._current(c,j['asset']);self._approved(c,a)
            if adapter.cost_usd>max_cost_usd:raise ValueError('Cost limit exceeded')
            c.execute("UPDATE jobs SET state='running',attempts=attempts+1 WHERE id=?",(j['id'],))
        try:
            # Check again immediately before invoking the mock. No live adapter can enter.
            with self.tx() as c:
                a=self._current(c,j['asset']);self._approved(c,a)
                result=adapter.upload(Path(a['path'])/'video.mp4',read(Path(a['path'])/'metadata.json'),j['id'])
                c.execute("UPDATE jobs SET state='succeeded',result=? WHERE id=?",(json.dumps(result),j['id']))
                c.execute('INSERT INTO finances(kind,amount,asset,note,at) VALUES(?,?,?,?,?)',
                          ('production_expense',adapter.cost_usd,a['id'],'mock upload cost',now().isoformat()))
        except Exception as e:
            attempts=j['attempts']+1
            safe_retry=isinstance(e,TimeoutError) and adapter.mode=='mock' and attempts<3
            with self.tx() as c:
                c.execute('UPDATE jobs SET state=?,due=?,error=? WHERE id=?',
                          ('retry' if safe_retry else 'failed',(now()+timedelta(seconds=2**attempts)).isoformat(),type(e).__name__,j['id']))
            raise
        return result

    def dashboard(self):
        with self.connect() as c:
            rows=lambda table:[dict(r) for r in c.execute('SELECT * FROM '+table)]
            return {'campaigns':rows('campaigns'),'assets':rows('assets'),'jobs':rows('jobs'),
                    'approvals':rows('approvals'),'finances':rows('finances'),'metrics':rows('metrics'),
                    'unavailable':['views','retention','subscribers','revenue until verified imports or official API authorization'],
                    'runtime':'local SQLite; no hosted scheduler or live publishing'}
