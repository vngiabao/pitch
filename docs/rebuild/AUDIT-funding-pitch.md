# Function audit: Funding and Pitch pages (rebuild vs old app)

Audited Nov 11-12, 2026, read-only on source. Line numbers were re-read on Nov 12 (page files last changed
Nov 11, 21:42-22:02). Old code: `founder_os/ui/app.js`, `pitch.js`, `scouts.js`, `ranker.js`, `assumptions.js`;
handlers: `founder_os/server.py` and the modules it calls.

## Bottom line

**No wrong payload, no missing action, no missing confirmation and no broken link** on the 15 pages. Every POST uses
the old endpoint, the old keys and the value types the server checks. Every old `confirm()` and `prompt()` is kept,
and `confirmed: true` is only sent after a dialog. 7 defects remain, none of them in a payload: 1 swallowed error
(Materials), 1 outward action with no dialog (same as the old app, but the brief asks for one), 1 crash on a
malformed `#anchor`, and 4 shared-file weaknesses.

## How it was checked

- **Read:** every page and data file in the brief, `api.ts`, `feedback.tsx`, `page.tsx`, `format.ts`, `routes.tsx`,
  `App.tsx`, the `PAGES` list in `shell.tsx`, and each server handler the pages call.
- **Live GET shapes (curl, session cookie):** `/api/dashboard`, `application-list`, `growth-alerts`,
  `opportunities?view=All` (71 programs), `opportunity/<id>`, `win/<id>` (all 71; 4 have briefs), `autonomy`,
  `application/<id>` (all 33, 304 questions), `application-review/<id>`, `credits`, `stack`, `money`, `lab`,
  `lab/<id>` (all 60 items), `lab-options`, `assumptions`, `pitches`, `pitch/<id>` (all 18), `materials`,
  `material/<id>` (12), `answers` (280). Every field the pages read exists with the type the code expects.
- **Record-only POSTs on the data copy:** `/api/money-move` (TODO -> DOING -> TODO, restored), `/api/stack-cost`
  with `monthly_usd: "12.50"` as a string (accepted, stored 12.5) then `/api/stack-delete` (row removed, 7 items as
  before), `/api/assumptions-seen` (marks assumption alerts seen on the copy; not undone, the page does this on
  every view).
- **Not run:** no worker, email, submit or window endpoint was called. `tsc` was not run. The pages were not opened
  in a browser, so this audit covers code and data, not rendering.

Status key: OK = same endpoint, payload, confirmation and after-effect as the old page. WRONG and MISSING are
defects and appear in the ranked list.

---

## 3.2 Funding, needs you (`FundingNeeds.tsx`, `lib/funding.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET dashboard, application-list, growth-alerts (the two optional ones fall back to `[]`) | OK | funding.ts:164-168 |
| To-do list: ready answers, closing within 7 days, login-blocked forms (2), funding alerts | OK | funding.ts:67-101 vs app.js doNext/fundingItems |
| Lead card: title, money, closing words, left-for-you tasks, extra count, date tip, profile tip | OK | funding.ts:133-155; FundingNeeds.tsx:19-51 |
| More cash / more credits (5 each, to-do items excluded), day bar out of 60 | OK | funding.ts:173, 50; FundingNeeds.tsx:76-103 |
| Waiting on results, Decided, inbox line | OK | FundingNeeds.tsx:125-149; funding.ts:178-185 |
| Export tracker (CSV) link | OK | FundingNeeds.tsx:142 |
| `#wait-results-title` scroll after render | OK (see defect 3 for a malformed hash) | FundingNeeds.tsx:129, 153-156 |
| Links `/application/<id>`, `/opportunity/<id>`, `/credits`, `/opportunities`, `/founder-profile`, `/decisions`, external form in a new tab | OK | FundingNeeds.tsx:41, 44, 82, 145, 165, 168 |
| Empty states (4) | OK | FundingNeeds.tsx:132, 160, 167, 170 |

