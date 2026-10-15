"""Daily owner digest email in the gbaonvo identity: one screen, actions first, access made explicit.

Email-safe: tables, inline styles, system/serif fallback fonts, no images, no scripts, no attachments.
"""
from html import escape
from urllib.parse import urlsplit

TEMPLATE_VERSION='gbaonvo-digest-v1'
NAVY='#00274c';INK='#0d2238';PAPER='#ece5d6';SOFT='#fbf8f1';LINE='#ddd4c3';MUTED='#545f6b'
BRASS='#7a5612';MAIZE='#e8c064';URGENT='#8a2e1c';GOOD='#2f6b4a'
SERIF="Georgia,'Times New Roman',serif";SANS="'Segoe UI',Arial,Helvetica,sans-serif"
ACCESS_COLOR={'READY':GOOD,'DRAFTING':BRASS,'BLOCKED':URGENT,'NOT_CHECKED':MUTED,'FINISHED':MUTED}


def e(v):return escape(str(v),quote=True)


def a(url,label,style=''):
    if urlsplit(str(url)).scheme not in ('http','https'):return e(label)
    return f'<a href="{e(url)}" style="color:{NAVY};text-decoration:underline;{style}">{e(label)}</a>'


def button(url,label):
    if urlsplit(str(url)).scheme not in ('http','https'):return ''
    return f'<a href="{e(url)}" style="display:inline-block;background:{NAVY};color:{SOFT};padding:12px 22px;border-radius:999px;text-decoration:none;font:600 14px {SANS};">{e(label)}</a>'


def section(title,body,note=''):
    return (f'<tr><td class="pad" style="padding:28px 34px 6px;"><h2 style="margin:0 0 4px;font:400 22px/1.25 {SERIF};color:{NAVY};">{e(title)}</h2>'
            +(f'<p style="margin:0 0 12px;font:13px/1.55 {SANS};color:{MUTED};">{e(note)}</p>' if note else '<div style="height:8px"></div>')
            +body+'</td></tr>')


def program_rows(rows,empty):
    if not rows:return f'<p style="margin:0 0 8px;font:14px/1.6 {SANS};color:{MUTED};">{e(empty)}</p>'
    out=[]
    for r in rows:
        color=ACCESS_COLOR.get(r['access']['level'],MUTED)
        out.append(f'''<tr><td style="padding:12px 0;border-top:1px solid {LINE};vertical-align:top;">
<div style="font:400 17px/1.35 {SERIF};color:{INK};">{a(r['url'],r['name'],'color:'+INK+';text-decoration:none;')}</div>
<div style="font:13px/1.6 {SANS};color:{MUTED};margin-top:2px;">{e(r['when'])} &nbsp;·&nbsp; <span style="color:{color};font-weight:600;">{e(r['access']['label'])}</span></div></td>
<td align="right" style="padding:12px 0 12px 12px;border-top:1px solid {LINE};vertical-align:top;white-space:nowrap;font:600 15px/1.35 {SANS};color:{BRASS if r['amount_known'] else MUTED};">{e(r['amount'])}</td></tr>''')
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{"".join(out)}</table>'


