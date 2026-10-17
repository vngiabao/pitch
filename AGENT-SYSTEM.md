# How the Founder OS agents work together

Every piece of outward-facing writing (an application answer, a tailored pitch, a press pitch, a follow-up email) moves through the same assembly line. No single agent ships anything. Each one does one job, hands off, and can send work back. Bao is the last step every time, and nothing is submitted or sent without his explicit yes.

## The agents

| Layer | Agent | Job | Uses AI? | Web? |
|---|---|---|---|---|
| Find | **Competition Scout** | Pitch competitions, pitch nights and hackathons with cash prizes (4 search families). Monday and Thursday. Lands in the Money map. | Yes | Yes |
| Find | **Grant Scout** | Non-dilutive grants: foundations, SBIR/STTR, MEDC, AgeTech and family-tech funds (4 families). Tuesday and Friday. | Yes | Yes |
| Find | **Founder Money Scout** | Fellowships, stipends and awards paid to Bao or Daniel personally; judged on founder eligibility (3 families). Wednesday. | Yes | Yes |
| Find | **Accelerator Scout** | Pre-seed accelerators and corporate or AI programs that put cash in, terms labelled plainly (4 families). Saturday. | Yes | Yes |
| Find | **Credits Scout** | Credits for the top AI models, voice, transcription, media and cloud (5 credit families, rotating), told which of A Story's costs are still uncovered. Daily at 7:30. | Yes | Yes |
| Find | **Perks Scout** | Free tools, software, ad credits, fee waivers, office space, legal and accounting help and expert hours for a bootstrapped startup (4 families). Sunday. Lands in the Money map under free tools and perks. | Yes | Yes |
| Find | **Investor Scout** | Angel groups, pre-seed funds, university and alumni funds and syndicates with a published way in; thesis fit, check size and stage as published. Wednesday. Lands on the deal board as investor deals. | Yes | Yes |
| Find | **Win Scout** | For one competition: rules, scoring weights, judges and what they look for, past winners and why, this cycle's other companies, and the unwritten expectations, each with a source. Pitch Tailor builds the edition to it, the Drafter shapes answers to it, the Coach judges by it. Weekly refresh for programs A Story is in; changes reach Today. | Yes | Yes |
| Find | **Customer Voice Scout** | What adult children and family caregivers say online about a parent's stories, memory, aging and gifts (r/AgingParents, r/CaregiverSupport, r/Genealogy, r/GiftIdeas, X, Quora, genealogy and senior-care forums): themes with how many threads voiced each, short quotes with URLs, what they tried (Storyworth, Remento, recording apps, nothing), objections, what they say they would pay, and the words they use. Thursday 8:15 and on request. Every run is kept (`customer_voice`) and compared to last week. Evidence about the market for Pitch Tailor and the Coach; objections and words for the Campaign Planner and the field-day script. Never a fact about A Story. | Yes | Yes |
| Find | **Funding Hunter (broad sweep)** | All 19 search families at once, kept as a weekly safety net behind the scouts; also runs targeted re-verifications | Yes | Yes |
| Find | **Press Scout** | Finds gift guides, newsletters and outlets | Yes | Yes |
| Find | **Partner Scout** | Finds organizations that reach adult children or buy for many older adults (employers, alumni groups, senior living, faith communities, libraries) and Michigan and Ohio angels. Each lands on the deal board as Found, with the public route it publishes. Tuesday mornings until mid-December. | Yes | Yes |
| Find | **Form Reader** | Opens official application forms and reads the questions | No | Yes (read-only) |
| Find | **Inbox Tracker** | Reads both inboxes for results (read-only) | No | No |
| Find | **Metrics Intake** | Reads CSV exports (App Store Connect, Stripe, RevenueCat) from `data/metrics-inbox`; every number keeps its file, fingerprint and day. API pulls are a documented stub whose keys would live only in Windows Credential Manager. | No | No |
| Rank | **Money Ranker** | Gives every open, not-yet-applied program an expected value per founder hour (prize or discounted credits x win likelihood from the fit score / estimated hours, raised near a deadline) and names the five to apply to first. Every component is shown; the figure is an estimate. Then it prepares those five ahead of Bao: reads the form, queues the drafter, or starts the Pitch Lab edition, one action per cycle. | No (rules) | No |
| Draft | **Application Drafter** | Answers form questions from approved facts | Yes | No |
| Draft | **Form Filler** | Copies what only Bao knows from the Founder Profile Vault (`founder_profile`: EIN, addresses, phone, dates of birth, citizenship, links, incorporation date, team and money lines, plus his own extra facts) into form answers, matching labels and synonyms ("EIN" / "tax ID", "incorporated on", "LinkedIn", "video"). Provenance `founder_profile`. A question stays "Needs you" only when the vault is empty for it. Sensitive values are masked on the page and never reach logs, reports or AI drafts. | No (rules) | No |
| Draft | **Pitch Tailor** | Reads a program's rules and builds the program edition: slide plan, timed script, materials checklist, ask | Yes | Official rules page only |
| Draft | **Follow-up and Press Drafters** | Notes to people and outlets | Yes | No |
| Draft | **Reservation Drive** | Bao loads his leads and beta families from a CSV (name, email, context, kind); each becomes a contact tagged `reservation-2026`, due today, so the Follow-up drafter writes one note per cycle with a drive task: leads get a personal note about the $1 reservation (15 percent off the first year of Individual, closes November 2), beta families get a thank-you with one referral ask. Fact Guard and Bao's Voice check every note. Bao sends each one himself and records replies, reservations and referrals; reservations and referrals land in channel math. | Yes (the Follow-up drafter) | No |
| Draft | **Deal Drafter** | The first note or follow-up for a deal, from approved facts and pricing only. Goes through Fact Guard and Bao's Voice like every growth draft. Bao sends it and presses "I sent it"; only he moves a deal forward. | Yes | No |
| Draft | **Campaign Planner** | Turns pricing, the calendar, known outlets, deals and channel math into a dated plan for the holiday gift-pass campaign: per channel, what, when, the lead message, the success measure and what Bao must supply. Fact Guard checks its words; Bao's Voice rewrites its messages. | Yes | No |
| Check | **Fact Guard** | Every number and claim traces to approved facts or the evidence table. Applies the team, traction and pricing rules. | No (rules) | No |
| Check | **Bao's Voice** | Rewrites wording into Bao's voice (BAO-VOICE.md). Never changes facts. | Yes | No |
| Check | **Pitch Coach** | YC-partner review: 10-point scorecard, hard questions, the three fixes that matter most | Yes | No |
| Check | **Format Check** | Word and character limits, time at 130–150 wpm, required sections | No (rules) | No |
| Check | **Channel Math** | Visits, signups, purchases, spend and revenue Bao records per channel per week become conversion, cost per purchasing family and revenue per dollar, with the dates they cover. Fact Guard allows these measured numbers in a pitch. | No (rules) | No |
| Check | **Retention Tracker** | Counts what the beta families actually do from the family journal: second-call rate, relatives contributing, calls that followed a contribution. Each number carries its denominator, date range and source, and reaches Fact Guard as a measured fact. | No (rules) | No |
| Build | **Edition Builder** | Turns the slide plan into a real deck from the frozen core deck's own slides (`seed-data/core-deck-*`): order, speaker notes and page numbers change, the design never does. New slides (`new-1`, `new-2`) are drafted from one plain template and flagged. | No (rules) | No |
| Check | **Slide QA** | Renders every slide in headless Edge and measures it: text overlapping text, text running past its box, anything off the slide, rows a few pixels out of line, text under 18px, missing images and notes. Problems go to Bao under "Still needs your eyes". | No (rules) | No |
| Decide | **Bao** | Edits, approves or rejects. Submits himself. | - | - |
| Learn | **Outcome Learner** | Turns results and Bao's edits into proposed lessons | Yes | No |
| Report | **Daily Report and Today** | One list of what needs Bao, every morning | No | No |
| Report | **Planner** | On request, or every Monday morning: answers Bao's question from every desk (Today, money per hour, deals, campaigns, channel math, scouts, win briefs, Pitch Lab, measured facts), lays out the dated next moves with an owner, and lists the questions only he can answer. Delivered as a PDF in his own identity (The Turn) on the Plans page and linked in the daily brief. | Yes | No |

