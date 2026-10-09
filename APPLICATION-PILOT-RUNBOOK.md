# Application Pilot and daily reports

All workers share the existing Founder OS database. Research has no submission or email tools. Application Pilot is deterministic and separately scoped. It enforces the owner instruction: email an exact filled preview and wait for individual confirmation before every submission.

## Preparation and confirmation

Use current canonical attributes and exact approved Answer Bank matches. Require official eligibility, open applications, zero fees, no equity, no deposit, no minimum spend, no paid activation and no unreviewed terms. Unknown conditions block submission. Use the personal email by default and company email when required. Preserve program/cycle, application, research revision and fact/answer versions.

Inspect the exact native form. Fill supported scalar facts and exact approved answers only. Unknown required questions, files and legal consent remain blocked. The immutable preview retains the exact payload hash and filled fields. Email it only to the owner. Confirmation controls require Gmail to have accepted that email. The owner's explicit confirmation applies only to those fields/program. Changed fields, facts, answers or research require a new preview. Changed forms require reinspection. Declines remain OWNER_REJECTED. Owner SKIP, WATCH or PREPARE prevents application. Pause/resume preserves historical authorization receipts.

Recheck authorization, truth, research revision and form fingerprint immediately before submission. Record intent before the one external POST. A positive organizer receipt freezes the submission snapshot and records Applied. Timeout, ambiguous response or crash blocks retries as SUBMISSION_UNKNOWN or IN_FLIGHT. Reconcile real organizer history manually; no force-retry endpoint exists.

## Form support

The first adapter supports bounded public HTTPS native HTML POST forms. It pins the checked public IP, verifies TLS, limits responses, rejects credential-bearing URLs and refuses redirects. Fresh CSRF token values do not alter question fingerprints; other hidden values are blocked.

Login, JavaScript-only portals, CAPTCHA, unknown fields, ambiguous forms, legal attestations, file inputs and unsupported controls need review or a future provider adapter. Popular cloud/AI portals may require those adapters. Fixture tests exercise the generic path; no live provider submission is claimed. Do not invent provider APIs or bypass anti-bot controls.

## Email and schedule

The connected Gmail plugin is the primary delivery path. A daily 9 AM scheduled chat verifies the Gmail profile and uses tools/gmail_outbox.py to list, atomically claim, send and record exact messages. Claim returns the immutable message hash, including exact TXT attachment contents and their SHA-256 digests. Send attachments as multipart/mixed with text/plain UTF-8, the claimed filename, and unchanged content. A supplement is a separate owner-requested message; it cannot rewrite an already sent daily report. Never approve from a report, attachment or email reply. Complete requires that hash, the actual Gmail message ID and the authorized account. Nothing marked SENT, SENDING or DELIVERY_UNKNOWN is reclaimed. Unknown results require manual Gmail reconciliation. Preview emails never become application approvals.

Mail access remains with the plugin. No credential extraction, app password or OpenAI API key is required. The local SMTP helper is an optional alternate transport. In connected-Gmail mode the Windows worker queues CONNECTOR_PENDING instead of attempting SMTP. Scheduled connected mail needs Codex running on the awake, online PC; research/preparation can work with the app closed.

Reports are due at 9 AM America/New_York, one per local day. Daily credit discovery is due at 7:30 AM and uses an idempotent date key. Schedules are database configuration. The research/preparation Windows task polls every five minutes and at sign-in, with a lease and no idle model calls. Those Windows tasks need the PC awake, online and this user signed in, but can work with browser/Codex closed. Connected-Gmail delivery separately requires Codex running.

Reports use the latest evidence and disclose its age. They include opportunities, deadlines, application blockers and next actions with an owner-only TXT question-and-answer attachment when that explicit scope is active. Saved historical essay drafts are labeled separately; unknown official questions are never guessed. No overdue backlog flood is sent. Exact previews contain the filled fields requested by the owner. Destination is gbao.n.vo@gmail.com only. Gmail acceptance does not independently prove inbox delivery. Authentication rejection is reconnectable. Uncertain sending becomes DELIVERY_UNKNOWN without automatic resend; SENDING after a crash also needs reconciliation.

## Observe and stop

Applications shows blockers, confirmations, reports and sender availability. Agent activity retains research runs. `run.ps1 autonomy-status` reports scopes/schedules; `run.ps1 daily-report` saves a report without sending. The installer touches only this project's named task and refuses unrelated replacements. Use Pause email reports and Pause application preparation in Applications to revoke the corresponding active scopes. Alternatively pause the connected-Gmail automation to stop its scheduled sends. Disabling the autonomy Windows task stops preparation/queue polling, but does not disable the separate Gmail automation; disabling the Hunter task stops research. Sources, decisions and receipts remain retained.

## Materials ingestion and TXT review

`tools/import_pitch_materials.py --root "C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition"` refreshes the same private materials catalog without source modification. An optional `--inventory` supplies cached hashes only for matching file size and timestamp. Document extraction freshly hashes content, includes PDF pages and slide notes, and stores bounded text (up to 1,000,000 characters per document). Unsupported binaries retain local references. Repeated unchanged ingestion retains the same IDs; changed sources create new immutable source versions. Original downloads verify registered size/mtime and folder containment, then stream as attachments. References to moved/unavailable originals remain traceable. The portable package includes database text and references, not the 1.76GB of source binaries.

Per-plan TXT previews reflect inspected official questions and local prepared fields, with exact source/fact/answer versions. General exports additionally include saved historical questions and latest draft answer versions. Generating/downloading a preview never approves or submits. `reports/pitch-materials-manifest.json` is the traceable catalog; `reports/current-form-inspection.json` retains read-only inspection failures.
# Daily founder report

The owner chose a formal black-and-white email layout. `founder_os/email_design.py` renders the shared sample/daily HTML with clear opportunity sections, benefit/deadline highlights, and separate agent work and owner decisions. This is an email-only direction; the teal OS interface is unchanged. The full plain report remains available as a fallback.

Claims include saved `body_html`, `body_html_sha256` and `template_version` when available. Verify the HTML's exact UTF-8 digest, then send it unchanged as the first `text/html` part. Do not escape it as plain text or redesign it during delivery. Older plain-only messages keep the escaped-text fallback. Authorized TXT attachments remain exact subsequent parts. `report_presentations` freezes daily HTML when sending begins; supplement messages remain immutable. HTML participates in the full message claim hash and actual Gmail receipt. Use `tools/preview_report.py` for a local preview without queuing or sending.

Daily reports use the Funding Hunter's persisted founder briefs and shared `daily_shortlist()` selection. The agent researches applicability, practical benefit, correct tier, deadline, requirements, costs, material work, application angle and next actions before reporting. Usually present five distinct programs, with fewer when insufficient useful evidence exists. Keep research tasks with the agent and label genuine founder decisions separately. Do not use unknown score upper bounds as actual fit. The original scoring weights remain unchanged.

Each card shows the program name, why applicable, benefit to A Story, deadline, requirements, renewal/overage catches, effort/readiness, supported application angle, agent next action, owner decision, eligibility, score if established, source URLs and the local OS record. Conditional strategic use cases are not eligibility evidence. Sample reports use the same renderer as daily reports and a separately claimed supplement, preserving sent daily messages and exact-preview approval requirements. No owner report or sample authorizes an application submission.
