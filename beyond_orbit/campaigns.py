"""Evidence-labelled manual imports; forecasts are never earned cash."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from urllib.parse import urlsplit

FIELDS = ('active','owner','rate_per_1000','currency','payment_model','eligibility',
          'min_followers','countries','platforms','deadline','remaining_budget',
          'source_footage','usage_rights','submission_conditions','payout_threshold',
          'payment_method','payment_timing','fee_fraction','max_payout','rejection_risks',
          'required_disclosures')
STATUSES = {'verified','unconfirmed','unavailable'}


def now():
    return datetime.now(timezone.utc)


def when(s):
    d = datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return d.astimezone(timezone.utc)


def number(value, minimum=0, maximum=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Finite numeric value required')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError('Numeric value out of range')
    return value


def validate(data):
    if not isinstance(data.get('fixture'),bool):
        raise ValueError('Explicit fixture boolean required')
    url=urlsplit(data['source_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password:
        raise ValueError('Direct HTTPS source URL required')
    if not data.get('external_id') or not data.get('name'):
        raise ValueError('Campaign identity required')
    if set(data['fields']) != set(FIELDS):
        raise ValueError('Every campaign field needs evidence status')
    for name,f in data['fields'].items():
        if f['status'] not in STATUSES:
            raise ValueError('Unknown evidence status')
        if f['status']=='unavailable':
            if f.get('value') is not None:
                raise ValueError('Unavailable fields must use null')
        elif f.get('value') is None or not f.get('source_url') or not f.get('checked_at'):
            raise ValueError('Evidence value, URL and verification timestamp required')
        if f.get('checked_at') and when(f['checked_at']) > now()+timedelta(minutes=5):
            raise ValueError('Evidence timestamp is in the future')
    for key in ('rate_per_1000','min_followers','remaining_budget','payout_threshold','max_payout'):
        f=data['fields'][key]
        if f['value'] is not None: number(f['value'])
    if data['fields']['fee_fraction']['value'] is not None:
        number(data['fields']['fee_fraction']['value'],0,1)
    typed={'active':bool,'countries':list,'platforms':list,'usage_rights':dict,'required_disclosures':list}
    for key,kind in typed.items():
        v=data['fields'][key]['value']
        if v is not None and not isinstance(v,kind):raise ValueError('Invalid field type: '+key)
        if kind is list and v is not None and any(not isinstance(x,str) or not x.strip() for x in v):
            raise ValueError('List entries must be nonempty strings: '+key)
    if data['fields']['deadline']['value'] is not None:when(data['fields']['deadline']['value'])
    if data['fixture'] and data['fields']['active']['value'] is True:
        raise ValueError('Synthetic campaigns must never be labelled active')
    restrictions=data.get('restrictions',{})
    for key in ('min_account_age_days','min_age_years'):
        if key in restrictions:number(restrictions[key])
    return data


def identity(data):
    return hashlib.sha256((data['source_url']+'|'+data['external_id']).encode()).hexdigest()[:24]


def fingerprint(data):
    material={'fixture':data['fixture'],'name':data['name'],'restrictions':data.get('restrictions',{}),'manual_terms_review':data.get('manual_terms_review',{}),'fields':{
        k:{'value':v['value'],'status':v['status'],'source_url':v.get('source_url')}
        for k,v in data['fields'].items()}}
    return hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest()


def eligibility(data, account, at=None, allow_fixture=False):
    validate(data)
    at=at or now()
    reasons=[]
    if not isinstance(account,dict):raise ValueError('Structured account information required')
    try:number(account.get('followers'))
    except ValueError:reasons.append('Invalid or missing follower count')
    for key in ('country','platform'):
        if not isinstance(account.get(key),str) or not account[key]:reasons.append('Invalid or missing account '+key)
    def value(key):
        f=data['fields'][key]
        if f['status']!='verified' or not f.get('checked_at') or at-when(f['checked_at'])>timedelta(days=1):
            reasons.append(key+': missing, unconfirmed or stale')
            return None
        return f['value']
    if data['fixture'] and not allow_fixture:
        reasons.append('Test fixture cannot authorize a real campaign')
    active=value('active'); followers=value('min_followers'); countries=value('countries')
    platforms=value('platforms'); deadline=value('deadline'); budget=value('remaining_budget')
    rights=value('usage_rights'); source=value('source_footage'); terms=value('submission_conditions')
    value('eligibility');value('required_disclosures')
    if active is not True and not (data['fixture'] and allow_fixture): reasons.append('Campaign is not verified active')
    if followers is not None and isinstance(account.get('followers'),(int,float)) and account['followers']<followers: reasons.append('Insufficient followers')
    if countries is not None and account.get('country') not in countries: reasons.append('Country ineligible')
    if platforms is not None and account.get('platform') not in platforms: reasons.append('Platform ineligible')
    if deadline is not None and when(deadline)<=at: reasons.append('Campaign expired')
    if budget is not None and budget<=0: reasons.append('No remaining campaign budget')
    if not isinstance(rights,dict) or rights.get('commercial_clipping') is not True:
        reasons.append('Commercial clipping permission missing')
    if not source or not terms: reasons.append('Source footage or submission terms missing')
    if not data['fixture']:
        review=data.get('manual_terms_review',{})
        if not review.get('complete') or not review.get('reviewer') or not review.get('checked_at'):
            reasons.append('Uninterpreted terms require documented manual verification')
        elif at-when(review['checked_at'])>timedelta(days=1):reasons.append('Manual terms review stale')
        restrictions=data.get('restrictions')
        if not isinstance(restrictions,dict) or not {'min_account_age_days','min_age_years'}.issubset(restrictions):
            reasons.append('Structured account-age and participant-age restrictions required')
        else:
            for limit,field in [('min_account_age_days','account_age_days'),('min_age_years','age_years')]:
                if field not in account or number(account[field])<restrictions[limit]:reasons.append('Unmet restriction: '+field)
        for key in ('rate_per_1000','currency','payment_model','fee_fraction','max_payout','payout_threshold'):
            value(key)
    return {'eligible':not reasons,'reasons':reasons,'fixture':data['fixture'],
            'requires_human_terms_review':True}


def forecast(data, assumptions):
    validate(data)
    def financial(key):
        f=data['fields'][key]
        if f['status']!='verified': raise ValueError('Unverified financial term: '+key)
        if not f.get('checked_at') or now()-when(f['checked_at'])>timedelta(days=1):raise ValueError('Stale financial term: '+key)
        return f['value']
    if financial('payment_model')!='per_1000_qualifying_views' or financial('currency')!='USD':
        raise ValueError('Only explicit USD per-1000 qualifying-view campaigns supported')
    rate=number(financial('rate_per_1000'));fee=number(financial('fee_fraction'),0,1)
    cap=number(financial('max_payout'));budget=number(financial('remaining_budget'))
    threshold=number(financial('payout_threshold'))
    results={}
    for name in ('downside','base','best'):
        s=assumptions[name]
        views=number(s['views']);q=number(s['qualifying_fraction'],0,1)
        relevance=number(s.get('audience_relevance',1),0,1)
        p=number(s['approval_probability'],0,1)
        gross=min(views*q*relevance/1000*rate,cap,budget)
        net=gross*(1-fee)
        cash=net if net>=threshold else 0
        cost=number(s['production_cost'])+number(s['minutes'])/60*number(s['hourly_cost'])
        results[name]={'forecast_gross_usd':round(gross,2),'risk_adjusted_net_usd':round(net*p,2),
                       'estimated_collectible_usd':round(cash*p,2),
                       'estimated_contribution_usd':round(net*p-cost,2),'production_cost_usd':round(cost,2)}
    return {'kind':'illustrative_forecast','fixture':data['fixture'],'scenarios':results,
            'assumptions':assumptions,'accrued_revenue_usd':None,'cash_received_usd':None,
            'caveat':'Assumptions are estimates. Shared budget and terms can change; no payment is guaranteed.'}


def rank_opportunities(campaigns,account,assumptions_by_id):
    """Rank eligible expected contribution; no fabricated missing assumptions."""
    ranked=[];blocked=[]
    for data in campaigns:
        key=identity(data)
        decision=eligibility(data,account)
        if not decision['eligible']:
            blocked.append({'id':key,'name':data['name'],'reasons':decision['reasons']});continue
        if key not in assumptions_by_id:
            blocked.append({'id':key,'name':data['name'],'reasons':['Explicit forecast assumptions unavailable']});continue
        try:
            estimate=forecast(data,assumptions_by_id[key])
        except ValueError as e:
            blocked.append({'id':key,'name':data['name'],'reasons':[str(e)]});continue
        ranked.append({'id':key,'name':data['name'],'forecast':estimate,
                       'rank_value_usd':estimate['scenarios']['base']['estimated_contribution_usd'],
                       'source_url':data['source_url'],'eligibility':decision})
    ranked.sort(key=lambda r:-r['rank_value_usd'])
    return {'ranked':ranked,'blocked':blocked,'note':'Ranking is an estimate, not an offer, earnings or legal clearance'}
