import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store
from founder_os.agents import Founder


def main():
    s=Store(ROOT/'data'/'founder.sqlite');f=Founder(s);summary=json.loads((ROOT/'reports'/'migration-summary.json').read_text(encoding='utf-8'))
    approvals=s.rows("SELECT * FROM approvals WHERE state='pending' ORDER BY requested_at")
    issues=s.rows("SELECT * FROM issues WHERE state='open' ORDER BY created_at")
    jobs=s.rows('SELECT capability,state,attempts,error FROM jobs ORDER BY created_at')
    parts=['# A Story Founder OS Review',
           'October 4, 2026. This is a saved review snapshot of the working local foundation, not a live connection or an autonomous service. The seven local capability checks completed. No source file was changed, no company fact was approved, and no application or message was sent.',
           '## 1 Needs my decision',
           'Five proposed fact reviews are waiting. Confirm the underlying evidence or provide corrections; do not approve a draft simply to clear the queue. Language changes can proceed while these facts remain unresolved.']
    for approval in approvals:
        payload=json.loads(approval['payload_json']);v=s.one('SELECT v.*,c.label,c.topic FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=?',(payload['version_id'],))
        source=s.one('SELECT s.original_path FROM source_versions v JOIN sources s ON s.id=v.source_id WHERE v.id=?',(v['source_version_id'],))
        parts += [f"### {v['label']}",payload['decision_needed'],f"**Current proposal:** {v['body']}",f"Status: unapproved, {v['evidence_status']}. Source: `{source['original_path']}`, {v['locator']}. Review ID: `{approval['id']}`."]
    parts += ['## 2 Agent activity','These are implemented deterministic tools under the Founder dispatcher. Model reasoning, live web research and external connectors are not connected. No automatic schedule is running.']
    descriptions={
      'opportunity_scout':'Registered/deduplicated supplied MBC and ElevenLabs records. Unknown eligibility kept the fit scores unknown.',
      'application':'Checked nine essay questions, raw variants and revised answers. No application was marked submission-ready.',
      'research':'Retrieved passages from selected local research snapshots with path, hash and line citations.',
      'consistency_truth':'Checked registered source hashes and flagged specific risky wording in the essay. This is not an exhaustive semantic audit.',
      'follow_up':'Reviewed deadlines. None is currently verified enough for scheduling.',
      'customer_evidence':'Registered one reported pilot learning as unverified internal evidence.',
      'pitch':'Registered a 30-second narrative draft with linked proposed claims and an estimated speaking time; no rehearsal or approval recorded.'}
    for job in jobs:parts.append(f"- **{job['capability'].replace('_',' ').title()}: {job['state']}.** {descriptions[job['capability']]}")
    parts += ['## 3 New opportunities','No live discovery scan was performed. Three existing program records provide the starting queue: the F6S competition draft, historical MBC materials and ElevenLabs grant research. All need current-cycle verification. None has a verified deadline, eligibility decision or automatic apply recommendation.']
    parts += ['## 4 Applications in progress','The F6S essay review holds **nine parsed essay prompts, nine preserved raw draft sections and nine revised internal answers**. Seven prompts have explicit character limits in the essay. The short description has no stated limit, and the source question wording/limits still need comparison with the actual current form. Non-essay fields and required attachments have not been declared complete.',
             'The revised drafts lead with the phone-interview workflow, frame family context as a hypothesis, separate waiting buyers from paying customers, qualify economics and remove sweeping competitor/retention claims. Some answers intentionally contain review wording; they are not submission-ready copy.',
             'There are no approved answers yet. When an exact version is approved, the answer bank can retrieve it. If its canonical evidence changes, it becomes stale for reuse while historical versions remain preserved.']
    # Count directly to avoid assumptions about the imported template.
    limited=s.db.execute('SELECT count(*) FROM questions WHERE limit_value IS NOT NULL').fetchone()[0]
    parts[-3]=parts[-3].replace('Seven prompts',str(limited)+' prompts')
    parts += ['## 5 Upcoming deadlines','No current deadline is verified. The MBC form belongs to the 2025–2026 cycle; the saved F6S material contains conflicting September deadline references. They remain research tasks rather than scheduled reminders. This avoids generating false urgency from historical dates.']
    parts += ['## 6 Knowledge inconsistencies','The review queue has '+str(len(issues))+' items. In addition to the five fact decisions above:']
    for issue in issues:
        if issue['kind']=='confirmation':continue
        detail=issue['detail']
        if detail.startswith('['):
            matches=json.loads(detail);detail='Flagged in the supplied essay at '+', '.join('line '+str(x['line']) for x in matches)+'. Review the wording against evidence before reuse.'
        parts.append(f"- **{issue['title']}.** {detail}")
    parts += ['## 7 Recent submissions and results','No confirmed submission snapshot or organizer result was imported. The local history query for NVIDIA returns no records. It does not invent an answer using current memory. Prepared drafts and analyst rejection commentary remain separate from actual submissions and organizer feedback.',
             '## Migration state',f"Registered {summary['source_versions']} source versions: 23 selected references and the two supplied attachments. Twelve claim proposals cover all requested memory topics; zero are approved as canonical. Bounded text snapshots are stored for selected narrative sources and the essay. Native decks, images and code remain references.",
             'The new taxonomy covers all 103,159 inventoried paths. It supplements the original KEEP/MERGE/ARCHIVE/IGNORE manifest without replacing it. No file is labeled CANONICAL KNOWLEDGE or HISTORICAL SUBMISSION without approval/evidence. The import ledger maps every imported record to its original path, fingerprint and source locator.',
             '## Verification and next build boundary','The local invariant tests cover idempotent ingestion, changed sources, human-only canonical promotion, stale approvals, answer limits, current approved-answer reuse, immutable submissions and file bytes, denied external actions, durable jobs, unknown fit scores and historical deadlines. See the packaged test results for the current run.',
             'Next implementation stages are deployed Pitch OS export/reconciliation, a chosen model and research connector, general application extraction, additional pitch durations, authenticated review controls and remote access, then an explicitly activated background service. Costs and external actions require approval. No current cloud-model connection is required to use this local foundation.']
    (ROOT/'reports'/'review.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    drafts=json.loads((ROOT/'draft-answers.json').read_text(encoding='utf-8'))
    essay=['# A Story Revised Essay Working Drafts','These are review drafts, not approved answers or a submission-ready package. The original attachment is preserved as a source snapshot. Factual assertions, personal details and program requirements require confirmation. Wording permission does not establish their truth. Character counts below include spaces and line breaks.']
    for draft in drafts:
        essay.extend(['## '+draft['heading'],draft['body'],'**Before approval:** '+' '.join(draft['unresolved']),f"Character count: {len(draft['body'])}."])
    (ROOT/'reports'/'essay-working-drafts.md').write_text('\n\n'.join(essay)+'\n',encoding='utf-8')
    data={'approvals':approvals,'issues':issues,'jobs':jobs,'summary':summary,'deadlines':f._follow_up({'days':30})}
    (ROOT/'reports'/'review.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');s.close();print(json.dumps({'review_file':str(ROOT/'reports'/'review.md'),'essay_file':str(ROOT/'reports'/'essay-working-drafts.md'),'character_limited_prompts':limited}))


if __name__=='__main__':main()
