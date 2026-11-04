"""Socket-free adapter preserving the existing domain handlers."""
import io
from email.message import Message
from types import SimpleNamespace
from founder_os.server import Handler
UNCONNECTED_ACTIONS={'/api/run-now','/api/research','/api/read-form','/api/report-now','/api/connect-report-email','/api/connect-inbox','/api/application-confirm'}
class CloudHandler(Handler):
    def _identity_ok(self):return True # Caller verifies signed JWT before dispatch.
    def send_response(self,status,message=None):self.result_status=status
    def send_header(self,name,value):self.result_headers[name]=str(value)
    def end_headers(self):pass
    def start_worker(self):raise ValueError('Cloud research is not connected yet. Request queued; no research was run.')
    def start_autonomy_worker(self):raise ValueError('Cloud email/application workers are not connected yet. Nothing was sent or submitted.')
def dispatch(db_path,token,method,path,headers,body):
    h=CloudHandler.__new__(CloudHandler);h.path=path;h.command=method;h.headers=Message()
    for k,v in headers.items():h.headers[k]=v
    h.headers['Host']='pitch.gbaonvo.com';h.headers['Content-Length']=str(len(body))
    h.rfile=io.BytesIO(body);h.wfile=io.BytesIO();h.result_status=500;h.result_headers={}
    h.server=SimpleNamespace(db_path=str(db_path),token=token,access=SimpleNamespace(hostname='pitch.gbaonvo.com'))
    if method=='POST' and path.split('?')[0] in UNCONNECTED_ACTIONS:h.respond(503,{'error':'This desktop research/email action is not connected to cloud automation yet. Your saved workspace is available; nothing was sent or submitted.'})
    elif method=='GET':h.do_GET()
    elif method=='POST':h.do_POST()
    else:h.respond(405,{'error':'Method not allowed'})
    h.result_headers['X-Pitch-Hosting']='cloudflare-python-durable-object'
    return h.result_status,h.result_headers,h.wfile.getvalue()
