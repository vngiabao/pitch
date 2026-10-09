"""Owner workspace links; publication is enabled only after live verification."""
import json,re
from pathlib import Path

PUBLIC_CONFIG=Path(__file__).resolve().parents[1]/'deploy/private/cloudflare.json'
LOCAL_ORIGIN='http://127.0.0.1:8765'
PUBLIC_ORIGIN='https://pitch.gbaonvo.com'

def public_site_enabled(config_path=None):
    try:
        c=Path(config_path or PUBLIC_CONFIG).read_text(encoding='utf-8-sig')
        c=json.loads(c)
        return (isinstance(c,dict) and c.get('report_links_enabled') is True
                and c.get('hostname')=='pitch.gbaonvo.com'
                and c.get('team_domain')=='astoryapp.cloudflareaccess.com'
                and c.get('email')=='gbao.n.vo@gmail.com'
                and isinstance(c.get('audience'),str)
                and bool(re.fullmatch(r'[a-fA-F0-9]{64}',c['audience'])))
    except (OSError,ValueError,TypeError):
        return False

def founder_url(path,config_path=None):
    if not isinstance(path,str) or not path.startswith('/') or path.startswith('//'):
        raise ValueError('Use a workspace-relative path')
    return (PUBLIC_ORIGIN if public_site_enabled(config_path) else LOCAL_ORIGIN)+path
