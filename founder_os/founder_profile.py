"""Founder Profile Vault: the facts only Bao knows and every form keeps asking for.

Bao writes each one once on the Founder profile page. The Form Filler (application_drafter.fill_known)
copies them into application answers with provenance 'founder_profile'. A question stays "Needs you"
only when the vault has no value for it.

Sensitive values (EIN, street addresses, phone, dates of birth, citizenship) are masked on the page
until Bao clicks to reveal one, and are never written into the audit log, reports or AI contexts.
Bank fields (account, routing, card numbers) are refused outright; they never belong here.
"""
import re
from .store import now

SCHEMA='''CREATE TABLE IF NOT EXISTS founder_profile(
 key TEXT PRIMARY KEY,label TEXT NOT NULL,value TEXT NOT NULL DEFAULT '',sensitive INTEGER NOT NULL DEFAULT 0,
 custom INTEGER NOT NULL DEFAULT 0,updated_at TEXT);'''

MASK='•'*8
MAX_VALUE=2000
BANK_WORDS=re.compile(r'\b(bank|account number|acct|routing|iban|swift|bic|card number|credit card|debit card|cvv|cvc|ssn|social security|password|passcode|pin)\b',re.I)

# (key, label, sensitive, where it is used). Order is the order on the page.
FIELDS=[
 ('Company',[
  ('ein','EIN (employer identification number)',True,'Grant, accelerator and vendor forms that ask for a tax ID.'),
  ('incorporation_date','Date of incorporation',False,'"Incorporated on" and "founded on" lines in accelerator and grant forms.'),
  ('incorporation_state','State of incorporation',False,'Legal-entity questions (Delaware C-Corp).'),
  ('legal_address','Legal (registered) street address',True,'Address lines on grant, accelerator and credit forms.'),
  ('mailing_address','Mailing address, if different',True,'Forms that ask where to send letters or checks.'),
  ('city','City',False,'Address blocks that split city, state and ZIP.'),
  ('state','State or province',False,'Address blocks and "where are you based" dropdowns.'),
  ('zip_code','ZIP or postal code',False,'Address blocks.'),
  ('country','Country',False,'Country dropdowns that are not about incorporation.'),
 ]),
 ('Contact',[
  ('phone','Phone number',True,'Primary-contact phone lines. Only you decide who gets it.'),
  ('pronouns','Preferred pronouns',False,'Founder-profile questions on fellowship and accelerator forms.'),
 ]),
 ('Founders',[
  ('founder_dob','Bao: date of birth',True,'Age-restricted fellowships and awards. Stored, never shown in lists.'),
  ('founder_citizenship','Bao: citizenship or visa status',True,'Eligibility questions about citizenship, residency or work authorization.'),
  ('cofounder_dob','Daniel: date of birth',True,'Age-restricted fellowships and awards. Stored, never shown in lists.'),
  ('cofounder_citizenship','Daniel: citizenship or visa status',True,'Eligibility questions about citizenship, residency or work authorization.'),
 ]),
 ('Links',[
  ('linkedin_url','Bao: LinkedIn profile',False,'"LinkedIn profile" on nearly every form.'),
  ('cofounder_linkedin_url','Daniel: LinkedIn profile',False,'"Team member 2" and co-founder LinkedIn lines.'),
  ('company_linkedin_url','Company LinkedIn page',False,'"Startup LinkedIn" lines.'),
  ('company_website','Company website',False,'Fallback when the approved website fact is missing.'),
  ('company_twitter_url','Company X (Twitter) profile',False,'"Twitter" and "X" lines. Leave empty if there is none.'),
  ('crunchbase_url','Crunchbase profile',False,'Accelerator forms. Leave empty if there is none.'),
  ('deck_link','Pitch deck link (shareable)',False,'"Pitch deck link" lines. A link, never the file itself.'),
  ('demo_video_link','Demo or pitch video link',False,'"Video pitch", "demo video" and "multimedia URL" lines.'),
  ('app_store_link','App Store or TestFlight link',False,'"Link to your product" lines once the app is listed.'),
 ]),
 ('Team and money',[
  ('team_size','Team size (people working on A Story)',False,'Fallback for "team size" when no approved fact covers it.'),
  ('employees','Employees (paid, full-time)',False,'"Number of employees" and headcount questions.'),
  ('revenue_to_date','Revenue to date',False,'"Revenue to date" and "total revenue" lines, e.g. "$0, pre-revenue".'),
  ('funding_to_date','Funding raised to date',False,'"Total funding raised" lines, e.g. "$0, bootstrapped".'),
  ('next_round_target','Next round target',False,'"How much are you raising next" lines. Leave empty if there is no plan.'),
 ]),
]
STANDARD={k:(label,sensitive,used) for _,items in FIELDS for k,label,sensitive,used in items}
GROUP_OF={k:g for g,items in FIELDS for k,_,_,_ in items}