def render_digest(d,sample=False):
    """d: dict built by DailyReporter.digest(). Returns the full HTML email."""
    stats=[(len(d['needs_you']),'need you'),(len(d['cash']),'cash programs open'),(d['closing_soon'],'closing this week'),(len(d['waiting']),'waiting on results')]
    stat_cells=''.join(f'<td class="stat" style="padding:12px 8px;border-right:1px solid {LINE};vertical-align:top;"><div style="font:400 26px/1 {SERIF};color:{URGENT if (label=="need you" and n) or (label=="closing this week" and n) else NAVY};">{n}</div><div style="font:12px/1.4 {SANS};color:{MUTED};margin-top:6px;">{e(label)}</div></td>' for n,label in stats)
    if d['needs_you']:
        items=''.join(f'''<tr><td style="padding:12px 0;border-top:1px solid {LINE};vertical-align:top;width:28px;font:400 18px/1.3 {SERIF};color:{BRASS};">{i}</td>
<td style="padding:12px 0;border-top:1px solid {LINE};vertical-align:top;"><div style="font:600 15px/1.45 {SANS};color:{INK};">{e(x['title'])}</div><div style="font:13px/1.6 {SANS};color:{MUTED};margin-top:2px;">{e(x['detail'])} {a(x['url'],x.get('link','Open'))}</div></td></tr>''' for i,x in enumerate(d['needs_you'],1))
        needs=f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{items}</table>'
    else:needs=f'<p style="margin:0 0 8px;font:15px/1.6 {SANS};color:{INK};">Nothing needs you today. The agents keep researching and reading forms.</p>'
    reach=''.join(f'<p style="margin:0 0 10px;font:14px/1.5 {SANS};color:{INK};">{a(x["url"],x["name"],"color:"+INK+";")}<br><span style="font-size:12px;color:{GOOD};">{e(x["detail"])}</span></p>' for x in d['access']['reach']) or f'<p style="margin:0;font:13px/1.5 {SANS};color:{MUTED};">None yet.</p>'
    blocked=''.join(f'<p style="margin:0 0 10px;font:14px/1.5 {SANS};color:{INK};">{e(x["name"])}<br><span style="font-size:12px;color:{URGENT};">{e(x["detail"])}</span></p>' for x in d['access']['blocked']) or f'<p style="margin:0;font:13px/1.5 {SANS};color:{MUTED};">Nothing blocked.</p>'
    access=(f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
<td class="col" width="50%" style="vertical-align:top;padding:14px 14px 4px 0;border-top:2px solid {GOOD};"><div style="font:600 12px/1.4 {SANS};color:{GOOD};margin-bottom:10px;">AGENT CAN REACH ({len(d['access']['reach'])})</div>{reach}</td>
<td class="col" width="50%" style="vertical-align:top;padding:14px 0 4px 14px;border-top:2px solid {URGENT};"><div style="font:600 12px/1.4 {SANS};color:{URGENT};margin-bottom:10px;">BLOCKED ({len(d['access']['blocked'])})</div>{blocked}</td></tr></table>'''
            +(f'<p style="margin:6px 0 0;font:13px/1.55 {SANS};color:{MUTED};">Not checked yet: {e(", ".join(d["access"]["not_checked"]))}. The agent reads one form every few minutes.</p>' if d['access']['not_checked'] else ''))
    waiting=''.join(f'<tr><td style="padding:9px 0;border-top:1px solid {LINE};font:14px/1.5 {SANS};color:{INK};">{e(w["name"])}</td><td align="right" style="padding:9px 0;border-top:1px solid {LINE};font:13px/1.5 {SANS};color:{MUTED};white-space:nowrap;">{e(w["status"])}</td></tr>' for w in d['waiting'])
    waiting=f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{waiting}</table>' if waiting else f'<p style="margin:0;font:14px/1.6 {SANS};color:{MUTED};">Nothing pending.</p>'
    body=(section('Needs you today',needs)
          +section('Cash on the table',program_rows(d['cash'],'No open cash programs are verified right now.'),'Prizes, grants and fellowships, soonest deadline first. A pool size is not your award.')
          +section('Credits worth claiming',program_rows(d['credits'],'No open credit programs right now.'),'Credits are not cash. Ranked by how directly they cover the voice and AI services A Story uses.')
          +section('Access report',access,'Whether the agent could open each official application form. Reachable forms have answers waiting on the website.')
          +section('Waiting on results',waiting))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>A Story daily brief</title>
<style>@media only screen and (max-width:600px){{.pad{{padding-left:20px!important;padding-right:20px!important}}.col{{display:block!important;width:100%!important;padding-left:0!important;padding-right:0!important;margin-bottom:12px}}.stat{{display:inline-block!important;width:46%!important;border-right:0!important}}.h1{{font-size:28px!important}}}}</style></head>
<body style="margin:0;padding:0;background:{PAPER};">
<div style="display:none;max-height:0;overflow:hidden;">{e(d['preheader'])}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{PAPER};"><tr><td align="center" style="padding:28px 10px;">
<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="width:100%;max-width:640px;background:{SOFT};border:1px solid {LINE};">
<tr><td class="pad" style="background:{NAVY};padding:22px 34px;"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
<td style="font:400 16px/1.2 {SERIF};letter-spacing:3px;color:{SOFT};">A STORY<span style="color:{MAIZE};font:600 11px {SANS};letter-spacing:1px;">&nbsp;&nbsp;FOUNDER OS</span></td>
<td align="right" style="font:12px {SANS};color:{MAIZE};">{e(d['date_label'])}{' · DESIGN SAMPLE' if sample else ''}</td></tr></table></td></tr>
<tr><td class="pad" style="padding:30px 34px 8px;"><h1 class="h1" style="margin:0 0 10px;font:400 32px/1.15 {SERIF};color:{NAVY};">{e(d['headline'])}</h1>
<p style="margin:0 0 18px;font:15px/1.6 {SANS};color:{INK};">{e(d['summary'])}</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid {LINE};border-bottom:1px solid {LINE};"><tr>{stat_cells}</tr></table></td></tr>
{body}
<tr><td class="pad" style="padding:26px 34px 30px;"><p style="margin:0 0 18px;">{button(d['os_url'],'Open Founder OS')}</p>
<p style="margin:0;font:12px/1.7 {SANS};color:{MUTED};">{e(d['agent_status'])}<br>Nothing is submitted for you. Questions and prepared answers are on the website; you copy them into each official form.</p></td></tr>
</table></td></tr></table></body></html>'''