## The assembly line (one work item)

```
 Hunter / Form Reader / Scout          (find)
            │
            ▼
 Drafter / Pitch Tailor                (draft, round 1)
            │
            ▼
 Fact Guard ──── fails ───► back to the drafter with the exact issues
            │ passes
            ▼
 Bao's Voice                           (wording only)
            │
            ▼
 Fact Guard again                      (voice edits can't add claims)
            │
            ▼
 Pitch Coach ── any score < 4 and round < 3 ──► back to the drafter with the top 3 fixes
            │ all ≥ 4, or round 3 reached
            ▼
 Format Check                          (limits, timing)
            │
            ▼
 Edition Builder                       (pitch editions: the deck itself, from core slides)
            │
            ▼
 Slide QA                              (renders and measures every slide)
            │
            ▼
 READY FOR BAO   → Today, the daily email, and the item's page
            │
   Bao edits ──► his edit becomes a voice example (feeds Bao's Voice and Coach)
   Bao approves and submits himself
            │
            ▼
 Inbox Tracker or Bao records the result
            │
            ▼
 Outcome Learner ──► proposed lessons in Decisions ──► approved lessons join the playbook context
```

**Stages** (stored on each work item): `DRAFT → FACT_CHECK → VOICE → FACT_RECHECK → COACH → (REVISE → DRAFT …) → FORMAT → BUILD → SLIDE_QA → READY → APPROVED → SUBMITTED → RESULT`.