## 3.3 Pipeline (`Pipeline.tsx`, `lib/funding.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/opportunities?view=&<filters>`, application-list, dashboard (types and notice only) | OK | funding.ts:207-211; Pipeline.tsx:82 |
| `?view=` and the 8 filter keys read from the URL; panel opens when a filter is set | OK | Pipeline.tsx:23-27, 73-77 |
| URL kept with `replaceState` | OK | Pipeline.tsx:83 |
| 5 view buttons, "More views" select, filter form, Clear | OK | Pipeline.tsx:90-92, 109-160 |
| Closed programs hidden on Recommended and Apply now; duplicate names merged with a count | OK | funding.ts:214-222 |
| Table: program link, value, deadline, access tag + "Open answers", effort | OK | Pipeline.tsx:30-70 |
| A refresh that fails shows a toast and keeps the list | OK | Pipeline.tsx:86-87 |
| Company-facts notice with link to `/memory` | OK | Pipeline.tsx:94, 100-105 |

## 3.4 Opportunity (`Opportunity.tsx`, `lib/funding.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET opportunity, application-list, win (the last two optional) | OK | funding.ts:252-259 |
| Read the form: `POST /api/read-form {opportunity_id}`, redirect to `/application/<id>` when read, else reload + toast | OK | Opportunity.tsx:209-216 |
| Mark submitted: confirm, then `/api/outcome {opportunity_id, outcome:'Applied', application_id:null, note}` | OK | Opportunity.tsx:217-224 |
| Watch / Skip: reason asked (required), `/api/decision {opportunity_id, decision, reason}`; nothing sent when cancelled | OK | Opportunity.tsx:225-234 |
| Check the program again: `/api/research {opportunity_id}`, toast, no reload | OK | Opportunity.tsx:235-238 |
| Decision form (APPLY, PREPARE, WATCH, SKIP + required reason) | OK | Opportunity.tsx:239-248, 324-337 |
| Win Scout research / research again: `/api/win-research {opportunity_id}`; disabled while researching | OK | Opportunity.tsx:93, 249-253 |
| Win Scout "Got it": `/api/win-seen {opportunity_id}`, reload | OK | Opportunity.tsx:254 |
| Open answers, official form (new tab), Tailor the pitch `/pitch-lab?program=<id>` | OK | Opportunity.tsx:260, 262, 319 |
| Lead facts, access line, stage strip, win brief sections, fit, eligibility, readiness, credits, score, sources, history | OK | Opportunity.tsx:54-87, 106-180, 272-394 |
| Malformed source URL no longer throws | OK (fixed vs old) | funding.ts:292 |
| Every action catches and toasts | OK | Opportunity.tsx:204-207 |

## 3.5 Applications (`Applications.tsx`, `lib/applications.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET application-list, autonomy; `?tab=work|reports|settings`; `#anchor` scroll | OK | Applications.tsx:24-27, 389-392, 400 |
| Preview: both buttons disabled until `email_state === 'SENT'` | OK | Applications.tsx:75, 119, 122 |
| Confirm and submit: dialog, then `/api/application-confirm {confirmation_id, decision:'APPROVED', confirmed:true}` | OK | Applications.tsx:78-82, 88-89 |
| Decline: dialog, then the same call with `'REJECTED'` | OK | Applications.tsx:83-89 |
| Groups by access level; Open answers; read / re-read / try again -> `/api/read-form {opportunity_id}`; external form or program page | OK | Applications.tsx:133-166; applications.ts:104-113 |
| Finished list with outcome tag | OK | Applications.tsx:179-196 |
| Connect report email: `/api/connect-report-email {}` + toast | OK vs old; no dialog (defect 2) | Applications.tsx:267-270 |
| Prepare today's report: `/api/report-now {}` | OK; a dialog was added | Applications.tsx:271-279 |
| Pause: `/api/autonomy-pause {authorization_id}` (both tabs) | OK | Applications.tsx:280-283, 343-346 |
| Resume: dialog, then `/api/autonomy-resume {scope, confirmed:true}` (both scopes) | OK | Applications.tsx:284-292, 347-355 |
| Past reports (14), state words, error, body toggled from `GET /api/report/<id>` | OK | Applications.tsx:230-256, 264 |
| Reload after every action; every error toasts | OK | Applications.tsx:395-399 |

