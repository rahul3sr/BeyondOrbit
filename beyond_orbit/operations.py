"""Repeatable commands for import, local scheduling, demo and review."""
import argparse
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import subprocess
import uuid
from .campaigns import FIELDS,eligibility,forecast,now
from .engine import digest,manifest,read,render,write
from .store import Store
from .video import candidates,clip


def campaign_fixture():
    url='https://example.invalid/beyond-orbit/synthetic-campaign'
    values={'active':False,'owner':'SYNTHETIC DEMO — not a marketplace offer',
        'rate_per_1000':2.0,'currency':'USD','payment_model':'per_1000_qualifying_views',
        'eligibility':'Synthetic fixture permits zero-follower adult accounts only',
        'min_followers':0,'countries':['US'],'platforms':['youtube'],
        'deadline':(now()+timedelta(days=7)).isoformat(),'remaining_budget':100,
        'source_footage':'Original Beyond Orbit generated source only',
        'usage_rights':{'commercial_clipping':True,'scope':'synthetic demo only'},
        'submission_conditions':'No external submission. Local review only.',
        'payout_threshold':10,'payment_method':'No real payments','payment_timing':'No real payments',
        'fee_fraction':.1,'max_payout':50,'rejection_risks':['Synthetic fixture; never submit'],
        'required_disclosures':['Synthetic campaign demonstration; no paid offer']}
    return {'external_id':'synthetic-001','name':'SYNTHETIC campaign fixture','fixture':True,
            'source_url':url,'fields':{k:{'value':values[k],'status':'verified','source_url':url,
            'checked_at':now().isoformat(),'verification_method':'synthetic test assertion, not live verification'} for k in FIELDS}}


def assumptions():
    return {name:{'views':views,'qualifying_fraction':.8,'approval_probability':p,
                  'production_cost':.1,'minutes':10,'hourly_cost':15,'audience_relevance':1.0}
            for name,views,p in [('downside',100,.3),('base',5000,.6),('best',30000,.8)]}


def daily(store,inbox):
    # Authorized manual imports only; no scraping or duplicate notifications.
    events=[]
    for path in sorted(Path(inbox).glob('*.json')):
        events.append(store.import_campaign(read(path)))
    return {'mode':'manual-import','events':events,'live_sources_checked':0,
            'notifications_sent':0,'at':now().isoformat()}


def scheduled_daily(store,inbox,at=None):
    at=at or now();day=at.date().isoformat()
    with store.tx() as c:
        c.execute('CREATE TABLE IF NOT EXISTS daily_runs(day TEXT PRIMARY KEY,state TEXT,at TEXT)')
        old=c.execute('SELECT state FROM daily_runs WHERE day=?',(day,)).fetchone()
        if old:return {'state':'already_claimed','day':day}
        c.execute('INSERT INTO daily_runs VALUES(?,?,?)',(day,'running',at.isoformat()))
    try:
        result=daily(store,inbox)
    except Exception:
        # Imports are idempotent. Release a failed discovery claim for a safe retry.
        with store.tx() as c:c.execute('DELETE FROM daily_runs WHERE day=?',(day,))
        raise
    with store.tx() as c:c.execute('UPDATE daily_runs SET state=? WHERE day=?',('succeeded',day))
    return result


