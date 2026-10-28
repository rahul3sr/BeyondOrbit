"""Verified imports only. Forecasts never flow into the financial ledger."""
from .campaigns import number,when,now

KINDS={'accrued_revenue','cash_received','platform_fee','production_expense','external_api_expense','infrastructure_expense'}
METRICS={'views','watch_time_minutes','retention_percent','subscribers_gained','engagements','qualifying_views','published_videos','submissions','approved_submissions','rejections'}


def import_evidence(store,data):
    if data.get('status')!='verified' or data.get('fixture') is not False:
        raise ValueError('Real verified evidence required; no fixture metrics in live reporting')
    if not data.get('source_url','').startswith('https://') or not data.get('evidence_id'):
        raise ValueError('Source and unique evidence ID required')
    if when(data['checked_at'])>now():raise ValueError('Future verification timestamp')
    value=number(data['value'])
    with store.tx() as c:
        c.execute('CREATE TABLE IF NOT EXISTS evidence_imports(id TEXT PRIMARY KEY,source TEXT,at TEXT)')
        if c.execute('SELECT 1 FROM evidence_imports WHERE id=?',(data['evidence_id'],)).fetchone():return 'duplicate'
        if data['type']=='financial':
            if data['kind'] not in KINDS or data.get('currency')!='USD':raise ValueError('Unsupported financial entry')
            c.execute('INSERT INTO finances(kind,amount,asset,note,at) VALUES(?,?,?,?,?)',
                      (data['kind'],value,data.get('asset'),data['source_url'],data['checked_at']))
        elif data['type']=='metric':
            if data['name'] not in METRICS:raise ValueError('Unsupported metric')
            if data['name']=='retention_percent' and value>100:raise ValueError('Retention out of range')
            c.execute('INSERT INTO metrics(platform,video,name,value,source,at) VALUES(?,?,?,?,?,?)',
                      (data['platform'],data['video'],data['name'],value,data['source_url'],data['checked_at']))
        else:raise ValueError('Unknown evidence type')
        c.execute('INSERT INTO evidence_imports VALUES(?,?,?)',(data['evidence_id'],data['source_url'],data['checked_at']))
    return 'imported'


def summarize(data):
    financial={}
    for kind in KINDS:
        values=[r['amount'] for r in data['finances'] if r['kind']==kind]
        financial[kind+'_usd']=round(sum(values),2) if values else None
    # Do not mix cash received and accrued revenue; one may settle the other.
    revenue=financial['accrued_revenue_usd']
    expense=[financial[k+'_usd'] for k in KINDS if k not in {'cash_received','accrued_revenue'}]
    financial['contribution_usd']=round(revenue-sum(expense),2) if revenue is not None and all(v is not None for v in expense) else None
    return {'financials':financial,'campaigns_discovered':len(data['campaigns']),
            'videos_produced':len(data['assets']),'fixture_campaigns':sum(1 for c in data['campaigns'] if __import__('json').loads(c['data'])['fixture']),
            'published_videos':None,'channel_metrics':data['metrics'],
            'optimization':'Insufficient verified performance data; no experiment recommendation supported yet'}
