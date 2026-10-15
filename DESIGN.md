---
name: A Story Founder OS - Bookbound
description: A founder's working book in the owner's gbaonvo identity. Navy bookcloth rail, warm paper, brass figures, and a money table of contents.
colors:
  navy: "oklch(27.1% 0.080 252)"
  navy-2: "oklch(32.9% 0.093 254)"
  navy-3: "oklch(38% 0.085 254)"
  ink: "oklch(24.7% 0.050 251)"
  paper: "oklch(95.9% 0.013 87)"
  paper-2: "oklch(92.3% 0.021 86)"
  soft: "oklch(98.0% 0.010 87)"
  stone: "oklch(87.3% 0.025 83)"
  muted: "oklch(48.0% 0.024 251)"
  brass: "oklch(64.5% 0.124 80)"
  brass-text: "oklch(48.0% 0.092 78)"
  maize: "oklch(82.5% 0.120 86)"
  maize-wash: "oklch(93.5% 0.050 88)"
  rail-text: "oklch(86.3% 0.020 253)"
  rail-quiet: "oklch(70% 0.030 253)"
  rail-line: "oklch(86.3% 0.020 253 / .3)"
  urgent: "oklch(43.5% 0.129 33)"
  urgent-wash: "oklch(94% 0.030 40)"
  good: "oklch(47.8% 0.083 157)"
  good-wash: "oklch(94% 0.030 157)"
  line: "oklch(24.7% 0.050 251 / .13)"
  line-strong: "oklch(24.7% 0.050 251 / .24)"
typography:
  display:
    fontFamily: "'Brygada 1918', 'Iowan Old Style', Georgia, serif"
    fontSize: "2.25rem"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "-0.012em"
  title:
    fontFamily: "'Brygada 1918', 'Iowan Old Style', Georgia, serif"
    fontSize: "1.625rem"
    fontWeight: 400
    lineHeight: 1.2
  body:
    fontFamily: "'Mona Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
  control:
    fontFamily: "'Mona Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 560
  label:
    fontFamily: "'Mona Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
  wordmark:
    fontFamily: "'Brygada 1918', 'Iowan Old Style', Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 400
    letterSpacing: ".14em"
rounded:
  hairline: "2px"
  nav: "8px"
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
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "8px 18px"
  button-secondary:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.navy}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "8px 18px"
  arrow-capsule:
    backgroundColor: "{colors.maize}"
    textColor: "{colors.navy}"
    rounded: "{rounded.pill}"
  nav-link-active:
    backgroundColor: "{colors.navy-3}"
    textColor: "{colors.soft}"
    rounded: "{rounded.nav}"
  tag-review:
    backgroundColor: "{colors.maize-wash}"
    textColor: "{colors.brass-text}"
    rounded: "{rounded.pill}"
  tag-urgent:
    backgroundColor: "{colors.urgent-wash}"
    textColor: "{colors.urgent}"
    rounded: "{rounded.pill}"
  panel:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.panel}"
    padding: "24px"
---

# Design System: A Story Founder OS - Bookbound

## Overview

**Creative North Star: "A founder's working book"**

Founder OS is Bao's private command center at pitch.gbaonvo.com, so it wears his gbaonvo identity ("The Turn"): Michigan navy, warm paper, brass and maize, the open-folio mark, Mona Sans and Brygada 1918. It is an Operate surface. The world lends type, palette, density and one signature move; navigation, tables, tabs and forms stay standard web controls.

The signature move is the **money table of contents** on Today: each program is a contents line, with the name in Brygada, a dotted leader, and the amount right-aligned in brass tabular figures. Below it sit days-left words and a hairline whose length is the time remaining. Cash programs come first, soonest deadline first. Credits are a separate list. Finished programs move to the Applied & tracked list and print faded.

Replaced on October 14, 2026: the inherited Pitch OS teal and Segoe UI system. That system's records, routes, approvals and evidence rules are unchanged.

