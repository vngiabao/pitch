"""Deterministic scoring, eligibility and dates; model output cannot assign points."""
import math
from datetime import datetime, timezone

WEIGHTS = {'eligibility':25,'strategic':20,'value':20,'probability':10,'reuse':10,'network':10,'timing':5}
SCORING_VERSION = 'a-story-fit-1'
FACT_KEYS = {'product_stage','industry','customer_type','uses_ai','location','incorporated','incorporation_date','funding_stage','funding_usd','revenue_usd','team_size','developer_count','working_website','university_affiliations','current_umich_ann_arbor_student','company_age_years','prior_finalist_mbc','previous_credits','aws_paid_account','activate_provider_id','self_funded','founder_age','university_role','founder_identity','us_company','headquarters','annual_revenue','seeking_equity','relocation_willing','business_type'}

FACT_KEYS |= {'company_name','website_url','founder_name','founder_first_name','founder_last_name','product_description','founded_year','monetized_product','targets_minors','enterprise_customer','prior_grant_application','institutional_equity_funding','building_with_claude','cloud_provider_usage','voice_provider_usage'}
FACT_KEYS |= {'founder_display_name','founder_role','cofounder_name','cofounder_role','founded_date','previous_programs'}

def date_info(deadline, timezone_name=None, checked_now=None):
    instant=checked_now or datetime.now(timezone.utc)
    if not deadline:return {'days_remaining':None,'urgency':'DEADLINE UNKNOWN','expired':False,'precision':'unknown'}
    try:
        if len(deadline)==10:
            target=datetime.fromisoformat(deadline).date()
            days=(target-instant.date()).days
            # Date-only is not an invented 23:59 deadline. Same-day remains REVIEW.
            precision='date_only';expired=days<0
        else:
            dt=datetime.fromisoformat(deadline.replace('Z','+00:00'))
            if dt.tzinfo is None or not timezone_name:raise ValueError('Timezone needed')
            days=math.ceil((dt-instant).total_seconds()/86400)
            precision='exact_time';expired=dt<instant
        return {'days_remaining':days,'urgency':'CRITICAL' if days<=3 else 'HIGH' if days<=7 else 'MEDIUM' if days<=21 else 'EARLY','expired':expired,'precision':precision}
    except ValueError:return {'days_remaining':None,'urgency':'DEADLINE UNKNOWN','expired':False,'precision':'invalid'}

def evaluate_eligibility(rules, facts, requirements_complete=False):
    checks=[]
    for rule in rules:
        key=rule['fact_key'];actual=facts.get(key)
        result=None
        if actual is not None:
            value=actual['value'];target=rule.get('value');op=rule['op']
            try:
                if op=='eq':result=value==target
                elif op=='in':result=value in target
                elif op=='contains':result=target in value
                elif op=='gte':result=isinstance(value,(int,float)) and not isinstance(value,bool) and value>=target
                elif op=='lte':result=isinstance(value,(int,float)) and not isinstance(value,bool) and value<=target
                elif op=='lt':result=isinstance(value,(int,float)) and not isinstance(value,bool) and value<target
                elif op=='present':result=bool(value)
                else:raise ValueError('Unknown eligibility operator')
            except (TypeError,ValueError):result=None
        checks.append({'requirement':rule['description'],'fact_key':key,'result':'PASS' if result is True else 'FAIL' if result is False else 'UNKNOWN','company_claim_version':actual['claim_version_id'] if actual else None,'source_url':rule['source_url']})
    if any(c['result']=='FAIL' for c in checks):status='INELIGIBLE'
    elif requirements_complete and all(c['result']=='PASS' for c in checks):status='ELIGIBLE'
    else:status='ELIGIBILITY UNKNOWN'
    missing=[c['requirement'] for c in checks if c['result']=='UNKNOWN']
    if not requirements_complete:missing.append('Complete official eligibility requirements need verification')
    return {'status':status,'checks':checks,'missing':missing,'confidence':sum(c['result']!='UNKNOWN' for c in checks)/len(checks) if checks else (1 if requirements_complete else 0)}

