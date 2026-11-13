# Function audit: Customers, Company and Agents pages (old app vs rebuild)

Audited 2026-11-11 to 2026-11-12 against `docs/rebuild/INVENTORY.md` (3.18 to 3.29, 2, 6, appendix), the old source
(`founder_os/ui/*.js`) and `founder_os/server.py`. Source was not edited. Line numbers were re-read on Nov 12 after
the builders' design fixes; paths are under `web/src/`. The builders were still editing (`People.tsx` moved by 7 lines
while this was written), so a line may sit a few lines off; each row names the action so it can be found.

## Bottom line

**No page lost an action, and no payload, confirmation or link is wrong.** All 12 pages read the right GETs, send the
old endpoints with the old keys and value types, keep every old confirmation (and add three), and catch every error.
There are **4 real defects, none blocking**: one stale list on Deals, one lost signal in the shell, and two small
after-action gaps. One thing I changed on the data copy could not be undone (see "What I changed on the copy").

## How it was checked

| Check | How | Result |
|---|---|---|
| Typecheck | `npx tsc --noEmit -p tsconfig.app.json` | passes |
| Response shapes | `curl` of `/api/growth`, `growth-alerts`, `product`, `drive`, `press`, `people`, `dashboard`, `founder-profile`, `scouts`, `plans`, `run/<id>` on localhost:8806, compared field by field with what the pages read | every field used exists |
| Handlers | read each POST handler in `server.py:231-391` and the Python it calls (`growth_desk.py`, `growth_agents.py`, `product_desk.py`, `reservation_drive.py`, `founder_profile.py`, `planner.py`, `scouts.py`) | keys and types match |
| Live, in the built app | all 12 pages opened with no console errors; `/growth#channels` and `/growth#deal-<id>` (a deal past the first six) scroll and open; "Lost" runs confirm then the note question, and Cancel sends nothing; a channel week was saved then removed; a private custom profile fact was added, revealed and removed; `/run/nope` shows the error with a retry | works |
| Not run, read only | every POST in INVENTORY 1.7 and 6.1 (run-now, scout-run, plan, partner-discover, press-discover, growth-draft, deal-draft, campaign-plan, connect-inbox) | wired as the old page; never called |
| Not checkable live | fact cards and inbox emails on Decisions (the copy has none waiting), drive members (none loaded), a campaign with a plan (none planned) | checked against the old code only |

## Real defects, ranked