def demo(out,*,fixture=False):
    if not fixture:raise ValueError("Demo is a technical fixture only. Use the source-first pipeline; no slideshow or robotic fallback is permitted.")
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    db=Store(out/'operations.sqlite')
    campaign=campaign_fixture();write(out/'campaign-fixture.json',campaign)
    imported=db.import_campaign(campaign)
    account={'followers':0,'country':'US','platform':'youtube'}
    estimate=forecast(campaign,assumptions())
    eligibility_result=eligibility(campaign,account,allow_fixture=True)
    spec=read(Path(__file__).resolve().parents[1]/'examples/original.json')
    spec.update(duration=48,narration=False)
    spec['rights']['audio']={'basis':'none','evidence':'Technical fixture only; no production narration'}
    render(spec,out/'original',fixture=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-stream_loop','1',
                    '-i',str(out/'original/video.mp4'),'-f','lavfi','-i','sine=frequency=440:duration=96','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',str(out/'authorized-source.mp4')],check=True,capture_output=True)
    segments=[{'start':i*8,'end':(i+1)*8,'text':spec['scenes'][i%6]} for i in range(12)]
    write(out/'source-transcript.json',{'segments':segments,'provenance':'Known timed original script; not ASR'})
    ranked=candidates(segments);write(out/'clip-candidates.json',ranked)
    chosen=ranked[0]
    destination={'platform':'youtube','channel':'@BeyondOrbitVentures','privacy':'private'}
    metadata={'title':'One small step: the 3-step creative reset','description':'Original Beyond Orbit footage. Synthetic campaign demonstration; no paid offer.',
              'destination':destination}
    context={'campaign_id':imported['id'],'fingerprint':imported['fingerprint'],'fixture':True,
             'disclosures':campaign['fields']['required_disclosures']['value'],'source_url':campaign['source_url']}
    rights={'source_sha256':digest(out/'authorized-source.mp4'),'commercial_clipping':True,
            'owner':'Beyond Orbit original demo','evidence':'Generated from original script and procedural graphics during this run',
            'audio_evidence':'Original Flite synthetic narration; no third-party audio recordings',
            'usage_scope':destination}
    report=clip(out/'authorized-source.mp4',out/'source-transcript.json',out/'campaign-clip',
                start=chosen['start'],duration=chosen['end']-chosen['start'],evidence=rights,
                metadata=metadata,campaign_context=context,campaign=campaign,account=account,allow_fixture=True)
    clip_id=db.register(out/'campaign-clip',imported['id'])
    original_id=db.register(out/'original')
    with db.tx() as c:
        c.execute('INSERT INTO finances(kind,amount,asset,note,at) VALUES(?,?,?,?,?)',
            ('external_api_expense',0,clip_id,'No external API calls. Compute unmetered; human time not measured.',now().isoformat()))
    blocked=False
    try:db.enqueue_mock(clip_id)
    except ValueError:blocked=True
    result={'fixture':True,'campaign':imported,'eligibility':eligibility_result,
            'forecast':estimate,'assets':{'campaign_clip':clip_id,'original':original_id},
            'approval_gate_blocked_upload':blocked,'qc':report['qc'],'live_integrations':[],
            'published_videos':0,'external_api_cost_usd':0,'compute_cost_usd':None,
            'automatic_transcription':False,'state':'awaiting_real_human_review'}
    write(out/'status.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    d=sub.add_parser('technical-fixture');d.add_argument('--out',required=True)
    d=sub.add_parser('import');d.add_argument('--db',required=True);d.add_argument('file')
    d=sub.add_parser('daily');d.add_argument('--db',required=True);d.add_argument('--inbox',required=True)
    d=sub.add_parser('status');d.add_argument('--db',required=True)
    d=sub.add_parser('health');d.add_argument('--db',required=True)
    d=sub.add_parser('evidence');d.add_argument('--db',required=True);d.add_argument('file')
    d=sub.add_parser('rank');d.add_argument('--db',required=True);d.add_argument('--account',required=True);d.add_argument('--assumptions',required=True)
    d=sub.add_parser('serve');d.add_argument('--db',required=True);d.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    if a.cmd=='technical-fixture':result=demo(a.out,fixture=True)
    elif a.cmd=='import':result=Store(a.db).import_campaign(read(a.file))
    elif a.cmd=='daily':result=scheduled_daily(Store(a.db),a.inbox)
    elif a.cmd=='status':
        from .analytics import summarize
        data=Store(a.db).dashboard();result={**data,'summary':summarize(data)}
    elif a.cmd=='evidence':
        from .analytics import import_evidence
        result={'state':import_evidence(Store(a.db),read(a.file))}
    elif a.cmd=='rank':
        from .campaigns import rank_opportunities
        data=Store(a.db).dashboard()
        result=rank_opportunities([json.loads(c['data']) for c in data['campaigns']],read(a.account),read(a.assumptions))
    elif a.cmd=='health':
        with Store(a.db).connect() as c:
            integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
            stuck=c.execute("SELECT count(*) FROM jobs WHERE state='running'").fetchone()[0]
        result={'database_integrity':integrity,'inflight_jobs_needing_reconciliation':stuck,'live_publishing_enabled':False,'hosted_scheduler_verified':False}
    else:
        from .review import server
        users=json.loads(os.environ.get('BEYOND_ORBIT_USERS','[]'))
        gate=None
        signing=os.environ.get('BEYOND_ORBIT_APPROVAL_KEY')
        if signing:
            if len(signing)<32:raise ValueError('Publication authority signing key must have at least 32 characters')
            from .approval import Authenticator,PublicationGate
            gate=PublicationGate(a.db,Path(a.db).parent/'immutable',Authenticator(users,signing.encode()))
        s=server(Store(a.db),users,a.port,publication_gate=gate)
        print('Local review server started; publishing disabled',flush=True)
        try:s.serve_forever()
        finally:s.server_close()
        return
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
