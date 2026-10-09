"""Bounded native HTML form transport. No guessed APIs, login or CAPTCHA bypass."""
import hashlib,ipaddress,re,socket,ssl,http.client
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler,HTTPCookieProcessor,HTTPSHandler,ProxyHandler
from http.cookiejar import CookieJar
from .store import digest,PolicyError

def public_https(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise PolicyError('Public HTTPS form URL required')
    addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise PolicyError('Private network addresses denied')
    return url

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise PolicyError('Redirect needs separate verification; no credentials or form data forwarded')

class PublicConnection(http.client.HTTPSConnection):
    def connect(self):
        # Pin the connection to an address we actually checked; a second DNS
        # resolution in urllib must not turn a public URL into a private target.
        addresses=socket.getaddrinfo(self.host,self.port,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise PolicyError('Private network addresses denied')
        ip=addresses[0][4][0];raw=socket.create_connection((ip,self.port),self.timeout)
        self.sock=ssl.create_default_context().wrap_socket(raw,server_hostname=self.host)

class PublicHTTPSHandler(HTTPSHandler):
    def https_open(self,request):return self.do_open(PublicConnection,request)

class Forms(HTMLParser):
    def __init__(self):
        super().__init__();self.forms=[];self.form=None;self.labels={};self.label=None;self.text=[];self.control=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form':
            if self.form is not None:raise PolicyError('Nested forms unsupported')
            self.form={'action':a.get('action',''),'method':a.get('method','get').lower(),'enctype':a.get('enctype','application/x-www-form-urlencoded'),'fields':[],'text':[]};self.forms.append(self.form)
        if tag=='label':self.label={'for':a.get('for'),'text':[]}
        if self.form is not None and tag in ('input','textarea','select','button'):
            name=a.get('name');kind=a.get('type','text' if tag=='input' else tag)
            if kind in ('submit','button','reset') or tag=='button':return
            if not name:return
            f={'name':name,'id':a.get('id',name),'type':kind,'required':'required' in a,'label':a.get('aria-label',''),'value':a.get('value',''),'maxlength':a.get('maxlength'),'disabled':'disabled' in a}
            self.form['fields'].append(f);self.control=f
            if self.label:self.label['for']=f['id']
    def handle_data(self,data):
        self.text.append(data)
        if self.form:self.form['text'].append(data)
        if self.label:self.label['text'].append(data)
    def handle_endtag(self,tag):
        if tag=='form':self.form=None
        if tag=='label' and self.label:
            self.labels[self.label['for']]=' '.join(' '.join(self.label['text']).split());self.label=None
    def finish(self,url):
        for f in self.forms:
            f['text']=' '.join(' '.join(f['text']).split())
            f['action']=urljoin(url,f['action'])
            for c in f['fields']:c['label']=self.labels.get(c['id']) or c['label']
        return self.forms

TOKEN=re.compile(r'(csrf|xsrf|authenticity|requestverification)',re.I)
LEGAL=re.compile(r'\b(agree|accept|consent|terms|certify|attest|signature|privacy|subscribe|payment|billing|credit card)\b',re.I)
CONFIRMATION=re.compile(r'(application (has been |was )?(received|submitted)|thank you for (your application|applying)|submission (received|successful))',re.I)
def form_definition(form):
    # Tokens refresh between GET and POST; the field layout cannot silently change.
    return {**form,'fields':[{k:v for k,v in c.items() if k!='value'} for c in form['fields']]}

class PublicFormTransport:
    def read(self,url):
        public_https(url)
        opener=build_opener(ProxyHandler({}),PublicHTTPSHandler(),NoRedirect(),HTTPCookieProcessor(CookieJar()))
        with opener.open(Request(url,headers={'User-Agent':'AStoryFounderOS/1.1 (startup application research)'}),timeout=25) as r:
            if r.headers.get_content_type()!='text/html':raise PolicyError('Application is not a native HTML form')
            raw=r.read(2_000_001)
            if len(raw)>2_000_000:raise PolicyError('Application page exceeds the read budget')
        parser=Forms();parser.feed(raw.decode('utf-8','replace'));forms=parser.finish(url)
        if not forms:raise PolicyError('Login or JavaScript application needs a provider-specific adapter')
        text=' '.join(parser.text)
        if re.search(r'(captcha|recaptcha|hcaptcha)',text,re.I) or re.search(r'(recaptcha|hcaptcha)',raw.decode('utf-8','replace'),re.I):raise PolicyError('CAPTCHA requires the owner')
        candidates=[f for f in forms if f['method']=='post']
        if len(candidates)!=1:raise PolicyError('A single verified POST application form is required')
        form=candidates[0]
        if urlsplit(form['action']).netloc!=urlsplit(url).netloc:raise PolicyError('Cross-site form destination needs separate review')
        public_https(form['action'])
        if form['enctype']!='application/x-www-form-urlencoded':raise PolicyError('Files or unsupported encoding require review')
        if LEGAL.search(form['text']):raise PolicyError('Application form contains legal, subscription or billing conditions requiring review')
        if any(c['disabled'] or c['type'] in ('file','password','checkbox','radio','select') for c in form['fields']):raise PolicyError('Files, account credentials or choice controls require provider-specific review')
        if any(c['type']=='hidden' and not TOKEN.search(c['name']) for c in form['fields']):raise PolicyError('Unknown hidden fields require review')
        if len({c['name'] for c in form['fields']})!=len(form['fields']):raise PolicyError('Duplicate field names need review')
        labels={re.sub(r'[^a-z ]','',c['label'].lower()).strip() for c in form['fields']}
        if not labels.intersection({'company name','startup name'}) or not labels.intersection({'email','email address','work email','business email','company email'}):raise PolicyError('Form is not clearly identified as a company application')
        return {'form':form,'definition':form_definition(form),'fingerprint':digest(form_definition(form)),'opener':opener,'page_sha256':hashlib.sha256(raw).hexdigest(),'initial_confirmation':bool(CONFIRMATION.search(raw.decode('utf-8','replace')))}

    def submit(self,session,fields):
        # All checks occur before the single POST. No automatic retries.
        form=session['form'];public_https(form['action'])
        values={c['name']:c['value'] for c in form['fields'] if c['type']=='hidden'};values.update(fields)
        response=session['opener'].open(Request(form['action'],data=urlencode(values).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'AStoryFounderOS/1.1'}),timeout=30)
        with response:
            raw=response.read(1_000_000);text=raw.decode('utf-8','replace')
            parser=Forms();parser.feed(text);remaining=[f for f in parser.finish(response.geturl()) if any(c['required'] for c in f['fields'])]
            confirmed=response.status in (200,201,202) and bool(CONFIRMATION.search(text)) and not session.get('initial_confirmation') and not remaining and not re.search(r'(validation error|submission failed|application failed|field is required)',text,re.I)
            return {'confirmed':confirmed,'http_status':response.status,'url':response.geturl(),'response_sha256':hashlib.sha256(raw).hexdigest(),'receipt':'Official application confirmation at '+response.geturl() if confirmed else None}