## 3.6 Application answers (`ApplicationAnswers.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/application/<id>`, then `/api/lab` for the review panel (hidden if it fails) | OK | ApplicationAnswers.tsx:196-203, 232 |
| Copy with the `execCommand` fallback, "Copied" for 1.6s | OK | ApplicationAnswers.tsx:24-32; applications.ts:116-129 |
| Read / re-read the form; stays on this page | OK | ApplicationAnswers.tsx:86-89; applications.ts:106 |
| Mark submitted: confirm, `/api/outcome {opportunity_id, outcome:'Applied', application_id, note}` | OK | ApplicationAnswers.tsx:90-98 |
| Record a result: `{opportunity_id, application_id, outcome, note, evidence_url|null}`, 6 results | OK | ApplicationAnswers.tsx:136-143 |
| Review these answers: `/api/lab-application {application_id}` -> `/pitch-lab/<id>`; "Open the review" link | OK | ApplicationAnswers.tsx:204-210, 225 |
| Questions: label, options (12), answer box and count, source words and notes, "Needs you" | OK | ApplicationAnswers.tsx:35-79 |
| `#q-<id>` anchors and jump links (now a "Needs you" panel) | OK | ApplicationAnswers.tsx:59, 183, 240 |
| Submitted view, history disclosure | OK | ApplicationAnswers.tsx:130-176, 246 |

## 3.7 Application plan (`ApplicationPlan.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/application-review/<id>`; `location.replace('/application/<id>')` when `application_id` is set | OK | ApplicationPlan.tsx:29-30 |
| Official form (new tab) or "link not found", blockers or "checks passed", back link | OK | ApplicationPlan.tsx:41-47 |

## 3.8 Credits (`Credits.tsx`, `lib/money.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET credits, stack (optional) | OK | money.ts:36-39 |
| Update dates and balance: `/api/credit {id, started_on, expires_on, balance_note, account_email, state, notes}` as strings; toast + reload | OK | Credits.tsx:19, 72-75 |
| Save / add a cost: `/api/stack-cost {[id], item, provider, monthly_usd, covered_by}` as strings (tested live) | OK | Credits.tsx:120-123 |
| Remove a cost: confirm, `/api/stack-delete {id}` (tested live) | OK | Credits.tsx:126-134 |
| Used up or ended list; `#stack` anchor; program page link | OK | Credits.tsx:173, 240-247 |
| The form no longer opens by itself for NEEDS_DATES; the page's primary button opens it | OK (changed on purpose) | Credits.tsx:229-233 |

## 3.9 Money map (`MoneyMap.tsx`, `lib/money.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/money` | OK | money.ts:89 |
| To do / Doing / Done: `/api/money-move {id, state}`, reload, no toast (tested live) | OK | MoneyMap.tsx:192-198 |
| Apply first rows, "How this was figured", "How this number is made", unpriced list | OK | MoneyMap.tsx:22-83 |
| Links `/opportunity/<id>`, `/application/<id>`, `/pitch-lab/<edition>`, `/pitch-lab?program=<id>` | OK | MoneyMap.tsx:32, 46-47, 136, 143-147 |
| Anchors `#apply-first`, `#moves`, `#cat-<key>` and scroll after load | OK, but see defect 3 | MoneyMap.tsx:68, 113, 157, 178-183, 190 |

