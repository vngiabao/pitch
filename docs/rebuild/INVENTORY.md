# Founder OS: inventory of the old web app

Written 2026-11-11 from a full read of `founder_os/ui/*.js`, `founder_os/ui/index.html` and `founder_os/server.py`.
Purpose: rebuild every screen in React (`web/src`) without losing a function.
File references are `file:line`. `app.js` lines are long; a line number points at the statement.
Nothing in the old source was changed.

Counts: **29 screens** (27 inside the single-page shell, plus the server-rendered deck preview `/edition/<id>` and the
plan web version `/plan/<id>.html`), **66 POST endpoints** on the server (63 reachable from rendered UI, 3 with no
button), **45 GET API routes** (37 used by the old UI, 8 not).

---

## 1. How the old app works

### 1.1 Page shell and routing
- **It is not a client-side router.** Every link is a plain `<a href>` and causes a full page load. There is no
  `pushState` or `popstate` anywhere. `history.replaceState` is used only to keep filters in the URL
  (`app.js:176`, `app.js:218`).
- The server returns the same shell (`founder_os/ui/index.html`) for a fixed list of paths (`server.py:42`):
  `/`, `/funding`, `/opportunities`, `/activity`, `/applications`, `/memory`, `/materials`, `/decisions`, `/pitches`,
  `/credits`, `/people`, `/press`, `/pitch-lab`, `/money`, `/growth`, `/families`, `/scouts`, `/drive`,
  `/founder-profile`, `/plans`, `/assumptions`, and prefixes `/opportunity/`, `/run/`, `/material/`,
  `/application-review/`, `/application/`, `/pitch/`, `/pitch-lab/`.
  While serving it, the server replaces `__CSRF__` in the HTML with the session token and sets the session cookie
  (`server.py:43-44`).
- The shell loads scripts in this order, all `defer` (`index.html:2`): `pitch.js`, `growth.js`, `scouts.js`, `plans.js`,
  `product.js`, `ranker.js`, `drive.js`, `profile.js`, `assumptions.js`, then `app.js`. The earlier files define page
  functions and their own document-level listeners; they call `app.js` helpers (`E`, `api`, `toast`, `heading`, `boot`)
  at call time. `edition.js` is not loaded by the shell (only by the deck preview page).
- `boot()` (`app.js:321`) runs on load: clears the once-cache, runs `routeContext()` (department chrome, breadcrumbs,
  title), then `route()`, then `paintDirectory()` (the "Next: ..." line under each department).
- `route()` (`app.js:322-347`) maps `location.pathname` to a render function:

| Path | Render function | File:line |
|---|---|---|
| `/` | `home()` | app.js:138 |
| `/funding` | `fundingFront()` | app.js:151 |
| `/opportunities` | `opportunities()` + `updateList()` | app.js:168, 176 |
| `/opportunity/<id>` | `detail(id)` (+ `winSection`) | app.js:185, scouts.js:30 |
| `/applications` | `applications()` then `applicationLayout()` | app.js:207, 314 |
| `/application/<id>` | `applicationPage(id)` (+ `fillLabPanel`) | app.js:385, 598 |
| `/application-review/<id>` | `applicationReview(id)` | app.js:228 |
| `/credits` | `credits()` (+ `stackSection`) | app.js:435, scouts.js:60 |
| `/money` | `moneyMap()` (+ `applyFirst`) | app.js:586, ranker.js:16 |
| `/pitch-lab` | `pitchLab()` | app.js:528 |
| `/pitch-lab/<id>` | `pitchLabItem(id)` | app.js:557 |
| `/pitches` | `pitchLibrary()` | pitch.js:8 |
| `/pitch/<id>` | `pitchEditor(id)` | pitch.js:26 |
| `/assumptions` | `assumptionsPage()` | assumptions.js:36 |
| `/materials` | `materials()` | app.js:217 |
| `/material/<id>` | `material(id)` | app.js:227 |
| `/growth` | `growthDesk()` | growth.js:77 |
| `/families` | `betaFamilies()` | product.js:29 |
| `/drive` | `reservationDrive()` | drive.js:22 |
| `/press` | `press()` | app.js:472 |
| `/people` | `people()` | app.js:455 |
| `/decisions` | `decisions()` | app.js:255 |
| `/memory` | `memory()` | app.js:203 |
| `/founder-profile` | `founderProfile()` | profile.js:21 |
| `/activity` | `activity()` | app.js:201 |
| `/run/<id>` | `run(id)` | app.js:202 |
| `/scouts` | `scouts()` | scouts.js:21 |
| `/plans` | `plans()` | plans.js:14 |
| anything else served by the shell | falls back to `home()` | app.js:346 |

- Pages in the lower half of `route()` (`/`, `/funding`, `/opportunities`, `/opportunity/`, `/run/`, `/activity`,
  `/memory`, `/decisions`, `/credits`, `/people`, `/press`) first load **`GET /api/dashboard`** into the global `dash`
  (`app.js:342`) and update the Company badge `#decision-count` with `waitingCount()` (`app.js:230, 343`). Pages in the
  upper half do not load the dashboard unless `paintDirectory()` does it afterwards (`app.js:298`).
- Server-rendered pages outside the shell: `/edition/<id>` (deck preview HTML, `server.py:74-81`),
  `/plan/<id>.pdf` and `/plan/<id>.html` (`server.py:69-73`).
- The new React app is served at `/next`, `/next/`, `/next/today`, `/next/today/` (`server.py:47-50`), assets at
  `/next/assets/<name>.(js|css|woff2|webp)` and `/next/logos/<name>.png` (`server.py:51-57`).

### 1.2 Authentication of requests
- **Host check** on every GET and POST: the `Host` header must be `127.0.0.1:<port>` or `localhost:<port>` locally, or
  the Cloudflare Access hostname in cloud mode (`server.py:22-24`). Otherwise `403 {"error":"Host denied"}`.
- **Identity check** in cloud mode only: header `Cf-Access-Jwt-Assertion` must verify (`server.py:25-26`).
- **Session cookie:** `founder_session=<token>; Path=/; HttpOnly; SameSite=Strict` (+ `Secure` in cloud mode), set when
  a shell page (old or `/next`) is served (`server.py:36`). The token is one random value per server process
  (`server.py:16`), so it changes every time the server restarts.
- **All `/api/*` GETs, `/edition*`, `/plan/*` and `/edition-asset/*`** need the cookie, else
  `403 {"error":"Open the Founder OS command center first"}` (`server.py:60`). Static JS/CSS/fonts do not.
- **POSTs** need all of (`server.py:231-238`):
  - host and identity checks, the session cookie, and
  - header **`X-Founder-CSRF`** equal to the same token; else `403 {"error":"Owner session required"}`.
    The old UI reads it from `<meta name="founder-csrf" content="...">` in the shell (`index.html:2`, `app.js:46`).
  - header **`Origin`** equal to `http://127.0.0.1:<port>` or `http://localhost:<port>` (local), or
    `https://<access hostname>` (cloud); else `403 {"error":"Origin denied"}`.
  - `Content-Type: application/json` (charset suffix allowed); else `415 {"error":"JSON request required"}`.
  - `Content-Length` between 1 and 65536 bytes; else `413 {"error":"Request size denied"}`. An empty body is refused,
    which is why the old UI sends `{}` for actions with no fields.
- **Gap for the rebuild:** `/next/index.html` is served as raw bytes with no `__CSRF__` replacement (`server.py:49`),
  and `web/index.html` has no `founder-csrf` meta. The token is also the HttpOnly cookie value, so React cannot read
  it. Until the server injects the token into the `/next` shell, the React app cannot make any POST.
- Response headers on everything: `Cache-Control: no-store`, `X-Frame-Options: DENY`, and a CSP of
  `default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:;
  frame-ancestors 'none'; form-action 'self'` (`server.py:33-34`). No inline scripts or inline styles, no iframes.

### 1.3 The fetch helper
`api(path, body)` (`app.js:44-50`):
- GET when `body` is missing; **POST when `body` is given**, with headers
  `{'Content-Type':'application/json','X-Founder-CSRF': <meta content>}` and `body: JSON.stringify(body)`.
  Default credentials (same-origin cookies).
- 20-second timeout through `AbortController`; on abort: "The workspace took too long to respond. Try again."
- If the response is not JSON: "Your sign-in expired or the server returned an unexpected page. Reload to sign in again."
- If `!r.ok`: throws `Error(v.error || 'Unable to complete this action.')`. Server errors are `{"error": "..."}` with
  400 (ValueError/TypeError/KeyError, including policy refusals), 403, 404, 409 (pitch version conflict,
  `server.py:390-391`), 413, 415.
- Network failure (`TypeError`): "The workspace is offline. Check that your PC is awake and online, then reload."
- `apiOnce(path)` (`app.js:52`): caches the GET promise per page load; used for `/api/application-list`,
  `/api/growth-alerts`, `/api/lab-alerts`, `/api/founder-profile`. `boot()` clears the cache.
- `loadDash()` (`app.js:320`): de-duplicates concurrent `/api/dashboard` calls.

### 1.4 After an action
The standard pattern is: disable the button, `await api(...)`, then **`await boot()`** (re-fetch and re-render the
whole page), then `toast(...)`. A few actions navigate instead (`location.href = ...`). There is no optimistic update.

### 1.5 Errors, notifications, confirmations
- `toast(text, error=false)` (`app.js:53`) writes one `<div class="toast [error]">` into `#status`
  (`role="status" aria-live="polite"`) and scrolls it into view. It replaces the previous toast and never times out;
  the next `boot()` does not clear it.
- Page-load failure: `boot().catch` (`app.js:630`) replaces the page with "Unable to open this page" + the error
  message + a "Reload workspace" button (`data-action="reload"`) + a link to `/pitches`.
- Confirmations use the browser's `confirm()`; free-text reasons use `prompt()`. Every one is listed in section 6.
- Initial loading state is the skeleton in the shell ("Opening your workspace / Reading saved work…", `index.html:4`).
  Pages have no per-page spinner except `#opportunity-list` ("Reading opportunities…", `app.js:173`).

### 1.6 Polling and timers
- **No polling anywhere.** Agent work (drafts, research, plans, builds) finishes in the background; the user reloads.
  Toasts say so ("Reload in about 2 minutes", "appears here in a few minutes").
- Timers: the 20s fetch timeout (`app.js:45`), the 1.6s "Copied" label (`app.js:402`), and the rehearsal stopwatch
  `setInterval(pitchDrawTimer, 500)` (`pitch.js:77`).
- `sessionStorage` keys: `astory-materials-list` (last materials URL, `app.js:218, 336`), `astory-pitch-library`
  (last pitch library URL, `pitch.js:10, 94`), `astory-pitch-recovery:<pitch_id>` (unsaved editor text,
  `pitch.js:101-108`). No `localStorage`.
- `beforeunload` warning when the pitch editor is dirty (`pitch.js:6`). `Ctrl/Cmd+S` saves the pitch (`pitch.js:114`).

### 1.7 Background workers started by POSTs
- `start_worker()` (`server.py:394`) launches `tools/research_worker.py` after: `/api/run-now`, `/api/read-form` (only
  when `draft_queued`), `/api/research`, `/api/growth-draft`, `/api/press-discover`, `/api/deal-draft`,
  `/api/partner-discover`, `/api/campaign-plan`, `/api/lab-edition`, `/api/lab-review`, `/api/lab-application`,
  `/api/lab-rerun`, `/api/plan`, `/api/win-research`, `/api/scout-run`, `/api/assumption-challenge`.
- `start_autonomy_worker()` (`server.py:398`) launches `tools/autonomy_worker.py` after `/api/application-confirm` and
  `/api/report-now`. This is the worker that can send email and submit a confirmed application.
- `/api/connect-report-email` and `/api/connect-inbox` open a PowerShell console window on the PC (`server.py:281-294`).

---

## 2. Navigation map

Source: `DEPTS` (`app.js:277-283`), the sidebar and "All pages" list in `index.html:4`, `routeParent()` (`app.js:284`).

| Department | Sidebar link | Tabs (path, label) | Detail pages under it |
|---|---|---|---|
| **Today** | `/` | `/` Today | none |
| **Funding** | `/funding` | `/funding` Needs you · `/opportunities` Pipeline · `/applications` Applications · `/credits` Credits · `/money` Money map | `/opportunity/<id>` (parent Pipeline) · `/application/<id>` and `/application-review/<id>` (parent Applications) · `/applications?tab=work|reports|settings` |
| **Pitch** | `/pitch-lab` | `/pitch-lab` Pitch Lab · `/pitches` Pitch Studio · `/assumptions` Assumptions · `/materials` Materials & answers | `/pitch-lab/<id>` (parent Pitch Lab) · `/edition/<id>` (deck preview, new tab, outside shell) · `/pitch/<id>` (parent Pitch Studio) · `/material/<id>` (parent Materials) |
| **Customers** | `/growth` | `/growth` Deals & campaigns · `/families` Beta families · `/drive` Reservation drive · `/press` Press & gift guides · `/people` People | none (anchors `#deal-<id>`, `#campaign-<key>`, `#families-say`, `#channels`, `#person-<id>`, `#drive-<id>`, `#family-<id>`) |
| **Company** | `/decisions` (switches to `/founder-profile` when no facts wait but the profile has blanks, `app.js:307`) | `/decisions` Decisions · `/memory` Company facts · `/founder-profile` Founder profile | none |
| **Agents** | `/activity` | `/activity` Activity · `/scouts` Scouts · `/plans` Plans | `/run/<id>` (parent Activity) · `/plan/<id>.pdf` and `/plan/<id>.html` (files) |

