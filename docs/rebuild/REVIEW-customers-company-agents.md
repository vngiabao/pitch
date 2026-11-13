# Design review: Customers, Company, Agents (bao-design-review, Nov 11, 2026)

Verdict: 5 of 12 pass (growth, memory, activity, run, plans). Shell, panels, type scale and the colour key are
consistent. The failures are content shape and space. Screenshots: `docs/design-concepts/2026-11-12-rebuild/<name>-*.jpg`.

Shared changes already made by the coordinator (use them):
- `PageHead` now aligns its action to the title row (`items-start`).
- `Fact` values are now 20px semibold everywhere (Today's size). Hide a strip of facts when every value is 0.
- `lib/format.ts` has `stamp(v)` ("Oct 26, 9:12 AM", no year inside this year, no zone) and `day(v)` ("Oct 26").
  Use them for every date and time shown on a page; never show a raw ISO date or "EDT/EST".

## Defects, worst first
1. **Press: wall of text and too many buttons.** Every outlet shows its full ~150-word draft open (5,981px page) and
   carries 5 buttons. Fix: each outlet is one `Row` (name, one line, deadline tag, one "Open pitch" action). The draft
   opens in a disclosure or dialog with "I sent it", "Skip" and a "More" for the rest.
2. **Press: a passed deadline leads the list.** Sort by soonest live deadline. Passed ones go to a "Missed" group at
   the bottom and out of the open count.
3. **Profile bug: "Revenue to date" and "Funding raised to date" render as date pickers.** `lib/company.ts:102`,
   `/_dob$|_date$/` matches `*_to_date`. Match only real date keys (`_dob$`, `^date_`, `incorporation_date$`, or an
   explicit list).
4. **Profile: a form wall with no next step.** 29 rows, each with its own Save. Open on "Do next: the facts your open
   applications need" (zip code and phone number are asked for on Today) as a short list with one primary action. One
   Save per panel (or save when the field loses focus). Drop "Not filled yet". Put "Used for" in one line per group
   or the placeholder.
5. **Decisions: space doesn't follow importance.** Two empty panels fill the main column while "Recently decided" is
   squeezed in the side column and cut with "…". When nothing is waiting: one line under the page head, and
   "Recently decided" gets the main column as rows (title, one line, date, tag). Mailboxes stay at the side.
6. **Drive opens on a dead campaign.** Closed Nov 2, 8 zero stats, past reminders, and a primary that invites loading
   people into a closed drive. When closed and empty: one line ("Closed Nov 2. Nothing was loaded."), with the form
   and reminders collapsed behind one disclosure.
7. **Families: empty stats three times, dead column.** With 0 families show one panel: one sentence and the Add
   family form in the main column. Show stats and rates only once there is data. The journal's empty state carries
   an action instead of "with the form on this page".
8. **Scouts: 11 text blocks; the schedule is said twice and may be untrue.** One row or table row per scout (name,
   lands in, last result, next run, Run now), description behind the row. Don't promise a next run the server
   doesn't schedule: check what `/api/scouts` really returns and show "Paused" when runs are off.
9. **Internal names and jargon.** "Fact Guard… with their denominators", "the file's fingerprint", a raw
   `C:\Users\…\metrics-inbox` path, `AStoryFounderOS:Metrics:<provider>`, the `reservation-2026` tag, "the drafter",
   "Feeds Pitch Tailor, the Drafter and the Coach", "Bao's Voice edit.". Rewrite in plain words. Show a folder as a
   copy button with a plain label, not a path.
10. **Monospace is a second font.** `font-mono` in Families, CompanyFacts, Run, People. Use the body face with
    tabular figures; mono only inside a collapsed "Exact run data".
11. (Fixed in the shared `PageHead`.)
12. **Subtitles explain the page instead of stating the state,** several with a reassurance ("nothing here is sent
    anywhere", "You send every note…" on 4 pages, "nothing here is invented"). One state line each ("Nothing
    waiting. 5 facts approved in October."). Say "you send it yourself" once, at the send action.
13. **70ch insets leave a dead strip inside wide panels** (press, people, plans at 1920). Let the inset fill the panel
    and cap only the text line, or move the tag and actions into that strip.
14. **People: the primary is far below the fold; two loose text links.** Put "I sent it" and "Copy message" in the
    item's header row. "Log a conversation" and "Pause follow-ups" become outline buttons or one "More".
15. **Same form on two pages.** The drive loader is on People and Drive. Keep it on Drive; People links to it.
16. **Drive: a note floats on the page ground.** Delete it (it repeats #12) or move it inside the form panel.
17. **Activity: the only primary is a disabled button.** While paused, "See what failed" is the primary and the paused
    state is a line of text. Run rows get a row action or chevron.
18. (Fact size fixed in the shared part.) Hide all-zero strips (families, drive, run "What it found").
19. **Company facts: repetition and ragged columns.** Show a verification date only where it differs from the
    panel's. Fold first and last name behind "Show all". Balance the columns at 1920.
20. **Decisions rows: the date twice, and an em dash.** Strip the date from the title; label the one that stays.
    Replace em dashes at render (" - ").
21. **Dates are verbose and inconsistent.** Use `stamp()` and `day()` everywhere.
22. **Plans: an orphaned meta line and bare counts.** Date on its own line; "6 briefs", "1 issue".
23. **Growth: stale and duplicate rows.** "Do next" lists "26 outreach notes ready" and one of those 26 separately;
    drop the duplicate. Mark the passed holiday campaign closed.

Decision for Bao (not for builders): whether Reservation drive (closed Nov 2, never used) stays as a tab.