## 3.10 Pitch Lab (`PitchLab.tsx`, `lib/lab.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET lab, lab-options | OK | PitchLab.tsx:187 |
| `?program=` and `?coach=` preselect only; nothing is submitted on load | OK | PitchLab.tsx:96, 100, 191-197 |
| Tailor: `/api/lab-edition {opportunity_id, minutes:Number, slide_limit:Number|null, note}` -> `/pitch-lab/<id>` | OK | PitchLab.tsx:113, 200-205 |
| Coach: `/api/lab-review {pitch_id}`; Review answers: `/api/lab-application {application_id}` | OK | PitchLab.tsx:136, 148 |
| Lesson approve / reject: `/api/lesson {id, decision}`, reload + the old toasts; approve now asks first | OK | PitchLab.tsx:207-215 |
| Ready (grouped per program, older drafts folded), being made, approved, 9 steps, approved lessons, `#lessons` | OK | lab.ts:109-130; PitchLab.tsx:232-270 |

## 3.11 Pitch Lab item (`PitchLabItem.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/lab/<id>` | OK | PitchLabItem.tsx:372 |
| Save script: `/api/lab-save {id}` -> `/pitch/<pitch_id>` | OK | PitchLabItem.tsx:376-379 |
| Approve (READY only): `/api/lab-approve {id}`, reload + toast | OK | PitchLabItem.tsx:380-383, 408 |
| Build / rebuild: `/api/lab-build {id}`, reloads even after the 20s timeout | OK | PitchLabItem.tsx:385-388 |
| Another round: `/api/lab-rerun {id, note}`, reload + toast | OK | PitchLabItem.tsx:389-392 |
| Deck preview `/edition/<id>` (new tab), zip download | OK | PitchLabItem.tsx:104, 107 |
| Copy whole script, per slide, per answer | OK, no fallback (defect 4) | PitchLabItem.tsx:195-202; page.tsx:122-136 |
| Each kind's body, coach card, rules, QA (12 then "N more"), unresolved, history, error and working states | OK | PitchLabItem.tsx:23-353, 413-441 |

## 3.15 Assumptions (`Assumptions.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/assumptions` | OK | Assumptions.tsx:178 |
| Page load: `/api/assumptions-seen {}` once, errors ignored | OK | Assumptions.tsx:182-187 |
| Challenge now: `/api/assumption-challenge {}`, toast, reload; disabled while the Coach works | OK | Assumptions.tsx:190-197, 213 |
| Edit and save: `/api/assumption {key, evidence_for, evidence_against, cheapest_test, owner_note[, status]}`; no `status` for measured rows | OK | Assumptions.tsx:103-104, 198-205 |
| `#assumption-<key>`, `#group-<status>` anchors; challenge panel; rejected list | OK | Assumptions.tsx:77, 146, 227, 247 |

## 3.13 Pitch Studio (`PitchStudio.tsx`, `lib/pitches.ts`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/pitches?<query>`; `/api/material/<id>` when `?material=` | OK | PitchStudio.tsx:219-220 |
| `astory-pitch-library` saved in sessionStorage | OK | PitchStudio.tsx:218 |
| New pitch: `/api/pitches {title, duration_minutes, audience, scenario, body, duration_seconds:int, sources, claim_versions}` -> `/pitch/<id>` (the server requires an integer; `Math.round` gives one) | OK | PitchStudio.tsx:48-57 |
| Cancel asks when typed in; leaving the page asks too | OK | PitchStudio.tsx:36-40, 63-66 |
| Filters navigate to `/pitches?<form fields>`; selects submit on change; length links keep the other filters and drop `material` | OK | PitchStudio.tsx:112-122 |
| Form opens by itself when adapting a material; first 40,000 characters | OK | PitchStudio.tsx:99, 223 |