**Loop limits.** At most two revision rounds. On round 3 the item goes to Bao anyway, with the Coach's open concerns attached. Bao's time is the bottleneck, so the system never loops silently forever, and never hides a weak score.

## The four feedback loops

1. **Quality loop (minutes).** Coach and Fact Guard send work back to the drafter with specific fixes, not general advice. The drafter must answer each fix or explain why not.
2. **Voice loop (every edit).** Bao's change from the final draft to his own version is saved as a voice example. Bao's Voice reads the ten newest examples on every run, so his corrections compound instead of repeating.
3. **Outcome loop (per result).** When a program accepts, rejects or gives feedback, the Outcome Learner links the result to the exact answers, deck edition and Coach scores used. It proposes lessons ("judges at voice-AI programs responded to the real-call demo"). Approved lessons are added to every future Tailor and Coach context. They also feed the Hunter, which ranks similar programs higher after a win and lower after repeated rejections.
4. **Playbook loop (weekly).** When the same lesson or voice pattern repeats three times, it's proposed as a permanent rule for PITCH-PLAYBOOK.md or BAO-VOICE.md. Bao approves it in Decisions. Nothing changes the playbook without him.

## Contracts between agents

- **Hand-offs are data, not prose.** Each agent returns JSON with a verdict, scores or issues, and the revised text. The next agent reads only that, plus approved facts and the playbook.
- **Facts only flow one way.** Only Bao can approve a fact (Decisions). Agents read approved facts; they never create them. Fact Guard blocks any number that isn't approved or in the evidence table.
- **Measured beats reported.** Numbers from the beta family journal are labelled measured, with their denominator and as-of date. Where a measured number and an owner-reported one both exist, drafters use the measured one, and Fact Guard notes which numbers in a draft are measured.
- **What families say online is evidence, not traction.** The Customer Voice Scout's themes, counts and quotes describe the market. No agent may turn them into a fact about A Story, and Fact Guard blocks any thread count from them unless it appears inside a quotation with the thread's URL beside it.
- **Voice can't change facts; Coach can't add facts.** If the Coach wants a number that doesn't exist, it says "missing proof" and the item lists it under open questions for Bao.
- **Every review is kept.** Each work item shows its full history: who said what, at which round, with scores. Nothing is overwritten.
- **Ranking is an estimate, shown whole.** The money-per-hour figure orders the work and never forecasts an award. Its parts (amount counted, likelihood, hours, urgency) are always displayed beside it, and programs with no published amount are listed as unranked rather than scored.
- **Cost guard.** One AI step per worker cycle (every 5 minutes), on the ChatGPT plan. No API keys. Coach and Voice skip items Bao already approved.
- **Safety.** Read-only on the web and in the inboxes. Agents never submit, send, pay or accept terms.

## Where Bao sees it

- **Today and the daily email:** items READY for him, and lessons waiting in Decisions. Reservation notes ready to send, and on October 26, October 30 and November 1 how many drive notes are still unsent.
- **Reservation drive:** the CSV loader (also on People), everyone in the drive by state (not yet written, note ready, sent, replied, reserved), days left to November 2, reservations and referrals recorded, and the channel entries they produced.
- **Apply to these first:** on Today (one line each), at the top of the Money map (every component), and in the daily email: the five open programs worth the most per founder hour, with what the agents have already prepared for each.
- **Beta families:** the family journal (Bao enters each family and logs first call, second call, a relative contributing, photo uploads, issues), the measured retention numbers with their denominators, and the metrics inbox.
- **What families say online (Deals & campaigns):** this week's themes with thread counts, two quotes each with links, what people tried, their objections, what they say they would pay and the words they use, plus how each theme moved since last week and a "Research now" button. The field-day card shows the objections to expect beside the script. The Scouts page has the card and its schedule.
- **Pitch Lab:** program editions, with the Coach scorecard, hard questions with suggested answers, the timed script and the slide plan.
- **Each application page:** answers with Fact Guard and Voice notes, plus the Coach's scorecard for the whole set.
- **Founder profile (under Company):** the vault Bao fills once. Every save re-runs the Form Filler over the applications whose forms were read; the page says how many answers it filled.
- **Agent activity:** the assembly line, live: what each agent is doing and every item's stage.


## Program edition decks