# Approved company facts that stand in when the vault is empty for a key.
FACT_FALLBACK={'legal_address':'headquarters','company_website':'website_url','team_size':'team_size','incorporation_date':'incorporation_date'}

# Question label (normalized: lowercase, punctuation removed) -> vault key. First match wins.
NOT_TYPE=r'^(?!.*\btype\b)'
RULES=[
 ('ein',r'\bein\b|\btax id\b|\btaxpayer id\b|employer identification|federal (tax )?id|\btin\b|\bfein\b'),
 ('mailing_address',r'mailing address|postal address'),
 ('incorporation_state',r'state of incorporation|incorporat\w*.*\b(state|where|jurisdiction)\b|\bjurisdiction\b|\b(where|which state).*incorporat'),
 ('incorporation_date',r'incorporat\w*.*\b(date|on|when|year)\b|\b(date|when|year).*incorporat|date of (incorporation|formation)|founded (on|date|in)|founding date|date founded|year founded|when (was|were) (your |the )?(company|startup|it) (founded|formed|established|started|incorporated)'),
 ('cofounder_linkedin_url',r'(team member 2|co ?founder|cofounder|daniel).*linkedin|linkedin.*(team member 2|co ?founder|cofounder|daniel)'),
 ('company_linkedin_url',r'(company|startup|organi[sz]ation|business).*linkedin|linkedin.*(company|startup|organi[sz]ation|business)'),
 ('linkedin_url',r'linkedin'),
 ('company_twitter_url',r'\btwitter\b|\bx com\b|\bx handle\b|\bx profile\b'),
 ('crunchbase_url',r'crunchbase'),
 ('deck_link',r'\bdeck\b.*\b(link|url)\b|\b(link|url)\b.*\bdeck\b|\bpitch deck\b|^deck$|\bslides? (link|url)\b'),
 ('demo_video_link',r'\b(video|loom|youtube|vimeo|multimedia)\b.*\b(link|url|pitch)\b|\b(link|url)\b.*\bvideo\b|\bdemo video\b|\bpitch video\b|\bvideo pitch\b|^video$'),
 ('app_store_link',r'app store|testflight|play store|link to (your )?(product|app)\b|\bproduct (link|url)\b|\bapp (link|url)\b'),
 ('cofounder_dob',r'(team member 2|co ?founder|cofounder|daniel).*(date of birth|birth ?date|\bdob\b|birthday)|(date of birth|birth ?date|\bdob\b|birthday).*(team member 2|co ?founder|cofounder|daniel)'),
 ('founder_dob',r'date of birth|birth ?date|\bdob\b|birthday'),
 ('cofounder_citizenship',r'(team member 2|co ?founder|cofounder|daniel).*(citizen|visa|immigration|work authori[sz]|resident|nationality)|(citizen|visa|immigration|work authori[sz]|resident|nationality).*(team member 2|co ?founder|cofounder|daniel)'),
 ('founder_citizenship',r'citizen|\bvisa\b|immigration status|work authori[sz]|permanent resident|nationality'),
 ('pronouns',r'pronoun'),
 ('phone',NOT_TYPE+r'.*\b(phone|mobile|cell|telephone)\b'),
 ('company_website',r'\bwebsite\b|\bhomepage\b|\bcompany url\b|url of your (company|startup)|\bweb address\b'),
 ('legal_address',NOT_TYPE+r'(?!.*\b(email|e mail|web|url|ip|wallet)\b).*\b(address|street)\b'),
 ('zip_code',r'\bzip\b|postal code|postcode'),
 ('city',r'^(?!.*\bstate\b).*\bcity\b'),
 ('state',r'^(?!.*\b(incorporat\w*|city|united|type|revenue|funding)\b).*\b(state|province)\b'),
 ('country',r'^(?!.*\b(incorporat\w*|registered)\b).*\bcountry\b'),
 ('next_round_target',r'\b(next|upcoming|current) (round|raise|fundrais\w*)\b|how much.*\b(raising|fundraise|looking to raise|seeking|plan to raise)\b|\btarget raise\b|\braise amount\b'),
 ('funding_to_date',r'\b(funding|capital|money|amount) (have you )?raised\b|raised to date|total (funding|capital|amount) raised|how much (have you|did you|funding|capital|money).*\braise[d]?\b|funding to date|external funding|outside (funding|capital|investment)'),
 ('revenue_to_date',r'revenue (to date|so far|generated|earned|last 12|in the (last|past)|this year)|total revenue|lifetime revenue|current (annual |monthly )?revenue|annual revenue|how much revenue'),
 ('team_size',r'team size|size of (your )?team|how many (people|team members|founders)|number of (team members|founders|people)'),
 ('employees',r'^(?!.*\bteam\b).*\b(employees|headcount|staff|full time)\b'),
]
COMPILED=[(k,re.compile(p)) for k,p in RULES]


