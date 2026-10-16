"""Loopback-only Founder OS command center, sharing the existing store."""
import json
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,quote
from .store import Store,PolicyError
from .funding_hunter import FundingHunter

class FounderServer(ThreadingHTTPServer):
    def __init__(self,db_path,port,access=None):
        self.db_path=db_path;self.token=secrets.token_urlsafe(32);self.access=access
        super().__init__(('127.0.0.1',port),Handler)

class Handler(BaseHTTPRequestHandler):
    server: FounderServer
    def log_message(self,*args):pass
    def _host_ok(self):
        if self.server.access:return self.headers.get('Host')==self.server.access.hostname
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def _identity_ok(self):
        return not self.server.access or self.server.access.authorized(self.headers.get('Cf-Access-Jwt-Assertion'))
    def _authorized(self):
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
        return bool(cookie.get('founder_session') and secrets.compare_digest(cookie['founder_session'].value,self.server.token))
    def respond(self,status,data,mime='application/json',cookie=False,filename=None,csp=None):
        raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',csp or "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'")
        if filename:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(filename,safe=''))
        if cookie:self.send_header('Set-Cookie',f'founder_session={self.server.token}; Path=/; HttpOnly; SameSite=Strict'+('; Secure' if self.server.access else ''))
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if not self._host_ok():return self.respond(403,{'error':'Host denied'})
        if not self._identity_ok():return self.respond(403,{'error':'Verified owner sign-in required'})
        p=urlsplit(self.path);route=p.path
        if route=='/' or route in ('/opportunities','/activity','/applications','/memory','/materials','/decisions','/pitches','/credits','/people','/press','/pitch-lab','/money') or route.startswith(('/opportunity/','/run/','/material/','/application-review/','/application/','/pitch/','/pitch-lab/')):
            html=(Path(__file__).with_name('ui')/'index.html').read_text(encoding='utf-8').replace('__CSRF__',self.server.token)
            return self.respond(200,html.encode(),'text/html',True)
        if route in ('/app.js','/pitch.js','/style.css','/edition.js','/edition.css','/vendor/gsap.min.js','/vendor/ScrollTrigger.min.js'):
            return self.respond(200,(Path(__file__).with_name('ui')/route[1:]).read_bytes(),'text/javascript' if route.endswith('.js') else 'text/css')
        if route in ('/fonts/mona-sans.woff2','/fonts/brygada-1918.woff2'):
            return self.respond(200,(Path(__file__).with_name('ui')/route[1:]).read_bytes(),'font/woff2')
        if not self._authorized():return self.respond(403,{'error':'Open the Founder OS command center first'})
        if route.startswith('/edition-asset/'):
            from . import slide_deck
            f=slide_deck.asset_path(route.rsplit('/',1)[1])
            if not f:return self.respond(404,{'error':'Image not found'})
            return self.respond(200,f.read_bytes(),slide_deck.MIME.get(f.suffix.lower(),'application/octet-stream'))
        s=Store(self.server.db_path)
        try:
            h=FundingHunter(s);q=parse_qs(p.query)
            if route.startswith('/edition/') or (route.startswith('/api/lab/') and route.endswith('/edition.zip')):
                from .pitch_lab import PitchLab
                from . import slide_deck
                lab=PitchLab(s);iid=route.split('/')[2] if route.startswith('/edition/') else route.split('/')[3];it=lab.item(iid);m=lab.edition_manifest(it)
                if not m:return self.respond(404,{'error':'This edition has no deck yet'})
                if route.endswith('/edition.zip'):return self.respond(200,slide_deck.edition_zip(m),'application/zip',filename='A-Story-'+iid+'-round-'+str(m['round'])+'.zip')
                page=slide_deck.preview_page(m,it['payload'].get('slide_qa'),it['title'])
                return self.respond(200,page.encode('utf-8'),'text/html',csp="default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; form-action 'none'")
            if route=='/api/pitches':
                from .pitch_studio import PitchStudio
                result=PitchStudio(s).list(q.get('q',[''])[0],q.get('audience',[''])[0],q.get('scenario',[''])[0],q.get('duration',[''])[0],q.get('archived',[''])[0]=='yes')
            elif route.startswith('/api/pitch/'):
                from .pitch_studio import PitchStudio
                studio=PitchStudio(s);parts=route.strip('/').split('/');key=parts[2]
                if len(parts)==4 and parts[3]=='export':return self.respond(200,studio.export(key,q.get('version',[None])[0]).encode('utf-8'),'text/plain',filename='A-Story-pitch-'+key+'.txt')
                result=studio.detail(key)
            elif route=='/api/materials':
                from .materials_library import MaterialsLibrary
                result=MaterialsLibrary(s).search(q.get('q',[''])[0],q.get('kind',[''])[0],q.get('category',[''])[0],q.get('offset',[0])[0],duplicates=q.get('duplicates',[''])[0]=='yes')
            elif route=='/api/materials-manifest':
                from .materials_library import MaterialsLibrary
                return self.respond(200,MaterialsLibrary(s).manifest().encode('utf-8'),'application/json',filename='A-Story-pitch-materials-manifest.json')
            elif route.startswith('/api/material/'):
                from .materials_library import MaterialsLibrary
                lib=MaterialsLibrary(s);parts=route.strip('/').split('/');key=parts[2]
                if len(parts)==4 and parts[3]=='file':
                    import shutil
                    original=lib.original(key)
                    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(original.name,safe=''));self.send_header('Content-Length',str(original.stat().st_size));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
                    with original.open('rb') as f:shutil.copyfileobj(f,self.wfile,1024*1024)
                    return
                result=lib.detail(key)
            elif route=='/api/review/export':
                from .application_pilot import ApplicationPilot
                from .application_review import ApplicationReview
                ApplicationPilot(s);a=ApplicationReview(s).snapshot(q.get('plan',[None])[0])
                return self.respond(200,a['content'].encode('utf-8'),'text/plain',filename=a['filename'])
            elif route.startswith('/api/review-file/'):
                from .application_review import ApplicationReview
                a=ApplicationReview(s).attachment(route.rsplit('/',1)[1]);return self.respond(200,a['content'].encode('utf-8'),'text/plain',filename=a['filename'])
            elif route.startswith('/api/application-review/'):
                from .application_pilot import ApplicationPilot
                from .application_review import ApplicationReview
                ApplicationPilot(s);result=ApplicationReview(s).plan(route.rsplit('/',1)[1])
            elif route=='/api/dashboard':
                from .inbox_tracker import InboxTracker
                result=h.dashboard();result['inbox']=InboxTracker(s,h).dashboard()
            elif route=='/api/inbox':
                from .inbox_tracker import InboxTracker
                result=InboxTracker(s,h).dashboard()
            elif route=='/api/tracker/export.csv':
                from .inbox_tracker import InboxTracker
                from datetime import date
                return self.respond(200,InboxTracker(s,h).export_csv().encode('utf-8'),'text/csv',filename='A-Story-application-tracker-'+date.today().isoformat()+'.csv')
            elif route=='/api/shortlist':result=h.daily_shortlist()
            elif route=='/api/opportunities':result=h.list(q.get('view',['Recommended'])[0],{k:v[0] for k,v in q.items() if k!='view'})
            elif route.startswith('/api/opportunity/'):result=h.detail(route.rsplit('/',1)[1])
            elif route.startswith('/api/application/'):result=h.application_view(route.rsplit('/',1)[1])
            elif route=='/api/application-list':
                from .application_drafter import application_list
                result=application_list(s)
            elif route in ('/api/credits','/api/people','/api/press','/api/growth-alerts'):
                from .growth_agents import Growth
                g=Growth(s);result={'/api/credits':g.credits,'/api/people':g.contacts,'/api/press':g.press,'/api/growth-alerts':g.alerts}[route]()
            elif route=='/api/lab':
                from .pitch_lab import PitchLab
                result=PitchLab(s).board()
            elif route.startswith('/api/lab/'):
                from .pitch_lab import PitchLab
                lab=PitchLab(s);result=lab.item(route.rsplit('/',1)[1]);result['program_detail']=lab.program_context(result['opportunity_id'])
            elif route=='/api/lab-options':
                from .pitch_studio import PitchStudio
                from .application_drafter import application_list
                seen=set();programs=[]
                for d in h.list('All'):
                    n=d['data']['canonical_name'].strip()
                    if n.lower() in seen or d['recommendation'] in ('EXPIRED','SKIP','REJECTED'):continue
                    seen.add(n.lower());programs.append({'id':d['opportunity_id'],'name':n,'type':d['data']['opportunity_type'],'deadline':d['data']['dates'].get('deadline')})
                result={'programs':sorted(programs,key=lambda x:x['name'].lower()),'pitches':[{'id':x['pitch_id'],'title':x['title']} for x in PitchStudio(s).list()['items']],
                        'applications':[{'id':a['application_id'],'program':a['program']} for a in application_list(s) if a.get('questions')]}
            elif route=='/api/lab-alerts':
                from .pitch_lab import PitchLab
                result=PitchLab(s).alerts()
            elif route=='/api/money':
                from .money_map import MoneyMap
                result=MoneyMap(s).board()
            elif route=='/api/applications':result=s.rows('SELECT a.*,o.program,o.cycle FROM applications a JOIN opportunities o ON o.id=a.opportunity_id')
            elif route=='/api/autonomy':
                from .application_pilot import ApplicationPilot
                from .report_email import credential_present
                result=ApplicationPilot(s).dashboard();delivery=h.settings().get('mail_delivery',{});result['mail_delivery']=delivery;smtp=credential_present();result['smtp_fallback_connected']=smtp;result['mail_connected']=smtp or (delivery.get('mode')=='gmail_connector' and delivery.get('profile_verified') is True);result['report_schedule']=h.settings().get('daily_report',{});result['credits_schedule']=h.settings().get('credits_schedule',{})
            elif route.startswith('/api/report/'):
                from .application_pilot import ApplicationPilot
                ApplicationPilot(s)
                result=s.one('SELECT id,local_date,subject,body,state FROM daily_reports WHERE id=?',(route.rsplit('/',1)[1],))
                from .application_review import ApplicationReview
                result['attachments']=[{k:v for k,v in a.items() if k!='content'} for a in ApplicationReview(s).report_attachment(result['id'])]
            elif route=='/api/answers':result=s.rows('SELECT a.id,a.body,a.created_at,r.status,q.prompt,q.limit_value,q.limit_unit FROM answer_versions a JOIN answer_reviews r ON r.version_id=a.id JOIN questions q ON q.id=a.question_id')
            elif route.startswith('/api/run/'):
                r=s.one('SELECT * FROM funding_runs WHERE id=?',(route.rsplit('/',1)[1],));result={**r,'report':json.loads(r['report_json'])}
            else:return self.respond(404,{'error':'Route not found'})
            self.respond(200,result)
        except (ValueError,TypeError,KeyError) as e:self.respond(400,{'error':str(e)})
        finally:s.close()
    def do_POST(self):
        if not self._host_ok() or not self._identity_ok() or not self._authorized() or not secrets.compare_digest(self.headers.get('X-Founder-CSRF',''),self.server.token):return self.respond(403,{'error':'Owner session required'})
        origin=self.headers.get('Origin')
        allowed_origins=(f'https://{self.server.access.hostname}',) if self.server.access else (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')
        if origin not in allowed_origins:return self.respond(403,{'error':'Origin denied'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.respond(415,{'error':'JSON request required'})
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:return self.respond(400,{'error':'Invalid request length'})
        if not 0<length<=65536:return self.respond(413,{'error':'Request size denied'})
        s=Store(self.server.db_path)
        try:
            p=json.loads(self.rfile.read(length));h=FundingHunter(s);route=urlsplit(self.path).path
            if route=='/api/pitches':
                from .pitch_studio import PitchStudio
                result=PitchStudio(s).create(p)
            elif route.startswith('/api/pitch/'):
                from .pitch_studio import PitchStudio
                studio=PitchStudio(s);parts=route.strip('/').split('/');key=parts[2]
                result=studio.restore(key,p['version_id'],p.get('expected_version_id')) if len(parts)==4 and parts[3]=='restore' else studio.save(key,p)
            elif route=='/api/run-now':
                result=h.request_run(p.get('reason','Founder requested broad scan'))
                self.start_worker()
            elif route=='/api/decision':result=h.decide(p['opportunity_id'],p['decision'],p['reason'])
            elif route=='/api/outcome':result=h.owner_outcome(p['opportunity_id'],p['outcome'],p.get('note',''),p.get('evidence_url'),p.get('application_id'))
            elif route=='/api/start-application':result={'application_id':h.start_application(p['opportunity_id']),'external_submission':False}
            elif route=='/api/read-form':
                from .application_drafter import ApplicationDrafter
                from .form_reader import BrowserFormReader
                result=ApplicationDrafter(s,BrowserFormReader(Path(self.server.db_path).parent/'browser-profile')).read_form(p['opportunity_id'])
                if result.get('draft_queued'):self.start_worker()
            elif route=='/api/prepare-application':
                from .application_pilot import ApplicationPilot
                result=ApplicationPilot(s).build(p['opportunity_id'])
            elif route=='/api/application-confirm':
                from .application_pilot import ApplicationPilot
                result=ApplicationPilot(s).confirm(p['confirmation_id'],p['decision'],p.get('confirmed',False))
                self.start_autonomy_worker()
            elif route=='/api/autonomy-pause':
                from .application_pilot import ApplicationPilot
                ApplicationPilot(s).revoke(p['authorization_id']);result={'paused':True}
            elif route=='/api/autonomy-resume':
                from .application_pilot import ApplicationPilot
                from .store import now
                if p.get('confirmed') is not True:raise PolicyError('Explicit owner resume action needed')
                scope=p['scope']
                if scope not in ('free_application_pilot','daily_email_report'):raise PolicyError('Unknown scope')
                old=s.one('SELECT payload_json,owner_instruction FROM autonomy_authorizations WHERE scope=? ORDER BY granted_at DESC LIMIT 1',(scope,))
                result={'authorization_id':ApplicationPilot(s).authorize(scope,json.loads(old['payload_json']),old['owner_instruction']+' | Owner resumed in command center at '+now())}
            elif route=='/api/report-now':
                from .report_email import DailyReporter
                result=DailyReporter(s).prepare();self.start_autonomy_worker()
            elif route=='/api/connect-report-email':
                script=Path(__file__).resolve().parents[1]/'Connect-Report-Email.ps1'
                subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
                result={'setup_opened':True,'email_sent':False}
            elif route=='/api/inbox-decision':
                from .inbox_tracker import InboxTracker
                if p.get('confirmed') is not True:raise PolicyError('Explicit confirmation needed')
                result=InboxTracker(s,h).decide(p['id'],p['decision'],p.get('outcome') or None)
            elif route=='/api/connect-inbox':
                from .report_email import INBOX_ACCOUNTS
                if p.get('account') not in INBOX_ACCOUNTS:raise PolicyError('Mailbox is outside owner authorization')
                script=Path(__file__).resolve().parents[1]/'Connect-Inbox.ps1'
                subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-Account',p['account']],creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
                result={'setup_opened':True,'email_sent':False}
            elif route=='/api/research':
                h.detail(p['opportunity_id'])
                result=h.request_run('Research opportunity '+p['opportunity_id'])
                self.start_worker()
            elif route=='/api/approval':
                if p.get('confirmed') is not True:raise PolicyError('Explicit confirmation needed')
                s.decide(p['approval_id'],p['decision'],True,p.get('note','Founder decision in local command center'));result={'decided':True}
            elif route=='/api/approval-edit':
                if p.get('confirmed') is not True:raise PolicyError('Explicit confirmation needed')
                result=h.owner_edit_claim(p['approval_id'],p.get('body',''))
            elif route in ('/api/credit','/api/person','/api/person-update','/api/person-touch','/api/growth-draft','/api/press-state','/api/press-discover'):
                from .growth_agents import Growth
                g=Growth(s)
                if route=='/api/credit':result=g.update_credit(p['id'],p)
                elif route=='/api/person':result=g.add_contact(p)
                elif route=='/api/person-update':result=g.update_contact(p['id'],p)
                elif route=='/api/person-touch':result=g.log_touch(p['id'],p)
                elif route=='/api/press-state':result=g.set_press_state(p['id'],p['state'])
                else:
                    result=g.queue_draft(p['kind'],p['id'],manual=True) if route=='/api/growth-draft' else g.request_press_discovery()
                    self.start_worker()
            elif route in ('/api/lab-edition','/api/lab-review','/api/lab-application','/api/lab-rerun','/api/lab-approve','/api/lab-save','/api/lab-build','/api/lesson'):
                from .pitch_lab import PitchLab
                lab=PitchLab(s)
                if route=='/api/lab-edition':result=lab.start_edition(p['opportunity_id'],p.get('minutes',3),p.get('slide_limit') or None,p.get('note',''))
                elif route=='/api/lab-review':result=lab.start_review(p['pitch_id'])
                elif route=='/api/lab-application':result=lab.start_application(p['application_id'])
                elif route=='/api/lab-rerun':result=lab.rerun(p['id'],p.get('note',''))
                elif route=='/api/lab-approve':result=lab.approve(p['id'])
                elif route=='/api/lab-save':result=lab.save_to_studio(p['id'])
                elif route=='/api/lab-build':result={k:v for k,v in lab.build_now(p['id']).items() if k!='payload'}
                else:result=lab.decide_lesson(p['id'],p['decision'])
                if route in ('/api/lab-edition','/api/lab-review','/api/lab-application','/api/lab-rerun'):
                    result={k:v for k,v in result.items() if k!='payload'};self.start_worker()
            elif route=='/api/money-move':
                from .money_map import MoneyMap
                result=MoneyMap(s).set_move(p['id'],p['state'])
            elif route=='/api/notification-read':
                s.db.execute('UPDATE funding_notifications SET read_at=datetime(\'now\') WHERE id=?',(p['id'],));result={'read':True}
            else:return self.respond(404,{'error':'Action not available'})
            self.respond(200,result)
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
            from .pitch_studio import PitchConflict
            self.respond(409 if isinstance(e,PitchConflict) else 400,{'error':str(e)})
        finally:s.close()

    def start_worker(self):
        runner=Path(__file__).resolve().parents[1]/'tools/research_worker.py'
        subprocess.Popen([sys.executable,str(runner),'--db',str(self.server.db_path)],cwd=runner.parent.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def start_autonomy_worker(self):
        runner=Path(__file__).resolve().parents[1]/'tools/autonomy_worker.py'
        subprocess.Popen([sys.executable,str(runner),'--db',str(self.server.db_path)],cwd=runner.parent.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def serve(db_path,port=8765,access=None):
    server=FounderServer(db_path,port,access)
    url=f'https://{access.hostname}' if access else f'http://127.0.0.1:{server.server_port}'
    print(json.dumps({'founder_os_url':url,'store':str(db_path),'scope':'verified Cloudflare owner only' if access else 'local owner only'}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