def score(data, eligibility, readiness, facts, checked_now=None):
    parts={}
    def part(key,points,why):parts[key]={'points':points,'weight':WEIGHTS[key],'reason':why}
    part('eligibility',25 if eligibility['status']=='ELIGIBLE' else 0 if eligibility['status']=='INELIGIBLE' else None,eligibility['status'])
    strategic_rules=data.get('strategic_matches',[])
    known=[facts.get(r['fact_key']) for r in strategic_rules]
    if strategic_rules and all(known):
        ratio=sum(k['value'] in r['accepted_values'] if isinstance(k['value'],(str,bool,int)) else any(v in k['value'] for v in r['accepted_values']) for k,r in zip(known,strategic_rules))/len(strategic_rules)
        strategic=round(20*ratio,1)
    else:strategic=None
    part('strategic',strategic,'Matches current approved company attributes to official program categories; unknown attributes remain unscored')
    funding=data['funding'];cash=funding.get('cash_prize_max');credits=funding.get('credits_value')
    if cash is not None:
        value=20 if cash>=100000 else 16 if cash>=25000 else 12 if cash>=5000 else 6 if cash>0 else 0
        if funding.get('equity_required') is True:value*=.65
        elif funding.get('equity_required') is None:value=None
    elif credits is not None:
        # Credits do not equal cash. Real usable value requires a confirmed spend plan.
        usable=funding.get('estimated_usable_credits')
        value=None if usable is None else 12 if usable>=10000 else 8 if usable>=1000 else 4 if usable>0 else 0
    else:value=None
    part('value',value,'Cash tier, with a 35% dilution penalty; credits capped at 12 and require a confirmed usable-credit estimate')
    prob=data.get('probability_estimate')
    if prob and prob.get('numerator') is not None and prob.get('denominator',0)>0:
        p=prob['numerator']/prob['denominator'];probability=round(10*min(1,max(0,p)),1)
    else:probability=None
    part('probability',probability,'Published acceptance counts only; historic rate is a base rate, not an A Story success forecast')
    pct=readiness['percentage'];hours=readiness['estimated_hours']
    reuse=None if pct is None or hours is None else round(10*(.6*pct/100+.4/(1+hours/2)),1)
    part('reuse',reuse,'60% proven ready material fraction, 40% remaining-time benefit')
    network=data.get('network_evidence',{})
    network_points=2*sum(network.get(k) is True for k in ('mentors','investors','alumni','customer_access','public_demo')) if network.get('complete') else None
    part('network',network_points,'Two points per documented mentor, investor, alumni, customer or public-demo benefit; brand prestige alone earns no points')
    dates=date_info(data['dates'].get('deadline'),data['dates'].get('timezone'),checked_now)
    if dates['expired']:timing=0
    elif data['status']=='OPEN' and data['application_url']:
        if dates['days_remaining'] is None:timing=3 if data['cycle_kind']=='rolling' else None
        elif hours is None:timing=None
        else:timing=5 if dates['days_remaining']>=max(3,math.ceil(hours/2)) else 2
    elif data['status']=='UPCOMING':timing=2
    elif data['status']=='CLOSED':timing=0
    else:timing=None
    part('timing',timing,'Actionable window compared with the disclosed effort estimate; unknown closing time prevents same-day APPLY NOW')
    low=round(sum(p['points'] or 0 for p in parts.values()),1)
    high=round(low+sum(p['weight'] for p in parts.values() if p['points'] is None),1)
    total=low if all(p['points'] is not None for p in parts.values()) else None
    return {'version':SCORING_VERSION,'components':parts,'score':total,'lower_bound':low,'upper_bound':high,'coverage':round(100-sum(p['weight'] for p in parts.values() if p['points'] is None),1),'dates':dates,'tier':'EXCEPTIONAL' if total is not None and total>=90 else 'STRONG' if total is not None and total>=80 else 'POSSIBLE' if total is not None and total>=70 else 'WEAK' if total is not None and total>=50 else 'SKIP' if total is not None else 'UNRESOLVED'}

def recommend(data, eligibility, scoring, historical=None):
    if historical in ('ACCEPTED','REJECTED','ALREADY APPLIED'):return historical
    if eligibility['status']=='INELIGIBLE':return 'SKIP'
    if scoring['dates']['expired'] or data['status']=='EXPIRED':return 'EXPIRED'
    if data['status']=='CLOSED':return 'WATCH'
    if eligibility['status']!='ELIGIBLE' or data.get('verification_state')!='VERIFIED':return 'REVIEW'
    total=scoring['score']
    if total is None:return 'REVIEW'
    if total<50:return 'SKIP'
    if total<70:return 'WATCH'
    if data['status']=='UPCOMING':return 'PREPARE'
    if data['status']=='OPEN' and data['application_url'] and not (scoring['dates']['precision']=='date_only' and scoring['dates']['days_remaining']==0):return 'APPLY NOW'
    return 'WATCH'
