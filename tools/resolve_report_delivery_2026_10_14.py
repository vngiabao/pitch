"""Owner decisions of October 14, 2026 on daily-report delivery.

1. Enable the SMTP fallback: if the connected Gmail sender has not claimed today's
   report 30 minutes after the 9:00 schedule, the autonomy task sends it locally.
   It needs the app password in Windows Credential Manager (Connect-Report-Email.ps1).
2. Supersede the Oct 11 and Oct 13 reports. Both were never claimed, so they were
   never sent; their shortlists predate the money-first ranking. Nothing is emailed.
Takes a consistent database backup first. Idempotent.
"""
import json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now,js
from founder_os.funding_hunter import FundingHunter
from founder_os.report_email import DailyReporter

MISSED=('2026-10-11','2026-10-13')
REASON='owner chose not to send this stale shortlist on Oct 14, 2026; the Oct 14 report replaced it'


def backup(db_path):
    target=db_path.parent/'repair-backups'/('before-report-delivery-'+now()[:19].replace(':','')+'.sqlite')
    target.parent.mkdir(exist_ok=True)
    src=sqlite3.connect(db_path);dst=sqlite3.connect(target)
    with dst:src.backup(dst)
    src.close();dst.close();return target


def main():
    db_path=ROOT/'data/founder.sqlite'
    saved=backup(db_path)
    s=Store(db_path)
    try:
        h=FundingHunter(s);reporter=DailyReporter(s)
        with s.transaction():
            mail=h.settings().get('mail_delivery',{})
            if not (mail.get('smtp_fallback') or {}).get('enabled'):
                mail['smtp_fallback']={'enabled':True,'after_minutes':30,'transport':'gmail_smtp_tls','credential':'Windows Credential Manager','approved_by':'owner','approved_at':now()}
                s.db.execute("UPDATE hunter_settings SET value_json=? WHERE key='mail_delivery'",(js(mail),))
                s.log('report.smtp_fallback_enabled','owner',mail['smtp_fallback'])
        reports=[]
        for day in MISSED:
            r=s.one('SELECT id,state FROM daily_reports WHERE local_date=?',(day,))
            if r['state']!='SUPERSEDED':r=reporter.supersede(r['id'],REASON)
            reports.append({'local_date':day,'id':r['id'],'state':r['state']})
        print(json.dumps({'backup':str(saved),'smtp_fallback':h.settings()['mail_delivery']['smtp_fallback'],'reports':reports},indent=2))
    finally:s.close()


if __name__=='__main__':main()
