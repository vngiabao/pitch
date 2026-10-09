"""Exact-message CLI bridge used by the scheduled chat's connected Gmail tools."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,PolicyError
from founder_os.connector_outbox import ConnectorOutbox

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['pending','claim','complete','uncertain']);p.add_argument('--kind',choices=['report','preview','supplement']);p.add_argument('--id');p.add_argument('--receipt');args=p.parse_args()
    s=Store(ROOT/'data/founder.sqlite');o=ConnectorOutbox(s)
    try:
        if args.action=='pending':result=o.pending()
        elif args.action=='claim':result=o.claim(args.kind,args.id)
        elif args.action=='complete':
            r=json.loads(Path(args.receipt).read_text(encoding='utf-8-sig'));result=o.complete(args.kind,args.id,r['message_sha256'],r['gmail_message_id'],r['account'])
        else:result=o.uncertain(args.kind,args.id)
        # ASCII JSON escapes survive Windows consoles with non-UTF8 encodings.
        print(json.dumps(result,ensure_ascii=True));return 0
    except PolicyError as e:print(json.dumps({'blocked':str(e)}));return 1
    finally:s.close()
if __name__=='__main__':raise SystemExit(main())
