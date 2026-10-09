import argparse
import json
import sys
from pathlib import Path
from .store import Store
from .agents import Founder, CAPABILITIES


def main():
    parser=argparse.ArgumentParser(description='A Story Founder OS and integrated Funding Hunter')
    parser.add_argument('--db',default=str(Path(__file__).resolve().parent.parent/'data'/'founder.sqlite'))
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status')
    sub.add_parser('approvals')
    sub.add_parser('ledger')
    sub.add_parser('work',help='Run all currently queued local jobs, then exit')
    sub.add_parser('snapshot',help='Print the decision-first review state')
    sub.add_parser('hunter-context');sub.add_parser('hunter-dashboard');sub.add_parser('hunter-run-now')
    q=sub.add_parser('hunter-notifications');q.add_argument('--ack')
    q=sub.add_parser('hunter-ingest');q.add_argument('file',type=Path);q.add_argument('--key')
    q=sub.add_parser('hunter-list');q.add_argument('--view',default='Recommended')
    q=sub.add_parser('hunter-detail');q.add_argument('opportunity_id')
    q=sub.add_parser('hunter-decision');q.add_argument('opportunity_id');q.add_argument('decision');q.add_argument('--reason',required=True);q.add_argument('--confirm-owner-decision',action='store_true')
    q=sub.add_parser('hunter-outcome');q.add_argument('file',type=Path);q.add_argument('--confirm-owner-decision',action='store_true')
    q=sub.add_parser('hunter-fact');q.add_argument('file',type=Path)
    q=sub.add_parser('serve');q.add_argument('--port',type=int,default=8765)
    q.add_argument('--cloudflare-config',type=Path,help='Fail-closed Access hostname, team domain, audience and owner email JSON')
    sub.add_parser('autonomy-status')
    q=sub.add_parser('application-plan');q.add_argument('opportunity_id');q.add_argument('--inspect',action='store_true')
    q=sub.add_parser('application-run');q.add_argument('plan_id')
    q=sub.add_parser('daily-report');q.add_argument('--send',action='store_true')
    q=sub.add_parser('autonomy-revoke');q.add_argument('authorization_id');q.add_argument('--confirm-owner-decision',action='store_true')
    q=sub.add_parser('enqueue');q.add_argument('capability',choices=CAPABILITIES);q.add_argument('--input',required=True,type=Path);q.add_argument('--key')
    q=sub.add_parser('decide');q.add_argument('approval_id');q.add_argument('decision',choices=['approved','rejected']);q.add_argument('--confirm-owner-decision',action='store_true');q.add_argument('--note',default='')
    q=sub.add_parser('search');q.add_argument('query')
    q=sub.add_parser('history');q.add_argument('program')
    q=sub.add_parser('retry');q.add_argument('job_id')
    args=parser.parse_args();s=Store(args.db);f=Founder(s)
    try:
        if args.cmd in ('autonomy-status','application-plan','application-run','daily-report','autonomy-revoke'):
            from .application_pilot import ApplicationPilot
            from .report_email import DailyReporter,credential_present
            p=ApplicationPilot(s)
            if args.cmd=='autonomy-status':result=p.dashboard();result['mail_connected']=credential_present()
            elif args.cmd=='application-plan':result=p.inspect(args.opportunity_id) if args.inspect else p.build(args.opportunity_id)
            elif args.cmd=='application-run':result=p.execute(args.plan_id)
            elif args.cmd=='daily-report':
                reporter=DailyReporter(s);result=reporter.prepare()
                if args.send:result=reporter.send(result['id'])
            elif args.cmd=='autonomy-revoke':
                if not args.confirm_owner_decision:raise ValueError('Explicit owner pause instruction needed')
                p.revoke(args.authorization_id);result={'paused':True}
        elif args.cmd.startswith('hunter-') or args.cmd=='serve':
            from .funding_hunter import FundingHunter
            h=FundingHunter(s)
            if args.cmd=='hunter-context':result=h.research_context()
            elif args.cmd=='hunter-dashboard':result=h.dashboard()
            elif args.cmd=='hunter-notifications':
                if args.ack:s.db.execute("UPDATE funding_notifications SET read_at=datetime('now') WHERE id=?",(args.ack,))
                result=s.rows('SELECT * FROM funding_notifications WHERE read_at IS NULL ORDER BY created_at DESC')
            elif args.cmd=='hunter-run-now':result=h.request_run()
            elif args.cmd=='hunter-list':result=h.list(args.view)
            elif args.cmd=='hunter-detail':result=h.detail(args.opportunity_id)
            elif args.cmd=='hunter-ingest':result=h.runFundingHunter(json.loads(args.file.read_text(encoding='utf-8-sig')),args.key)
            elif args.cmd=='hunter-decision':
                if not args.confirm_owner_decision:raise ValueError('Explicit founder decision needed')
                result=h.decide(args.opportunity_id,args.decision,args.reason)
            elif args.cmd=='hunter-outcome':
                if not args.confirm_owner_decision:raise ValueError('Explicit founder outcome confirmation needed')
                result=h.outcome(**json.loads(args.file.read_text(encoding='utf-8-sig')))
            elif args.cmd=='hunter-fact':
                p=json.loads(args.file.read_text(encoding='utf-8-sig'))
                vid=s.propose_claim(p['topic'],p['label'],p['body'],p['evidence_status'],p['source_version_id'],p['locator'],last_verified_at=p.get('last_verified_at'))
                for k,v in p['attributes'].items():h.attach_fact_value(vid,k,v)
                result={'claim_version_id':vid,'approval_id':s.request_approval('promote_claim',{'version_id':vid},actor='funding_hunter'),'state':'proposed_only'}
            elif args.cmd=='serve':
                from .server import serve
                access=None
                if args.cloudflare_config:
                    from .cloudflare_access import AccessIdentity
                    config=json.loads(args.cloudflare_config.read_text(encoding='utf-8-sig'))
                    access=AccessIdentity(config['hostname'],config['team_domain'],config['audience'],config['email'])
                serve(str(s.path),args.port,access);return 0
        elif args.cmd=='status':
            result={t:s.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['sources','source_versions','claims','claim_versions','opportunities','applications','questions','answer_versions','approvals','submissions','jobs','issues']}
            from .funding_hunter import FundingHunter
            h=FundingHunter(s)
            result.update(live_model=False,external_connectors=False,funding_hunter_runner=h.settings()['runner'],canonical_claims=s.db.execute('SELECT count(*) FROM claims WHERE canonical_version_id IS NOT NULL').fetchone()[0])
        elif args.cmd=='approvals':result=s.rows('SELECT * FROM approvals WHERE state=\'pending\' ORDER BY requested_at')
        elif args.cmd=='ledger':result=s.export_ledger()
        elif args.cmd=='enqueue':result={'job_id':f.enqueue(args.capability,json.loads(args.input.read_text(encoding='utf-8-sig')),args.key)}
        elif args.cmd=='work':
            result=[]
            while (job:=f.run_one()) is not None:result.append({'job_id':job['id'],'state':job['state'],'error':job['error']})
        elif args.cmd=='decide':s.decide(args.approval_id,args.decision,args.confirm_owner_decision,args.note);result={'approval_id':args.approval_id,'decision':args.decision}
        elif args.cmd=='search':result=f._research({'query':args.query})
        elif args.cmd=='history':result=s.snapshots(args.program)
        elif args.cmd=='retry':f.retry(args.job_id);result={'queued':args.job_id}
        elif args.cmd=='snapshot':
            result={
                'needs_my_decision':s.rows('SELECT id,action,payload_json FROM approvals WHERE state=\'pending\''),
                'agent_activity':s.rows('SELECT id,capability,state,attempts,error,updated_at FROM jobs ORDER BY updated_at DESC'),
                'new_opportunities':s.rows('SELECT program,cycle,state,fit_score,fit_reason FROM opportunities'),
                'applications_in_progress':s.rows('SELECT * FROM applications'),
                'upcoming_deadlines':f._follow_up({'days':30}),
                'knowledge_inconsistencies':s.rows('SELECT * FROM issues WHERE state=\'open\''),
                'recent_submissions_results':s.rows('SELECT id,application_id,submitted_at,receipt,payload_sha256 FROM submissions ORDER BY submitted_at DESC'),
            }
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 1
    finally:s.close()
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
