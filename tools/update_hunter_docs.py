"""Record the current implementation; earlier foundation package stays intact."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
guide='''# A Story Founder OS with Funding Hunter

Funding Hunter is the first autonomous research worker in this existing Founder OS. It shares data/founder.sqlite with the canonical company-memory approval system, applications, Answer Bank, pitches, source registry and frozen submission history. Original OneDrive files remain at their original paths.

## Open the command center

Run Open-Founder-OS.ps1 in this folder, then open http://127.0.0.1:8765/ on this PC. The server runs in the background and serves only the local Windows owner. Home, Opportunities, Agent activity, Applications, Company memory, Answer Bank and Needs decision use the same existing store.

[A Story Funding Hunter Operations](https://chatgpt.com/space/page_62f83cb5e0fc8191b78981bfa5467364) is a saved Work operations report. The live database and controls are on the PC. The deployed historical Pitch OS has not been replaced or reconciled with a current remote export.

## Automatic research

A Windows Scheduled Task polls durable requests every five minutes and at sign-in. Research defaults to Monday and Thursday at 8 AM America/New_York, plus due checks and Run now requests. Schedule days, time, timezone, budgets and runner metadata are database configuration, separate from the engine. The existing Codex CLI ChatGPT login is used; no API key was created or loaded. Research uses the account's existing allowance.

The PC must be awake, online and this Windows user signed in. ChatGPT and the Codex desktop app can be closed. A missed scan is caught up after sign-in. The idle poll uses no model calls. tools/install_hunter_schedule.ps1 installs only this project's named task and refuses to overwrite an unrelated task. Verified metadata is in reports/scheduler-verification.json. To disable research, disable that named Windows task.

Run Funding Hunter now queues a durable request and starts the same worker. Research more targets a program. Closing the browser does not cancel a request. One worker lease prevents concurrent research; failures are retained and retry at most three times.

## Selection and uncertainty

Eight search families cover competitions, grants, AI, Michigan, Midwest, vertical programs, corporate programs and ecosystem directories. Discovery is broad; important claims need current official evidence. The worker returns observations. Deterministic code owns program/cycle identities, deduplication, eligibility, seven weighted score components, readiness, recommendations and notification thresholds.

Annual cycles remain separate from rolling programs. Existing application/submission links stay intact. Aliases, exact program URLs and name similarity help reconcile duplicates; ambiguous identities become review failures. A shared domain alone does not merge programs.

Missing facts, unpublished odds, unclear equity and inaccessible forms stay unknown. Unresolved points appear as a range. Credit headline values are not cash or confirmed usable credits. Conflicting amounts are not resolved by selecting the largest figure. Date-only deadlines do not acquire a fabricated closing time.

Notifications appear prominently in the command center only for defined high-value changes. Routine scan completion creates no alert. Email, external messaging and separate desktop push delivery are not connected.

## Company memory and owner approval

Zero company claims are currently canonical. Five migrated proposals await evidence review. Structured eligibility attributes must be bound to a claim version before its exact approval request is prepared. Only approved, verified, current source versions qualify the company. Changed sources, conflicts and expired verification fail closed.

Approving prose does not establish all eligibility attributes. The hunter-fact command proposes a sourced structured value, then Needs decision shows its exact owner approval. Allowed keys are in founder_os/hunter_policy.py. A proposal includes topic, label, body, evidence status, registered source-version ID, precise locator, actual verification date and an attributes object. Do not infer current student status, incorporation or headquarters from an old essay. The command never promotes facts automatically.

Use run.ps1 hunter-fact <verified-fact.json>, run.ps1 approvals and run.ps1 hunter-context. Canonical approval is an explicit owner decision. The local session requires a same-origin cookie and action token. This is a single-owner localhost application, not remote multi-user authentication; an owner with direct filesystem/database access is trusted.

## Materials and results

The Answer Bank retains nine original essay sections and nine revised drafts. Material references retain paths and fingerprints. References are not automatically ready: reuse checks approval, canonical dependencies and source currentness. Readiness and founder hours use a disclosed planning rubric, not measured application time.

Founder choices/reasons remain separate from agent recommendations. Attributed Applied, Advanced, Finalist, Won, Rejected, Accepted and Withdrawn outcomes can link to an exact application/submission. Saved forms and analyst rejection discussion never become organizer outcomes. Scoring weights are versioned and never silently learned from a few decisions.

Starting an application creates an internal draft. No submission, email, investor contact, terms acceptance, payment, confidential program-site upload or autonomous canonical-fact change is implemented.

## Provenance and verification

reports/first-broad-run.json records the retained broad scan and unresolved research. reports/runs preserves actual responses and schemas; the database holds run reports and usage. reports/hunter-history-import.json indexes 37 historical program mentions and 18 unapproved material references. reports/import-ledger.json traces 121 destinations to paths, hashes, locators and transformations. reports/founder-taxonomy.jsonl.gz covers all 103,159 inventoried paths as classification metadata, not a blind folder copy. reports/verification.json records matching source fingerprints and database/import checks.

FUNDING-HUNTER-RUNBOOK.md defines evidence, scoring, budgets and recovery. FUNDING-HUNTER-DELIVERY.json is the current state; DELIVERY.json describes the earlier foundation snapshot. Historical migration remains selective, with no verified organizer outcomes or submission receipts imported.

Run run.ps1 test to check disposable fixture databases. Tests cover identities/cycles, evidence, unknown facts, exact approvals, stale sources, scoring, deadlines, reuse, idempotency, leases/retries, scheduling/timezones and localhost protections. Desktop/mobile browser checks cover seven routes.

## Backup and portability

The database contains private drafts and is not encrypted; keep it in the user's private workspace. No credentials are stored. Use SQLite's backup API for a consistent snapshot while the server runs. The Funding Hunter package uses that API and preserves the original foundation package. Moving computers requires source-location mapping without replacing recorded original paths, and reconnecting that computer's signed-in runner.
'''
(ROOT/'README.md').write_text(guide,encoding='utf-8')
print('Current Funding Hunter run instructions saved')
