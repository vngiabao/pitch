"""Save a corrected version of the Oct 14 three-minute pitch with the survey stats from
the Oct 14 slides (owner: "slide is definitely more reliable than script").

Slides (Ancestry/OnePoll 2023): 79% want to know more; 37% know their mom's life
before kids; 74% regret not learning more. Keeps every earlier version.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.pitch_studio import PitchStudio

SEED='pitch-mbc-3min-2026-10-14'
OLD_STAT="Seventy-four percent of adult children want to know more about their parents' lives before parenthood, but only thirty-seven percent knew their mother's early life."
NEW_STAT="Seventy-nine percent of adults want to know more about their parents' lives, but only thirty-seven percent know their mother's life before kids."
OLD_NOTE="3. Survey stats (74% / 37%): add the source to the slide footnote. The 79% regret figure was dropped for time; add it back only with its source."
NEW_NOTE="3. Survey stats now match the Oct 14 slides (Ancestry/OnePoll 2023): 79% want to know more, 37% know their mom's life before kids, 74% regret not learning more. The 74% regret line was dropped for time."

def main():
    s=Store(ROOT/'data/founder.sqlite')
    try:
        studio=PitchStudio(s);pid=s.one('SELECT pitch_id FROM pitch_seed_keys WHERE seed_key=?',(SEED,))['pitch_id']
        cur=studio.detail(pid)
        if NEW_STAT in cur['body']:print(json.dumps({'pitch_id':pid,'changed':False}));return
        if OLD_STAT not in cur['body']:raise SystemExit('Pitch text was edited since the Oct 14 draft; fix the stats by hand in Pitch Studio.')
        fields={k:cur[k] for k in ('title','duration_seconds','audience','scenario','speaker','format','status','sources','claim_versions')}
        fields.update(body=cur['body'].replace(OLD_STAT,NEW_STAT),notes=cur['notes'].replace(OLD_NOTE,NEW_NOTE),
                      change_note='Survey stats corrected to match the Oct 14 slides (79% / 37%)',expected_version_id=cur['id'])
        new=studio.save(pid,fields)
        print(json.dumps({'pitch_id':pid,'changed':True,'version_id':new['id'],'word_count':new['word_count']}))
    finally:s.close()

if __name__=='__main__':main()
