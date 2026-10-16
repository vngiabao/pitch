"""Edition Builder and Slide QA (AGENT-SYSTEM.md).

Edition Builder turns Pitch Tailor's slide plan into a real deck: the frozen core deck's own slides, in the
edition's order, with the edition's speaker notes and page numbers. It never redesigns a core slide. New
slides (new-1, new-2) are drafted from one plain template and flagged for Bao.

Slide QA renders every slide in headless Edge or Chrome and measures it: text overlapping text, text spilling
over the edge of its box, anything off the slide, rows a few pixels out of line, tiny text, missing images
and missing notes. No AI is involved; nothing here publishes or sends anything.
"""
import html
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from .store import now

ROOT=Path(__file__).resolve().parents[1]
BROWSERS=(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
          r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
          '/usr/bin/microsoft-edge','/usr/bin/google-chrome','/usr/bin/chromium','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
FONTS='https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,400..800;1,400..800&family=Source+Serif+4:ital,wght@0,300..700;1,300..700&display=swap'
BLOB=re.compile(r'/_blob/([0-9a-f]{32})')
PAGE_NO=re.compile(r'(<p style="[^"]*bottom:\s*40px[^"]*">)\s*\d{1,2}\s*(</p>)')
ASIDE=re.compile(r'<aside>.*?</aside>',re.S)
MIME={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.gif':'image/gif'}
FRAME_CSS=('*{box-sizing:border-box;margin:0}.qa-frame{position:relative;width:1920px;height:1080px;overflow:hidden}'
           '.qa-frame section{position:relative;width:1920px;height:1080px;overflow:hidden;display:block;font-family:Montserrat,Arial,sans-serif}'
           '.qa-frame section div{display:flex;flex-direction:column}h1,h2,h3,p{margin:0}aside{display:none}')


# ---------- the frozen core deck ----------
def core_dir():
    found=sorted(p for p in (ROOT/'seed-data').glob('core-deck-*') if (p/'deck.json').exists())
    if not found:raise ValueError('No frozen core deck in seed-data. Freeze the core deck first.')
    return found[-1]

def load_core():
    d=core_dir();deck=json.loads((d/'deck.json').read_text(encoding='utf-8'))
    slides={sid:(d/'slides'/(sid+'.html')).read_text(encoding='utf-8') for sid in deck['order'] if (d/'slides'/(sid+'.html')).exists()}
    return d,deck,slides

def asset_path(blob_id):
    if not re.fullmatch(r'[0-9a-f]{32}',blob_id or ''):return None
    hits=sorted((core_dir()/'assets').glob(blob_id+'.*'))
    return hits[0] if hits else None

def editions_root(store):
    return Path(store.path).parent/'editions'


# ---------- Edition Builder ----------
def set_notes(slide,seconds,text):
    note=(f'~{int(seconds)//60}:{int(seconds)%60:02d} · ' if seconds else '')+(text or '').strip()
    block='<aside>'+html.escape(note,quote=False)+'</aside>'
    return ASIDE.sub(lambda m:block,slide,count=1) if ASIDE.search(slide) else slide.replace('</section>','  '+block+'\n</section>',1)

def set_page(slide,n):
    return PAGE_NO.sub(lambda m:m.group(1)+f'{n:02d}'+m.group(2),slide,count=1)

def sentences(text,limit=3):
    parts=[s.strip() for s in re.split(r'(?<=[.!?])\s+',(text or '').strip()) if s.strip()]
    return parts[:limit]

def new_slide(sid,title,lines,n):
    """One plain draft slide in the deck's style, for Bao to finish. Never used for a core slide."""
    E=lambda s:html.escape(s or '',quote=False)
    rows=''.join(f'<p style="position:absolute; top:{300+i*150}px; left:160px; width:1600px; font-family:Montserrat, Arial, sans-serif; font-size:38px; font-weight:700; line-height:1.3; color:#3b291d">{E(t)}</p>'
                 f'<div style="position:absolute; top:{316+i*150}px; left:120px; width:16px; height:16px; display:flex; flex-direction:column; background:#c9973a; border-radius:8px"></div>' for i,t in enumerate(lines[:3]))
    return (f'<section id="{E(sid)}" data-transition="fade" data-draft="true" style="background:#f3ebde">\n'
            f'  <h2 style="position:absolute; top:84px; left:96px; width:1728px; font-family:Montserrat, Arial, sans-serif; font-size:64px; font-weight:800; line-height:1.08; letter-spacing:-1.5px; color:#3b291d">{E(title)}</h2>\n'
            f'  <div style="position:absolute; top:240px; left:96px; width:1728px; height:{max(1,min(3,len(lines)))*150+60}px; display:flex; flex-direction:column; background:#fbf7ef; border-radius:30px"></div>\n'
            f'  {rows}\n'
            f'  <p style="position:absolute; right:64px; bottom:40px; width:80px; font-family:Montserrat, Arial, sans-serif; font-size:24px; font-weight:700; text-align:right; color:#8a7360">{n:02d}</p>\n'
            '  <aside></aside>\n</section>\n')

def build_edition(store,item_id,round_no,brief,program,minutes):
    """Writes editions/<item>/round-<n>/ with deck.json, slides/ and manifest.json. Returns the manifest."""
    d,deck,core=load_core()
    out=editions_root(store)/item_id/f'round-{int(round_no)}'
    if out.exists():shutil.rmtree(out)
    (out/'slides').mkdir(parents=True)
    section_of={};current=None;starts={v['start']:k for k,v in deck.get('sections',{}).items()}
    for sid in deck['order']:
        current=starts.get(sid,current);section_of[sid]=current
    order=[];slides=[];last_section=None
    for x in brief.get('script',[]):
        sid=x.get('slide_id')
        if not sid or sid in order:continue
        if sid in core:body,source=core[sid],'core'
        elif re.fullmatch(r'new-\d+',sid):
            is_ask='ask' in (x.get('title') or '').lower() or sid=='new-2'
            lines=sentences(brief.get('ask') if is_ask and brief.get('ask') else x.get('text'),3) or [x.get('title','')]
            body,source=new_slide(sid,x.get('title') or 'New slide',lines,len(order)+1),'new'
        else:continue
        n=len(order)+1;body=set_notes(set_page(body,n),x.get('seconds'),x.get('text',''))
        (out/'slides'/(sid+'.html')).write_text(body,encoding='utf-8')
        sec=section_of.get(sid,last_section);last_section=sec
        order.append(sid);slides.append({'id':sid,'n':n,'title':x.get('title',''),'seconds':x.get('seconds'),'source':source,'section':sec})
    if not order:raise ValueError('The slide plan has no slides from the core deck')
    sections={}
    for s in slides:
        if s['section'] and s['section'] not in sections:sections[s['section']]={**deck['sections'][s['section']],'start':s['id']}
    edition={**deck,'title':f'A Story - {program} ({float(minutes):g} min)','order':order,'cover':'cover' if 'cover' in order else order[0],'sections':sections}
    (out/'deck.json').write_text(json.dumps(edition,ensure_ascii=False,indent=1),encoding='utf-8')
    manifest={'item_id':item_id,'round':int(round_no),'program':program,'minutes':minutes,'core':d.name,'built_at':now(),'dir':str(out),'slides':slides,
              'new_slides':[s['id'] for s in slides if s['source']=='new']}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=1),encoding='utf-8')
    return manifest

