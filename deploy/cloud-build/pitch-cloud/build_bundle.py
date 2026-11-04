"""Bundle source and assets; runtime data is migrated separately."""
import base64,io,json,re,zipfile,os
import tzdata
from pathlib import Path
root=Path(__file__).resolve().parent
source=root.parent/'pitch'
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    tzroot=Path(tzdata.__file__).parent
    tzbuf=io.BytesIO()
    with zipfile.ZipFile(tzbuf,'w',zipfile.ZIP_DEFLATED) as tz:
        for p in tzroot.rglob('*'):
            if p.is_file() and p.suffix!='.pyc':tz.writestr('tzdata/'+p.relative_to(tzroot).as_posix(),p.read_bytes())
    z.writestr('timezones.zip',tzbuf.getvalue())
    for p in sorted((source/'founder_os').rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:continue
        data=p.read_bytes()
        if p.as_posix().endswith('/ui/app.js'):
            t=data.decode().replace('Download original</a></div><details', '${m.cloud_copy_notice?\'Download current copy\':\'Download original\'}</a></div>${m.cloud_copy_notice?`<p class="small">${E(m.cloud_copy_notice)}</p>`:\'\'}<details')
            t=t.replace('Daily email at 9 AM Eastern. Nothing is ever submitted for you.','Cloud workspace is online. Research runs and scheduled email are not connected.')
            data=t.encode()
        if p.as_posix().endswith('/ui/index.html'):
            data=data.decode().replace('class="rail-run" data-action="run"','class="rail-run" disabled title="Research automation is not connected to this cloud workspace"').replace('Run research now</button>','Research not connected</button>').encode()
        if p.name in ('report_email.py','product_desk.py'):
            t=data.decode().replace('\r\n','\n').replace('import ctypes,json,smtplib,ssl','import json,smtplib,ssl\nfrom types import SimpleNamespace\nctypes=SimpleNamespace()').replace('import ctypes\n','from types import SimpleNamespace\nctypes=SimpleNamespace()\n').replace('from ctypes import wintypes\n','')
            if p.name=='report_email.py':t=re.sub(r'class Credential\(ctypes.Structure\):.*?\n\ndef credential_target','Credential=None\n\ndef credential_target',t,flags=re.S)
            data=t.encode()
        z.writestr(p.relative_to(source).as_posix(),data)
    z.writestr('deploy/private/cloudflare.json',json.dumps({'hostname':'pitch.gbaonvo.com','team_domain':'astoryapp.cloudflareaccess.com','audience':'31a9f790dee8455b1ed8591943c3cd0ac020e55bcc7832c22afc0fa54be96aa9','email':'gbao.n.vo@gmail.com','report_links_enabled':True}))
(root/'app_bundle.tmp').write_text('ARCHIVE = '+repr(base64.b64encode(buf.getvalue()).decode())+'\n')
os.replace(root/'app_bundle.tmp',root/'app_bundle.py')
print(json.dumps({'source_archive_bytes':len(buf.getvalue()),'private_database_bundled':False}))