Shell pieces that appear on every page:
- **Sidebar** (`aside.directory`): brand link to `/`, six department links each with a purpose line and a live
  "Next: ..." line painted by `paintDirectory()` (`app.js:295-312`), the Company count badge `#decision-count`.
- **"All pages"** `<details>` (`index.html:4`): Funding (Needs you, Pipeline, Applications, Credits, Money map), Pitch
  (Pitch Lab, Pitch Studio, Assumptions, Materials & answers), Customers (Deals & campaigns, Beta families,
  Reservation drive, Press & gift guides, People), Company (Decisions, Company facts, Founder profile), Agents
  (Activity, Scouts, Plans). The current page gets `aria-current="page"`.
- **Global search** form `#global-search`: plain `GET /materials?q=<text>` (`index.html:4`).
- **"Run research now"** button (`.rail-run`, `data-action="run"`) → `POST /api/run-now {}`. Disabled with the title
  "Paused until the research agent is fixed" when the last run failed with a known cause (`app.js:309`).
- **`#workspace-location`**: "Owner sign-in protected" on `pitch.gbaonvo.com`, else "On this PC" (`app.js:291`).
- **Top bar**: phone brand link, `#breadcrumbs` (only on detail pages: `Dept / Tab / Detail`, `app.js:289`), the
  "Departments" toggle for the phone drawer (`#nav-toggle`, `#nav-close`, Escape closes; `app.js:350-352`).
- **Department chrome** `#dept-chrome`: department name, purpose and the tab row (not on Today) (`app.js:290`).
- **Document title**: `<Tab> · <Dept> | A Story`, or `Today | A Story` (`app.js:291`).
- **Skip link** to `#app`.

`paintDirectory()` data (`app.js:295-312`): `/api/dashboard`, `/api/application-list`, `/api/growth-alerts`,
`/api/lab-alerts`, `/api/founder-profile` (`total`, `filled`). It sets:
Funding "Next: <first funding item>", Pitch "Next: <first lab alert or assumptions alert>", Customers
"Next: <first customer alert title>", Company "Next: confirm a company fact / company facts" or "Next: fill your
founder profile" or "All facts confirmed", Agents "Research stopped <day>" (urgent) / "Research is running now" /
"Last research <day>".

---

## 3. Pages

Notation: **GET** = data read on load. **Actions** = element, endpoint, payload keys, confirmation, what happens after.
"reload" means `await boot()` then the toast quoted.

### 3.1 Today: `/` (already rebuilt at `/next/today`)
- **Purpose:** one line of state, the single next step, at most 3 follow-ups, three numbers.
- **Render:** `home()` `app.js:138-149`; helpers `doNext` `app.js:86-98`, `leadCard` `app.js:116-126`, `leftForYou`
  `app.js:107-114`, `alertItem` `app.js:102`, `researchAlert` `app.js:130-135`, `itemRows` `app.js:127`.
- **GET:** `/api/dashboard` (`money_board.cash[]`, `money_board.credits[]`, `money_board.tracked[]` with `waiting`,
  `outcome`; `needs_decision[]` with `card.kind`; `inbox.proposed`, `inbox.review`, `inbox.deal_replies`;
  `agent_activity[0]`), `/api/application-list` (`opportunity_id`, `application_id`, `program`, `questions`,
  `answered`, `access.level`, `access.label`, `url`), `/api/growth-alerts` and `/api/lab-alerts` (`title`, `detail`,
  `url`, `link`), and for the lead card `/api/application/<id>` (`questions[]`).
- **Next-step order** (`doNext`): applications with READY/DRAFTING answers; "Confirm N company facts" → `/decisions`;
  "Confirm N results from your inboxes" → `/decisions`; programs closing in 0-7 days; up to 2 login-blocked forms
  (external link). Capped at 6, then growth alerts and lab alerts are appended.
- **Actions:** all are links. `data-action="run"` "Run it again" inside the research alert → `POST /api/run-now {}`
  → toast "Research request saved. The connected worker will run the scan and record its findings." (no reload).
- **States:** nothing waiting ("Nothing needs you right now"); partial load ("Part of your work didn’t load" with a
  "Load it again" button); research failed alert with "See what failed" → `/run/<id>`.
- **Unusual:** the "Load it again" button uses an inline `onclick="location.reload()"` (`app.js:145`), which the CSP
  (`script-src 'self'`) blocks, so that button does nothing in the old app.
- **Links out:** `/funding`, `/funding#wait-results-title`, `/opportunities`, `/founder-profile`.

### 3.2 Funding, needs you: `/funding`
- **Purpose:** Funding's own to-do list, then more cash programs, more credit programs, and what is waiting on results.
- **Render:** `fundingFront()` `app.js:151-161`; `fundingItems` `app.js:105`, `leadCard(…, compact=true)`, `itemRows`
  `app.js:127`, `tocRow` `app.js:80-84`, `moneyFigure` `app.js:74`, `closingWords` `app.js:68`, `paintDays`
  `app.js:85`, `waitingSection` `app.js:364-369`.
- **GET:** `/api/dashboard` (`money_board.cash/credits[]`: `opportunity_id`, `data.canonical_name`,
  `data.dates.deadline`, `analysis.scoring.dates.days_remaining`, `analysis.money.{kind,cash_max,credits_face_value}`,
  `analysis.founder_brief.{how_it_helps,priority}`; `money_board.tracked[]`: `waiting`, `outcome`, `occurred_at`,
  `next_date`, `canonical_name`, `application_id`, `opportunity_id`; `inbox.accounts[].connected`),
  `/api/application-list`, `/api/growth-alerts` (only alerts whose `url` starts `/credits` or `/opportunity/`).
- **Actions:** links only. To-do rows link to `/application/<id>`, `/opportunity/<id>`, `/credits`, or the external
  form (new tab).
- **Downloads:** "Export tracker (CSV)" → `GET /api/tracker/export.csv`
  (file `A-Story-application-tracker-<date>.csv`).
- **States:** "Nothing in Funding needs you right now."; empty cash list ("Nothing else open with cash right now…");
  empty credits list; "Nothing pending. Mark an application submitted and it shows up here."