def edition_files(manifest):
    out=Path(manifest['dir']);order=[s['id'] for s in manifest['slides']]
    return out,{sid:(out/'slides'/(sid+'.html')).read_text(encoding='utf-8') for sid in order}

def edition_zip(manifest):
    """deck.json, slides and the images they use, ready to publish as a Slides deck."""
    out,slides=edition_files(manifest);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(out/'deck.json','project/deck.json')
        used=set()
        for sid,body in slides.items():
            z.writestr(f'project/slides/{sid}.html',body);used|=set(BLOB.findall(body))
        for b in sorted(used):
            p=asset_path(b)
            if p:z.write(p,'assets/'+p.name)
        z.writestr('README.txt','A Story program edition built from the frozen core deck.\nproject/ holds the Slides files; assets/ holds the images, named by their /_blob id.\n')
    return buf.getvalue()


# ---------- shared page wrapper ----------
def _frames(slides,asset_url,extra=''):
    def fix(body):
        body=BLOB.sub(lambda m:asset_url(m.group(1)),body)
        body=re.sub(r'<x-shape kind="arrow-right" style="([^"]*)"></x-shape>',lambda m:'<div style="'+m.group(1)+';clip-path:polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%)"></div>',body)
        body=re.sub(r'<x-shape kind="line"[^>]*style="([^"]*)"></x-shape>',lambda m:'<div style="'+m.group(1)+'"></div>',body)
        return re.sub(r'<x-icon name="[^"]*" style="([^"]*)"></x-icon>',lambda m:'<div style="'+m.group(1)+';border-radius:50%;background:currentColor"></div>',body)
    return ''.join(f'<div class="qa-frame" data-id="{html.escape(sid)}">{fix(body)}{extra if isinstance(extra,str) else extra(sid)}</div>' for sid,body in slides.items())


