"""Loopback review UI with individual local credentials, sessions, CSRF and roles.
Not an Internet-facing identity provider; deploy only behind approved identity/TLS.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import hmac
import json
from pathlib import Path
import secrets
import time
from .engine import read
from .store import authorize

PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Beyond Orbit review desk</title><style>
body{background:#101b35;color:#eef3ff;font:17px system-ui;max-width:1000px;margin:40px auto;padding:20px}input,button{font:inherit;padding:10px;margin:5px}article{border:1px solid #55709b;padding:20px;margin:20px 0;border-radius:12px}video{width:250px;max-height:450px}pre{white-space:pre-wrap;overflow-wrap:anywhere}button{cursor:pointer}small{color:#b4c9ee}
</style><h1>Beyond Orbit review desk</h1><p>Local development · publishing disabled · estimates are not earnings</p>
<form id="login"><input id="credential" type="password" autocomplete="off" placeholder="Your individual review key" required><button>Sign in</button></form>
<p id="notice" role="status"></p><main id="desk"></main><script>
let csrf='';async function request(path,method='GET',body){let r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF':csrf},body:body?JSON.stringify(body):undefined});let data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
function node(tag,text,parent){let n=document.createElement(tag);n.textContent=text;parent.append(n);return n;}
async function load(){let d=await request('/api/dashboard');csrf=d.csrf;let desk=document.querySelector('#desk');desk.replaceChildren();document.querySelector('#login').hidden=true;
node('h2','Campaigns and operations',desk);node('pre',JSON.stringify({identity:d.identity,summary:d.summary,campaigns:d.campaigns.map(c=>({id:c.id,...JSON.parse(c.data)})),jobs:d.jobs,finances:d.finances,metrics:d.metrics,unavailable:d.unavailable},null,2),desk);
for(let a of d.assets){let card=node('article','',desk);node('h2',a.metadata.title,card);let v=document.createElement('video');v.controls=true;v.preload='metadata';v.src='/media/'+a.id;card.append(v);node('p',a.metadata.description,card);node('pre',JSON.stringify({state:a.state,version:a.sha,campaign:a.campaign,source:a.spec.source_name||'Original procedural graphics',rights:a.report.rights,compliance:a.report.compliance||'Human rights and facts review required',cost:a.report.external_api_cost_usd,target:a.metadata.destination,suggested_time:a.spec.suggested_time||'Not selected',disclosures:a.spec.campaign?.disclosures||[],qc:a.report.qc},null,2),card);
if(d.can_approve)for(let [label,decision] of [['APPROVE','approved'],['REJECT','rejected'],['REQUEST CHANGES','changes_requested']]){let b=node('button',label,card);b.onclick=async()=>{try{await request('/api/decision','POST',{asset:a.id,decision,expected_sha:a.sha});document.querySelector('#notice').textContent='Decision saved. No upload performed.';await load();}catch(e){document.querySelector('#notice').textContent=e.message;}};}}
}
document.querySelector('#login').onsubmit=async e=>{e.preventDefault();try{await request('/session','POST',{credential:document.querySelector('#credential').value});document.querySelector('#credential').value='';await load();}catch(e){document.querySelector('#notice').textContent=e.message;}};
load().catch(()=>{});
</script></html>'''


def server(store,users,port=0):
    if not users:raise ValueError('Individual user credentials must be configured')
    if any(len(u.get('credential',''))<24 for u in users):raise ValueError('Use individual random credentials of at least 24 characters')
    sessions={}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Never log login payloads or cookies.
        def send(self,status,data,ctype='application/json',headers=None):
            body=json.dumps(data).encode() if ctype=='application/json' else data
            self.send_response(status)
            self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.end_headers();self.wfile.write(body)
        def same_origin(self):
            base=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=base:raise PermissionError('Unrecognized host')
            if self.headers.get('Origin') not in {None,'http://'+base}:raise PermissionError('Cross-origin request denied')
        def identity(self):
            cookie=SimpleCookie(self.headers.get('Cookie',''))
            sid=cookie['orbit_session'].value if 'orbit_session' in cookie else ''
            session=sessions.get(sid)
            if not session or session['expires']<time.monotonic():raise PermissionError('Sign in required')
            return session
        def do_GET(self):
            try:
                self.same_origin()
                if self.path=='/':return self.send(200,PAGE.encode(),'text/html; charset=utf-8')
                session=self.identity();p=session['principal'];authorize(p,'read')
                if self.path=='/api/dashboard':
                    d=store.dashboard()
                    from .analytics import summarize
                    d['summary']=summarize(d)
                    for a in d['assets']:
                        directory=Path(a.pop('path'))
                        a['metadata']=read(directory/'metadata.json');a['report']=read(directory/'report.json');a['spec']=read(directory/'spec.json')
                    d['identity']={k:p.get(k) for k in ('id','role','minor')}
                    d['can_approve']=p['role'] in {'OWNER','APPROVER'} and not p.get('minor')
                    d['csrf']=session['csrf']
                    return self.send(200,d)
                if self.path.startswith('/media/'):
                    key=self.path.removeprefix('/media/')
                    with store.connect() as c:a=c.execute('SELECT path FROM assets WHERE id=?',(key,)).fetchone()
                    if not a:return self.send(404,{'error':'Unknown video'})
                    return self.send(200,(Path(a[0])/'video.mp4').read_bytes(),'video/mp4')
                return self.send(404,{'error':'Unknown path'})
            except (PermissionError,ValueError):return self.send(403,{'error':'Access denied'})
        def do_POST(self):
            try:
                self.same_origin()
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=8192:raise ValueError('Invalid payload size')
                data=json.loads(self.rfile.read(size))
                if self.path=='/session':
                    key=data.get('credential','')
                    principal=next((u for u in users if isinstance(key,str) and hmac.compare_digest(key,u['credential'])),None)
                    if not principal:raise PermissionError('Invalid credential')
                    sid=secrets.token_urlsafe(32)
                    sessions[sid]={'principal':{k:v for k,v in principal.items() if k!='credential'},'csrf':secrets.token_urlsafe(32),'expires':time.monotonic()+3600}
                    return self.send(200,{'signed_in':True},headers={'Set-Cookie':f'orbit_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'})
                session=self.identity()
                if not hmac.compare_digest(self.headers.get('X-CSRF',''),session['csrf']):raise PermissionError('CSRF denied')
                if self.path=='/api/decision':
                    # Bind the UI submission to the version actually displayed, not a later revision.
                    with store.connect() as c:a=c.execute('SELECT sha FROM assets WHERE id=?',(data['asset'],)).fetchone()
                    if not a or a[0]!=data.get('expected_sha'):raise ValueError('Displayed version changed')
                    store.decide(data['asset'],data['decision'],session['principal'])
                    return self.send(200,{'decision':data['decision'],'uploaded':False})
                return self.send(404,{'error':'Unknown path'})
            except PermissionError:return self.send(403,{'error':'Permission or session denied'})
            except (ValueError,KeyError,TypeError):return self.send(400,{'error':'Invalid request or changed artifact; review again'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
