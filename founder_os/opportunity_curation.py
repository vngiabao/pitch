"""Founder decision briefs and a bounded shortlist, shared by hunter and reports.

Editorial priorities never assign fit points or assert company eligibility.
Only current, sourced briefs can enter the daily shortlist.
"""
from datetime import datetime, timezone

BRIEF_KEYS = {'why_applicable', 'how_it_helps', 'application_angle',
              'agent_next_step', 'owner_decisions', 'company_fact_keys',
              'source_urls', 'priority', 'basis'}
PRIORITIES = {'CORE_PRODUCT': 3, 'COST_SAVINGS': 2, 'EXPLORATORY': 1, 'UNKNOWN': 0}


def validate_brief(brief, data, facts, clean_url):
    if brief is None:
        return
    if not isinstance(brief, dict) or set(brief) != BRIEF_KEYS:
        raise ValueError('Founder brief must contain all defined fields')
    for key in ('why_applicable', 'how_it_helps', 'application_angle', 'agent_next_step'):
        if not isinstance(brief[key], str) or not 1 <= len(brief[key].strip()) <= 800:
            raise ValueError('Founder brief requires concise ' + key)
    if brief['priority'] not in PRIORITIES or brief['basis'] not in ('approved_memory', 'conditional', 'unknown'):
        raise ValueError('Invalid founder brief priority or basis')
    for key in ('owner_decisions', 'company_fact_keys', 'source_urls'):
        if not isinstance(brief[key], list) or len(brief[key]) > 12 or any(not isinstance(v, str) or not v.strip() or len(v) > 800 for v in brief[key]):
            raise ValueError('Invalid founder brief ' + key)
    from .hunter_policy import FACT_KEYS
    if set(brief['company_fact_keys']) - FACT_KEYS:
        raise ValueError('Unknown company fact in founder brief')
    if brief['basis'] == 'approved_memory' and (not brief['company_fact_keys'] or any(k not in facts for k in brief['company_fact_keys'])):
        raise ValueError('Approved-memory brief requires current canonical facts')
    official = {clean_url(s['url']) for s in data['sources'] if s['role'] in ('official_program', 'official_organizer', 'official_announcement') and (datetime.now(timezone.utc)-datetime.fromisoformat(s['checked_at'].replace('Z','+00:00'))).total_seconds() <= 30*86400}
    if not brief['source_urls'] or any(clean_url(u) not in official for u in brief['source_urls']):
        raise ValueError('Founder brief needs checked official source URLs')


def assessed_brief(data, facts):
    brief = data.get('founder_brief')
    if not brief:
        return None
    missing = [k for k in brief['company_fact_keys'] if k not in facts]
    return {**brief, 'basis': 'unknown' if missing else brief['basis'],
            'missing_company_facts': missing,
            'company_fact_versions': {k: facts[k]['claim_version_id'] for k in brief['company_fact_keys'] if k in facts},
            'eligibility_note': 'This is a strategic assessment, not proof of eligibility.'}


def shortlist(items, limit=5, instant=None):
    instant = instant or datetime.now(timezone.utc)
    limit = max(1, min(5, int(limit)))
    eligible = []
    for d in items:
        b = d['analysis'].get('founder_brief')
        if not b or b['priority'] == 'UNKNOWN' or b['basis'] == 'unknown':
            continue
        if d['recommendation'] in ('SKIP', 'EXPIRED', 'REJECTED', 'ACCEPTED', 'ALREADY APPLIED') or d['analysis']['eligibility']['status'] == 'INELIGIBLE' or d.get('superseded_by'):
            continue
        if d['decisions'] and d['decisions'][0]['decision'] == 'SKIP':
            continue
        if not d['last_verified'] or (instant - datetime.fromisoformat(d['last_verified'].replace('Z', '+00:00'))).total_seconds() > 30 * 86400:
            continue
        if d['verification_state'] != 'VERIFIED' or d['data']['status'] not in ('OPEN', 'UPCOMING'):
            continue
        cited = set(b['source_urls'])
        fresh = {s['url'] for s in d['data']['sources'] if (instant-datetime.fromisoformat(s['checked_at'].replace('Z','+00:00'))).total_seconds() <= 30*86400}
        if not cited <= fresh:
            continue
        if d['fit_score'] is not None and d['fit_score'] < 70:
            continue
        eligible.append(d)

    def order(d):
        b = d['analysis']['founder_brief']
        days = d['analysis']['scoring']['dates']['days_remaining']
        action = d['recommendation'] in ('APPLY NOW', 'PREPARE') and d['analysis']['eligibility']['status'] == 'ELIGIBLE'
        hours = d['analysis']['materials']['estimated_hours']
        money = (d['analysis'].get('money') or {}).get('rank', 0)
        # A closing deadline and real cash outrank editorial product relevance.
        return (int(action), int(days is not None and 0 <= days <= 21), money,
                d['fit_score'] if d['fit_score'] is not None else -1,
                PRIORITIES[b['priority']], int(b['basis'] == 'approved_memory'),
                -(hours if hours is not None else 1000), d['last_verified'], d['opportunity_id'])

    # One underlying program per email; real future annual cycles stay in the DB.
    selected = []; seen = set()
    for d in sorted(eligible, key=order, reverse=True):
        if d['program_id'] in seen:
            continue
        seen.add(d['program_id']); selected.append(d)
        if len(selected) == limit:
            break
    return selected