def norm(text):return re.sub(r'[^a-z0-9 ]+',' ',(text or '').lower()).strip()


def slug(label):
    s=re.sub(r'[^a-z0-9]+','_',(label or '').lower()).strip('_')[:40]
    return s or 'other'


def mask(value):
    """The page never receives a sensitive value; it gets this token and a flag saying one is saved."""
    return MASK if value else ''


class FounderProfile:
    def __init__(self,store):
        self.store=store;self.db=store.db
        self.db.executescript(SCHEMA)

    # ---------- reading ----------
    def _rows(self):
        return {r['key']:dict(r) for r in self.db.execute('SELECT * FROM founder_profile')}

    def fields(self):
        """Every field for the page, sensitive values masked. Custom fields come last under Other."""
        saved=self._rows();out=[]
        for group,items in FIELDS:
            for key,label,sensitive,used in items:
                r=saved.get(key,{});value=r.get('value','') or ''
                out.append({'key':key,'group':group,'label':label,'sensitive':bool(sensitive),'used_for':used,'custom':False,
                            'set':bool(value),'value':None if sensitive else value,'masked':mask(value) if sensitive else '','updated_at':r.get('updated_at')})
        for key,r in sorted(saved.items(),key=lambda kv:kv[1]['label'].lower()):
            if key in STANDARD:continue
            value=r['value'] or '';sensitive=bool(r['sensitive'])
            out.append({'key':key,'group':'Other','label':r['label'],'sensitive':sensitive,'used_for':'Any form question whose label contains these words.','custom':True,
                        'set':bool(value),'value':None if sensitive else value,'masked':mask(value) if sensitive else '','updated_at':r['updated_at']})
        return out

    def board(self):
        f=self.fields()
        return {'fields':f,'groups':[g for g,_ in FIELDS]+['Other'],'filled':sum(1 for x in f if x['set']),'total':len(f)}

    def value(self,key):
        r=self.db.execute('SELECT value FROM founder_profile WHERE key=?',(key,)).fetchone()
        return (r[0] or '').strip() if r else ''

    def values(self):
        """Non-empty values by key, for the Form Filler. Sensitive ones included: they go into answers Bao copies, never into logs."""
        return {r['key']:r['value'].strip() for r in self.db.execute('SELECT key,value FROM founder_profile') if (r['value'] or '').strip()}

    def public_values(self):
        """Non-sensitive values only. The only part of the vault an AI drafter may ever see."""
        return {r['key']:r['value'].strip() for r in self.db.execute('SELECT key,value FROM founder_profile WHERE sensitive=0') if (r['value'] or '').strip()}

    def is_sensitive(self,key):
        if key in STANDARD:return STANDARD[key][1]
        r=self.db.execute('SELECT sensitive FROM founder_profile WHERE key=?',(key,)).fetchone()
        return bool(r and r[0])

    def reveal(self,key):
        """Owner click. The audit log records which key was revealed, never its value."""
        if key not in STANDARD and key not in self._rows():raise ValueError('Unknown profile field')
        self.store.log('founder_profile.revealed','owner',{'key':key})
        return {'key':key,'value':self.value(key)}

    # ---------- writing ----------
    def save(self,key,value,label=None,sensitive=None):
        value=str(value if value is not None else '').strip()
        if len(value)>MAX_VALUE:raise ValueError('Keep each profile value under 2000 characters')
        if key in STANDARD:
            std_label,std_sensitive,_=STANDARD[key]
            self.db.execute('INSERT INTO founder_profile(key,label,value,sensitive,custom,updated_at) VALUES(?,?,?,?,0,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
                            (key,std_label,value,int(std_sensitive),now()))
        else:
            existing=self.db.execute('SELECT label,sensitive FROM founder_profile WHERE key=?',(key,)).fetchone() if key else None
            label=(label or (existing['label'] if existing else '')).strip()
            if not label:raise ValueError('A custom profile field needs a label')
            key=key or slug(label)
            if not re.fullmatch(r'[a-z0-9_]{1,40}',key):raise ValueError('Profile field names use lowercase letters, digits and underscores')
            if BANK_WORDS.search(label) or BANK_WORDS.search(key):raise ValueError('Bank, card and password details never go in the profile. Enter those on the official form yourself.')
            flag=int(bool(sensitive)) if sensitive is not None else (int(existing['sensitive']) if existing else 0)
            self.db.execute('INSERT INTO founder_profile(key,label,value,sensitive,custom,updated_at) VALUES(?,?,?,?,1,?) ON CONFLICT(key) DO UPDATE SET label=excluded.label,value=excluded.value,sensitive=excluded.sensitive,updated_at=excluded.updated_at',
                            (key,label[:120],value,flag,now()))
        self.store.log('founder_profile.saved','owner',{'key':key,'set':bool(value)})
        return {'key':key,'set':bool(value)}

    def delete(self,key):
        if key in STANDARD:raise ValueError('Standard fields are cleared, not removed')
        self.db.execute('DELETE FROM founder_profile WHERE key=?',(key,))
        self.store.log('founder_profile.deleted','owner',{'key':key})
        return {'deleted':True}

    # ---------- mapping ----------
    def match(self,label):
        """Which vault key a form question asks for, or None. `label` is the question text without its options."""
        text=norm(label)
        if not text:return None
        for key,pattern in COMPILED:
            if pattern.search(text):return key
        for key,r in self._rows().items():
            if key in STANDARD or not (r['value'] or '').strip():continue
            words=[w for w in norm(r['label']).split() if len(w)>1]
            if words and all(re.search(r'\b'+re.escape(w)+r'\b',text) for w in words):return key
        return None


def match_key(label):
    """Rule-only mapping, without custom fields. Handy for tests and tools."""
    text=norm(label)
    for key,pattern in COMPILED:
        if text and pattern.search(text):return key
    return None
