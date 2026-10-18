# A Story Founder OS: Funding Hunter and Application Pilot

Owner website: https://pitch.gbaonvo.com - sign in with Google as gbao.n.vo@gmail.com. The full OS connects through Cloudflare Tunnel to this Windows PC; keep the PC awake, online and signed in. Automatic restart checks run at sign-in and every five minutes. See [deployment setup](deploy/README.md). The application source is public. Keep operational databases, company materials, credentials, and recovery snapshots private. A read-only demonstration with synthetic data is available in [the project showcase](https://github.com/vngiabao/project-showcase/tree/main/founder-os).

Both workers extend this existing Founder OS and share `data/founder.sqlite` with company memory, applications, Answer Bank, pitches, sources, approvals and frozen submissions. Original OneDrive files remain unchanged at their original paths.

## Open and connect

Run `Open-Founder-OS.ps1`, then open http://127.0.0.1:8765/. Applications shows preparation, exact confirmation previews, saved daily reports and email connection status.

Daily reports are scheduled for **9 AM Eastern** to **gbao.n.vo@gmail.com** through the connected Gmail plugin. The first real report was sent on October 6 and its Gmail receipt is retained. The scheduled chat reads the exact Founder OS outbox, sends once, and records the actual message ID. No Gmail app password or OpenAI API key is needed for this path. Keep the PC awake, online and Codex running for scheduled mail. Research/preparation Windows tasks can still work while the app is closed.

The former local SMTP setup remains an optional alternate transport, not a requirement for connected Gmail. No credentials are extracted from the plugin or stored in this project.