# ---------- Slide QA ----------
QA_JS=r'''
(function(){
const inter=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
const area=r=>Math.max(0,r.width)*Math.max(0,r.height);
const inset=r=>{const dy=r.height*0.22,dx=Math.min(3,r.width*0.1);return {left:r.left+dx,right:r.right-dx,top:r.top+dy,bottom:r.bottom-dy,width:r.width-2*dx,height:r.height-2*dy};};
const visible=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&parseFloat(s.opacity)>0.05;};
const blockOf=n=>{let e=n.parentElement;while(e&&!/^(P|H1|H2|H3|H4|LI|DIV|SECTION)$/.test(e.tagName))e=e.parentElement;return e;};
const label=e=>((e.innerText||e.getAttribute&&e.getAttribute('alt')||e.tagName)+'').replace(/\s+/g,' ').trim().slice(0,70);
function run(){
 const out=[];
 document.querySelectorAll('.qa-frame').forEach(fr=>{
  const F=fr.getBoundingClientRect(),issues=[],sec=fr.querySelector('section');
  const box=r=>r?{x:Math.round(r.left-F.left),y:Math.round(r.top-F.top),w:Math.round(r.width),h:Math.round(r.height)}:null;
  const add=(rule,severity,text,r)=>{if(issues.filter(i=>i.rule===rule).length<(severity==='block'?6:3)&&!issues.some(i=>i.rule===rule&&i.text===text))issues.push({rule,severity,text,box:box(r)});};
  if(!sec){out.push({id:fr.dataset.id,issues:[{rule:'NO_SLIDE',severity:'block',text:'The slide file has no <section>',box:null}]});return;}
  const all=[...sec.querySelectorAll('*')].filter(e=>!e.closest('aside')&&!e.closest('svg')&&visible(e));
  const lines=[],walker=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){const t=walker.currentNode;if(!t.nodeValue.trim())continue;const p=t.parentElement;if(!p||p.closest('aside')||p.closest('svg')||!visible(p))continue;
   const rg=document.createRange();rg.selectNodeContents(t);const own=blockOf(t)||p,fs=parseFloat(getComputedStyle(p).fontSize);
   const cs=getComputedStyle(own);for(const r of rg.getClientRects()){if(r.width>2&&r.height>2)lines.push({r,own,fs,fw:cs.fontWeight,color:cs.color,align:cs.textAlign,text:label(own)});}}
  const T=4;
  for(const e of all){const r=e.getBoundingClientRect();if(area(r)<9)continue;
   if(r.left<F.left-T||r.top<F.top-T||r.right>F.right+T||r.bottom>F.bottom+T)add('OFF_SLIDE','block','“'+label(e)+'” runs off the slide',r);}
  for(let i=0;i<lines.length;i++)for(let j=i+1;j<lines.length;j++){const a=lines[i],b=lines[j];if(a.own===b.own||a.own.contains(b.own)||b.own.contains(a.own))continue;
   if(inter(inset(a.r),inset(b.r))>0.1*Math.min(area(inset(a.r)),area(inset(b.r))))add('TEXT_OVERLAP','block','“'+a.text+'” overlaps “'+b.text+'”',a.r);}
  const cards=all.filter(e=>{if(e.tagName==='IMG')return false;const s=getComputedStyle(e),bg=s.backgroundColor,r=e.getBoundingClientRect();
   const hasBg=bg&&bg!=='transparent'&&!/rgba\([^)]*,\s*0\)$/.test(bg),bd=(parseFloat(s.borderTopWidth)||0)+(parseFloat(s.borderLeftWidth)||0)>0;return (hasBg||bd)&&area(r)>6000;});
  for(const l of lines){const li=inset(l.r),a=area(li);if(a<=0)continue;for(const c of cards){if(c===l.own||c.contains(l.own)||l.own.contains(c))continue;
   const cr=c.getBoundingClientRect(),o=inter(li,cr);if(o>0.04*a&&o<0.96*a){const over=li.bottom>cr.bottom+2||li.right>cr.right+2;
    if(over&&li.top>=cr.top-2&&li.left>=cr.left-2)add('TEXT_SPILL','block','“'+l.text+'” runs past the edge of its box',l.r);else add('TEXT_STRADDLE','warn','“'+l.text+'” sits across the edge of a box',l.r);}}}
  const imgs=all.filter(e=>e.tagName==='IMG');
  for(const l of lines.filter(l=>l.text.length>2))for(const im of imgs){if(inter(inset(l.r),im.getBoundingClientRect())>0)add('TEXT_ON_IMAGE','warn','“'+l.text+'” sits on top of an image',l.r);}
  for(const im of imgs){if(!im.complete||im.naturalWidth===0)add('IMAGE_MISSING','block','An image did not load ('+(im.getAttribute('alt')||'no description')+')',im.getBoundingClientRect());
   else if(!im.getAttribute('alt'))add('NO_ALT','warn','An image has no description',im.getBoundingClientRect());}
  const small=lines.filter(l=>l.fs<18);if(small.length)add('SMALL_TEXT','warn','Text under 18px is hard to read on a projector: “'+small[0].text+'”',small[0].r);
  const blocks=[...new Set(lines.map(l=>l.own))].map(e=>{const ls=lines.filter(l=>l.own===e);return {e,top:Math.min(...ls.map(l=>l.r.top)),left:Math.min(...ls.map(l=>l.r.left)),right:Math.max(...ls.map(l=>l.r.right)),bottom:Math.max(...ls.map(l=>l.r.bottom)),fs:ls[0].fs,fw:ls[0].fw,color:ls[0].color,align:ls[0].align};});
  for(let i=0;i<blocks.length;i++)for(let j=i+1;j<blocks.length;j++){const a=blocks[i],b=blocks[j];if(a.e.contains(b.e)||b.e.contains(a.e)||Math.abs(a.fs-b.fs)>1||a.fw!==b.fw||a.color!==b.color)continue;
   const side=a.right<b.left||b.right<a.left,dt=Math.abs(a.top-b.top);
   if(side&&dt>=3&&dt<=12)add('ALMOST_ALIGNED','warn','“'+label(a.e)+'” and “'+label(b.e)+'” are '+Math.round(dt)+'px out of line',{left:Math.min(a.left,b.left),top:Math.min(a.top,b.top),right:Math.max(a.right,b.right),bottom:Math.max(a.bottom,b.bottom),width:Math.max(a.right,b.right)-Math.min(a.left,b.left),height:Math.max(a.bottom,b.bottom)-Math.min(a.top,b.top)});
   const stack=(a.bottom<b.top||b.bottom<a.top)&&a.align!=='center'&&b.align!=='center'&&a.align!=='right'&&b.align!=='right',dl=Math.abs(a.left-b.left);
   if(stack&&dl>=3&&dl<=10&&Math.abs(a.right-a.left-(b.right-b.left))>4)add('ALMOST_ALIGNED','warn','“'+label(a.e)+'” and “'+label(b.e)+'” start '+Math.round(dl)+'px apart',{left:Math.min(a.left,b.left),top:Math.min(a.top,b.top),right:Math.max(a.right,b.right),bottom:Math.max(a.bottom,b.bottom),width:Math.max(a.right,b.right)-Math.min(a.left,b.left),height:Math.max(a.bottom,b.bottom)-Math.min(a.top,b.top)});}
  const aside=sec.querySelector('aside');if(!aside||!aside.textContent.trim())add('NO_NOTES','warn','No speaker notes',null);
  if(sec.dataset.draft)add('NEW_SLIDE','warn','A new slide drafted from the plain template. Design it before you present.',null);
  out.push({id:fr.dataset.id,issues});
 });
 const fonts=document.fonts?document.fonts.check('32px Montserrat'):null;
 const s=document.createElement('script');s.type='application/json';s.id='qa-out';s.textContent=JSON.stringify({slides:out,fonts}).replace(/</g,'\\u003c');document.body.appendChild(s);
}
window.addEventListener('load',()=>{(document.fonts?document.fonts.ready:Promise.resolve()).then(()=>setTimeout(run,50));});
})();
'''

