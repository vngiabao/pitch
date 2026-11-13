---
name: A Story Founder OS - Front Office
description: Bao's private work tool on pitch.gbaonvo.com. Six departments by purpose in a navy directory, a morning brief on Today, one family (Switzer) on The Turn palette.
colors:
  navy: "oklch(27.1% 0.080 252)"
  navy-2: "oklch(32.9% 0.093 254)"
  navy-3: "oklch(38% 0.085 254)"
  ink: "oklch(27.1% 0.080 252)"
  muted: "oklch(40.0% 0.026 251)"
  paper: "oklch(95.9% 0.013 87)"
  paper-2: "oklch(92.3% 0.021 86)"
  soft: "oklch(98.0% 0.010 87)"
  brass-text: "oklch(48.0% 0.092 78)"
  maize: "oklch(82.5% 0.120 86)"
  urgent: "oklch(43.5% 0.129 33)"
  good: "oklch(47.8% 0.083 157)"
typography:
  display:
    fontFamily: "'Switzer', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "4.5rem"
    fontWeight: 500
    lineHeight: 1.02
    letterSpacing: "-0.03em"
  heading:
    fontFamily: "'Switzer', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  lead:
    fontFamily: "'Switzer', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  body:
    fontFamily: "'Switzer', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.55
  small:
    fontFamily: "'Switzer', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  mark: "4px"
  field: "10px"
  panel: "14px"
  pill: "999px"
spacing:
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  8: "32px"
  10: "40px"
  12: "48px"
  16: "64px"
components:
  button-primary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.soft}"
    typography: "{typography.small}"
    rounded: "{rounded.pill}"
    height: "44px"
  department:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.soft}"
    typography: "{typography.lead}"
---

# Design philosophy (restart, Nov 9, 2026) · APPROVED by Bao, Nov 9, 2026: "Yes, both picks"

Bao, Nov 9: "why others website looks like it's 10k usd while mine looks like it's from 2009". The Front Office look below is retired. Its logic is kept: the six departments by purpose, the next-step logic, the research-failure cause, closed programs hidden and honest load-failure states. The screens get rebuilt from this philosophy.

**1. Audience.** Bao, alone, at a desk. Microsoft Edge on a large display, often zoomed out, at window sizes from 1366 to 2560 wide. Bao opens it most mornings and a few times a day after that. Bao knows the company in depth, but doesn't remember what changed since the last visit, and doesn't want to hunt for it.

**2. Job: decide fast.** In the first few seconds Bao should know what needs him today, by when and for how much money, then get to the right department in one click and do it. Reading long text is the exception: it happens inside a task (an answer draft, a pitch), never on an entrance page.

**3. Feeling: premium for a work tool.** For this audience and job, premium means:
- **Precise:** every edge on one grid, every number aligned, nothing approximate or decorative.
- **Calm:** neutral grounds, one accent, and colour only where it carries a meaning. Nothing shouts except the one next step and a real deadline.
- **Dense:** a lot of state visible at once, set in quiet type, like Linear's issue list or Stripe's dashboard. It is not a poster, and not a pile.

Premium here does not mean luxury goods, big serif display type, or warm ornament.

**4. The philosophy in one paragraph.** Founder OS should feel like the cockpit of a well-run company. Bao sits down and the instruments are already reading: what needs him, what's waiting and what's broken. Each instrument sits in its own panel on one grid. The type is small enough to show a whole morning's state at once and large enough to read without effort. The single next step is the one loud thing. It's built on a real component system, so every button, table, panel and menu behaves the same everywhere.