**Key Characteristics:**
- A navy bookcloth rail with a maize active mark, on a warm paper ground.
- Brygada 1918 (always roman) for page titles, program names and the wordmark; Mona Sans for everything you read or press.
- Tabular brass figures for money. Unknown amounts stay as words.
- Hairline rules and soft paper panels, with no shadows.
- One fixed-scale stage strip on every opportunity: Found, Preparing, Applied, Decided.

## Colors

Restrained-committed: the navy rail owns the left of every screen; paper owns the work area; colour elsewhere does jobs.

- **Navy** (`navy`, `navy-2`, `navy-3`): the rail, primary actions, headings, and the selected navigation surface.
- **Paper** (`paper`, `paper-2`, `soft`, `stone`): page ground, tonal hover, panels and dotted leaders.
- **Brass** (`brass`, `brass-text`): deadline hairlines, focus rings, link underline on hover, and cash figures (`brass-text` for text, 5.9:1 on paper). `brass` itself is 3:1 and never carries text.
- **Maize** (`maize`, `maize-wash`): the active-nav mark, the arrow capsule, the decision count, and REVIEW tags.
- **States**: `urgent` (closing within a week, errors), `good` (eligible, success). Each always sits beside a status word.

## Typography

Two self-hosted OFL faces from the owner's site, served from `founder_os/ui/fonts/`. Brygada 1918 headings are always roman; italic headings are banned. Mona Sans carries body, controls, labels and data with tabular lining numerals. Scale: 2.25rem page title, 1.625rem section title, 1.25rem contents entries, 0.9375rem body, 0.8125rem controls, 0.75rem labels. Body measure is capped near 72ch.

## Layout

A 248px sticky navy rail (216px under 1100px) beside a centred work area (max 1360px, 40px gutters). Today is a two-column contents page (1.75fr and 1fr): the money lists dominate, and the side column holds Waiting on you, Applied & tracked, Latest pitch and Agents. Detail pages are 1.5fr and 1fr. Below 1100px every split stacks. Below 760px the rail becomes a top bar with a Menu button opening grouped two-column navigation; contents lines drop their leaders and stack amount under name; tables become labelled two-column records. There is no horizontal scroll at 320 to 1440px.

## Elevation & Depth

None. Depth comes from the navy rail against paper, soft panels on paper, and 1px hairlines (`line`, `line-strong`).

## Motion

Emil Kowalski rules: `--ease-out` cubic-bezier(.23,1,.32,1) at 140ms for press and 200ms for state. Buttons scale to .97 on press; the arrow capsule moves 3px on hover; toasts fade down 4px. Keyboard actions and navigation are not animated. `prefers-reduced-motion` removes movement and animations.

## Components

- **Buttons:** pills. Primary is navy on paper; secondary is soft with a strong hairline. A primary link that moves you forward carries the maize arrow capsule (`.go .cap`).
- **Contents line** (`.toc-row`): title, leader, figure, then a meta row (days and hairline, eligibility words, status tag) and an optional one-line why.
- **Tags:** pill status words. Review is maize-wash, closing is urgent-wash, eligible is good-wash, and finished is faded.
- **Stage strip** (`.stages`): four equal segments with a 3px top rule. Reached segments are navy and the current one is brass.
- **Panels** (`.section`): soft paper, 14px radius, hairline.
- **Inputs:** soft fill, strong hairline, 10px radius, brass focus ring, brass caret.
- **Browser surfaces:** maize selection, thin stone scrollbars, underline offset 3px.

## Do's and Don'ts

### Do:
- Do keep cash, credits and finished programs in separate lists; credits are never cash.
- Do write unknown amounts, deadlines and eligibility as words.
- Do reference colours and fonts only through the `--color-*` and `--font-*` tokens in `style.css`.
- Do set any per-row CSS value through `style.setProperty`, never an inline `style=""`; the Content-Security-Policy blocks inline styles.

### Don't:
- Don't use italic headings, eyebrows or kickers above headings, or section numbers.
- Don't add shadows, gradients or glass.
- Don't put brass on text, or show a score range as a confirmed score.
- Don't reintroduce the retired teal.