## 3.14 Pitch editor (`PitchEditor.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/pitches`, `/api/pitch/<id>` | OK | PitchEditor.tsx:361 |
| Save (button, Ctrl/Cmd+S): `POST /api/pitch/<pitch_id>` with every field, `duration_seconds:Number`, `sources`, `claim_versions`, `expected_version_id` | OK | PitchEditor.tsx:36, 110, 137-146 |
| 409 conflict: toast, plus a panel that keeps the wording | OK (better than old) | PitchEditor.tsx:149, 204-213 |
| Make a variant: title + " - variant" (160), `status:'draft'`, `change_note:'Adapted from <version>'` -> `/pitch/<new>` | OK | PitchEditor.tsx:154-165 |
| Restore: confirm only when dirty, `/restore {version_id, expected_version_id}` | OK | PitchEditor.tsx:166-179 |
| Recovery copy `astory-pitch-recovery:<pitch_id>`, restore / keep saved, newer-version wording | OK | PitchEditor.tsx:38-40, 117, 125-135, 215-225 |
| `beforeunload` guard, word count, seconds at 130 wpm, open prompts, custom length | OK | PitchEditor.tsx:107-115, 187-189, 243-247 |
| Rehearsal: unsaved text, start / pause / resume, reset, over target, back | OK | PitchEditor.tsx:43-87 |
| Copy text with select fallback; export; "Read as text" per version; Get coached; back link from sessionStorage | OK | PitchEditor.tsx:180-183, 192, 259, 307, 314 |
| A length not in the list now shows as Custom (the old select silently fell to its first option) | OK (fixed vs old) | PitchEditor.tsx:30 |

## 3.16 Materials (`Materials.tsx`) and 3.17 Material (`Material.tsx`)

| Function | Status | Evidence |
|---|---|---|
| GET `/api/materials?q=&kind=&category=&offset=`, `/api/answers` | OK | Materials.tsx:103, 147-149 |
| `q`, `kind`, `category`, `offset` from the URL (the site search lands here) | OK | Materials.tsx:23-26 |
| Search resets offset; URL kept; `astory-materials-list` saved | OK | Materials.tsx:29-33, 150-151 |
| Previous / Next, scroll to top | OK | Materials.tsx:93-94, 154 |
| A failed search or page turn shows nothing | **WRONG** (defect 1) | Materials.tsx:147-160 |
| File download, manifest download, answers with Copy | OK | Materials.tsx:78, 96, 119-134 |
| Material: GET, Adapt in Pitch Studio, Download original, back link from sessionStorage, file details, aliases, no-text state | OK | Material.tsx:19-21, 33, 42-44 |

---

## Outward actions on these pages (INVENTORY 1.7 and 6.1)

None fires on page load or from an effect; each needs a deliberate click. `confirmed: true` appears 4 times, always
after a dialog (Applications.tsx:89, 290, 353).

| Action | Endpoint | Guard now | Old app |
|---|---|---|---|
| Submit a previewed application | application-confirm APPROVED | dialog + disabled until SENT | confirm + disabled |
| Decline a preview | application-confirm REJECTED | dialog + disabled until SENT | confirm + disabled |
| Resume daily reports / preparation | autonomy-resume | dialog | confirm |
| Prepare today's report | report-now | dialog (added) | none |
| Connect report email | connect-report-email | **click only** | none |
| Read / re-read a form | read-form | click only | none |
| Check the program again | research | click only | none |
| Research how to win | win-research | click only | none |
| Tailor, coach, review answers | lab-edition, lab-review, lab-application | click only (a form submit) | none |
| Another round | lab-rerun | click only | none |
| Challenge now | assumption-challenge | click only | none |

The "click only" rows match the old app and CONVENTIONS ("keep every confirmation the old page had"). The audit brief
names `connect-*` as needing one, so that row is defect 2. The other rows are a call for the coordinator: they start
research or AI work on the ChatGPT plan and send nothing.

---

## Ranked defects

**1. Materials: a failed search or page turn is silent.** `Materials.tsx:147-160`. When the list is already on
screen and a new search, filter or Previous/Next fails, `LoadGate` keeps the old list (`page.tsx:31`), the form
already shows the new words, and no message appears. The old page showed a toast.
Fix (the pattern in `Pipeline.tsx:86-87`): in `MaterialsPage` add
`const { toast } = useFeedback()`, `const failed = state.data ? state.error : null`,
`useEffect(() => { if (failed) toast(failed, true) }, [failed, toast])`, and import `useEffect` and `useFeedback`.