| # | Defect | Where | Exact fix |
|---|---|---|---|
| 1 | **Nothing outside /decisions says a fact or an inbox email is waiting.** The old shell showed the Company count badge on every page (`app.js:230, 343`) and "Next: confirm a company fact" (`app.js:307`). The new shell has no badge, and Today's Company row only covers profile blanks. A proposed program result or deal reply can sit unseen. | `lib/today.ts:125`, `shell.tsx` | In `lib/today.ts`, before line 125: `const waiting = (dash.needs_decision?.length || 0) + (dash.inbox ? dash.inbox.proposed + dash.inbox.review : 0)`; `if (waiting) rows.push({ name: "Company", line: waiting === 1 ? "Confirm 1 company fact" : \`Confirm ${waiting} company facts\`, href: "/decisions", tone: "due" })`, else keep the profile row. Optional: the same count as a badge on "Company" in `shell.tsx`. |
| 2 | **"Do next" on Deals goes stale after an action.** The alerts are read with `apiOnce`, which is never cleared, so after "I sent it" the row "26 outreach notes ready to send" stays until a full reload. The old `boot()` cleared the cache before every re-render (`app.js:321`). | `lib/growth.ts:131` | Change `apiOnce<Alert[]>("/api/growth-alerts")` to `api<Alert[]>("/api/growth-alerts")` (and drop the `apiOnce` import on line 3). |
| 3 | **A failed re-read after a successful action is silent.** `useLoad.reload()` swallows the error and returns null; with data already on screen `LoadGate` keeps showing the old data, and the page toasts success. The record was saved, but the screen is stale with no hint. The old app replaced the page with the load error. Applies to every page here. | `components/app/page.tsx:23, 34` | In `LoadGate`, when `state.data && state.error`, render a one-line alert above the children: "This page could not refresh. " + `state.error` + a "Load it again" button. (Shared file: coordinator's.) |
| 4 | **Cancel on the optional note now cancels the stage move.** Old: Cancel on the prompt saved the move with an empty note (`growth.js:104`). New: Cancel after the "Won/Lost" confirmation drops the move with no message, so Bao can think a deal was marked won when it was not. | `pages/deals/DealsPanel.tsx:25` (`if (said === null) return`) | Either keep it and toast "Not saved." on that return, or match the old page: `note = said ?? ""` and continue. Recommended: the toast (safer for a record of what happened). |

Not defects, for the record: the 11 MB `/api/dashboard` read on Decisions, Company facts and Activity is the old app's
behaviour; `key` warnings are possible if two themes or sources share a name (`deals/Voice.tsx`), with no effect.

## What the old shell had that is gone

| Old shell piece | Now | Does it matter |
|---|---|---|
| Global search box on every page (`GET /materials?q=`) | Only on `/materials` (`pages/Materials.tsx:40`) | Small: one extra click |
| "Run research now" on every page | `/activity` only (`pages/Activity.tsx:80`), same pause rule when the last failure has a known cause | Small. Today shows "See what failed", no rerun button |
| Company count badge (`#decision-count`) | Gone | **Yes: defect 1** |
| "Next: ..." line under each department | Partly on Today: Funding, Customers, Company (profile blanks only), and a research-stopped note. **Gone:** Pitch's next (lab alerts and assumptions alert; `/api/lab-alerts` is not read anywhere in `web/src`), Company's "confirm a company fact", Agents' "Research is running now / Last research <day>" | Company: defect 1. Pitch: worth a Today row. Agents: `/activity` says it in its first line |
| Company link switching to `/founder-profile` when no facts wait but the profile has blanks | Company always opens `/decisions`; Today's Company row links to `/founder-profile` | Small |
| Phone drawer ("Departments" toggle, Escape closes) | The six departments wrap in the header; no drawer | No: nothing is unreachable |
| "All pages" list | Replaced by each department's tab row | No |
| "On this PC / Owner sign-in protected" line | Gone | No |
| Load-error screen's link to `/pitches` | `LoadGate` shows the error and "Load it again" | No |
| Breadcrumbs, skip link, document title | Kept (title now ends "· Founder OS") | No |

## Page tables

Status: OK, WRONG or MISSING. "+confirm" means the rebuild asks first where the old page did not.

### Deals & campaigns `/growth`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/growth`, `/api/growth-alerts` | OK (alerts go stale: defect 2) | `lib/growth.ts:129-131` |
| Stage moves, same DEAL_MOVES, `{id, stage, note}` | OK | `lib/growth.ts:81-88`, `pages/deals/DealsPanel.tsx:28` |
| Confirm for SENT, WON, LOST; optional note for REPLIED, MEETING, PROPOSAL, WON, LOST | OK (Cancel on the note: defect 4) | `DealsPanel.tsx:21-25` |
| Park, Lost, Move back to open (DRAFTED if a draft, else FOUND) | OK | `DealsPanel.tsx:123-127` |
| Draft it now / Write a new note `{id}` | OK, not called | `DealsPanel.tsx:54` |
| Find partners now `{}`, off while searching | OK, not called | `pages/Deals.tsx:50-51` |
| Add a deal (9 fields as strings) | OK | `DealsPanel.tsx:176` |
| Log what happened `{id, summary, occurred_on, next_step, next_on}` | OK | `DealsPanel.tsx:92` |
| Deal details `{id, value_usd, value_note, contact_route}` | OK | `DealsPanel.tsx:102` |
| Plan it / Plan again `{key, note}` | OK, not called | `deals/Campaigns.tsx:188` |
| Mark it running / done `{key, state}` | OK | `Campaigns.tsx:99` |
| Tally the day `{key, approached, conversations, emails, reservations, on, note}` | OK | `Campaigns.tsx:59` |
| Record a week (8 fields as strings) | OK, tested live | `deals/Channels.tsx:95` |
| Remove a week `{id}` with confirm | OK, tested live | `Channels.tsx:29-34` |
| Research now / again `{key:'customer_voice'}` | OK, not called | `deals/Voice.tsx:27` |
| Type filter, Do next (top 3), copy buttons | OK (filter is a select; it no longer filters closed deals) | `DealsPanel.tsx`, `Deals.tsx` |
| Anchors `#deal-<id>`, `#campaign-<key>`, `#families-say`, `#channels` | OK, tested live | `Deals.tsx:35-43`, `deals/parts.tsx:33-36` |
| Reload then message; errors toasted | OK | `Deals.tsx:26-31` |
| Link to `/decisions` on a possible reply | OK | `DealsPanel.tsx:80` |

### Beta families `/families`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/product` | OK | `pages/Families.tsx:218` |
| Add a family (6 fields) | OK | `Families.tsx:110` |
| Status select `{id, status}` on change | OK | `Families.tsx:60` |
| Log an event `{family_id, kind, at, detail}`, day required, max today (Eastern) | OK | `Families.tsx:58` |
| Remove an event `{id}` with confirm | OK | `Families.tsx:224-229` |
| Import a file `{file, provider, note}`, toast "Imported N numbers from <file>" | OK | `Families.tsx:137` |
| Counts, measured list, intake tables, API-key note | OK | `Families.tsx` |
| Anchors `#family-<id>`, `#intake` | OK | `Families.tsx:221`, `lib/customers.ts:119` |

### Reservation drive `/drive`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/drive` | OK | `pages/Drive.tsx:235` |
| Load people `{csv}` from the file (60 KB cap) or the box; same result message; goes to `/drive` from another page | OK | `Drive.tsx:110-121` |
| I sent it / I sent the reminder, They replied, They reserved: `{id, action}` each with its confirm | OK | `Drive.tsx:246-247` |
| They referred someone `{id, action, who}`, question first, Cancel aborts | OK | `Drive.tsx:243` |
| Draft it now / Write a new draft `{kind:'contact', id}` | OK, not called | `Drive.tsx:250` |
| Open email (mailto with the draft subject), copy buttons | OK | `Drive.tsx:92` |
| Groups, countdown, "What channel math sees" with link `/growth#channels`, reminder days | OK | `Drive.tsx:306` |
| Anchor `#drive-<id>` | OK | `Drive.tsx:238` |

### Press & gift guides `/press`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/press` | OK | `pages/Press.tsx:110` |
| Find more now `{}`, off while searching | OK, not called | `Press.tsx:132` |
| Draft it now / Write a new draft `{kind:'press', id}` | OK, not called | `Press.tsx:128` |
| I sent it `{id, state:'PITCHED'}` | OK, +confirm | `Press.tsx:117-123` |
| Skip, It was published, Move back to open | OK | `Press.tsx:123` |
| Open how to pitch, Source (new tab, noopener) | OK | `Press.tsx` |

### People `/people`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/people` | OK | `pages/People.tsx:132` |
| I sent it `{id, summary:'Sent the follow-up email.'}` with confirm | OK | `People.tsx:138-144` |
| Draft it now / Write a new draft `{kind:'contact', id}` | OK, not called | `People.tsx:33` |
| Log a conversation `{id, summary, occurred_on, next_followup_on}` | OK | `People.tsx:43` |
| Pause / Resume follow-ups `{id, state}` | OK | `People.tsx:37` |
| Add a person, `cadence_days` sent as a number | OK | `People.tsx:105-106` |
| Drive loader, link to `/drive`, Open email | OK | `People.tsx` ("Load people for the reservation drive") |
| Anchors `#person-<id>`, `#drive-loader` | OK | `People.tsx:135` |

### Decisions `/decisions`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/dashboard` | OK | `pages/Decisions.tsx:194` |
| Approve / Reject / Dismiss `{approval_id, decision, confirmed:true}`, sent only after confirm | OK | `Decisions.tsx:212-221` |
| Edit, then Save and approve `{approval_id, body, confirmed:true}` after confirm | OK | `Decisions.tsx:224-229` |
| Inbox Confirm `{id, decision:'confirm', outcome, confirmed:true}` after confirm | OK | `Decisions.tsx:238-243` |
| Deal reply `{id, decision:'confirm', confirmed:true}` after confirm | OK | `Decisions.tsx:233-235` |
| Not relevant / Not a reply `{id, decision:'dismiss', confirmed:true}` | OK, +confirm | `Decisions.tsx:246-251` |
| Connect a mailbox `{account}`, no reload, same message | OK, not called; one click as before, off while it runs | `Decisions.tsx:254` |
| Export tracker (CSV), Open the deal, Find the program | OK | `Decisions.tsx:274, 133, 147` |
| Recently decided (one per label, cut on a whole word) | OK | `lib/company.ts:44-53` |

### Company facts `/memory`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/dashboard`; groups, labels, common verification day, original records | OK | `pages/CompanyFacts.tsx:34`, `lib/company.ts:61-89` |
| Link to `/decisions`; empty states | OK | `CompanyFacts.tsx:47` |

### Founder profile `/founder-profile`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/founder-profile` | OK | `pages/FounderProfile.tsx:128` |
| Save `{key, value}`; empty refused with the old message; toast with the filled count | OK, tested live | `FounderProfile.tsx:144-146` |
| Reveal `{key}`, no reload | OK, tested live | `FounderProfile.tsx:42` |
| Clear `{key, value:''}` with confirm | OK, tested live | `FounderProfile.tsx:149-153` |
| Remove a custom fact `{key}` with confirm | OK, tested live | `FounderProfile.tsx:156-157` |
| Add another fact `{label, value, sensitive: boolean}` | OK, tested live | `FounderProfile.tsx:160` |
| Input types (url, date, text; private ones text with autocomplete off) | OK | `lib/company.ts:117` |
| **A revealed value lives only in its row's state** | OK. It is never cached, logged or put in the page's data; any successful action remounts every row (`key={stamp}`, lines 132-136, 174) and it is gone. Checked live: gone after another row's save; still shown after a refused save, as on the old page | `FounderProfile.tsx:39-46` |

### Activity `/activity`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/dashboard` (`agent_activity`) | OK | `pages/Activity.tsx:72` |
| Run research now / Run it again `{}`; disabled with "Paused until the research agent is fixed" on a known cause | OK, not called (shown disabled on the copy) | `Activity.tsx:77-83, 98` |
| Rows link to `/run/<id>`; See what failed | OK | `Activity.tsx:50, 97` |

### Research run `/run/<id>`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/run/<id>`; counts, issues, searches, sources, usage, exact data | OK | `pages/Run.tsx:80` |
| Unknown id | OK: error with retry | checked live |

### Scouts `/scouts`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/scouts` | OK | `pages/Scouts.tsx:51` |
| Run now `{key}`, off while running; `win` shows a link to `/opportunities` | OK, not called | `Scouts.tsx:38-45, 58` |
| "Results land in" links (`/money#cat-…`, `/credits`, `/growth`, `/growth#families-say`, `/press`, `/opportunities`) | OK: all served, and `/money` has the `cat-` ids | `Scouts.tsx:33`, `pages/MoneyMap.tsx:154` |
| Broad sweep, link to `/activity` | OK | `Scouts.tsx:96` |

### Plans `/plans`
| Function | Status | Evidence |
|---|---|---|
| GET `/api/plans` | OK | `pages/Plans.tsx:149` |
| Write the brief `{question}` (may be empty), off while writing | OK, not called. Enter in the box adds a line; only the button sends | `Plans.tsx:155-163` |
| Open the PDF, Web version (new tab), past briefs with PDF / Open | OK | `Plans.tsx:23-24, 135-139` |
| Older long-form report shape | OK | `Plans.tsx:34-43` |

## Outward and agent-starting actions

None can fire by accident. Each is one deliberate button, as on the old page: no action runs on page load, on a
change event or from pressing Enter in another field, and every such button is disabled while its call is running.
`confirmed: true` appears only in `Decisions.tsx:221, 229, 235, 243, 251`, each after `confirm()` returns true.

## What I changed on the copy

- Channel math: saved one test week ("AUDIT TEST - remove") and removed it. The copy is back to its 2 entries.
- Founder profile: added a private custom fact "Zz audit probe" and removed it.
- **Not undone:** I saved the value "audit" into Pronouns to test a successful save, then cleared it. The save ran the
  form filler, which wrote "audit" as a draft answer on 3 questions: `answer-26d23f98df5ea613b893428d` (Preferred
  Pronouns), `answer-7476ff3b263b40aefb91918c` (Preferred Pronouns Other), `answer-7072fffd2ec7dc10f9602639` (Team
  member pronouns Other). No endpoint removes an answer, and I did not touch the database. This is on the test copy
  only; fix those three answers on their application pages or re-copy the data.
