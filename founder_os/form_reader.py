"""Read application questions from an official form so the owner can copy prepared answers.

Read-only: the page is rendered in a throwaway headless Edge profile (so JavaScript
forms work), then parsed. Nothing is typed, clicked or submitted. A login wall is
reported as blocked, never bypassed.
"""
import json,os,re,subprocess
from html.parser import HTMLParser
from pathlib import Path
from .public_forms import public_https

EDGE_PATHS=[r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']
SKIP_TYPES={'hidden','submit','button','reset','image','password','search'}
LIMIT_PATTERNS=[(re.compile(r'(\d{1,5})\s*words?',re.I),'words'),(re.compile(r'(\d{1,5})\s*char(?:acter)?s?',re.I),'characters')]
LOGIN_TEXT=re.compile(r'\b(sign in|log in|login|sign up to continue|create an account to)\b',re.I)


class DomQuestions(HTMLParser):
    """Collect form controls and the text that names them from a rendered page."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.texts={};self.open_ids=[];self.controls=[];self.label_for={};self.label_stack=[];self.recent=[];self.passwords=0
        self.select=None;self.option=None;self.page_text=[];self.skip=0;self.named=[];self.last_label=''
    def handle_starttag(self,tag,attrs):
        a={k:(v or '') for k,v in attrs}
        if tag in ('script','style','noscript','template'):self.skip+=1;return
        if tag in ('br','hr','img','meta','link'):return
        if a.get('id'):self.open_ids.append((tag,a['id']));self.texts.setdefault(a['id'],[])
        if tag not in ('input','textarea','select','label','option') and a.get('aria-labelledby'):
            # Many form builders name the question on a wrapper around its inputs.
            self.named.append((tag,a['aria-labelledby'].split(),a.get('aria-describedby','').split()))
        if tag=='label':self.label_stack.append({'for':a.get('for'),'text':[],'control':None})
        if tag=='input':
            kind=(a.get('type') or 'text').lower()
            if kind=='password':self.passwords+=1
            if kind in SKIP_TYPES:return
            self._control(tag,kind,a)
        elif tag=='textarea':self._control(tag,'textarea',a)
        elif tag=='select':self.select=self._control(tag,'select',a)
        elif tag=='option' and self.select is not None:self.option=[]
    def _control(self,tag,kind,a):
        inherited=self.named[-1] if self.named else (None,[],[])
        own=a.get('aria-labelledby','').split()
        c={'tag':tag,'type':kind,'id':a.get('id'),'name':a.get('name'),'labelledby':own if own and kind not in ('radio','checkbox') else inherited[1] or own,'describedby':a.get('aria-describedby','').split() or inherited[2],'group':' '.join(inherited[1]),
           'aria_label':a.get('aria-label',''),'placeholder':a.get('placeholder',''),'required':'required' in a or a.get('aria-required')=='true',
           'maxlength':a.get('maxlength'),'value':a.get('data-value') or a.get('value',''),'last_label':self.last_label,'options':[],'context':' '.join(self.recent[-3:])}
        if self.label_stack and self.label_stack[-1]['control'] is None:self.label_stack[-1]['control']=c
        self.controls.append(c);return c
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','template'):self.skip=max(0,self.skip-1);return
        if tag=='label' and self.label_stack:
            l=self.label_stack.pop();text=' '.join(' '.join(l['text']).split())
            if l['for']:self.label_for[l['for']]=text
            if l['control'] is None and text and len(text)<300 and not l['for']:self.last_label=text
            if l['control'] is not None and l['control']['type'] in ('radio','checkbox'):l['control']['option_label']=text
            elif l['control'] is not None and not l['for']:l['control']['wrapped_label']=text
        if tag=='option' and self.option is not None and self.select is not None:
            t=' '.join(' '.join(self.option).split())
            if t and not re.match(r'^(please select|select|choose|--)',t,re.I):self.select['options'].append(t)
            self.option=None
        if tag=='select':self.select=None
        for i in range(len(self.open_ids)-1,-1,-1):
            if self.open_ids[i][0]==tag:del self.open_ids[i];break
        for i in range(len(self.named)-1,-1,-1):
            if self.named[i][0]==tag:del self.named[i];break
    def handle_data(self,data):
        if self.skip:return
        t=' '.join(data.split())
        if not t:return
        self.page_text.append(t)
        for _,i in self.open_ids:
            if len(self.texts[i])<40:self.texts[i].append(t)
        for l in self.label_stack:l['text'].append(t)
        if self.option is not None:self.option.append(t)
        self.recent.append(t);self.recent=self.recent[-6:]

    def _text(self,ids):return ' '.join(' '.join(self.texts.get(i,[])) for i in ids).strip()

    def questions(self):
        out=[];groups={}
        for c in self.controls:
            label=(self._text(c['labelledby']) or (self.label_for.get(c['id']) if c['id'] else '') or c.get('wrapped_label') or c['aria_label'] or '').strip()
            if not label and c['type'] in ('radio','checkbox','text') and c['last_label']:label=c['last_label']
            described=self._text(c['describedby'])
            if c['type'] in ('radio','checkbox'):
                # Choice controls form one question; each control contributes an option.
                key=c['group'] or c['name'] or label or c['context']
                if c['type']=='text':pass
                g=groups.get(key)
                if g is None:
                    g={'label':label if not c.get('option_label') or label!=c.get('option_label') else c['context'],'type':c['type'],'required':c['required'],'options':[],'description':described,'limit':None,'unit':None}
                    groups[key]=g;out.append(g)
                opt=c['value'] or c.get('option_label')
                if opt and opt not in g['options']:g['options'].append(opt)
                g['required']=g['required'] or c['required'];continue
            squash=lambda t:re.sub(r'[^a-z0-9]','',t.lower())
            if c['placeholder'] and label and squash(c['placeholder']) not in squash(label) and c['type']=='text' and len(c['placeholder'])<20:
                label=label+' ('+c['placeholder']+')'
            label=label or c['placeholder'] or c['context']
            if not label:continue
            q={'label':label,'type':c['type'],'required':c['required'] or label.rstrip().endswith('*'),'options':c['options'],'description':described,'limit':None,'unit':None}
            if c['maxlength'] and str(c['maxlength']).isdigit():q['limit'],q['unit']=int(c['maxlength']),'characters'
            for pattern,unit in LIMIT_PATTERNS:
                m=pattern.search(label+' '+described)
                if m and (q['limit'] is None or unit=='words'):q['limit'],q['unit']=int(m.group(1)),unit;break
            out.append(q)
        seen=set();clean=[];previous=[]
        for q in out:
            label=re.sub(r'(?i)opens in a new tab,?\s*your progress stays here\.?','',' '.join(q['label'].split()))
            # Text from the previous question's options can leak into the next label.
            for opt in sorted(previous,key=len,reverse=True):
                if opt and label.startswith(opt+' '):label=label[len(opt):].strip();break
            label=re.sub(r'^[\s*.:,-]+','',label)
            label=re.sub(r'^(yes|no|true|false)\s+(?=[A-Z])','',label)
            q['label']=re.sub(r'\s*\*\s*$','',label)[:500]
            previous=q['options'] or previous
            key=re.sub(r'[^a-z0-9]+',' ',q['label'].lower()).strip()
            if not key or key in seen:continue
            seen.add(key);q['key']=key;clean.append(q)
        return clean


def parse(html):
    p=DomQuestions();p.feed(html);p.close()
    questions=p.questions();text=' '.join(p.page_text)
    if p.passwords:return {'state':'LOGIN_REQUIRED','reason':'The application asks you to sign in first, so the agent cannot see its questions.','questions':[]}
    if not questions or (len(questions)<=4 and LOGIN_TEXT.search(text[:4000])):
        if LOGIN_TEXT.search(text[:4000]):return {'state':'LOGIN_REQUIRED','reason':'The application page asks you to sign in or create an account first.','questions':[]}
        return {'state':'NO_FORM_FOUND','reason':'No application questions were found on this page; it may link elsewhere or open only after signing in.','questions':[]}
    captcha=bool(re.search(r'(recaptcha|hcaptcha|captcha)',html,re.I))
    return {'state':'QUESTIONS_READ','reason':'Questions read from the official form'+(' (it has a CAPTCHA, so you submit it yourself)' if captcha else '')+'.','questions':questions,'captcha':captcha}


def edge_path():
    for p in EDGE_PATHS:
        if Path(p).is_file():return p
    return None


class BrowserFormReader:
    def __init__(self,profile_dir):self.profile=Path(profile_dir).resolve()
    def read(self,url):
        public_https(url)
        exe=edge_path()
        if not exe:return {'state':'UNREADABLE','reason':'Microsoft Edge is not installed on this PC, so JavaScript forms cannot be read.','questions':[]}
        self.profile.mkdir(parents=True,exist_ok=True)
        cmd=[exe,'--headless=new','--disable-gpu','--no-first-run','--disable-extensions','--disable-sync','--mute-audio','--user-data-dir='+str(self.profile),'--virtual-time-budget=15000','--dump-dom',url]
        try:r=subprocess.run(cmd,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except subprocess.TimeoutExpired:return {'state':'UNREADABLE','reason':'The application page did not finish loading within 90 seconds.','questions':[]}
        html=r.stdout.decode('utf-8','replace')
        if len(html)<200:return {'state':'UNREADABLE','reason':'The application page could not be loaded.','questions':[]}
        return parse(html)