def find_browser():
    env=os.environ.get('FOUNDER_OS_BROWSER')
    for b in ([env] if env else [])+list(BROWSERS):
        if b and Path(b).exists():return b
    return None

def run_qa(manifest,timeout=180):
    """Measure every slide of an edition. Returns {available, slides:[{id,title,issues}], blocking, warnings}."""
    base={'ran_at':now(),'slides':[],'blocking':0,'warnings':0}
    if os.environ.get('FOUNDER_OS_SLIDE_QA','').lower()=='off':return {**base,'available':False,'reason':'Slide QA is turned off on this machine.'}
    browser=find_browser()
    if not browser:return {**base,'available':False,'reason':'No Edge or Chrome found to render the slides.'}
    _,slides=edition_files(manifest)
    def local(b):
        p=asset_path(b);return p.resolve().as_uri() if p else 'missing-image-'+b
    page=('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="'+FONTS+'"><style>'+FRAME_CSS+'body{margin:0}</style></head><body>'
          +_frames(slides,local)+'<script>'+QA_JS+'</script></body></html>')
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/'qa.html';f.write_text(page,encoding='utf-8')
        cmd=[browser,'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars','--window-size=1920,1080',
             '--user-data-dir='+str(Path(td)/'profile'),'--allow-file-access-from-files','--virtual-time-budget=20000','--dump-dom',f.resolve().as_uri()]
        try:dom=subprocess.run(cmd,capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout.decode('utf-8','replace')
        except subprocess.TimeoutExpired:return {**base,'available':False,'reason':'The browser took too long to render the slides.'}
    m=re.search(r'<script type="application/json" id="qa-out">(.*?)</script>',dom,re.S)
    if not m:return {**base,'available':False,'reason':'The browser rendered no measurements.'}
    data=json.loads(m.group(1));titles={s['id']:s.get('title','') for s in manifest['slides']}
    res=[{'id':s['id'],'n':i+1,'title':titles.get(s['id'],''),'issues':s['issues']} for i,s in enumerate(data['slides'])]
    blocking=sum(1 for s in res for i in s['issues'] if i['severity']=='block');warnings=sum(1 for s in res for i in s['issues'] if i['severity']=='warn')
    return {**base,'available':True,'fonts_loaded':data.get('fonts'),'slides':res,'blocking':blocking,'warnings':warnings}


# ---------- preview page (served by Founder OS, animated with GSAP) ----------
def preview_page(manifest,qa,title):
    _,slides=edition_files(manifest);by={s['id']:s for s in (qa or {}).get('slides',[])}
    E=lambda s:html.escape(str(s if s is not None else ''))
    def flags(sid):
        return ''.join(f'<div class="pv-flag {E(i["severity"])}" data-flag="{E(sid)}-{k}" style="left:{i["box"]["x"]}px;top:{i["box"]["y"]}px;width:{max(8,i["box"]["w"])}px;height:{max(8,i["box"]["h"])}px"><span>{k+1}</span></div>'
                       for k,i in enumerate(by.get(sid,{}).get('issues',[])) if i.get('box'))
    cards=[]
    frames=_frames(slides,lambda b:'/edition-asset/'+b,flags)
    parts=re.split(r'(?=<div class="qa-frame" data-id=")',frames)[1:]
    for s,frame in zip(manifest['slides'],parts):
        iss=by.get(s['id'],{}).get('issues',[])
        items=''.join(f'<li class="{E(i["severity"])}" data-for="{E(s["id"])}-{k}"><b>{k+1}</b> {E(i["text"])}</li>' for k,i in enumerate(iss))
        state='block' if any(i['severity']=='block' for i in iss) else 'warn' if iss else 'ok'
        cards.append(f'<article class="pv-card {state}"><div class="pv-slide">{frame}</div><div class="pv-side"><p class="pv-no">{s["n"]:02d} · {E(s["id"])}{" · new" if s["source"]=="new" else ""}</p>'
                     f'<h2>{E(s.get("title"))}</h2><p class="pv-sec">{E(s.get("seconds") or "")}{" sec" if s.get("seconds") else ""}</p>'
                     +(f'<ol class="pv-issues">{items}</ol>' if items else '<p class="pv-clean">No layout problems found.</p>')+'</div></article>')
    if qa and qa.get('available'):summary=f'{qa["blocking"]} problem{"s" if qa["blocking"]!=1 else ""} to fix · {qa["warnings"]} to look at'+('' if qa.get('fonts_loaded') else ' · fonts did not load, so measurements are approximate')
    else:summary='Slide QA has not run: '+E((qa or {}).get('reason','not yet'))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(title)+' · deck</title>'
            '<link rel="stylesheet" href="'+FONTS+'"><link rel="stylesheet" href="/edition.css"></head><body>'
            f'<header class="pv-head"><a href="/pitch-lab/{E(manifest["item_id"])}">← Back to the edition</a><h1>{E(title)}</h1>'
            f'<p>{len(manifest["slides"])} slides from the core deck ({E(manifest["core"])}) · round {manifest["round"]} · {E(summary)}</p>'
            f'<a class="pv-download" href="/api/lab/{E(manifest["item_id"])}/edition.zip">Download the deck files</a></header>'
            '<main class="pv-list">'+''.join(cards)+'</main><script src="/vendor/gsap.min.js"></script><script src="/vendor/ScrollTrigger.min.js"></script><script src="/edition.js"></script></body></html>')