**2. Connect report email has no confirmation.** `Applications.tsx:267-270`. One click opens a PowerShell window on
the PC. Same as the old app, but the brief asks that no `connect-*` call fires without a dialog.
Fix: at the top of `connect`'s callback add
`if (!(await confirm({ title: "Open the Gmail setup on this PC?", body: "A setup window opens on this PC. Enter the Google app password there, never in chat.", action: "Open setup" }))) return`
(`confirm` is already in scope at line 259).

**3. A malformed `#anchor` crashes the page.** `decodeURIComponent(location.hash.slice(1))` throws on a hash such as
`#%`. `MoneyMap.tsx:190` runs it during render; `MoneyMap.tsx:181`, `FundingNeeds.tsx:155` and `PitchLab.tsx:54`
(used by Pitch Lab and Assumptions) run it in an effect. The app has no error boundary, so React removes the whole
page. Fix: use the guarded version that already exists, `useHashScroll` in `lib/applications.ts:138-145`, in place
of the three effects, and in MoneyMap replace line 190 with
`let hash = ""; try { hash = decodeURIComponent(location.hash.slice(1)) } catch { /* no anchor */ }`.

**4. Copy fails silently where the clipboard is refused (shared file).** `lib/format.ts:90` `copyText` has no
fallback and returns false; `CopyBox` (`components/app/page.tsx:133`) and "Copy the whole script"
(`PitchLabItem.tsx:198`) then do nothing. The old app fell back to `execCommand('copy')`. It affects Pitch Lab item
and Materials answers; Application answers is fine (`copyAnswer`). Fix: move the body of `copyAnswer`
(`lib/applications.ts:116-129`) into `copyText` in `format.ts` and have `copyAnswer` call it.

**5. A reload that fails after a successful action still shows the success toast (shared file).**
`useLoad.reload` (`components/app/page.tsx:22-24`) never throws and returns null on failure, so
`await state.reload(); toast("Saved.")` reports success over stale data on every page here except the pitch editor,
which checks the result (`PitchEditor.tsx:372-373`). Fix in one place: in `page.tsx` have `reload` return the value
as now, and add to each page's action helper `if (!(await state.reload())) toast("That was saved, but the page did not refresh. Reload to see it.", true)`.
Caution: `Pipeline` returns `[]` for an empty list, so test with `=== null`, not falsiness.

**6. No error boundary, and a malformed path throws (shared files).** `routes.tsx:20` calls `decodeURIComponent` on
the path with no guard, and `main.tsx` has no boundary, so any render error on any page leaves a blank screen where
the old app showed "Unable to open this page" with a reload button. Fix: wrap `<App />` in `main.tsx` with a small
error boundary that shows that message, a "Reload" button and a link to `/pitches`; guard the decode in
`routes.tsx` with try/catch and fall back to the raw string.

**7. Quick view or page changes can show an older answer (shared file, also in the old app).** `useLoad`
(`page.tsx:16-27`) applies whichever request finishes last, so two fast clicks on Pipeline views or Materials
Next can leave the earlier request's list under the newer URL. Fix: keep a request counter in a ref inside
`reload` and ignore a result whose number is not the latest.

## Differences that are not defects

- Confirmations added: Prepare today's report (Applications.tsx:272) and Approve a lesson (PitchLab.tsx:208).
- "Could not read this form" is now a red toast (Opportunity.tsx:215; applications.ts:112).
- A closing program's to-do title keeps the month's capital letter (funding.ts:88); "Closes today" now carries the
  date (format.ts closingWords).
- The Applications notice about company facts now shows (the old page never loaded the data for it).
- The pitch editor's browser title is "<pitch> · Pitch · Founder OS" from the shell, not "<pitch> | A Story".
- `act()` on Applications and Application answers reloads even when a dialog is cancelled (harmless extra GET).