**Decisions, each with the product that shows it** (step 2's research board will add saved screenshots):
| Decision | Direction | Shown by |
|---|---|---|
| Foundation | shadcn/ui components with a tweakcn theme from The Turn colours and Switzer, plus animate-ui for motion. No hand-rolled buttons, panels or tables | Vercel and Linear (both built on primitives) |
| Type | Switzer (Bao's Nov 4 pick), 4-5 sizes far apart, weights 400/500/600, tighter tracking on headings, tabular figures. No poster sizes: the current 72px display goes | Linear, Stripe |
| Colour and material | Near-neutral grounds toned toward The Turn paper, navy as the one accent, brass for money only, red for deadlines only. Panels with a 1px low-opacity border, one small radius and at most one soft shadow | Stripe, Attio |
| Density | Lists and tables over cards. State shown as status dots, progress bars and small inline charts, never as sentences | Linear, Attio, Superhuman |
| Shell | A fixed app shell with content panels on one grid. Where the navigation sits is decided by step 3's three directions | Linear, Notion home |
| Motion | Fast and quiet (150-200ms), on state changes only, through animate-ui. Nothing moves to decorate | Superhuman, Linear |
| Imagery | None. Bao's own data is the picture | Stripe dashboard |
| Ground (added Nov 11, the Brain check) | One ground family: a quiet dot grid (GROUNDS.md #18, "blueprint or dot grid for a builder's tool") on the page shell only, behind the panels. Its job is to separate the shell from the work panels so the division of the screen reads at a glance. Panels stay solid card colour: no texture inside any panel, under any text or chart | Linear, Vercel dashboards |
| Home screen (Bao's pick, Nov 11: "2 · Outbox wall") | Founder OS opens on a home screen, not on Today: a GPT render of the company's applications as a paper model of an outbox wall (sealed letters waiting, brass-sealed letters accepted, one navy envelope in progress), a greeting, one live line and one button, "Open today". The picture is impressionistic; live numbers stay in type. One arrival moment, once, under about 600 ms. No logo mark: the name in type | Serial Startup home (Bao's reference: "brainstorm like it, not copy") |
| Voice | Plain and short, in sentence case, and in Bao's words (WRITING-VOICE). No disclaimers, no formulas on a first screen | Superhuman |

**Desktop first (Bao, Nov 11, 2026):** "care less about phone app design for now". Design and review at 1366, 1920 and 2560 first. At 390 the page only has to hold: no sideways scroll, nothing unreadable. No rounds spent on phone layout.

**5. Where Bao's taste bends it, and where it must not.**
- **Bends it:** warmth through The Turn palette (paper, navy, brass) instead of cold SaaS grey. Readability above the SaaS norm.
- **Must not override:**
  - Bao's love of showing more must not become a pile. Each screen still has one obvious next step.
  - The warm palette must not slide back into the "2009" look of beige pages with underlined links. Surfaces and controls come from the component system.

**Bao's calls (Nov 9, 2026, "Yes, both picks"): A = 16px list and table rows, 20px reading text, 14px labels only. B = React + shadcn/ui built with Vite, served by the same server, one narrow style-security change, tweakcn theme from The Turn and Switzer, animate-ui for motion.**

The options as asked:
- **A. Reading size versus density.** Bao's floor is 20px reading text on desktop, while premium work tools run lists at 14-15px.
  - **Recommend:** 16px for list and table rows (inside Bao's "secondary 16px+"), 20px for any sentence Bao reads, 14px only for labels.
  - **Alternative:** 20px everywhere, which is less dense.
- **B. Foundation.** shadcn/ui needs React. Founder OS is plain JavaScript on a Python server with a strict security policy.
  - **Recommend:** a React + shadcn front end built with Vite into static files that the same server serves. Same origin, so the script policy holds. One narrow change is needed: allowing the small style blocks some shadcn parts insert.
  - **Alternative:** a framework-free component library (Web Awesome). It needs no build step but looks less like the products Bao named.

# Design System: A Story Founder OS - Front Office (retired Nov 9, 2026: kept only as the record of the logic)

Approved by Bao on Nov 4, 2026 ("Build 2 Front Office"; DESIGN-APPROVED.md). Typeface picked by Bao from three specimens on the real Today page ("B · Switzer"). Bao's same-day rulings: "Keep The Turn colours. Spread the type scale, move the research banner under the next step, and replace the to-do counts." This replaces Bookbound (retired Nov 4: "the book bound right now does not work").

## Overview

A front office for one busy founder. Bao should always know where to go and what to do next.
- **Departments by purpose come first, each with sub-tabs.** A permanent navy directory on the right lists Today, Funding, Pitch, Customers, Company and Agents. Each has a one-line purpose and its next thing in words ("Next: Duquesne New Venture Challenge", "Research stopped Oct 26", "All facts confirmed"). There are never counts.
- **Today is a brief:** one sentence of state, the next step as the largest thing, the research banner under it, at most 3 moves, and on wide windows up to 4 numbers.
- **Every department page** opens on what needs Bao, biggest first. Its tools follow.

## The system (Bao, Nov 4: "the system before the screens")

**Fonts: one family.** Switzer (Indian Type Foundry, self-hosted from `founder_os/ui/fonts/`, licence noted in `switzer-LICENSE.txt`) at 400 for text, 500 for titles, and 600 for emphasis and buttons. There's no second face; money, labels and navigation all use Switzer. Mona Sans and Brygada 1918 stay in the folder but are not loaded.

**Type scale: five sizes, spread far apart.** At a 1366 window; the root grows from 16px to 20px by about 1700px wide, and wider windows add columns instead.

| Step | Token | Size | Job |
|---|---|---|---|
| display | `--text-display` | 72px (phone 44) | Today's next step |
| heading | `--text-2xl` | 44px (phone 32) | Department names, page titles |
| lead | `--text-lg`, `--text-xl` | 30px (phone 24) | Today's state sentence, section titles, money in the lead |
| body | `--text-base`, `--text-md` | 20px (phone 18) | Reading text and item titles |
| small | `--text-sm`, `--text-xs` | 16px | Secondary lines, labels, buttons, tabs |

Nothing is under 16px. Older token names map onto these five, so no text sits between two steps. Sentence case throughout; the only letter-spaced capitals are the A STORY wordmark.

**Colour: The Turn, every colour with a job.**

| Colour | Job |
|---|---|
| paper, paper-2, soft | Page ground, hover ground, raised surfaces |
| navy, navy-2, navy-3 | The directory, primary buttons, the selected department |
| ink (= navy) | All headings and text |
| muted | Secondary text (40% lightness, so it never reads faint) |
| brass-text | Money and figures |
| brass (The Turn #b58420) | Fine rules, the active deal or scout outline, checkbox marks, focus rings |
| rail-text, rail-quiet, rail-line | Text, quiet text and dividers on the navy directory |
| urgent-on-navy | A failure named inside the navy directory ("Research stopped Oct 26") |
| maize | The selected department's underline, the next thing in the directory, the arrow capsule |
| urgent, urgent-wash | Failures and deadlines within a week |
| good, good-wash | Done, accepted, all clear |

**Grid and spacing.** The work column is on the left (max 96rem) and the directory on the right (22.5rem; 18.75rem under 1100px). On a phone the directory becomes a full-screen panel behind a Departments button. Spacing scale: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64. Every touch target is at least 44px.

## Highlight key (Bao, Nov 4: "Design for how people see")
One meaning per channel, the same on every page. No colour or bold without a meaning.

| Channel | Means | Example |
|---|---|---|
| **Bold** (600) | The thing to do, or the item's name | "**Zip code**", "**Emergent Ventures**: 12 of 36 answers ready" |
| Brass, semibold | Money | "Up to $30,000" |
| Red (urgent) | A deadline within 14 days, and nothing else (Nov 9 audit: one channel, one meaning) | "Closes in 6 days · Nov 15" |
| Quiet panel, bold ink | A failure Bao should know about but can't fix with a click | "Research stopped Oct 26." on paper-2 |
| Ink figures | Counts and progress numbers (brass is kept for money only) | "Applications waiting on results 7" |
| Green (good) | Done, accepted, all clear | "Accepted", "You're all caught up" |
| Maize (on navy) | Where you are, and each department's next thing | the selected department, "Next: …" |
| Muted | Context you can skip | sources, past dates, "Nothing is ever submitted for you" |

**Order is priority:** the state sentence, then the next step, then the research banner, then the moves. **Space follows importance:** groups sit further apart than the items within them. **Five-second test** on every screen: what matters most, what to do, and by when.

## Components
- **Directory department:** name at lead size, then the purpose at small, then the next thing at small in maize (urgent tone for failures, calm for all clear). The current department has a navy-3 ground and a maize underline under its name.
- **Department chrome:** the department name at heading size, its purpose at body size, then the sub-tabs (48px, with a navy underline on the current tab).
- **Lead:** a 4px navy rule, the title at display size, money (brass, semibold) with the deadline (red within 14 days), the count of answers ready, then one line per task in bold (five in view), and the primary button with the maize arrow capsule. On department pages it's a compact band.
- **Moves and to-do rows:** a title, an optional detail line, and one button each.
- **Alert:** the urgent wash with one sentence and its fix inline.
- **Where things stand:** a plain list of up to 4 labelled figures, never stat tiles.

## Motion
One motion: the phone directory fades and rises 8px over 220ms with `cubic-bezier(.23,1,.32,1)`. Under reduced motion it becomes a 120ms fade. Close is instant (emil-design-eng review, Nov 4). Buttons scale to .97 on press.

## Never
- Counts in navigation, stat tiles, formulas or scores on a first screen.
- A second typeface, or a size between two steps.
- Coloured side-stripes or thick accent borders on rounded cards, shadows, gradients, glass.
- The same program twice on one screen.