Each pitch edition gets a real deck at `data/editions/<item>/round-<n>/` (`deck.json`, `slides/`, `manifest.json`). Bao opens it at `/edition/<item>`: every slide at half size, with Slide QA's notes numbered on the slide (animated with GSAP, which honours reduced motion). "Download the deck files" gives a zip with the Slides files and the images, ready to publish as a Slides deck. Editions made before Edition Builder existed get a "Build the deck" button. The core deck's images live in `seed-data/core-deck-*/assets/`, so editions and QA work without claude.ai. Slide QA turns off with `FOUNDER_OS_SLIDE_QA=off` and skips itself, with a note, when no browser is installed.


## Product desk (Phase 1 of the C-suite plan)

`founder_os/product_desk.py` holds three small parts. The **beta family journal** (`beta_families`, `family_events`) is filled by Bao only; nothing is seeded. The **retention tracker** is pure functions over those events: second-call rate (families with a second call / families with a first call), relatives contributing, and calls that followed a contribution, each with its numerator, denominator, date range and source. A rate with an empty denominator stays empty, never zero. **Metrics intake** is read-only: Bao saves a CSV export into `data/metrics-inbox`, picks the provider on the Beta families page, and every imported number is stored with the file name, its SHA-256 and its day (`metrics_sources`, `metrics_points`). The same file is never imported twice. API pulls are a stub (`api_pull`) that only reports whether a key exists under `AStoryFounderOS:Metrics:<provider>` in Windows Credential Manager; it never reads the key into the app or the database. Fact Guard reads the measured facts through `PitchLab.facts()['measured']`.

## Money per hour (apply to these first)

`founder_os/money_ranker.py` ranks every open, not-yet-applied program by expected money per founder hour. The function is pure over the hunter's analysis: cash prize maximum (or credit face value at 25 percent) x a win likelihood from the fit score (fit above 40 scaled to a 60 percent ceiling, halved while eligibility is unknown) / estimated founder hours (3 when the hunter has none) x an urgency factor for programs closing within 14 days (up to 2x on the closing day). Applied, expired, closed, skipped and ineligible programs are left out; programs with no published amount are listed as unranked. The result is labelled an estimate everywhere it appears. Each cycle the autonomy worker takes one preparation step for the top five, in rank order: read the official form (Form Reader), queue the Application Drafter when answers are missing, or start a Pitch Lab edition for a pitch competition with the minutes the program states (3 by default). It never submits. Bao sees the list on Today, the Money map and the daily brief, with each program's preparation state and what the agents will do next.

## Customer Voice Scout (what families say online)

`founder_os/customer_voice.py` runs a read-only public-web job every Thursday at 8:15 Eastern (through the scout registry, so the Scouts page shows its schedule and a Run now button) and whenever Bao presses "Research now" on the Growth desk. It reads public threads where adult children and caregivers talk about a parent's stories, memory, aging and gifts, and returns themes counted by thread (not by comment), one or two short quotes per theme with the thread's URL, what people tried and what they said about it, the objections, what they say they would or did pay, and ten to twelve phrases families use. A quote without a URL is dropped on save; a run with no web activity is rejected and saves nothing. Each run is one row in `customer_voice` with its run date, ISO week, report, sources and queries, so `compare` can say which themes are new, gone, up or down against the newest run from an earlier week. `for_agents` gives Pitch Tailor and Pitch Coach the themes with counts and two quotes each, labelled as evidence about the market; `for_field_day` gives the Campaign Planner and the field-day card the top objections (each with a quote and URL) and the words. Nothing here is a fact about A Story: Fact Guard still blocks every number from it unless the number sits inside a quotation and one of the scout's source URLs is in the same text (rule `cited`, severity info).

## Reservation drive (October 2026)

`founder_os/reservation_drive.py` runs the $1 reservation push to the leads and beta families before November 2, 2026. The people come only from Bao's CSV (header row: name, email, context, kind, with kind Lead or Beta family); nothing is invented. The loader skips a repeated email, enrolls someone already in People instead of copying them, and tags each member in `drive_members` with the campaign key `reservation-2026`. Every member is a Customer contact due today, so `Growth.poll` queues one follow-up draft per worker cycle through the existing Follow-up drafter; `drive_task` swaps in the drive's task text (lead note, lead reminder after a send, beta thank-you with one referral ask) and the draft then goes through Fact Guard and Bao's Voice like any growth draft. The page at `/drive` shows each note; "I sent it" logs the touch and retires the draft, "They replied", "They reserved" and "They referred someone" record the outcome on the person and add a `channel_entries` row (email, 1 purchase at $1; referrals, 1 signup) for the current week with source `reservation_drive`, so channel math and Fact Guard see the drive. Today carries notes ready to send any day and the unsent count on October 26, October 30 and November 1; the generic follow-up alert leaves drive members to those nudges. Nothing here emails anyone.
