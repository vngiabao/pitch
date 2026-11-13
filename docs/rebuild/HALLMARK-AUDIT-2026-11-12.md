# `hallmark audit web/src`: the rebuilt Founder OS (Nov 12, 2026)

Run through the hallmark skill (`audit` verb: `references/verbs/audit.md`, gates from `references/slop-test.md`) on the
final code and the screenshots in `docs/design-concepts/2026-11-12-rebuild/final/`, after the impeccable critique,
audit and polish passes. Audit only: nothing was edited during it. This replaces the earlier file of the same name,
which was greps plus a hand-written list and not a hallmark run (skills-steward, Nov 12).

Context read first: `DESIGN.md` at the project root (a system-managed project, so pages must share the system; the
variety gates 20-21 and 32 are inverted). Genre: modern-minimal (a work tool). Phone gates 34 and 49-53 were not
exercised: phone is out of scope at Bao's word ("care less about phone app design for now").

## Critical (ships as slop)
None. No AI page template (this is an app shell, not hero / 3 features / CTA), no purple-blue gradient or gradient
text (gate 2: 0), no icon-above-heading card grid (3), no nested cards (4), no side-stripe borders (5: 0), no invented
metrics (46: every figure is read from the app's data), no re-drawn chrome (47).

## Major (looks AI-generated)
| Tell | Where | Fix |
|---|---|---|
| Missing system reference (gate 20, `design.md` rule) | `web/src/index.css`, top of file: no `/* Hallmark · ... design-system: DESIGN.md */` stamp | Add the stamp naming DESIGN.md as the system |

## Minor (small taste issues)
| Tell | Where | Fix |
|---|---|---|
| Focus ring fades in (gate 15) | `components/ui/button.tsx` line 7: `box-shadow` is in the 150ms transition list and the ring is drawn as a shadow | Take `box-shadow` out of the transition, or draw the ring as an outline |
| Measure over 75ch (gate 25) | `max-w-[80ch]` in `pages/ApplicationAnswers.tsx:47`, `pages/Decisions.tsx:181`, `pages/Plans.tsx:65`; Material's two columns at 1366 run about 80 characters | Cap at 70-75ch |
| Success toast for a visible effect (gate 16) | 18 messages across `pages/` ("Family added", "Saved") | Kept on purpose: Bao's north star asks for plain confirmation that something saved. One line, no celebration |
| Tooltip hover delay 0 (gate 17) | `components/ui/tooltip.tsx:6` | Unused component today; set 800ms if it is ever used, or delete the file |
| Pure black scrim (gate 7) | `components/ui/dialog.tsx:40` `bg-black/10` | Tint the scrim from the ink token |
| Zero-chroma neutral (gate 22) | `index.css:76` `--primary-foreground: oklch(1 0 0)`; `.dark` borders | Allowed for modern-minimal (pure white on navy); the `.dark` block is unused |
| Off-scale spacing (gate 24) | `components/ui/tabs.tsx:25` `p-[3px]` | shadcn default; unused by the pages |
| Dead scaffold files | `assets/react.svg`, `components/ui/tooltip.tsx` | Delete in a cleanup |
| Instruction subtitles | Pitch Studio ("Choose who you're talking to..."), Applications ("Copy the prepared answers...") | Replace with a state line |
| Raw date in a source title | Pitch editor: "Pitch editorial 2026-10-09" | Format as "Oct 9" |

Clean gates, checked in code: 1 (Switzer, not a default face), 10 `transition-all` 0, 11 hover-scale 0, 12 bounce 0,
14 layout-property animation 0, 19 placeholder names 0, 27 reduced-motion fallbacks present (ring, Home, toast,
dialogs), 30 one icon library (lucide, 26 imports), 33 decorative SVGs all `aria-hidden`, 37 one font family, 48 no
colour or font outside the token block. Checked in the browser at 1366x650: 40-41 no text under 4.5:1 on any of the
29 pages; 36 bars vertically centred; no sideways scroll at 1366, 1920, 2560.

Left as data, not design: the file name "A Story — Investor Deck.pptx"; the saved campaign line "The $1 reservation
closes November 2".

**0 critical · 1 major · 10 minor**

Pre-emit critique: P4 H4 E4 S5 R5 V3 (variety is low by design on a system-managed app).

## After the audit (fixes applied, then the same gates re-checked in code)
- Major closed: `index.css` now opens with the Hallmark stamp naming DESIGN.md as the system.
- Minor closed: `box-shadow` removed from the button's transition list (the focus ring appears at once); the three
  `max-w-[80ch]` caps are 70ch; the dialog scrim is tinted from the ink token.
- Still open (minor, listed for a later cleanup): success toasts (kept on purpose), unused tooltip and tabs
  components and `react.svg`, two instruction subtitles, one raw date in a source title, Material's 80-character
  columns at 1366.
Count after fixes: 0 critical · 0 major · 6 minor. Detector re-run on the final code: `[]`.


## Re-run on the final code (`hallmark audit web/src`, second Skill call, after the last UI edit)
Last edits before this run: Material text as one block per slide in a 1/2/3-column grid; deadline line on
Applications rows; Materials filter grid. Audit only, nothing edited after it.

| Gate | Result |
|---|---|
| 2 gradient text / purple-blue | 0 |
| 5 side-stripe borders | 0 |
| 7 pure black or white base | 0 (`bg-black` gone) |
| 10 `transition-all` | 0 |
| 11 hover-scale | 0 |
| 15 focus ring fades in | closed (`box-shadow` no longer transitions) |
| 20 system stamp | present (`index.css` line 1) |
| 25 measure over 75ch | 0 `max-w-[80ch]`; Material blocks capped at 70ch |
| 26 states / 44px targets | 0 links or buttons under 44px in `main` on all pages measured |
| 40-41 contrast | 0 text under 4.5:1 (29 pages, 1366) |
| 48 colours outside tokens | 0 raw hex in components |
| Text under 14px | 0 |
| impeccable detector | `[]` |

Critical 0 · Major 0 · Minor 6 (success toasts kept on purpose; unused tooltip, tabs and `react.svg`; two
instruction subtitles; one raw date in a source title; hand-rolled segmented buttons on Money map and Pipeline;
unused `.dark` tokens).

**0 critical · 0 major · 6 minor**

## Gates re-scanned after the last edit (Material: slides in number order, page-number lines dropped)
transition-all 0, text under 14px 0, raw hex 0, native details in pages 0, 80ch caps 0, bg-black 0, stamp 1. Detector `[]`. Count unchanged: 0 critical · 0 major · 6 minor.

## `hallmark audit web/src/pages/Material.tsx` (third Skill call, the last-edited file, after its last edit)
Audit only; nothing edited after it. The page was also read in the browser at 1366 and 1920 (deck order, 58 blocks
when expanded, grid tops aligned, no sideways scroll).

| Tell | Where | Severity | Fix |
|---|---|---|---|
| No way back after "Show all the text" (the page grows to about 20,000px) | `Material.tsx`, `Text` | minor | Add "Show less", or keep the preview and open the full text per slide |
| The preview can end on a notes block without its slide | `Material.tsx`, `preview` | minor | Cut the preview on a slide boundary |
| Notes come before their slide | `Material.tsx`, `blocks` sort | minor | Slide first, its notes under it |

Gates checked in this file: 0 `transition-all`, 0 hover-scale, 0 raw colour values, 0 text under 14px, one font
family, 0 italic, 0 off-scale pixel spacing, measure capped at 70ch, 0 em dashes in rendered strings, icons from one
library and `aria-hidden`, both header buttons 44px with states from the shared Button, no invented content (the
text is the file's own), stamp present in `index.css`.

**0 critical · 0 major · 3 minor** (file). Whole app after all fixes: 0 critical · 0 major · 9 minor.

## Not re-audited
`Run.tsx` and `lib/agents.ts` changed after the last hallmark Skill run (a "Fixed Nov 12" note with a 44px link, and the date guard behind it). Treated as small polish: the code gates and the impeccable detector were re-run (`[]`, 0 targets under 44px, 0 text under 14px), bao-design-review and skills-steward looked at both pages; the hallmark Skill was not called again for these two files.

## `hallmark audit web/src/components/app/page.tsx` (fourth Skill call, Nov 12 late, after the two shared fixes)
Scope: the state line under page titles (ink, dates and counts semibold) and `evenBottoms` (near-level panel pairs end on one line). Audit only; nothing edited after it. Read with the screenshots in `docs/design-concepts/2026-11-12-rebuild/final-even/` (28 pages at 1366, 1920, 2560).

| Tell | Where | Severity | Fix |
|---|---|---|---|
| A bolded number that is not a vital | Pitch Lab item line "round **1**"; Pipeline "close within **14** days" | minor | Leave, or pass those lines as nodes with the emphasis chosen by hand |
| Three lines stay instructions, so they gain ink but no fact | Pitch Studio, Applications, Materials | minor (already listed) | Replace with a state line |
| Layout set by script | `evenBottoms` sets a min-height after first paint | minor | Accepted: no CSS can stretch only near-level columns; it runs once per resize, no animation |

Gates in this file: 0 `transition-all`, 0 hover-scale, 0 raw colour values, 0 text under 14px, 0 italic, 0 em dashes, one font family, emphasis by weight only (semibold, tabular figures), the one transition is the chevron's transform with a reduced-motion rule, stamp present in `index.css`. Measured: 0 near-miss panel bottoms, 0 sideways scroll, 0 failed loads on 28 pages at three sizes. Detector `[]`.

**0 critical · 0 major · 3 minor** (file). Pre-emit critique: P4 H4 E4 S5 R5 V3.