[Work operations](https://chatgpt.com/space/page_62f83cb5e0fc8191b78981bfa5467364) is a saved report and portable package. Live controls/data remain on the PC. The historical deployed Pitch OS has not been replaced or reconciled with a current remote export.

## Schedules and search

Broad discovery runs Monday and Thursday at 8 AM Eastern. Daily free-credit discovery runs at 7:30 AM; reports are due at 9 AM. Days, times, timezone and budgets are database settings. Twelve search families cover competitions, grants, AI, Michigan, Midwest, vertical programs, corporate programs, directories, cloud credits, voice credits, creative credits and bootstrapped startup credits. The daily 7:30 AM scan rotates two cash families (competitions, grants, Michigan, Midwest, vertical, AI programs) and two credit families each day. Today and the daily shortlist rank a closing deadline and real cash ahead of credits; credits are never treated as cash. Official sources verify current conditions; screenshots are discovery leads.

Two named Windows tasks poll research/preparation every five minutes and at sign-in. Those tasks require the PC awake, online and this Windows user signed in; they can work with the browser and Codex app closed. The separate connected-Gmail scheduled chat runs daily at 9 AM Eastern and requires Codex running. A powered-off PC cannot run these local jobs. Idle Windows polling makes no model calls. Research reuses the existing Codex ChatGPT login and allowance. Durable request IDs, leases, bounded retries, sources and run usage remain observable.

## Truth and application approval

One owner-confirmed canonical profile contains 15 company attributes. Five older essay proposals remain unapproved. NVIDIA Inception is an owner-reported prior program; acceptance, credit amounts and outcome remain unknown. A personal location and founding date do not establish incorporation or headquarters. Missing eligibility facts stay unknown.

Application Pilot uses gbao.n.vo@gmail.com by default, or bao@astoryapp.com when a company email is required. It prepares verified, eligible, free, non-dilutive opportunities using current approved facts and answers. **Every submission requires an exact filled preview emailed to the owner and the owner's individual confirmation.** Changed fields, facts, questions or research invalidate approval and require another preview. General permission does not bypass this gate.

The first adapter supports simple public native HTML forms. Login, JavaScript-only forms, CAPTCHA, unknown required answers, files, payment, deposits, paid account activation and legal attestations remain blocked for review or a future provider adapter. No live provider application has been submitted. Fixture tests validate the transport/gates, not compatibility with every provider. Only a positive organizer receipt records Applied; uncertain sends never retry automatically.

## Email behavior

Reports go only to the authorized personal email, once per local day, using the latest saved evidence and its timestamps. The owner authorized private TXT attachments containing current official questions, locally prepared values, blank fields, blockers and saved essay drafts. Historical drafts are clearly separated from current official forms. Exact submission previews pair each inspected question with its filled answer and retain an immutable TXT snapshot. Reports and supplements never approve a submission. Gmail acceptance is distinct from independently confirmed inbox delivery. Authentication failures require reconnection; uncertain transmission is retained without automatic resend. Pause/resume controls preserve owner authorizations and decisions.

## Pitch materials and question previews

**Pitch Studio** is available at http://127.0.0.1:8765/pitches and in the website navigation. Sixteen active pitches cover 30 seconds through 20 minutes, families, investors, judges, storytellers, community partners and technology partners. Short scripts and longer working outlines are distinguished. Length, audience, scenario, speaker, wording and notes are editable; custom choices are supported. Save keeps earlier versions, Make a variant creates a separate pitch, and Practice aloud shows current wording with a start/pause/reset timer. Saved pitches export as TXT.

The studio preserves historical sources and the original Pitch OS pitch. Version conflicts cannot silently overwrite another tab's edits. Materials includes Adapt in Pitch Studio for using extracted source text as a new working draft. Editing a pitch does not approve answers, change canonical facts or submit anything externally. See `PITCH-STUDIO-RUNBOOK.md`; `reports/pitch-studio-manifest.json` traces the starter drafts to their source versions.

Materials now catalogs 1,551 files from the exact Pitch Competition folder: 1,234 distinct content hashes, 59 PowerPoint decks, 46 PDFs, 87 documents and 1,357 image references. Text from 192 files, including deck speaker notes, is searchable in OS. Binary files remain local original references. Exact duplicate source paths are grouped; generated previews are available under Archived. The source manifest records every library item, original path, hash basis, category, extraction status and source version. No original was moved, overwritten or deleted. Code/dependency files remain in the earlier inventory, outside the pitch-material library.

Applications has per-plan Questions & prepared answers and TXT downloads, plus one export of all current plans and the nine saved essay questions/drafts. Unknown official forms stay unknown. Read-only checks of the current Claude, ElevenLabs and AssemblyAI form URLs could not produce a supported official form: login/dynamic forms or multiple forms need review/provider support. Nothing was filled on those external sites or submitted.

The owner-requested TXT supplement was actually delivered through Gmail on October 6, with exact attachment readback confirmed. The original daily report remains immutable. Future daily reports include private owner-only TXT previews.

## Evidence, reuse and history

Program aliases and separate annual/cohort/rolling IDs prevent duplicate applications without discarding future cycles. Resolved unknown-cycle placeholders link to current records while originals, versions and application links remain intact. A shared domain alone does not merge programs.

Seven weighted scoring components total 100. Missing evidence produces unknown components and score bounds. Credit headlines are not cash or confirmed usable savings. Provider/tier, referrals, products, payment/deposit conditions, minimum spend, expiration and terms retain individual official sources. Founder effort and readiness are disclosed estimates. Old answers are not canonical truth. Founder choices/outcomes remain separate from agent recommendations; scoring versions never silently change.

## Verification and portability

`reports/verification.json` checks all 202 registered source versions and 299 import destinations. The expanded materials library adds document text without promoting historical facts. The initial 25 selected originals and owner-confirmation source remain retained. The compressed taxonomy records all 103,159 inventoried paths as metadata, not a blind folder copy. No original source was modified.

Run `run.ps1 test` for disposable fixture tests; `reports/tests-passed.json` records current results. Desktop/mobile checks cover original routes and new Applications/credit detail surfaces. `AUTONOMY-DELIVERY.json` records the latest operational state. Earlier delivery files remain historical snapshots. Read `FUNDING-HUNTER-RUNBOOK.md` and `APPLICATION-PILOT-RUNBOOK.md` for recovery and limits.

The autonomy ZIP uses a consistent SQLite backup and preserves earlier release packages. The database/package contain private company materials, without credentials. Moving computers requires retaining original source paths and reconnecting research and mail access.
