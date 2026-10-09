"""Owner-only editorial email. Inline styles are the baseline in mail clients."""
from html import escape
from urllib.parse import urlsplit
from .owner_links import public_site_enabled

TEMPLATE_VERSION='editorial-mono-v2'

def e(value):return escape(str(value),quote=True)

def link(url,label,button=False):
    if urlsplit(str(url)).scheme not in ('http','https'):return e(label)
    style=('display:inline-block;background:#171717;color:#ffffff;padding:12px 18px;text-decoration:none;font-weight:600;' if button else 'color:#171717;text-decoration:underline;')
    return '<a href="'+e(url)+'" style="'+style+'">'+e(label)+'</a>'

def paragraph(label,text):
    return '<p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:#333333;"><strong style="color:#171717;">'+e(label)+'</strong> '+e(text)+'</p>'

def render_email(day,cards,status,attached=False,sample=False):
    access_note=('Founder OS links require your owner sign-in. Keep your Windows PC awake and online.' if public_site_enabled() else 'Founder OS links open on your Windows PC. Official source links work on any device.')
    pieces=[]
    for n,c in enumerate(cards,1):
        f=c['fields'];category={'CORE_PRODUCT':'Product & experience','COST_SAVINGS':'Infrastructure & savings','EXPLORATORY':'Explore & evaluate'}.get(c['priority'],'Funding & programs')
        benefit=f['Benefit / tier'].replace('. Advertised credits are not cash or guaranteed savings.','')
        decision=f['Your decision'];none=decision.startswith('None ')
        pieces.append('''<tr><td class="pad" style="padding:30px 36px;border-bottom:1px solid #d8d8d8;">'''
            +'<h2 style="margin:0 0 12px;font-size:25px;line-height:1.25;letter-spacing:-.4px;color:#171717;">'+e(str(n).zfill(2)+'. '+c['name'])+'</h2>'
            +'<p style="margin:0 0 8px;font-size:12px;color:#595959;">'+e(category)+'</p>'
            +'<p style="margin:0 0 20px;font-size:12px;font-weight:600;color:#333333;"><span style="border:1px solid #a8a8a8;padding:4px 8px;display:inline-block;">'+e(c['recommendation'])+'</span> <span style="display:inline-block;padding:4px 0 4px 8px;">'+e('Eligibility still being verified' if 'UNKNOWN' in f['Eligibility'] else f['Eligibility'])+'</span></p>'
            +'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f2f2;margin-bottom:20px;"><tr><td style="padding:16px 18px;"><p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:.7px;color:#595959;">POTENTIAL BENEFIT</p><p style="margin:0;font-size:17px;line-height:1.5;font-weight:600;color:#171717;">'+e(benefit)+'</p><p style="margin:12px 0 0;font-size:13px;line-height:1.5;color:#333333;"><strong>Deadline:</strong> '+e(f['Deadline'])+'</p></td></tr></table>'
            +paragraph('Why it fits.',f['Why applicable'])+paragraph('What it unlocks.',f['How it helps A Story'])
            +paragraph('Requirements.',f['Requirements'])
            +(paragraph('Watch-outs.',f['Costs / catches']) if f.get('Costs / catches') else '')
            +paragraph('Preparation.',f['Effort / readiness'])
            +'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:20px 0;background:#fafafa;border:1px solid #d8d8d8;"><tr><td style="padding:16px 18px;">'
            +paragraph('Agent is handling:',f['Agent next'])
            +'<p style="margin:0;font-size:15px;line-height:1.6;color:#171717;"><strong>'+('Your action:' if not none else 'No action needed:')+'</strong> '+e(decision)+'</p></td></tr></table>'
            +'<p style="margin:0 0 16px;">'+link(c['os_url'],'Review in Founder OS',True)+'</p>'
            +'<p style="margin:0;font-size:12px;line-height:1.7;color:#595959;">Checked '+e(c['checked'])+' &nbsp; / &nbsp; '+ ' &nbsp; '.join(link(u,'Official source'+(' '+str(i+1) if len(c['sources'])>1 else '')) for i,u in enumerate(c['sources']))+'</p>'
            +'</td></tr>')
    intro=('These are the '+str(len(cards))+' most useful opportunities in the latest saved research. '+str(sum(c['recommendation']=='REVIEW' for c in cards))+' need further review before applying.' if cards else 'No opportunities meet today\'s research and relevance checks. The agent will keep researching.')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A Story opportunity brief</title><style>@media only screen and (max-width:600px){.pad{padding-left:22px!important;padding-right:22px!important}.headline{font-size:32px!important}.outer{padding:0!important}}</style></head><body style="margin:0;padding:0;background:#eeeeee;font-family:'Segoe UI',Arial,sans-serif;color:#171717;">
<div style="display:none;max-height:0;overflow:hidden;">Your opportunity shortlist, practical benefits, and next decisions. No applications submitted.</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td class="outer" align="center" style="padding:32px 12px;"><table role="presentation" width="680" cellspacing="0" cellpadding="0" style="width:100%;max-width:680px;background:#ffffff;">
<tr><td class="pad" style="padding:28px 36px;background:#171717;color:#ffffff;"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="font-size:22px;font-weight:600;letter-spacing:-.5px;">A Story</td><td align="right" style="font-size:12px;color:#d6d6d6;">'''+e(day)+'''</td></tr></table></td></tr>
<tr><td class="pad" style="padding:36px;border-bottom:1px solid #d8d8d8;"><h1 class="headline" style="margin:0 0 18px;font-size:40px;line-height:1.1;letter-spacing:-1.2px;">Opportunities worth<br>your time.</h1><p style="margin:0 0 22px;font-size:16px;line-height:1.6;color:#454545;">'''+e(intro)+'''</p><p style="margin:0;font-size:13px;line-height:1.6;border-top:2px solid #171717;padding-top:16px;">'''+('DESIGN SAMPLE &nbsp; / &nbsp; ' if sample else '')+'''<strong>Review first. Submit only after your approval.</strong><br>Credit allowances are not cash or guaranteed savings. Unverified eligibility stays visible.</p></td></tr>
'''+''.join(pieces)+'''<tr><td class="pad" style="padding:28px 36px;background:#f5f5f5;"><h2 style="margin:0 0 12px;font-size:20px;line-height:1.3;">Behind the brief</h2><p style="margin:0 0 16px;font-size:13px;line-height:1.7;color:#454545;">'''+e(status)+'''</p>'''+(paragraph('Attached for review.', 'Your private text file contains application questions, saved answers, blank fields, blockers, and essay drafts. Unfinished work is marked; it is not a submission approval.') if attached else '')+'''<p style="margin:18px 0 0;font-size:12px;line-height:1.7;color:#595959;">'''+e(access_note)+'''<br>Prepared for Bao Vo. No application is sent by approving or reading this report.</p></td></tr></table></td></tr></table></body></html>'''
