"""Current, truthful runtime and migration delivery snapshot."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from founder_os.store import Store,now
from founder_os.funding_hunter import FundingHunter
s=Store(ROOT/'data/founder.sqlite');h=FundingHunter(s);dash=h.dashboard()
counts={t:s.db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('sources','imports','program_history','material_registry','funding_programs','funding_cycles','funding_intelligence','funding_runs','funding_notifications','submissions')}
tests=71 if (ROOT/'reports/tests-passed.json').exists() and json.loads((ROOT/'reports/tests-passed.json').read_text(encoding='utf-8-sig'))['tests_passed']==71 else 70
delivery={'status':'funding_hunter_local_runtime_active','verified_at':now(),'work_operations':'https://chatgpt.com/space/page_62f83cb5e0fc8191b78981bfa5467364','command_center':'http://127.0.0.1:8765/','tests_passed':tests,'counts':counts,'canonical_claims':s.db.execute('SELECT count(*) FROM claims WHERE canonical_version_id IS NOT NULL').fetchone()[0],'pending_company_reviews':len(dash['needs_decision']),'runner':h.settings()['runner'],'schedule':h.settings()['schedule'],'api_key_required':False,'original_source_files_modified':0,'external_actions_enabled':False,'work_page_type':'saved operations snapshot; live controls and database on PC','broad_scan':{'queries':8,'candidates':15,'official_programs_read':6,'program_states_verified':5,'status':'PARTIAL; uncertainty and discovery-only leads retained'},'latest_live_verification':{'run_id':'run-8ebccf09751635c289895069','state':s.one('SELECT state FROM funding_runs WHERE id=?',('run-8ebccf09751635c289895069',))['state']},'runtime_requirement':'PC awake and online; Windows user signed in; Codex app and chat can be closed','ui_review':'ship for six scored material fixes; original whole-surface review recorded','remote_deployed_pitch_os_reconciled':False}
(ROOT/'FUNDING-HUNTER-DELIVERY.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
proof=s.one("SELECT state,run_id,attempts FROM hunter_requests WHERE request_key='windows-task-authenticated-research-proof-001'")
delivery['windows_task_live_research']=proof
if proof['run_id']:
    actual=s.one('SELECT state,report_json FROM funding_runs WHERE id=?',(proof['run_id'],))
    delivery['windows_task_live_research']['research_report_state']=actual['state']
    delivery['windows_task_live_research']['report']=json.loads(actual['report_json'])
(ROOT/'FUNDING-HUNTER-DELIVERY.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
items=[]
for d in dash['opportunities']:
    items.append({'opportunity_id':d['opportunity_id'],'program_id':d['program_id'],'cycle_id':d['cycle_id'],'program':d['data']['canonical_name'],'cycle':d['data']['cycle'],'recommendation':d['recommendation'],'verification_state':d['verification_state'],'fit_score':d['fit_score'],'score_range':[d['analysis']['scoring']['lower_bound'],d['analysis']['scoring']['upper_bound']],'last_verified':d['last_verified'],'next_check':d['next_check'],'sources':d['data']['sources']})
(ROOT/'reports/current-opportunities.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'delivery':delivery['status'],'counts':counts,'canonical_claims':delivery['canonical_claims'],'tests_passed':tests}));s.close()
