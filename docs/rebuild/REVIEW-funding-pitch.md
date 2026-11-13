# Design review: Funding and Pitch (bao-design-review, Nov 11, 2026)

Verdict: FAIL with a fix list. The shell, panels, type scale, tokens and the brass/green key hold on every page; the
content inside the panels doesn't yet hold Today's standard. Pass: applications-settings, labitem (with notes),
pitches (with notes). Screenshots: `docs/design-concepts/2026-11-12-rebuild/<name>-*.jpg`.

Shared changes already made by the coordinator (use them; read the files):
- `components/app/page.tsx`: `Disclosure` (the one disclosure style: chevron and text, replaces native triangles,
  bare text toggles and local chevron versions), `useHashScroll(ready)`, `PageHead` aligns its action to the title
  row, `Fact` values are 20px semibold (Today's size; hide a strip when every value is 0).
- `lib/format.ts`: `stamp(v)` ("Oct 26, 9:12 AM") and `day(v)` ("Oct 26"). Use them for every date and time.
- `pages/Today.tsx` now exports `Ring`, `Stat`, `NextStep` and `CompanyRow`; `lib/today.ts` exports `leftForYou`
  (turns an application's unanswered questions into plain tasks: "Zip code", "Phone number", "2 agreements to
  accept") and `loadToday`. Reuse them so the same task looks the same on every page.

## Defects, worst first
1. **Applications: a broken row in Blocked.** A program name wraps to 5 lines in a ~100px column beside a reason that
   wraps 5 more, a meta line and two buttons. Name and reason take the full row width; the one action sits under them
   on the same left edge.
2. **Buttons squeezed beside wrapping text** (applications rows at 1366; pitchlab Lessons with Approve and Reject;
   pitch Version history; funding "After that" login rows). When the text is more than two short lines, the buttons
   go on their own line under it, same left edge.
3. **Applications: two buttons on every row** ("Open answers" + "Re-read the form"; "Open the program page" + "Try
   reading it again"). One row action; the re-read moves to the answers page or a "More" control.
4. **Assumptions: a wall of text, ~8,000px.** Each item: claim, status tag, one line of the cheapest test; the rest
   behind `Disclosure` ("See the full row"). The 18 below go in a table.
5. **The same Duquesne task is shown three ways** (Today; funding; answers with raw scraped labels like "Phone Number
   * Please enter a valid phone number", "Browse FilesDrag and drop files here Choose a file"). Funding's lead uses
   Today's `NextStep`; the answers page labels each unanswered question with `leftForYou`'s plain words, with the
   form's own wording as a muted second line.
6. **Funding: the primary button is under the fold at 1366x650.** Fixed by using `NextStep` (button above the list).
7. **Opportunity contradicts itself:** "Not started…" above a four-part stepper ending "Decided · Accepted", next to
   "100% ready"; all segments navy; Accepted not green. One status line from the latest state, a green Accepted tag;
   no stepper (connector-line steppers are on the never list).
8. **Money map: formula text as body copy** ("$220,000 x 6% likelihood (fit about 53, eligibility unknown, halved)
   / 3 hours assumed, x1.5 …") on 5 rows. Move it into `Disclosure` "How this was figured"; one plain line stays.
9. **Money map: 12 filter chips float on the page ground above ~10 stacked tables (5,875px).** Chips go inside a
   panel as tabs that show one group at a time.
10. **Credits repeats sentences and empty rows.** One table row per credit (provider, value, ends, balance, one
    action), detail behind the row. The right panel's 7 identical "Cost not set · Not covered" rows collapse to one
    empty state plus "Add a cost".
11. **Internal names and file plumbing shown to Bao.** Agent names ("Win Scout", "Pitch Tailor", "the Drafter",
    "Form Filler", "HUNTER", "Fact Guard", "Credits and Perks scouts"); scripts and tools ("Codex",
    "Connect-Report-Email.ps1"); full `C:\Users\...` paths, "[ppt/notesSlides/notesSlide1.xml]", "Version and
    content hash"; "Answers:" and "Voice:" prefixes on titles. Plain words ("the research agent", "the pitch
    review"); paths behind `Disclosure` "Show location".
12. **Red outside the key.** "Needs your login", "No form link", "Form not readable" are red tags. Red is a deadline
    within 14 days or a failure only; use `tone="review"` for "needs you".
13. **Three disclosure styles.** Use the shared `Disclosure` everywhere.
14. **Applications reports: the "Daily reports on" tag stretches the full panel width.** `w-fit`.
15. **Past reports rows are ~73px for a date and "Sent".** Compact rows with an "Open report" action, or a table.
16. **Statuses as raw text** ("PASS", "EDITED", "Decided · Accepted"). Use `Tag` (green for done).
17. **The primary button points at the wrong step.** Answers: "Mark submitted" is primary while 9 answers still need
    Bao; make "Open the form" primary until all are ready. Materials: "Search" is primary but outline on pitches;
    make both outline. Pipeline and applications-reports: add a state line.
18. **Too many buttons; "Back to…" repeats the breadcrumb** (pitch: 7 buttons; material: 3 in the header). Drop the
    "Back to" buttons; secondary actions behind one "More" `Disclosure` or menu.
19. **Pipeline's Value column switches type** (a 16px sentence where there is no amount; brass money elsewhere; "About
    1 hours"). "Value unknown" in the value slot, the sentence at 14px muted below; fix the plural.
20. **Funding "After that" rows are sentences** with no program mark. Reuse Today's `CompanyRow` (mark, name,
    progress bar, "12 of 36 ready").
21. **Applications: two tab rows in two styles.** Its sub-tabs use the same segmented control as Pipeline's views.
22. **Opportunity "Your call" repeats the row title on the button** ("Watch / Watch"). Link rows with a chevron, or
    two buttons plus "More".
23. **Disclaimer lines:** "Evidence for review, not a company fact until you confirm it" (material), "Drafts here are
    earlier wording, not approved answers" (materials), "A pool size is not your award" (funding). A one-word tag
    ("Draft", "Unconfirmed") or cut.
24. **Em dashes in generated labels** ("What do you do in detail? — 2,500 characters"). Use " - " or a muted count.
25. **Duplicate rows read as bugs** ("AssemblyAI Startup Program" twice; "Claude Startups" in two groups; each saved
    answer twice; "general" vs "General"). De-duplicate in the page's data mapping, or show the cycle or date that
    tells them apart.
Also from screen-check: lines of 86-111 characters on funding, money, assumptions, pitches. Cap reading text at 70ch.