- **Unusual:** scrolls to `location.hash` after render (used by Today's `#wait-results-title` links). The day bar
  width is set through a CSS variable `--days-pct` = days/60 (`paintDays`).

### 3.3 Funding pipeline: `/opportunities`
- **Purpose:** every tracked program in a filterable table.
- **Render:** `opportunities()` `app.js:168-175`, `updateList()` `app.js:176`, `rows()` `app.js:56-60`, `dedupe`
  `app.js:55`, `notice()` `app.js:61`.
- **GET:** `/api/dashboard` (for type options and the notice), `/api/opportunities?view=<view>&<filters>`,
  `/api/application-list` (cached in `appsCache`).
  Row fields: `opportunity_id`, `data.canonical_name`, `data.opportunity_type`, `data.cycle`, `data.cycle_kind`,
  `data.funding.{cash_prize_max,award_scope,credits_value,other_benefits}`, `data.dates.deadline`,
  `analysis.scoring.dates.days_remaining`, `analysis.materials.estimated_hours`.
- **Views:** buttons `Recommended`, `Apply Now`, `Watching`, `Applied`, `All`; "More" select `New`, `Prepare`,
  `Accepted`, `Rejected`, `Skipped`, `Expired` (`app.js:3`). The view comes from `?view=` (default `Recommended`).
  For Recommended and Apply Now, programs past their deadline are hidden client-side.
- **Filter form `#filters`** (query keys): `type` (select), `min_cash` (number), `deadline_before` (date),
  `non_dilutive` (`""`/`"1"`), `effort` (`Very Low|Low|Medium|High|Very High|UNKNOWN`), `location`, `category`,
  `min_score` (0-100). Submit re-queries; URL becomes `/opportunities?view=…&…` via `replaceState`. "Clear" links to
  `/opportunities`. The filter panel opens by itself when any filter is in the URL.
- **Table columns:** Program (link to `/opportunity/<id>`, type · cycle · "N other cycles"), Value, Deadline,
  Application (access chip + "Open answers" link to `/application/<id>`), Your effort.
- **Actions:** none that POST.
- **States:** "Reading opportunities…"; "No programs in this view. Try All, or clear the filters."; the notice
  "Company eligibility needs confirmation" when `dash.company_memory.canonical_claims` is empty.
- **Unusual:** duplicate names are merged into one row client-side with a count of other cycles.

### 3.4 Opportunity detail: `/opportunity/<id>`
- **Purpose:** everything about one program: value, deadline, fit, eligibility, readiness, how to win, sources.
- **Render:** `detail(id)` `app.js:185-199`; `stageStrip` `app.js:162`, `accessLine` `app.js:371`, `creditConditions`
  `app.js:179-184`, `materialList` `app.js:178`, `score` `app.js:15`, `winSection` `scouts.js:30-47`.
- **GET:** `/api/opportunity/<id>` (`data.{canonical_name,cycle,cycle_kind,organizer,application_url,official_url,
  notes,funding.{cash_prize_max,credits_value,award_scope,equity_required,investment_terms},dates.deadline,
  credit_benefits.*}`, `analysis.{why_fit[],why_not_fit[],risks[],eligibility.{checks[]{result,requirement,
  source_url},missing[]},materials.{percentage,estimated_hours,ready[],needs_adaptation[],missing[]},
  scoring.{components{points,weight,reason},coverage,dates.days_remaining},credits.{cost_status,value_note}}`,
  `fit_score`, `recommendation`, `outcomes[]`, `applications[]`, `last_verified`,
  `source_provenance[]{url,role,excerpt,checked_at}`, `history[]{kind,note,original_path}`,
  `decisions[]{decision,reason}`), `/api/application-list`, `/api/win/<id>` (`brief`, `researching`, `checked_at`,
  `runs`, `changes[]`, `seen`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Read the form & prepare answers" (`data-read-form`) | `POST /api/read-form` | `{opportunity_id}` | none | button text "Reading the form…"; if `state==='QUESTIONS_READ'` and `application_id` → go to `/application/<id>`; else reload + toast "Read N questions and filled M from your facts. [The agent is drafting the rest.]" or "The agent could not read this form: <reason>" (`app.js:414-418`) |
| "Open answers · X of Y ready" | link `/application/<id>` | | | |
| "Official form ↗ / Official program ↗" | external link, new tab | | | |
| "Mark submitted" (`data-outcome="Applied"`) | `POST /api/outcome` | `{opportunity_id, outcome:'Applied', application_id:null, note:'Owner marked submitted in Founder OS.'}` | `confirm('Record that you submitted this application? The agents will stop recommending it.')` | reload + "Marked submitted. It now appears under Waiting on results." (`app.js:404-409`) |
| "Watch" / "Skip" (`data-action="decision"`) | `POST /api/decision` | `{opportunity_id, decision:'WATCH'|'SKIP', reason}` | `prompt('Reason for your watch/skip decision:')`; nothing sent when empty | reload + "Decision saved with the agent recommendation." |
| "Check the program again" (`data-action="research"`) | `POST /api/research` | `{opportunity_id}` | none | toast "Re-verification request saved for this opportunity." (no reload) |
| "Tailor the pitch" | link `/pitch-lab?program=<id>` | | | |
| Form `#decision-form` "Record a decision with a reason" | `POST /api/decision` | `{opportunity_id, decision:'APPLY'|'PREPARE'|'WATCH'|'SKIP', reason}` (reason required) | none | reload + "Decision saved. Scoring weights remain unchanged." (`app.js:349`) |
| Win Scout "Research how to win" / "Research again" (`data-win-research`) | `POST /api/win-research` | `{opportunity_id}` | none | reload + "Win Scout started. The brief lands on this page in about 15 minutes." (`scouts.js:48-54`) |
| Win Scout "Got it" (`data-win-seen`) | `POST /api/win-seen` | `{opportunity_id}` | none | reload |

- **Sections:** four lead facts; access line; stage strip (Found, Preparing, Applied, Decided); "How we win here"
  (moves grouped by `applies_to`: pitch, application, qa, demo, materials; "What nobody writes down"; criteria chips;
  rules; judges; other companies; past winners; risks and open questions; sources); "Why it may fit A Story";
  "Eligibility" checks (Meets/Fails/Unknown + source link); "Application readiness" with a `<progress>` bar;
  disclosures: Credits & conditions, How the fit score works, Sources & verification, Program history, Record a
  decision.
- **States:** "Not started. The agent has not read this application form yet."; Win Scout empty and "Researching…"
  states; "Changed since last time" notice.
- **Unusual:** `new URL(s.url).hostname` can throw on a malformed source URL (`app.js:198`).

### 3.5 Applications: `/applications` (three tabs via `?tab=work|reports|settings`)
- **Purpose:** the application to-do list, the daily email, and the agent's on/off settings.
- **Render:** `applications()` `app.js:207-215` builds four sections; `applicationLayout()` `app.js:314-319` adds the
  tab row ("To do", "Daily email", "Agent settings") and hides sections by tab. `confirmationPreviews` `app.js:204`,
  `applicationGroups` `app.js:380`, `appRow` `app.js:372`, `fallbackNote` `app.js:200`.
- **GET:** `/api/application-list`, `/api/autonomy` (`authorizations[]{id,scope,revoked_at}`,
  `confirmations[]{id,decision,email_state,payload_json{email,application_url,fields}}`,
  `reports[]{id,local_date,state,error}`, `mail_delivery{mode,smtp_fallback{enabled,after_minutes}}`,
  `mail_connected`, `smtp_fallback_connected`, `report_schedule{hour,minute}`), and on demand `/api/report/<id>`
  (`body`).
- **Tab "To do" (default):**
  - *Filled application previews* (one per confirmation): email used, preview-email state, link to the official
    application, a `<dl>` of every field and value, and two buttons that are **disabled until `email_state==='SENT'`**:

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Confirm these fields and submit" (`data-action="confirm-application"`, `data-decision="APPROVED"`) | `POST /api/application-confirm` | `{confirmation_id, decision:'APPROVED', confirmed:true}` | `confirm('Submit this exact emailed application preview?')` | starts the autonomy worker; reload + "Your exact application decision is saved." |
| "Decline this application" (`data-decision="REJECTED"`) | `POST /api/application-confirm` | `{confirmation_id, decision:'REJECTED', confirmed:true}` | `confirm('Decline this exact application preview?')` | same |

  - *Application groups* by `access.level` (`ACCESS_GROUPS`, `app.js:370`): Ready to copy, Agent is drafting,
    Blocked, Not read yet. Row actions: "Open answers" → `/application/<id>`; "Read the form now" / "Re-read the
    form" / "Try reading it again" → `POST /api/read-form {opportunity_id}` (see 3.4); "Open the official form ↗" or
    "Open the program page ↗" (external).
  - *Finished and not pursuing (N)* disclosure: links to `/application/<id>` with the outcome tag.
- **Tab "Daily email":** connection tag, schedule line, and:

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Connect report email" (only when not connected) | `POST /api/connect-report-email` | `{}` | none | opens a PowerShell window on the PC; toast "Secure Gmail setup opened on this PC. Enter the Google app password there, never in chat." |
| "Prepare today’s report" | `POST /api/report-now` | `{}` | none | starts the autonomy worker (which may email the report); reload + "Today’s report is saved. The sender will use the connected mail account when available." |
| "Pause email reports" | `POST /api/autonomy-pause` | `{authorization_id}` | none | reload + "Automatic action paused." |
| "Resume daily reports" | `POST /api/autonomy-resume` | `{scope:'daily_email_report', confirmed:true}` | `confirm('Resume this previously authorized agent with the same limits?')` | reload + "Automatic action resumed with the existing limits." |
| Past report date (`data-action="show-report"`) | `GET /api/report/<id>` | | | toggles the report body inline as `<pre>`; sets `aria-expanded` |

  Past reports list: first 14, with state word (`STATE_WORDS`, `app.js:6`) and error text. Empty: "No reports yet. The
  first one arrives at 9 AM."
- **Tab "Agent settings":** Application Pilot status tag and:

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Pause application preparation" | `POST /api/autonomy-pause` | `{authorization_id}` | none | reload + "Automatic action paused." |
| "Resume application preparation" | `POST /api/autonomy-resume` | `{scope:'free_application_pilot', confirmed:true}` | same confirm as above | reload + "Automatic action resumed with the existing limits." |

- **States:** "No open applications. New programs appear here once the agent finds and reads their forms."
- **Unusual:** tab switching is a full page load; `applicationLayout` depends on there being exactly 4 `.section`
  children; hard-coded emails `gbao.n.vo@gmail.com` and `bao@astoryapp.com` in the copy (`app.js:211-212`).

### 3.6 Application answers: `/application/<id>`
- **Purpose:** the copy-paste sheet for one application, plus recording its result.
- **Render:** `applicationPage(id)` `app.js:385-398`; `answerBox` `app.js:358`, `countLabel` `app.js:354`,
  `fillLabPanel` `app.js:598-606`.
- **GET:** `/api/application/<id>` (`id`, `program`, `cycle`, `opportunity_id`, `application_url`, `official_url`,
  `access{level,label,detail}`, `outcomes[]{outcome,occurred_at,note}`,
  `questions[]{id,label,prompt,type,options[],limit,unit,needs_you,answer{body,status,provenance,notes[]}}`),
  then `/api/lab` to find an `APPLICATION_SET` item with `subject_id===id`.
- **Not yet submitted:** three numbered steps: open the official form (external link), copy the answers (with jump
  links `#q-<id>` to the first 5 open questions), "Mark submitted".
- **Submitted:** a status block with the latest outcome and the result form.
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Copy" on each answer (`data-copy`) | clipboard only | | | label "Copied" for 1.6s (`app.js:399-405`) |
| "Read the form now" / "Re-read the form" | `POST /api/read-form` | `{opportunity_id}` | none | reload + toast (see 3.4; stays on this page) |
| "Mark submitted" | `POST /api/outcome` | `{opportunity_id, outcome:'Applied', application_id, note:'Owner marked submitted in Founder OS.'}` | `confirm('Record that you submitted this application? The agents will stop recommending it.')` | reload + "Marked submitted. It now appears under Waiting on results." |
| Form `#outcome-form` "Record a result" | `POST /api/outcome` | `{opportunity_id, application_id, outcome, note, evidence_url}`; `outcome` ∈ `Advanced|Finalist|Won|Accepted|Rejected|Withdrawn`; `evidence_url` null when empty | none | reload + "Result saved." (`app.js:410-413`) |
| "Review these answers" (`data-lab-app`) | `POST /api/lab-application` | `{application_id}` | none | go to `/pitch-lab/<new id>` |
| "Open the review" | link `/pitch-lab/<id>` | | | |

- **Per question:** label, options (first 12) when unanswered, the answer box with a word or character count against
  `limit`/`unit` ("over limit" state), the source line (`SOURCE_WORDS`, `app.js:384`: From your facts, From your
  founder profile, Agent draft, Your wording, Draft, or Approved) plus notes; or "Needs you." with `needs_you` /
  "Upload this file yourself on the official form."
- **States:** "No questions saved for this application yet."; "Link not found yet"; history disclosure when more than
  one outcome; the lab panel hides itself if `/api/lab` fails.
- **Unusual:** answers are read-only here; editing happens in the official form. Clipboard falls back to
  `document.execCommand('copy')`.

### 3.7 Application plan: `/application-review/<id>`
- **Purpose:** a stub for a planned application whose form has not been read.
- **Render:** `applicationReview(id)` `app.js:228`.
- **GET:** `/api/application-review/<id>` (`application_id`, `program`, `cycle`, `url`, `blockers[]`).
- **Behaviour:** if `application_id` is set, `location.replace('/application/<id>')`. Otherwise shows "Open the
  official form ↗" (external) or "Application link not found yet.", and "What needs attention" (blockers, or
  "Preparation checks passed.").
- **Actions:** none.

### 3.8 Credits: `/credits`
- **Purpose:** credit grants won, their dates and balances, and the monthly cost stack they should cover.
- **Render:** `credits()` `app.js:435-441`; `creditCard` `app.js:422-434`; `stackSection`, `stackRow`
  `scouts.js:56-66`.
- **GET:** `/api/dashboard` (route prerequisite), `/api/credits` (`id`, `provider`, `level`
  (`DONE`, `NEEDS_DATES`, …), `label`, `allowance`, `covers`, `started_on`, `ends_on`, `expires_on`, `term_months`,
  `after_expiry`, `balance_note`, `balance_checked_on`, `balance_stale`, `notes`, `account_email`, `state`,
  `program_url`), `/api/stack` (`items[]{id,item,provider,monthly_usd,covered_by}`, `credit_providers[]`,
  `monthly_uncovered`, `monthly_covered`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| `.credit-form` "Update dates and balance" | `POST /api/credit` | `{id, started_on, expires_on, balance_note, account_email, state, notes}`; `state` ∈ `ACTIVE|NOT_ACTIVATED|USED_UP|ENDED` | none | toast "Credit details saved." + reload (`app.js:490-499`) |
| `.stack-form` row "Save" | `POST /api/stack-cost` | `{id, item, provider, monthly_usd, covered_by}` | none | reload + "Saved." |
| `.stack-form.stack-add` "Add" | `POST /api/stack-cost` | `{item, provider, monthly_usd, covered_by}` (no `id`) | none | reload + "Saved." |
| "Remove" (`data-stack-delete`) | `POST /api/stack-delete` | `{id}` | `confirm('Remove this item?')` | reload + "Removed." |

- **States:** "No active credit grants. Accepted credit programs appear here on their own."; "Used up or ended (N)"
  disclosure; the form opens by itself when `level==='NEEDS_DATES'`; stack section is skipped if `/api/stack` fails.
- **Unusual:** form values are sent as strings (`Object.fromEntries(new FormData)`), including `monthly_usd`.

### 3.9 Money map: `/money`
- **Purpose:** every route to money: the ranked "apply first" list, Bao's own money moves, and programs by category.
- **Render:** `moneyMap()` `app.js:586-597`; `applyFirst` `ranker.js:16-21` (rows `ranker.js:9-15`, parts
  `ranker.js:5-8`).
- **GET:** `/api/money` (`moves[]{id,grp,title,detail,state}`, `categories[]{key,title,note,programs[]{id,name,amount,
  kind,deadline,days,rolling,outcome,access,application_id,edition{id,stage}}}`, `apply_first{rows[]{opportunity_id,
  name,reason,per_hour,expected_value,money{counted,basis},likelihood{value,fit,fit_known,eligibility,
  eligibility_factor},hours{value,source},urgency{factor,days},preparation{summary,application_id,questions,
  edition{id}}},unpriced[]{name}}`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| Segmented To do / Doing / Done (`data-move`, `data-state`) | `POST /api/money-move` | `{id, state:'TODO'|'DOING'|'DONE'}` | none | reload, no toast (`app.js:626`) |

- **Links:** `/opportunity/<id>`, `/application/<id>`, `/pitch-lab/<edition id>`, `/pitch-lab?program=<id>`; anchor nav
  `#apply-first`, `#moves`, `#cat-<key>`.
- **Unusual:** "How this was figured" and "How this number is made" disclosures carry the method text
  (`ranker.js:19`); the per-hour figure is labelled "per hour, modeled".

### 3.10 Pitch Lab: `/pitch-lab` (accepts `?program=<opportunity id>` and `?coach=<pitch id>` to preselect)
- **Purpose:** start and follow agent-made pitch editions, pitch reviews and answer reviews; approve lessons.
- **Render:** `pitchLab()` `app.js:528-545`; `labGroups` `app.js:520`, `labCard` `app.js:524`, `stageChip`
  `app.js:514`, `assemblyLine` `app.js:516`.
- **GET:** `/api/lab` (`items[]{id,kind,title,stage,stage_words,round,error,summary{low,avg,timing{seconds}},
  updated_at,created_at,subject_id}`, `lessons[]{id,state,body,evidence,applies_to}`, `stages{}`, `voice_examples`),
  `/api/lab-options` (`programs[]{id,name}`, `pitches[]{id,title}`, `applications[]{id,program}`).
- **Forms:**

| Form | Fields | Endpoint | Payload | After |
|---|---|---|---|---|
| `#lab-edition` "Tailor for a program" | `opportunity_id` (select, required), `minutes` (0.5-30, step 0.5, default 3, required), `slide_limit` (1-40, optional), `note` (≤1000) | `POST /api/lab-edition` | `{opportunity_id, minutes:Number, slide_limit:Number|null, note}` | go to `/pitch-lab/<id>` |
| `#lab-review` "Coach a saved pitch" | `pitch_id` (select, required) | `POST /api/lab-review` | `{pitch_id}` | go to `/pitch-lab/<id>` |
| `#lab-application` "Review application answers" | `application_id` (select, required) | `POST /api/lab-application` | `{application_id}` | go to `/pitch-lab/<id>` |

- **Other actions:** lesson "Approve" / "Reject" (`data-lesson`, `data-decision`) → `POST /api/lesson`
  `{id, decision:'APPROVED'|'REJECTED'}` → reload + "Every agent follows this from now on." / "Lesson rejected."
- **Sections:** Ready for you (newest per program, older drafts folded), On the assembly line, Start something new,
  How every draft is made (9 steps, `LAB_AGENTS` `app.js:502`), Lessons (proposed, approved list), Approved (N).
- **States:** "No new lessons. They appear after a result comes in or after you edit three drafts."

### 3.11 Pitch Lab item: `/pitch-lab/<id>`
- **Purpose:** one agent-made item: progress, coach scorecard, rules, timed script, slide plan, deck build, history.
- **Render:** `pitchLabItem(id)` `app.js:557-584`; `progressLine` `app.js:553`, `coachCard` `app.js:546-552`,
  `deckSection` `app.js:504-513`, `scoreDots` `app.js:515`.
- **GET:** `/api/lab/<id>` (`title`, `kind`, `round`, `stage`, `stage_words`, `flow[]`, `error`,
  `coach{summary,top_fixes[],scores[]{criterion,score,why,fix},hard_questions[]{question,answer,gap}}`,
  `reviews[]{agent,round,verdict,created_at,detail{issues[],changed[],answers_to_feedback[]}}`, `payload{minutes,
  timing{words,seconds},unresolved[]{from,text,where},brief{rules{minutes,format,slide_limit,prize,equity,deadline,
  judging_criteria[],required_sections[],source_urls[]},strategy,script[]{title,text,seconds},
  slide_plan[]{action,slide_id,change,why},ask,materials[],open_questions[]},edition{slides[],core,round,
  new_slides[]},slide_qa{available,blocking,warnings,reason,slides[]{n,id,issues[]{severity,text}}},
  answers[]{question_id,question,text,suggested,limit,unit},fact_issues[]{where,severity,text},text,title,body}`,
  `program_detail`).
- **Kinds** (`LAB_KIND_WORDS`, `app.js:501`): `PITCH_EDITION`, `PITCH_REVIEW`, `APPLICATION_SET`, `GROWTH_DRAFT`,
  `OUTCOME_LESSON`, `VOICE_RULES`. Each shows a different body.
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Save script to Pitch Studio" (`data-lab-save`, editions only) | `POST /api/lab-save` | `{id}` | none | go to `/pitch/<pitch_id>` |
| "Approve" (`data-lab-approve`, stage READY) | `POST /api/lab-approve` | `{id}` | none | reload + "Approved. Submit it yourself when you’re ready." |
| "Build the deck" / "Rebuild and check again" (`data-lab-build`) | `POST /api/lab-build` | `{id}` | none | button text "Building and checking…"; synchronous, can outlast the 20s timeout; then re-renders the item |
| "Open the deck preview" | link `/edition/<id>` (new tab) | | | |
| "Download the deck files" | `GET /api/lab/<id>/edition.zip` | | | file `A-Story-<id>-round-<n>.zip` |
| "Copy the whole script" / per-slide "Copy" / answer "Copy" | clipboard | | | |
| Form `.lab-rerun` "Ask for another round" | `POST /api/lab-rerun` | `{id, note}` (≤1000) | none | reload + "Another round started." |

- **States:** agent error notice ("An agent step stopped" + first 300 chars); working state ("This page fills in as
  each agent finishes."); "Still needs your eyes" list; "Slide QA did not run: <reason>"; first 12 QA issues then
  "N more in the preview."; "Rules not read from an official page yet."
- **Unusual:** the largest payload shape in the app; the whole script is built into one `data-copy` attribute.

### 3.12 Deck preview: `/edition/<id>` (server-rendered, opens in a new tab)
- **Purpose:** every slide of an edition rendered at 1920 wide, with Slide QA flags drawn over the slide.
- **Render:** Python `slide_deck.preview_page(manifest, qa, title)` (`slide_deck.py:234`), served by `server.py:74-81`
  with its own CSP (allows inline styles and Google Fonts; `connect-src 'none'`; `form-action 'none'`).
- **Assets:** slide images from `GET /edition-asset/<name>` (`server.py:61-65`, cookie required); `/edition.css`,
  `/edition.js`, `/vendor/gsap.min.js`, `/vendor/ScrollTrigger.min.js`.
- **Behaviour (`edition.js:1-19`):** scales each `.pv-slide` by `clientWidth/1920` on load and resize; hovering a QA
  note highlights its flag (`data-for` ↔ `data-flag`); GSAP entrance and a pulsing "block" flag, only when
  `prefers-reduced-motion: no-preference`.
- **Errors:** `404 {"error":"This edition has no deck yet"}`.
- **Actions:** none. Read-only.

### 3.13 Pitch Studio library: `/pitches` (query: `q`, `audience`, `scenario`, `duration`, `archived=yes`, `material=<id>`)
- **Purpose:** the library of saved pitches and the form to start a new one.
- **Render:** `pitchLibrary()` `pitch.js:8-24`; `pitchLengthLinks` `pitch.js:96-100`, `pitchDataLists` `pitch.js:25`.
- **GET:** `/api/pitches?<query>` (`items[]{pitch_id,title,audience,scenario,preview,word_count,duration_seconds,
  estimated_seconds,status,format,placeholders[]}`, `audiences[]`, `scenarios[]`, `lengths[]`); when `?material=` is
  present also `/api/material/<id>` (`relative_path`, `source_path`, `body`, `source_version_id`).
- **Forms:**
  - `#pitch-new-form` (hidden until "Write a new pitch", or shown when adapting a material): `title` (required, ≤160),
    `duration_minutes` (0.17-120, default 1), `audience` (datalist, default "General"), `scenario` (datalist, default
    "Quick introduction"), `body` (textarea, required, ≤40000; prefilled with the first 40,000 characters of the
    material). → `POST /api/pitches` with `{title, duration_minutes, audience, scenario, body,
    duration_seconds: round(minutes×60), sources:[source_version_id]|[], claim_versions:[], expected_version_id:
    undefined}` → go to `/pitch/<pitch_id>` (`pitch.js:42-46, 56-64`).
  - `#pitch-filters`: `q`, `audience`, `scenario`, `archived`, hidden `duration` → navigates to `/pitches?<query>`;
    selects submit on change (`pitch.js:116`). Length links: All, 30s, 1, 3, 5, 7, 10, 15, 20 min.
- **Actions:** "Write a new pitch" shows the form; "Cancel" asks `confirm('Discard the unsaved new pitch?')` when dirty.
- **States:** "No pitches match these choices. Clear the filters or create a new pitch."

### 3.14 Pitch editor: `/pitch/<id>` (with rehearsal mode)
- **Purpose:** write and version one pitch, check its length, rehearse against a timer.
- **Render:** `pitchEditor(id)` `pitch.js:26-41`, then `pitchEditorLayout(p)` `pitch.js:83-95` rearranges the DOM
  (core fields first, "Delivery notes & settings" disclosure, side sections become disclosures). `pitchCounts`
  `pitch.js:47`, `pitchDrawTimer` `pitch.js:53`, recovery `pitch.js:101-113`.
- **GET:** `/api/pitches` (for `lengths`, `audiences`, `scenarios`), `/api/pitch/<id>` (`id` = current version id,
  `pitch_id`, `title`, `audience`, `scenario`, `speaker`, `format`, `status`, `duration_seconds`, `body`, `notes`,
  `created_at`, `sources[]`, `claim_versions[]`, `source_details[]{original_path,captured_at,material_id}`,
  `claim_details[]{id,label,body,canonical_version_id,status}`, `history[]{id,created_at,change_note,format}`).
- **Form `#pitch-editor-form` fields:** `title` (≤160), `duration_seconds` (select of `lengths` + "custom"),
  `custom_seconds` (10-7200, shown for custom), `audience`, `scenario`, `speaker` (≤100), `format`
  (`script|outline`), `status` (`draft|rehearsal_ready|archived`), `body` (≤40000), `notes` (≤10000), `change_note`
  (≤300).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Save pitch" (or Ctrl/Cmd+S) | `POST /api/pitch/<pitch_id>` | all form fields + `duration_seconds:Number`, `sources`, `claim_versions`, `expected_version_id:<current version id>` | none | re-render editor + "Saved as a new version. Your earlier wording is preserved."; **409** when another save happened first (`PitchConflict`) → error toast |
| "Make a variant" | `POST /api/pitches` | same fields with `title + ' - variant'`, `status:'draft'`, `change_note:'Adapted from <version id>'` | none | go to `/pitch/<new id>` |
| "Restore as new version" (per history row) | `POST /api/pitch/<pitch_id>/restore` | `{version_id, expected_version_id}` | when dirty: `confirm('Restore this saved version? Unsaved edits will be replaced.')` | re-render + "Restored as a new version. All previous versions are retained." |
| "Practice aloud" | none | | | hides the editor, shows rehearsal with the current (unsaved) text |
| "Start/Pause/Resume timer", "Reset", "Back to editing" | none | | | stopwatch; "over target" when past the target length |
| "Copy text" | clipboard | | | "Current pitch text copied." or selects the text |
| "Get coached" | link `/pitch-lab?coach=<pitch_id>` | | | |
| "Download as text file" | `GET /api/pitch/<id>/export` | | | file `A-Story-pitch-<id>.txt` |
| "Read TXT" per version | `GET /api/pitch/<id>/export?version=<version id>` | | | file download |
| "Restore unsaved wording" / "Keep saved version" | none (sessionStorage) | | | recovery banner |

- **Live behaviour:** every input marks the form dirty, writes a recovery copy to `sessionStorage`, sets "Unsaved
  edits", and recounts: words (Unicode-aware regex), seconds at 130 words/minute against the target, and the list
  of `[open prompts]` in the text (`pitch.js:47-52`).
- **Unusual:** long text editor; optimistic-concurrency version id; `beforeunload` guard; DOM re-arranged after
  render; rehearsal mode and timer; the back link returns to the last library URL from `sessionStorage`.

### 3.15 Assumptions: `/assumptions`
- **Purpose:** every number the deck depends on, its status (measured, modeled, assumed), evidence and cheapest test.
- **Render:** `assumptionsPage()` `assumptions.js:36-45`; `acChallenge` `assumptions.js:23`, `acCard`
  `assumptions.js:12`, `acMeasured` `assumptions.js:6`.
- **GET:** `/api/assumptions` (`counts{measured,modeled,assumed}`, `slide_titles{}`, `researching`, `next_challenge`,
  `challenge{created_at,edition_title,measured[],weakest[]{key,statement,status,why_weak,cheapest_test,
  judge_question},note,rejected[]{key,reason}}`, `assumptions[]{key,statement,number,status,slides[],
  measured{fact{text},evidence[]{text}},status_changed_at,evidence_for[],evidence_against[],cheapest_test,
  owner_note}`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| Page load | `POST /api/assumptions-seen` | `{}` | none | fire-and-forget; marks alerts seen (`assumptions.js:44`) |
| "Challenge now" (`data-action="assumption-challenge"`) | `POST /api/assumption-challenge` | `{}` | none | toast "Asked the Coach. The three weakest assumptions land here in a few minutes." + reload |
| `.assumption-form` "Edit" → "Save" | `POST /api/assumption` | `{key, evidence_for, evidence_against, cheapest_test, owner_note, status}`; evidence fields are newline-separated text; `status` (`assumed|modeled`) is absent for measured rows | none | toast "Saved. The agents read this on their next run." + reload |

- **States:** "No challenge yet. <next_challenge>"; "Coach is working…" disabled button; "None yet." per group.
- **Unusual:** a POST fires on every view. The "Challenge now" button also passes through the global
  `data-action` handler in `app.js:348`, which re-enables it in its `finally`.

### 3.16 Materials & answers: `/materials` (query: `q`, `kind`, `category`, `offset`)
- **Purpose:** search the indexed files (decks, essays, scripts) and read saved answer versions.
- **Render:** `materials()` `app.js:217-226`.
- **GET:** `/api/materials?q=&kind=&category=&offset=` (`stats{unique_files,searchable_text,kinds[]{kind,count}}`,
  `total`, `limit`, `items[]{id,relative_path,kind,extraction,size_bytes,duplicates}`), `/api/answers`
  (`prompt`, `status`, `body`, `limit_value`, `limit_unit`, `created_at`).
- **Form `#material-filters`:** `q`, `kind` (from `stats.kinds`), `category` (`""` Useful materials, `ARCHIVE`
  Archived / generated, `all` All materials). Submit resets `offset` to 0 and re-renders; URL kept via
  `replaceState`. The global sidebar search lands here with `?q=`.
- **Actions:** "Previous" / "Next" (`data-action="material-page"`, `data-offset`) re-render and scroll to top; "Copy"
  on answers.
- **Downloads:** per file `GET /api/material/<id>/file` (original, streamed, any size); "Download the source manifest"
  `GET /api/materials-manifest` (`A-Story-pitch-materials-manifest.json`).
- **States:** "No materials match. Try a broader search or choose All materials."

### 3.17 Material detail: `/material/<id>`
- **Purpose:** one file's extracted text and details.
- **Render:** `material(id)` `app.js:227`; back link patched from `sessionStorage` in `route()` (`app.js:336`).
- **GET:** `/api/material/<id>` (`relative_path`, `kind`, `size_bytes`, `source_path`, `source_version_id`, `sha256`,
  `aliases[]{source_path}`, `body`).
- **Actions:** "Adapt in Pitch Studio" → `/pitches?material=<id>`; "Download original" → `GET
  /api/material/<id>/file`; "Back to materials".
- **States:** "This file is kept as an original. Download it to see its slides or images." when there is no text.
- **Unusual:** `body` can be very long; shown in one `<pre>`.

### 3.18 Deals & campaigns: `/growth`
- **Purpose:** partner deals by stage, the campaign plans, what families say online, and channel math.
- **Render:** `growthDesk()` `growth.js:77-92`; `dealCard` `growth.js:5-19`, `addDealForm` `growth.js:20`,
  `campaignCard` `growth.js:23-41`, `fieldVoice` `growth.js:44`, `voiceSection` `growth.js:49-64`, `mathSection`
  `growth.js:66-76`; `draftBlock` `app.js:443`.
- **GET:** `/api/growth` (`stages[]{key,label,deals[]}`, `kinds[]{key,label}`, `open`, `due[]`, `ready_to_send[]`,
  `searching`, `last_run{at,found}`, `campaigns[]`, `voice`, `math`, `measured`, `channel_words{}`),
  `/api/growth-alerts`.
  Deal fields: `id`, `name`, `kind`, `kind_words`, `region`, `value_usd`, `value_note`, `stage`, `stage_words`,
  `due`, `open`, `next_step`, `next_on`, `why`, `angle`, `contact_route`, `url`, `source`, `source_url`,
  `events[]{occurred_on,summary}`, `reply_proposal{sender,subject,received_at}`, `draft{title,body,note}`,
  `drafting`.
  Campaign fields: `key`, `title`, `brief`, `state` (`NEW|PLANNED|RUNNING|DONE`), `planning`, `owner_note`,
  `issues[]{severity,text,where}`, `drafts[]{title,body,note}`, `plan{goal,audience,offer,channels[]{channel,what,
  message,start_on,end_on,spend_cap_usd,success_metric,needs_from_bao},checkpoints[]{on,check},open_questions[],
  risks[]}`, `field{approached,emails,reservations,entries[]{week_start,visits,signups,purchases,note}}`,
  `voice{as_of,objections[],words[]}`.
  Voice fields: `report{threads_read,places_read[],themes[]{theme,threads,summary,quotes[]{text,who,url}},tried[],
  objections[],willing_to_pay[],words[],sources[]}`, `researching`, `run_on`, `runs`, `previous_on`, `movement`,
  `movement_words`.
  Math fields: `totals{weeks,from,to,visits,signups,signup_rate,purchases,conversion,cost_per_family,spend_usd,
  revenue_usd,revenue_per_dollar}`, `deck_formula{visits,rate,families,visits_needed_for_30}`,
  `channels[]{label,weeks,visits,signups,purchases,conversion,spend_usd,cost_per_family}`,
  `entries[]{id,channel,week_start,visits,signups,purchases,spend_usd,revenue_usd,note}`.
- **Deal stage moves** (`DEAL_MOVES`, `growth.js:3`): FOUND/DRAFTED → SENT; SENT → REPLIED, MEETING; REPLIED →
  MEETING, PROPOSAL, WON; MEETING → PROPOSAL, WON, REPLIED; PROPOSAL → WON, LOST. Plus "Park" (PARKED), "Lost", and
  "Move back to open" (DRAFTED when a draft exists, else FOUND).
- **Actions:**

| Element | Endpoint | Payload | Confirm / prompt | After |
|---|---|---|---|---|
| Stage buttons (`data-deal-stage`) | `POST /api/deal-stage` | `{id, stage, note}` | `confirm` for SENT ("Log that you sent this note yourself? A follow-up is scheduled in a week."), WON ("Mark this deal won?"), LOST ("Mark this deal lost?"); then `prompt('One line on what happened (optional):')` for REPLIED, MEETING, PROPOSAL, WON, LOST | reload + "Saved." |
| "Draft it now" / "Write a new note" (`data-deal-draft`) | `POST /api/deal-draft` | `{id}` | none | reload + "The agent is drafting the note. It appears here in a few minutes, checked and in your voice." |
| "Find partners now" (`data-growth-discover`) | `POST /api/partner-discover` | `{}` | none | reload + "Partner Scout started. New deals appear in about 15 minutes." |
| `.deal-form` "Add a deal" | `POST /api/deal` | `{name, kind, region, url, contact_route, value_usd, next_on, why, summary}` | none | toast "Added. The agent drafts a first note; you send it." + reload |
| `.deal-event-form` | `POST /api/deal-event` | `{id, summary, occurred_on, next_step, next_on}` | none | "Logged." + reload |
| `.deal-edit-form` | `POST /api/deal-update` | `{id, value_usd, value_note, contact_route}` | none | "Saved." + reload |
| `.campaign-form` "Plan it now / Plan again" | `POST /api/campaign-plan` | `{key, note}` | none | "Campaign Planner started. The plan appears here in a few minutes." + reload |
| "Mark it running" / "Mark it done" (`data-campaign-state`) | `POST /api/campaign-state` | `{key, state:'RUNNING'|'DONE'}` | none | reload + "Saved." |
| `.field-form` "Tally the day" | `POST /api/field-day` | `{key, approached, conversations, emails, reservations, on, note}` | none | "Tally saved. It counts in channel math under events." + reload |
| `.entry-form` "Record a week" | `POST /api/channel-entry` | `{channel, week_start, visits, signups, purchases, spend_usd, revenue_usd, note}` | none | "Week saved." + reload |
| "Remove" entry (`data-entry-delete`) | `POST /api/channel-entry-delete` | `{id}` | `confirm('Remove this week’s entry?')` | reload + "Removed." |
| "Research now / Research again" (`data-scout-run="customer_voice"`) | `POST /api/scout-run` | `{key:'customer_voice'}` | none | reload + "Scout started. Results appear on its page in about 15 minutes." (handler in `scouts.js:77`) |
| "Copy" on subject, message, script, lead messages | clipboard | | | |

- **Client-only behaviour:** deal type filter buttons (`data-deal-kind`) hide cards and empty stage groups
  (`growth.js:94-99`); clicking any `#deal-<id>` link opens the enclosing disclosures (`growth.js:93`); "Do next" list
  (top 3) built from customer alerts, due deals and ready-to-send deals.
- **States:** "No deals yet"; "No plan yet." / "Planning."; "Nothing read yet." / "Reading the threads now."; "Nothing
  recorded yet"; "Searching…" disabled button.
- **Unusual:** the biggest page; deals sit inside nested `<details>`; all numbers go as strings; anchors `#deal-<id>`
  are linked from Decisions.

### 3.19 Beta families: `/families`
- **Purpose:** the journal of beta families and events, the retention numbers counted from it, and CSV metrics intake.
- **Render:** `betaFamilies()` `product.js:29-36`; `measuredList` `product.js:8`, `familyCard` `product.js:11`,
  `addFamilyForm` `product.js:18`, `intakeSection` `product.js:21-28`.
- **GET:** `/api/product` (`counts{families,first_calls,second_calls,contributing,issues}`, `retention{as_of,
  metrics[]{key,label,measurable,numerator,denominator,denominator_label,percent,calls,range{start,end},sources[]}}`,
  `families[]{id,label,storyteller,adult_child,enrolled_on,status,notes,events[]{id,at,kind_words,detail,source}}`,
  `event_kinds[][value,label]`, `family_states[][value,label]`, `intake{inbox,files[]{name,size,modified,
  imported{imported_at,provider}},providers{},sources[]{provider,file_name,period_start,period_end,point_count,
  imported_at},latest[]{provider,metric,period,value,unit,file_name},api[]{name,credential_present}}`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| `.family-form` "Add a family" | `POST /api/family` | `{label, storyteller, adult_child, enrolled_on, status, notes}` | none | "Family added. Log its first call when it happens." + reload |
| Status select (`data-family-status`, on change) | `POST /api/family-update` | `{id, status}` | none | reload + "Status saved." |
| `.event-form` "Log an event" | `POST /api/family-event` | `{family_id, kind, at, detail}` (`at` required, max today) | none | "Logged. The measured numbers above are updated." + reload |
| "Remove" event (`data-event-delete`) | `POST /api/family-event-delete` | `{id}` | `confirm('Remove this event from the journal? The measured numbers change with it.')` | reload + "Event removed." |
| `.import-form` "Import this file" | `POST /api/metrics-import` | `{file:<file name>, provider, note}` | none | toast "Imported N numbers from <file>." + reload |

- **States:** "No families yet. Add the first one above."; "No events yet."; "Not measurable yet. Needs …"; "No
  exports waiting."
- **Unusual:** metrics import is **not a browser upload**: the server reads a CSV already saved into the intake
  folder on the PC (`intake.inbox`), chosen by file name. Dates use the Eastern "today" as `max`.

### 3.20 Reservation drive: `/drive`
- **Purpose:** the $1 reservation push: one personal note per lead or beta family, tracked from draft to reservation.
- **Render:** `reservationDrive()` `drive.js:22-32`; `driveMemberCard` `drive.js:10-21`, `driveLoaderForm`
  `drive.js:4`, `driveLoaderCard` `drive.js:7` (also embedded on People).
- **GET:** `/api/drive` (`days_left`, `counts{total,leads,beta,not_written,ready,sent,replied,reserved,referrals}`,
  `members[]{contact_id,name,email,kind_words,context,shown (NEW|READY|SENT|REPLIED|RESERVED),state_words,drafting,
  draft{title,body,note},touches[]{occurred_on,summary},referrals,reserved_on,sent_on}`,
  `entries[]{created_at,channel,purchases,note}`, `nudge_days[]`).
- **Actions:**

| Element | Endpoint | Payload | Confirm / prompt | After |
|---|---|---|---|---|
| `.drive-import-form` "Load these people" | `POST /api/drive-import` | `{csv:<text>}`; the text comes from the chosen file (read in the browser with `file.text()`, max 60,000 bytes) or the textarea (max 60,000 chars) | none | toast "N new people, M known contacts enrolled, K duplicates skipped, R rows rejected (row n: reason; …)."; from another page goes to `/drive`; else reload |
| "I sent it" / "I sent the reminder" (`data-drive-action="sent"`) | `POST /api/drive-action` | `{id, action:'sent'}` | `confirm('Log that you sent this note from your own email?')` | reload + "Logged. Record the reply or the reservation when it comes." |
| "They replied" | `POST /api/drive-action` | `{id, action:'replied'}` (server reads optional `note`; UI never sends it) | `confirm('Log that they replied?')` | reload + "Logged. Answer them from your email." |
| "They reserved" | `POST /api/drive-action` | `{id, action:'reserved'}` | `confirm('Record that they reserved A Story for $1? This adds one purchase to the email channel this week.')` | reload + "Reservation recorded. Channel math has it." |
| "They referred someone" | `POST /api/drive-action` | `{id, action:'referred', who}` | `prompt('Who did they refer? Leave empty if you do not know yet.')`; Cancel aborts | reload + "Referral recorded under the referrals channel. Add the new family in People when you have their details." |
| "Draft it now" / "Write a new draft" (`data-growth-draft="contact"`) | `POST /api/growth-draft` | `{kind:'contact', id:<contact_id>}` | none | reload + "The agent is drafting it. It appears here in a few minutes." (handler `app.js:479-489`) |
| "Open email ↗" | `mailto:<email>?subject=<draft title>` | | | opens the mail client; nothing is sent by the app |
| "Copy" on subject and message | clipboard | | | |

- **States:** "No one loaded yet"; groups Ready to send, Sent waiting, They replied, Still being written, Reserved;
  countdown "N days to November 2" / "Closes today" / "Closed November 2".
- **Unusual:** file input read client-side (CSV header `name,email,context,kind`); hard-coded November 2 date in the
  copy; the 64 KB POST limit bounds the import.

### 3.21 Press & gift guides: `/press`
- **Purpose:** outlets that take pitches, each with a drafted pitch; track pitched, published, skipped.
- **Render:** `press()` `app.js:472-478`; `pressCard` `app.js:463-471`.
- **GET:** `/api/dashboard` (route prerequisite), `/api/press` (`targets[]{id,outlet,kind,audience,deadline,days_left,
  angle,submit_method,submit_url,url,source_url,state (NEW|PITCHED|PUBLISHED|SKIPPED),draft{title,body,note},
  drafting}`, `searching`, `last_run{at,found}`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Find more now" (`data-press-discover`) | `POST /api/press-discover` | `{}` | none | reload + "Search started. New outlets appear here in about 15 minutes." |
| "Draft it now" / "Write a new draft" (`data-growth-draft="press"`) | `POST /api/growth-draft` | `{kind:'press', id}` | none | reload + "The agent is drafting it. It appears here in a few minutes." |
| "I sent it" (`data-press-state="PITCHED"`) | `POST /api/press-state` | `{id, state:'PITCHED'}` | **none** | reload + "Marked as pitched." |
| "Skip" / "It was published" / "Move back to open" | `POST /api/press-state` | `{id, state:'SKIPPED'|'PUBLISHED'|'NEW'}` | none | reload + "Saved." |
| "Open how to pitch ↗", "Source ↗" | external links | | | |

- **States:** "No open press targets"; "Searching…"; "Pitched, published or skipped (N)" disclosure.

### 3.22 People: `/people`
- **Purpose:** contacts to follow up with; a note is drafted when a follow-up is due.
- **Render:** `people()` `app.js:455-461`; `personCard` `app.js:444-451`, `addPersonForm` `app.js:452`,
  `driveLoaderCard` `drive.js:7`.
- **GET:** `/api/dashboard` (route prerequisite), `/api/people` (`id`, `name`, `org`, `kind`, `email`, `state`
  (`ACTIVE|PAUSED`), `due`, `next_followup_on`, `cadence_days`, `context`, `touches[]{occurred_on,summary}`,
  `draft{title,body,note}`, `drafting`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "I sent it" (`data-person-sent`) | `POST /api/person-touch` | `{id, summary:'Sent the follow-up email.'}` | `confirm('Log that you sent this follow-up? The next one is scheduled automatically.')` | reload + "Logged. The next follow-up is scheduled." |
| "Draft it now" / "Write a new draft" | `POST /api/growth-draft` | `{kind:'contact', id}` | none | reload + toast |
| `.touch-form` "Log a conversation" | `POST /api/person-touch` | `{id, summary, occurred_on, next_followup_on}` | none | "Conversation logged." + reload |
| "Pause follow-ups" / "Resume follow-ups" (`data-person-state`) | `POST /api/person-update` | `{id, state:'PAUSED'|'ACTIVE'}` | none | reload + "Saved." |
| `.person-form` "Add a person" | `POST /api/person` | `{name, org, kind, email, next_followup_on, cadence_days:Number, context, summary}`; `kind` ∈ Investor, Partner, Program, Press, Mentor, Customer, Other | none | "Added. The agent drafts a note when the follow-up date arrives." + reload |
| Reservation-drive loader (`.drive-import-form`) | `POST /api/drive-import` | `{csv}` | none | goes to `/drive` when anyone was added |
| "Open email ↗" | `mailto:<email>` | | | |

- **States:** "No follow-ups due"; the add form opens by itself when the list is empty.

### 3.23 Decisions: `/decisions`
- **Purpose:** facts only Bao can confirm, results proposed from the inboxes, reminders, and the recent decisions.
- **Render:** `decisions()` `app.js:255-264`; `factCard` `app.js:238-248`, `inboxSection` `app.js:235`,
  `inboxAccounts` `app.js:231`, `inboxItem` `app.js:232`, `inboxReplyItem` `app.js:234`, `recentDecisions`
  `app.js:249-254`.
- **GET:** `/api/dashboard` (`needs_decision[]{id, card{kind (APPROVE|CHECK|ANSWER|REMINDER), topic, label, sentence,
  why, unlocks[], replaces[]{fact,current,proposed}, source, locator, editable}}`, `inbox{proposed, review,
  accounts[]{account,connected,last_checked,last_error}, pending[]{id,program,state,proposed_outcome,sender,account,
  received_at,subject,snippet,reason,opportunity_id,deal_id,deal,deal_stage}}`,
  `recent_decisions[]{label,sentence,state,decided_at}`).
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| "Approve" / "Reject" / "Dismiss" (`data-action="approve"`) | `POST /api/approval` | `{approval_id, decision:'approved'|'rejected', confirmed:true}` (server also reads optional `note`) | `confirm('Confirm this exact approved/rejected decision after reviewing the proposal and evidence?')` | reload + "Owner decision recorded." |
| "Edit" (`data-fact-edit`) | none | | | toggles the edit form, focuses the textarea (`app.js:265-269`) |
| `form.fact-edit` "Save and approve" | `POST /api/approval-edit` | `{approval_id, body, confirmed:true}` | `confirm('Save this wording as a confirmed company fact?')` | reload + "Saved your wording as a confirmed fact." (`app.js:270-275`) |
| Inbox "Confirm" (program email) | `POST /api/inbox-decision` | `{id, decision:'confirm', outcome, confirmed:true}`; `outcome` from the select: Applied, Advanced, Finalist, Accepted, Rejected | `confirm('Record this program as <outcome> from this email?')` | reload + "Outcome recorded with the email as evidence." |
| Inbox "They replied" / "Log this email" (deal reply) | `POST /api/inbox-decision` | `{id, decision:'confirm', confirmed:true}` | `confirm('Mark <deal> as replied, with this email logged on the deal?')` | reload + "Logged on the deal. Answer them from your own email." |
| "Not relevant" / "Not a reply" | `POST /api/inbox-decision` | `{id, decision:'dismiss', confirmed:true}` | **none** | reload + "Email set aside. Nothing was recorded." |
| "Connect" per mailbox (`data-action="connect-inbox"`) | `POST /api/connect-inbox` | `{account}` (must be in the server's `INBOX_ACCOUNTS`) | none | opens a PowerShell window on the PC; toast "Secure inbox setup opened on this PC. Enter the Google app password there, never in chat." |
| "Open the deal" | link `/growth#deal-<deal_id>` | | | |
| "Find the program" (unmatched email) | link `/opportunities` | | | |

- **Downloads:** "Export tracker (CSV)" → `GET /api/tracker/export.csv`.
- **States:** "You’re all caught up"; the count line (facts, inbox, reminders); "No new program emails to confirm.";
  reminders can only be dismissed; recent decisions are de-duplicated by label.
- **Unusual:** the server refuses approvals without `confirmed:true` (`server.py:300, 303, 287`).

### 3.24 Company facts: `/memory`
- **Purpose:** read-only view of the approved company profile.
- **Render:** `memory()` `app.js:203`; `factsView` `app.js:33-39`, `factShown` `app.js:29`, `FACT_GROUPS`
  `app.js:27`, `FACT_LABELS` `app.js:26`.
- **GET:** `/api/dashboard` (`company_memory.attributes{<key>:{value,last_verified}}`,
  `company_memory.canonical_claims[]{label,body}`).
- **Actions:** none; link to `/decisions`.
- **States:** "No structured eligibility facts are approved yet."; the notice when there are no canonical claims.
- **Unusual:** facts grouped into Company, Founders, Product and market, Funding, Other; the most common verification
  date is shown once and exceptions inline.

### 3.25 Founder profile: `/founder-profile`
- **Purpose:** the vault of facts only Bao knows; the Form Filler copies them into application answers.
- **Render:** `founderProfile()` `profile.js:21-27`; `profileRow` `profile.js:6-13`, `profileGroup` `profile.js:14`,
  `addProfileField` `profile.js:18`.
- **GET:** `/api/founder-profile` (`filled`, `total`, `groups[]`, `fields[]{key,label,group,set,sensitive,masked,
  value,updated_at,used_for,custom}`). Sensitive values are never in this response.
- **Actions:**

| Element | Endpoint | Payload | Confirm | After |
|---|---|---|---|---|
| Row form `.profile-form` "Save" | `POST /api/founder-profile` | `{key, value}`; refused client-side when empty ("Type a value first, or use Clear to empty this field.") | none | reload + "Saved. N application answers filled from your profile." or "Saved." (response `filled`) |
| "Reveal" (`data-profile-reveal`) | `POST /api/founder-profile-reveal` | `{key}` | none | puts `value` into that input until the page is left; no reload |
| "Clear" (`data-profile-clear`) | `POST /api/founder-profile` | `{key, value:''}` | `confirm('Clear this saved value? Questions it answered keep their current answers until you change them.')` | reload + "Cleared." |
| "Remove" (custom fields, `data-profile-delete`) | `POST /api/founder-profile-delete` | `{key}` | `confirm('Remove this fact from your profile?')` | reload + "Removed." |
| `.profile-add-form` "Add another fact" (in group Other) | `POST /api/founder-profile` | `{label, value, sensitive:Boolean}` | none | reload + "Saved." |

- **Input types:** `url` when the key ends `_url`, `_link` or `website`; `date` when it ends `_dob` or `_date`; else
  text. Sensitive inputs are text with `autocomplete="off"`.
- **Unusual:** holds sensitive data (EIN, addresses, dates of birth). Every save re-runs the filler across all read
  applications server-side (`server.py:378`). Group blurbs are hard-coded (`profile.js:15`).

### 3.26 Agent activity: `/activity`
- **Purpose:** list of research runs.
- **Render:** `activity()` `app.js:201`; `activityList` `app.js:62`, `researchAlert` `app.js:130`.
- **GET:** `/api/dashboard` (`agent_activity[]{id,started_at,completed_at,state,report{errors[],
  candidates_discovered,verified,new_programs}}`).
- **Actions:** "Run it again" in the failure alert → `POST /api/run-now {}`; rows link to `/run/<id>`.
- **States:** "The first research run will appear here with its queries, sources and results."

### 3.27 Research run: `/run/<id>`
- **Purpose:** what one research run checked, verified and failed on.
- **Render:** `run(id)` `app.js:202`; `errorView` `app.js:40`, `usageView` `app.js:41`.
- **GET:** `/api/run/<id>` (`state`, `started_at`, `usage_json`, `report{candidates_discovered,verified,
  records_created,duplicates_removed,errors[]{state,message,program},queries_used[],sources_checked[],usage{runner,
  research_runner,api_key_used,tokens{input_tokens,output_tokens},model_api_cost}}`).
- **Actions:** none. Disclosures: Searches used, Sources checked (external links), Usage, Exact run data (raw JSON).

### 3.28 Scouts: `/scouts`
- **Purpose:** one card per scout agent with its schedule, last run, next run and where results land.
- **Render:** `scouts()` `scouts.js:21-27`; `scoutCard` `scouts.js:16`, `scheduleWords` `scouts.js:3`, `lastRunWords`
  `scouts.js:10`.
- **GET:** `/api/scouts` (`scouts[]{key,name,group,hunts,running,schedule{days[],hour,minute},lands_url,lands_label,
  last_run{at,found,unit,checked},next_run,families[]}`, `broad_sweep{name,hunts,running,schedule,last_run}`).
- **Actions:** "Run now" (`data-scout-run`) → `POST /api/scout-run {key}` → reload + "Scout started. Results appear on
  its page in about 15 minutes." The `win` scout shows a link to `/opportunities` instead of a button.
- **States:** "Running…" disabled; "Has not run yet"; "On request".

### 3.29 Plans: `/plans` (+ files `/plan/<id>.pdf`, `/plan/<id>.html`)
- **Purpose:** ask the Planner a question and get a one-page brief; list past briefs.
- **Render:** `plans()` `plans.js:14-20`; `planReport` `plans.js:2-13`.
- **GET:** `/api/plans` (`default_question`, `writing`, `latest`, `items[]{title,question,created_at,state
  (READY|QUEUED|FAILED),error,auto,pdf_url,html_url}`); `latest` has `title`, `question`, `finished_at`, `pdf_url`,
  `html_url`, `report{bottom_line,moves[]{what,owner,by,why},decisions[]{decision,recommend,unblocks},
  numbers[]{value,label,source},by_agent[]{agent,result,needs},risks[],later[]{what,owner,by},answer[]}`.
- **Actions:** form `.plan-form` → `POST /api/plan {question}` (≤600; may be empty, the server uses the default) →
  reload + "The Planner is writing. Reload in about 2 minutes; the PDF appears here."
- **Files:** "Open the PDF" → `GET /plan/<id>.pdf` (attachment `A-Story-plan-<last 8 of id>.pdf`); "Web version" →
  `GET /plan/<id>.html` (new tab, own CSP, a self-contained page). `GET /api/plan/<id>` exists but the old UI never
  calls it.
- **States:** "No brief yet"; "Writing…" disabled; an older long-form report shape (`answer[]` without `bottom_line`).

### 3.30 Load-error screen (not a route)
`app.js:630`: "Unable to open this page" + message, "Reload workspace" button, link to `/pitches`.

---

## 4. Shared pieces

### 4.1 Helpers (all in `app.js` unless noted)
| Helper | Line | What it does |
|---|---|---|
| `E(v)` | 1 | HTML-escape `& < > " '`; every interpolated value goes through it. React escapes by default; do not carry `E` over |
| `plural(n, one, many)` | 4 | "3 questions", "1 copy" / "2 copies" |
| `money(v)` | 13 | USD, no decimals; `Unknown` for null. `usd(v)` (`growth.js:4`) is the same but returns `''` for null |
| `deadlineLabel(v)` | 16 | "Nov 2, 2026" in America/New_York; date-only strings are pinned to noon to avoid a day shift |
| `shortDay(v)` | 8 | "Tue, Nov 11" |
| `readableDate(v)` / `exactDate(v)` | 20-21 | "Nov 11, 2026, 9:00 AM EST" / the same inside `<time datetime title>`; "Not yet verified" when empty |
| `fmtDay(v)` | 420 | "Nov 11, 2026" from the first 10 chars (local, no timezone). Twins: `pdDay` (`product.js:3`), `acDay` (`assumptions.js:3`), `fpDay` (`profile.js:4`, Eastern) |
| `isClosed(iso)` | 17 | deadline passed (end of that day, local time) |
| `closingWords(days, deadline)` | 68-73 | "Closes today / tomorrow / in N days · Nov 2", "Closed", "No deadline published", "Closing time unverified" |
| `hoursWords(h)` | 18 | "Under an hour" / "About 2.5 hours" |
| `cycleLabel(c)` | 5 | hides `unknown`; `rolling` → "Rolling admissions" |
| `prettyKey(k)` | 25 | `snake_case` → "Snake case" |
| `humanState(s)` + `STATE_WORDS` | 6-7 | run and report states in plain words |
| `fileSize(b)` | 24 | KB / MB |
| `factLabel`, `factShown`, `factValue` | 28-32, 237 | labels and display for company facts (booleans → Yes/No, ISO dates → long dates) |
| `countWords`, `countLabel` | 353-357 | word or character count against a limit, "over limit" |
| `accessShort`, `accessChip`, `accessLine` | 10-11, 371 | the application access state chip (levels READY, DRAFTING, BLOCKED, NOT_CHECKED, FINISHED) |
| `appUrl(x)` | 12 | `/application/<id>` when the form's questions were read |
| `benefits`, `benefitText`, `date`, `score` | 15-23 | table cells for the pipeline |
| `moneyFigure(d)` | 74-79 | "Up to $X", "Up to $X credits", "Amount unknown" |
| `dedupe(items)` | 55 | merges same-name programs |
| `pitchLength(s)` | pitch.js:2 | seconds → "30 sec", "3 min", "1 min 30 sec" |
| `scheduleWords`, `lastRunWords` | scouts.js:3, 10 | scout schedule and last-run sentences |
| `pdRange`, `pdToday`, `pdValue` | product.js:4-6 | date range, Eastern today (`en-CA`), metric value by unit |
| `copyText(button)` | 399-403 | clipboard with `execCommand` fallback and a 1.6s "Copied" label |

All dates are shown in **America/New_York**.

### 4.2 Shared components (HTML string builders)
| Component | Where | Used on |
|---|---|---|
| `heading(title, subtitle, action)` | app.js:54 | every page |
| `tag(s)` status pill (classes review, good, faded, urgent) | app.js:14 | pipeline, applications, decisions, pitches |
| `answerBox(body, limit, unit)` copyable text, short inline or boxed with count | app.js:358-362 | application answers, lab item, materials, drafts, campaigns |
| `draftBlock(d)` subject + message + note | app.js:443 | people, press, deals, drive |
| `itemRows(items, cls, brief)` to-do rows | app.js:127 | Today, Funding |
| `leadCard(item, board, compact)` the one next step | app.js:116-126 | Today, Funding |
| `tocRow` ranked program row with days bar | app.js:80-84 | Funding |
| `waitingSection(tracked)` | app.js:364-369 | Funding |
| `rows(items, byOpp)` pipeline table | app.js:56-60 | Pipeline |
| `stageStrip`, `progressLine`, `assemblyLine` step indicators | app.js:162, 553, 516 | opportunity, lab item, lab |
| `notice()` company-facts warning | app.js:61 | pipeline, applications, memory |
| `researchAlert(run)` | app.js:130-135 | Today, activity |
| `factsView`, `factCard` | app.js:33, 238 | memory, decisions |
| `stageChip`, `scoreDots`, `labCard`, `coachCard`, `deckSection` | app.js:504-552 | Pitch Lab |
| `applyFirst(data, opts)` | ranker.js:16 | Money map (a compact mode exists, unused) |
| `winSection(w, id)` | scouts.js:30 | opportunity detail |
| `stackSection(st)` | scouts.js:60 | credits |
| `driveLoaderForm/Card` | drive.js:4-9 | drive, people |
| `voiceSection`, `fieldVoice` | growth.js:44-64 | deals & campaigns |
| Class conventions | style.css | `.section`, `.section-title`, `.record`, `.actions`, `.quiet-actions`, `.link-button`, `.button.primary`, `.small`, `.muted`, `.empty`, `.all-clear`, `.state-line`, `.tracker`, `.form-grid`, `details.more`, `.count-chip`, `.credit-status[.due]`, `.qa-needs`, `.block-title`, `.table-scroll` |

There is **no dialog component** (native `confirm`/`prompt` only), **no toast stack** (one message in `#status`), and
no client-side table sorting.

### 4.3 Icons and fonts
- SVG sprite in `index.html:3`: `#i-arrow`, `#i-search`, `#i-refresh`, used as `<svg class="icon"><use href="#i-…">`.
- Brand mark: inline two-path SVG (`viewBox 0 0 64 64`) in the top bar and sidebar.
- Text arrows: "↗" for external links, "→" in brief rows, "←" in back links.
- Fonts served at `/fonts/`: `switzer-400/500/600.woff2`, `mona-sans.woff2`, `brygada-1918.woff2` (`server.py:58`).
- Vendor: `/vendor/gsap.min.js`, `/vendor/ScrollTrigger.min.js` (deck preview only).

### 4.4 Document-level listeners (the old app's "controllers")
| Listener | File:line | Handles |
|---|---|---|
| click on `button[data-view]`, `button[data-action]` | app.js:348 | views, `reload`, `material-page`, `confirm-application`, `resume-agent`, `inbox-confirm`, `inbox-dismiss`, `connect-inbox`, `connect-mail`, `report-now`, `show-report`, `pause-agent`, `prepare-pilot`, `run`, `research`, `start`, `decision`, `approve`, `read-notice` |
| submit `#material-filters`, `#filters`, `#decision-form` | app.js:349 | |
| change `[data-more-view]` | app.js:177 | |
| click `[data-fact-edit]`; submit `.fact-edit` | app.js:265-275 | |
| click `[data-copy]`, `button[data-outcome]` | app.js:404-409 | |
| submit `#outcome-form` | app.js:410-413 | |
| click `[data-read-form]` | app.js:414-418 | |
| click `[data-press-state]`, `[data-growth-draft]`, `[data-press-discover]`, `[data-person-sent]`, `[data-person-state]` | app.js:479-489 | |
| submit `.credit-form`, `.person-form`, `.touch-form` | app.js:490-499 | |
| submit `#lab-edition`, `#lab-review`, `#lab-application`, `.lab-rerun` | app.js:607-618 | |
| click `[data-lab-save]`, `[data-lab-approve]`, `[data-lab-build]`, `[data-lesson]`, `[data-move]`, `[data-lab-app]` | app.js:619-629 | |
| pitch input/change/submit/click/keydown | pitch.js:54-80, 114-116 | |
| deal, campaign, entry clicks and submits | growth.js:93-124 | |
| win, stack, scout clicks and submits | scouts.js:48-81 | |
| `.plan-form` submit | plans.js:21 | |
| family forms, status change, event delete | product.js:37-55 | |
| profile forms and buttons | profile.js:28-46 | |
| drive import and actions | drive.js:33-55 | |
| assumption form and challenge | assumptions.js:46-54 | |

### 4.5 Things in the code with no visible entry point
Keep or drop these on purpose; do not lose them by accident.
- `data-action="start"` → `POST /api/start-application {opportunity_id}` (toast "Internal application draft is ready.
  No submission was sent."): the handler exists (`app.js:348`), no button renders it.
- `data-action="prepare-pilot"` → `POST /api/prepare-application {opportunity_id}`: handler exists, no button.
- `data-action="read-notice"` → `POST /api/notification-read {id}`: only rendered by `notifications()` (`app.js:166`),
  which nothing calls.
- `briefRow()` (`app.js:63`), `proposalView()` (`app.js:42`), `assumptionLine()` (`assumptions.js:32`), and the
  `compact` mode of `applyFirst` are defined and unused.
- GET routes the old UI never calls: `/api/home` (used by the React Home), `/api/inbox`, `/api/shortlist`,
  `/api/applications`, `/api/apply-first`, `/api/plan/<id>`, `/api/review/export?plan=<id>`,
  `/api/review-file/<id>` (the last two are attachment downloads linked from the daily email).

### 4.6 All GET API routes (`server.py:82-226`)
`/api/pitches` · `/api/pitch/<id>` · `/api/pitch/<id>/export[?version=]` (txt) · `/api/materials` ·
`/api/materials-manifest` (json file) · `/api/material/<id>` · `/api/material/<id>/file` (original) ·
`/api/review/export` (txt) · `/api/review-file/<id>` (txt) · `/api/application-review/<id>` · `/api/home` ·
`/api/dashboard` · `/api/inbox` · `/api/tracker/export.csv` · `/api/shortlist` · `/api/opportunities` ·
`/api/opportunity/<id>` · `/api/application/<id>` · `/api/application-list` · `/api/plans` · `/api/plan/<id>` ·
`/api/win/<id>` · `/api/stack` · `/api/scouts` · `/api/growth` · `/api/growth-alerts` · `/api/drive` ·
`/api/credits` · `/api/people` · `/api/press` · `/api/lab` · `/api/lab/<id>` · `/api/lab/<id>/edition.zip` ·
`/api/lab-options` · `/api/lab-alerts` · `/api/money` · `/api/apply-first` · `/api/product` ·
`/api/founder-profile` · `/api/assumptions` · `/api/applications` · `/api/autonomy` · `/api/report/<id>` ·
`/api/answers` · `/api/run/<id>`. Non-API: `/edition/<id>`, `/edition-asset/<name>`, `/plan/<id>.pdf|.html`.

---

## 5. Size and risk

Size by render code and number of POST actions: **S** under ~40 lines of template and 0-1 actions, **M** up to ~120
lines or 2-5 actions, **L** above that.

| Page | Path | Size | POST actions | Risk notes |
|---|---|---|---|---|
| Deals & campaigns | `/growth` | **L** | 12 | Largest page (4 sub-areas: deals, campaigns, family voice, channel math). 6 forms, stage machine with confirm + prompt, nested disclosures, client-side filter, anchors from other pages, a delete |
| Pitch editor | `/pitch/<id>` | **L** | 3 | Complex client state: dirty flag, version conflict (409), sessionStorage recovery, beforeunload, Ctrl+S, rehearsal timer, live word count, 40,000-char editor |
| Pitch Lab item | `/pitch-lab/<id>` | **L** | 4 | Six item kinds with different bodies, biggest payload shape, slow synchronous deck build, zip download, link to the server-rendered preview |
| Opportunity detail | `/opportunity/<id>` | **L** | 7 | Many sections and disclosures, Win Scout block, read-form flow that redirects, marks an application submitted |
| Applications | `/applications` | **L** | 6 | **Submits an application** (confirm preview), starts the email worker, pauses and resumes agents, opens a credential window on the PC, three tabs |
| Decisions | `/decisions` | **L** | 4 | Writes company facts the agents rely on; inbox confirmations change program outcomes and deal stages; all need `confirmed:true` |
| Pitch Lab | `/pitch-lab` | M | 4 | Three start forms that queue agent work, lessons that steer every agent |
| Application answers | `/application/<id>` | M | 4 | Records submission and results; copy boxes with limits; second fetch for the lab panel |
| Beta families | `/families` | M | 5 | Deletes journal events (changes measured numbers); server-side file import by name |
| Reservation drive | `/drive` | M | 3 | Client-side CSV file read; records purchases into channel math; prompt for referral name |
| Founder profile | `/founder-profile` | M | 3 | **Sensitive data**, reveal-on-click, clear and remove; a save rewrites application answers |
| People | `/people` | M | 5 | Follow-up logging, pause/resume, embedded drive loader |
| Press & gift guides | `/press` | M | 3 | "I sent it" has no confirmation; starts a search agent |
| Credits | `/credits` | M | 3 | Two different forms (credit card, cost stack rows), a delete |
| Assumptions | `/assumptions` | M | 3 | POST on every view (`assumptions-seen`); status select absent for measured rows |
| Money map | `/money` | M | 1 | Ranking explanation disclosures; segmented state control |
| Funding, needs you | `/funding` | M | 0 | Shares Today's next-step logic; hash scroll; CSV export |
| Pipeline | `/opportunities` | M | 0 | 11 views, 8 filters kept in the URL, client-side de-duplication |
| Pitch Studio library | `/pitches` | M | 1 | New-pitch form with material prefill; filters navigate; length links |
| Materials & answers | `/materials` | M | 0 | Search, paging, original-file downloads of any size |
| Plans | `/plans` | M | 1 | PDF and HTML file routes outside the shell; two report shapes |
| Today | `/` | M | 1 | Already rebuilt; keep `doNext` parity |
| Scouts | `/scouts` | S | 1 | Starts agents |
| Deck preview | `/edition/<id>` | S (server-rendered) | 0 | Not part of the single-page app: Python builds the HTML, own CSP, GSAP. Keep as a link or rebuild separately |
| Material detail | `/material/<id>` | S | 0 | Very long text |
| Research run | `/run/<id>` | S | 0 | Raw JSON dump |
| Agent activity | `/activity` | S | 1 | |
| Company facts | `/memory` | S | 0 | Read-only |
| Application plan | `/application-review/<id>` | S | 0 | Redirects when an application exists |
| Shell (sidebar, search, run research) | all | M | 1 | Five GETs to paint the "Next:" lines; phone drawer; Company link changes target |

**The five largest:** Deals & campaigns, Pitch editor, Pitch Lab item, Opportunity detail, Applications.

**Hard parts for the rebuild**
1. **CSRF token for `/next`.** The React shell gets no token (`server.py:49` serves it without the `__CSRF__`
   replacement) and cannot read the HttpOnly cookie. Needs a small server change before any POST works. The `/next`
   shell route list (`server.py:47`) also only knows `/next` and `/next/today`; every new React path must be added
   there, and `/next/assets` only serves `js|css|woff2|webp`.
2. **Origin and host rules.** POSTs must come from the same origin the server expects; a Vite dev server on another
   port will be refused (`403 Origin denied`) unless it proxies with the right `Origin`.
3. **Pitch editor state** (versions, 409 conflict, recovery, timer).
4. **Native `confirm()`/`prompt()` everywhere.** 22 confirmations and 3 prompts must become real dialogs without
   dropping any (section 6), and the server-enforced `confirmed:true` must still be sent.
5. **No polling.** Agent work finishes out of band; the rebuild must either keep "reload" messaging or add polling
   for `researching`, `drafting`, `planning`, `writing`, `searching`, `running` flags.
6. **Whole-page reload after every action** (`boot()`); React needs a refetch or cache-invalidation rule per action,
   including the sidebar "Next:" lines and the Company badge, which depend on five endpoints.
7. **Server-rendered and file routes** (`/edition/<id>`, `/plan/<id>.pdf|.html`, downloads) live outside the app and
   use different CSPs; X-Frame-Options DENY means they cannot be embedded in an iframe.
8. **Form values are strings.** The old UI sends `Object.fromEntries(new FormData)`; the server coerces. Sending
   numbers or nulls from React may behave differently for empty fields; test each form.
9. **20-second client timeout** against slow synchronous endpoints (`/api/read-form` reads a live web form;
   `/api/lab-build` renders slides).
10. **Payload shapes are deep and undocumented** (dashboard, lab item, growth board); types must be written from live
    responses.

---

## 6. Outward and destructive actions

Keep every confirmation below. "Server guard" means the server itself refuses the call without the flag.

### 6.1 Reaches an outside party, or can
| Action | Page | Endpoint | Payload | Old confirmation | Notes |
|---|---|---|---|---|---|
| **Confirm these fields and submit** (application) | Applications | `POST /api/application-confirm` | `{confirmation_id, decision:'APPROVED', confirmed:true}` | `confirm('Submit this exact emailed application preview?')`; button disabled until the preview email was SENT | The only action that submits an application to an outside program. Starts `autonomy_worker.py` (`server.py:263-266`) |
| Decline this application | Applications | `POST /api/application-confirm` | `{confirmation_id, decision:'REJECTED', confirmed:true}` | `confirm('Decline this exact application preview?')` | |
| **Prepare today’s report** | Applications, Daily email | `POST /api/report-now` | `{}` | none | Starts the autonomy worker, which emails the report to gbao.n.vo@gmail.com when mail is connected (`server.py:278-280`) |
| Resume daily reports | Applications | `POST /api/autonomy-resume` | `{scope:'daily_email_report', confirmed:true}` | `confirm('Resume this previously authorized agent with the same limits?')` | Server guard: `confirmed is True`, scope whitelist (`server.py:273-275`). Re-enables scheduled email |
| Resume application preparation | Applications | `POST /api/autonomy-resume` | `{scope:'free_application_pilot', confirmed:true}` | same | Re-enables the agent that reads outside forms and prepares applications |
| Connect report email | Applications | `POST /api/connect-report-email` | `{}` | none | Opens a PowerShell console on the PC for a Google app password (`server.py:281-284`). Local only |
| Connect inbox | Decisions | `POST /api/connect-inbox` | `{account}` | none | Same, for a mailbox; account must be in `INBOX_ACCOUNTS` (`server.py:289-294`) |
| Read the form (and re-read) | Opportunity, Applications, Application | `POST /api/read-form` | `{opportunity_id}` | none | The server opens the program's live web form in a browser profile (`server.py:255-259`); read-only, but it contacts the outside site |
| Run research now / Run it again | Shell, Today, Activity | `POST /api/run-now` | `{}` (`reason` optional) | none | Starts web research through the ChatGPT-plan runner; uses plan allowance |
| Check the program again | Opportunity | `POST /api/research` | `{opportunity_id}` | none | Web research |
| Research how to win | Opportunity | `POST /api/win-research` | `{opportunity_id}` | none | Web research |
| Run a scout | Scouts, Deals (customer voice) | `POST /api/scout-run` | `{key}` | none | Web research |
| Find partners now | Deals | `POST /api/partner-discover` | `{}` | none | Web research |
| Find more now | Press | `POST /api/press-discover` | `{}` | none | Web research |
| Draft a note or pitch | People, Press, Drive / Deals | `POST /api/growth-draft {kind,id}` / `POST /api/deal-draft {id}` | | none | AI drafting only; nothing is sent |
| Plan a campaign, write a brief, tailor/coach/review, another round, challenge | Deals, Plans, Pitch Lab, Assumptions | `/api/campaign-plan`, `/api/plan`, `/api/lab-edition`, `/api/lab-review`, `/api/lab-application`, `/api/lab-rerun`, `/api/assumption-challenge` | | none | AI work on the ChatGPT plan; nothing is sent |
| `mailto:` links ("Open email ↗") | People, Drive | none | | | Opens Bao's mail client with the address (and subject on Drive); the app sends nothing |
| External links (official forms, sources) | many | none | | | Open in a new tab with `rel="noopener noreferrer"` |

**No endpoint sends a message to a contact, a deal, a press outlet or a family.** Every "I sent it" button only
records that Bao sent it himself. **No endpoint spends money**; the only cost is ChatGPT plan allowance for agent
runs, and `spend_usd` / `monthly_usd` fields are records Bao types in.

### 6.2 Records that something outward happened (wrong clicks corrupt the record and the numbers)
| Action | Page | Endpoint | Payload | Old confirmation |
|---|---|---|---|---|
| Mark submitted | Opportunity, Application | `POST /api/outcome` | `{opportunity_id, outcome:'Applied', application_id, note}` | `confirm('Record that you submitted this application? The agents will stop recommending it.')` |
| Record a result | Application | `POST /api/outcome` | `{opportunity_id, application_id, outcome, note, evidence_url}` | none |
| Confirm an inbox result | Decisions | `POST /api/inbox-decision` | `{id, decision:'confirm', outcome, confirmed:true}` | `confirm('Record this program as <outcome> from this email?')`; server guard `confirmed` |
| Confirm a deal reply | Decisions | `POST /api/inbox-decision` | `{id, decision:'confirm', confirmed:true}` | `confirm('Mark <deal> as replied, with this email logged on the deal?')` |
| Deal: I sent it / Won / Lost | Deals | `POST /api/deal-stage` | `{id, stage, note}` | `confirm` per stage (SENT, WON, LOST) + optional `prompt` note |
| Person: I sent it | People | `POST /api/person-touch` | `{id, summary:'Sent the follow-up email.'}` | `confirm('Log that you sent this follow-up? The next one is scheduled automatically.')` |
| Drive: sent / replied / reserved / referred | Drive | `POST /api/drive-action` | `{id, action[, who]}` | `confirm` for sent, replied, reserved (reserved adds a purchase to channel math); `prompt` for referred |
| Press: I sent it | Press | `POST /api/press-state` | `{id, state:'PITCHED'}` | **none in the old app**; consider adding one |

### 6.3 Changes what the agents treat as true
| Action | Page | Endpoint | Payload | Old confirmation |
|---|---|---|---|---|
| Approve / Reject a fact, Dismiss a reminder | Decisions | `POST /api/approval` | `{approval_id, decision, confirmed:true}` | `confirm('Confirm this exact <decision> decision after reviewing the proposal and evidence?')`; server guard `confirmed` |
| Save and approve edited wording | Decisions | `POST /api/approval-edit` | `{approval_id, body, confirmed:true}` | `confirm('Save this wording as a confirmed company fact?')`; server guard `confirmed` |
| Save a founder-profile value | Founder profile | `POST /api/founder-profile` | `{key, value}` or `{label, value, sensitive}` | none; rewrites answers in every read application |
| Approve / Reject a lesson | Pitch Lab | `POST /api/lesson` | `{id, decision}` | none; an approved lesson guides every agent |
| Approve a lab item | Pitch Lab item | `POST /api/lab-approve` | `{id}` | none |
| Edit an assumption | Assumptions | `POST /api/assumption` | `{key, …}` | none |
| Watch / Skip / Apply / Prepare a program | Opportunity | `POST /api/decision` | `{opportunity_id, decision, reason}` | `prompt` for a reason (Watch, Skip) or a required reason field |
| Pause an agent | Applications | `POST /api/autonomy-pause` | `{authorization_id}` | none (pausing is the safe direction) |

### 6.4 Deletes or clears data
| Action | Page | Endpoint | Payload | Old confirmation |
|---|---|---|---|---|
| Remove a cost-stack item | Credits | `POST /api/stack-delete` | `{id}` | `confirm('Remove this item?')` |
| Remove a channel-math week | Deals | `POST /api/channel-entry-delete` | `{id}` | `confirm('Remove this week’s entry?')` |
| Remove a family journal event | Beta families | `POST /api/family-event-delete` | `{id}` | `confirm('Remove this event from the journal? The measured numbers change with it.')` |
| Clear a founder-profile value | Founder profile | `POST /api/founder-profile` | `{key, value:''}` | `confirm('Clear this saved value? Questions it answered keep their current answers until you change them.')` |
| Remove a custom founder-profile fact | Founder profile | `POST /api/founder-profile-delete` | `{key}` | `confirm('Remove this fact from your profile?')` |
| Dismiss an inbox email | Decisions | `POST /api/inbox-decision` | `{id, decision:'dismiss', confirmed:true}` | **none in the old app**; the email is set aside for good |
| Restore an old pitch version | Pitch editor | `POST /api/pitch/<id>/restore` | `{version_id, expected_version_id}` | `confirm` only when there are unsaved edits; not destructive (creates a new version) |
| Discard unsaved pitch text | Pitch Studio | none | | `confirm('Discard the unsaved new pitch?')`; `beforeunload` guard in the editor |

There is no endpoint that deletes a pitch, a deal, a person, a family, an application or an opportunity. Deals are
parked or lost, people are paused, pitches are archived by status.

### 6.5 Sensitive reads
| Action | Page | Endpoint | Notes |
|---|---|---|---|
| Reveal a masked value | Founder profile | `POST /api/founder-profile-reveal {key}` | Returns the secret value (EIN, address, date of birth). Old UI shows it in the input until the page is left. Never cache it, log it or keep it in client state longer than the view |

---

## Appendix: all 66 POST endpoints

| # | Endpoint | Payload keys read by the server | server.py | Called from |
|---|---|---|---|---|
| 1 | `/api/pitches` | whole body (pitch fields) | 242 | pitch.js:61, 73 |
| 2 | `/api/pitch/<id>` | whole body incl. `expected_version_id` | 245-248 | pitch.js:61 |
| 3 | `/api/pitch/<id>/restore` | `version_id`, `expected_version_id` | 248 | pitch.js:74 |
| 4 | `/api/run-now` | `reason` (optional) | 249 | app.js:348 |
| 5 | `/api/decision` | `opportunity_id`, `decision`, `reason` | 252 | app.js:348, 349 |
| 6 | `/api/outcome` | `opportunity_id`, `outcome`, `note`, `evidence_url`, `application_id` | 253 | app.js:408, 412 |
| 7 | `/api/start-application` | `opportunity_id` | 254 | app.js:348 (no button) |
| 8 | `/api/read-form` | `opportunity_id` | 255 | app.js:416 |
| 9 | `/api/prepare-application` | `opportunity_id` | 260 | app.js:348 (no button) |
| 10 | `/api/application-confirm` | `confirmation_id`, `decision`, `confirmed` | 263 | app.js:348 |
| 11 | `/api/autonomy-pause` | `authorization_id` | 267 | app.js:348 |
| 12 | `/api/autonomy-resume` | `scope`, `confirmed` | 270 | app.js:348 |
| 13 | `/api/report-now` | none | 278 | app.js:348 |
| 14 | `/api/connect-report-email` | none | 281 | app.js:348 |
| 15 | `/api/inbox-decision` | `id`, `decision`, `outcome`, `confirmed` | 285 | app.js:348 |
| 16 | `/api/connect-inbox` | `account` | 289 | app.js:348 |
| 17 | `/api/research` | `opportunity_id` | 295 | app.js:348 |
| 18 | `/api/approval` | `approval_id`, `decision`, `confirmed`, `note` | 299 | app.js:348 |
| 19 | `/api/approval-edit` | `approval_id`, `body`, `confirmed` | 302 | app.js:274 |
| 20 | `/api/credit` | `id` + body | 308 | app.js:494 |
| 21 | `/api/person` | body | 309 | app.js:495 |
| 22 | `/api/person-update` | `id` + body (`state`) | 310 | app.js:487 |
| 23 | `/api/person-touch` | `id` + body | 311 | app.js:482, 496 |
| 24 | `/api/growth-draft` | `kind`, `id` | 314 | app.js:485 |
| 25 | `/api/press-state` | `id`, `state` | 312 | app.js:484 |
| 26 | `/api/press-discover` | none | 314 | app.js:486 |
| 27 | `/api/deal` | body | 319 | growth.js:116 |
| 28 | `/api/deal-update` | `id` + body | 320 | growth.js:118 |
| 29 | `/api/deal-stage` | `id`, `stage`, `note`, `next_on` | 321 | growth.js:104 |
| 30 | `/api/deal-event` | `id` + body | 322 | growth.js:117 |
| 31 | `/api/deal-draft` | `id` | 328 | growth.js:106 |
| 32 | `/api/partner-discover` | none | 328 | growth.js:107 |
| 33 | `/api/campaign-plan` | `key`, `note` | 328 | growth.js:119 |
| 34 | `/api/campaign-state` | `key`, `state` | 323 | growth.js:108 |
| 35 | `/api/channel-entry` | body | 324 | growth.js:121 |
| 36 | `/api/channel-entry-delete` | `id` | 325 | growth.js:109 |
| 37 | `/api/field-day` | `key` + body | 326 | growth.js:120 |
| 38 | `/api/lab-edition` | `opportunity_id`, `minutes`, `slide_limit`, `note` | 333 | app.js:612 |
| 39 | `/api/lab-review` | `pitch_id` | 334 | app.js:613 |
| 40 | `/api/lab-application` | `application_id` | 335 | app.js:614, 627 |
| 41 | `/api/lab-rerun` | `id`, `note` | 336 | app.js:615 |
| 42 | `/api/lab-approve` | `id` | 337 | app.js:624 |
| 43 | `/api/lab-save` | `id` | 338 | app.js:623 |
| 44 | `/api/lab-build` | `id` | 339 | app.js:622 |
| 45 | `/api/lesson` | `id`, `decision` | 340 | app.js:625 |
| 46 | `/api/plan` | `question` | 343 | plans.js:24 |
| 47 | `/api/win-research` | `opportunity_id` | 349 | scouts.js:51 |
| 48 | `/api/win-seen` | `opportunity_id` | 348 | scouts.js:52 |
| 49 | `/api/stack-cost` | body (`id` optional) | 352 | scouts.js:70 |
| 50 | `/api/stack-delete` | `id` | 352 | scouts.js:75 |
| 51 | `/api/scout-run` | `key` | 353 | scouts.js:79 |
| 52 | `/api/money-move` | `id`, `state` | 356 | app.js:626 |
| 53 | `/api/family` | body | 362 | product.js:41 |
| 54 | `/api/family-update` | `id` + body (`status`) | 363 | product.js:49 |
| 55 | `/api/family-event` | body (`family_id`, `kind`, `at`, `detail`) | 364 | product.js:42 |
| 56 | `/api/family-event-delete` | `id` | 365 | product.js:54 |
| 57 | `/api/metrics-import` | `file`, `provider`, `note` | 366 | product.js:43 |
| 58 | `/api/drive-import` | `csv` | 370 | drive.js:39 |
| 59 | `/api/drive-action` | `id`, `action` (`sent|replied|reserved|referred`), `note`, `who` | 371 | drive.js:53 |
| 60 | `/api/founder-profile` | `key`, `value`, `label`, `sensitive` | 378 | profile.js:33, 34, 43 |
| 61 | `/api/founder-profile-reveal` | `key` | 376 | profile.js:42 |
| 62 | `/api/founder-profile-delete` | `key` | 377 | profile.js:44 |
| 63 | `/api/assumption` | `key` + body | 382 | assumptions.js:49 |
| 64 | `/api/assumption-challenge` | none | 384 | assumptions.js:53 |
| 65 | `/api/assumptions-seen` | none | 383 | assumptions.js:44 |
| 66 | `/api/notification-read` | `id` | 385 | app.js:348 (no button) |

Not verified in this inventory: the exact fields each Python module accepts beyond the keys the UI sends (the
server passes the whole body to `add_deal`, `update_credit`, `save_cost` and similar), and live response shapes;
the field lists above come from what the render code reads, not from running the server.
