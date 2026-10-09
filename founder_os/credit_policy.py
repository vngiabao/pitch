"""Credits are restricted benefits, not cash; unknown conditions are visible."""
BENEFIT_KEYS=('provider','category','tier','referral_required','company_email_required',
 'paid_account_required','deposit_required','minimum_spend','expiration_months',
 'eligible_products','excluded_products','renewal_behavior','stacking_restrictions',
 'terms_url','terms_acceptance_required')

def credits_report(data):
    b=data.get('credit_benefits',{});f=data['funding']
    amount=f.get('credits_value');usable=f.get('estimated_usable_credits')
    fee=f.get('application_fee');deposit=b.get('deposit_required');spend=b.get('minimum_spend')
    known_cost=fee is not None and deposit is not None and spend is not None and b.get('paid_account_required') is not None
    free=known_cost and fee==0 and deposit is False and spend==0 and b['paid_account_required'] is False
    cost='Free to apply; no required payment verified' if free else 'Payment / account conditions need review' if not known_cost else 'Required payment or paid account'
    return {'advertised_value':amount,'estimated_usable_value':usable,'kind':'credits' if amount is not None else 'other',
      'cost_status':cost,'free_verified':free,'benefits':b,
      'value_note':'Restricted credits are not cash. Usable value needs a current spend plan; provider headline awards are not guaranteed.'}
