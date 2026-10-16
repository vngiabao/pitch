"""Bounded local coordinator: daily credits discovery, free applications, email."""
import argparse,json,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now,js,uid
from founder_os.application_pilot import ApplicationPilot
from founder_os.report_email import DailyReporter
from founder_os.inbox_tracker import InboxTracker
from founder_os.application_drafter import ApplicationDrafter
from founder_os.form_reader import BrowserFormReader
from founder_os.growth_agents import Growth
from founder_os.growth_desk import GrowthDesk
from founder_os.pitch_lab import PitchLab

def poll(s):
    p=ApplicationPilot(s);h=p.h;instant=datetime.now(timezone.utc)
    with s.transaction():
        lock=s.db.execute("SELECT value_json FROM hunter_settings WHERE key='autonomy_lock'").fetchone()
        if lock and datetime.fromisoformat(json.loads(lock['value_json'])['until'])>instant:return {'busy':True}
        token=uid('autonomy-lock');s.db.execute('INSERT INTO hunter_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json',('autonomy_lock',js({'token':token,'until':(instant+timedelta(minutes=4)).isoformat()})))
    try:
        schedule=h.settings().get('credits_schedule',{'enabled':True,'hour':7,'minute':30,'timezone':'America/New_York'})
        local=instant.astimezone(ZoneInfo(schedule['timezone']))
        if schedule.get('enabled') and (local.hour,local.minute)>=(schedule['hour'],schedule['minute']):h.request_run('Daily free credits discovery',key='daily-credits-'+local.date().isoformat())
        applications=p.poll();report=DailyReporter(s).poll(instant)
        # Read-only inbox check last, so a slow mailbox never delays reports or applications.
        try:inbox=InboxTracker(s,h).poll(instant)
        except Exception as e:s.log('inbox.failed','autonomy_worker',{'error_type':type(e).__name__});inbox={'error':type(e).__name__}
        # Read one official application form per cycle (read-only) and queue answer drafts.
        try:forms=ApplicationDrafter(s,BrowserFormReader(ROOT/'data/browser-profile')).poll(limit=1)
        except Exception as e:s.log('forms.failed','autonomy_worker',{'error_type':type(e).__name__,'error':str(e)[:300]});forms={'error':type(e).__name__}
        # Growth agents: one follow-up or press draft per cycle, press discovery twice a week.
        try:growth=Growth(s).poll(limit=1)
        except Exception as e:s.log('growth.failed','autonomy_worker',{'error_type':type(e).__name__,'error':str(e)[:300]});growth={'error':type(e).__name__}
        # Growth desk: one deal note per cycle, Partner Scout on Tuesday mornings.
        try:desk=GrowthDesk(s).poll(limit=1)
        except Exception as e:s.log('growth_desk.failed','autonomy_worker',{'error_type':type(e).__name__,'error':str(e)[:300]});desk={'error':type(e).__name__}
        # Pitch Lab: harvest Bao's edits and results, start reviews, keep every item moving.
        try:lab=PitchLab(s).poll()
        except Exception as e:s.log('lab.failed','autonomy_worker',{'error_type':type(e).__name__,'error':str(e)[:300]});lab={'error':type(e).__name__}
        return {'application_pilot':applications,'daily_report':{'id':report.get('id'),'state':report.get('state','WAITING')},'inbox':inbox,'forms':forms,'growth':growth,'growth_desk':desk,'lab':lab}
    finally:
        with s.transaction():
            lock=s.db.execute("SELECT value_json FROM hunter_settings WHERE key='autonomy_lock'").fetchone()
            if lock and json.loads(lock['value_json'])['token']==token:s.db.execute("DELETE FROM hunter_settings WHERE key='autonomy_lock'")

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--poll',action='store_true');parser.add_argument('--db',default=str(ROOT/'data/founder.sqlite'));args=parser.parse_args();s=Store(args.db)
    try:print(json.dumps(poll(s)));return 0
    except Exception as e:s.log('autonomy.failed','autonomy_worker',{'error_type':type(e).__name__});return 1
    finally:s.close()
if __name__=='__main__':raise SystemExit(main())
