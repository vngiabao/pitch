# Audit and second critique · Founder OS Home · 2026-11-11

Screenshots first, then measured live at 1366x650, 1920x880, 390x844. No project files edited.

## Audit: 15/20 (Good)
| Dimension | Score | Key finding |
|---|---|---|
| Accessibility | 2 | Button's focus outline does not render |
| Performance | 3 | `/api/home`: 92 bytes, 605-997 ms |
| Theming | 3 | Paper colours hard-coded; no dark-safe rule |
| Responsive | 3 | Retry link 153x27px |
| Integrity | 4 | Detector `[]`; coherent, product-specific |

## Findings
**P1 · Focus ring is invisible.** The button holds focus from load (Enter goes in), but with `:focus-visible` true the computed outline is 2px, style `none`: the base Button's `outline-none` wins and `ring-0` removes the ring. Only a 0.67px, 55% navy border shows on a navy button. WCAG 2.4.7. Fix, `Home.tsx` line 78: add `focus-visible:outline-solid`. (`harden`)

**P2 · Hard seam on the picture's right edge** at x = 1265 / 1748 / 2336 (1366 / 1920 / 2560): 50% of rows differ from the paper by 4+ levels, max 49, about 6 darker on average. Left edge clean (max 3). The mask fades the full-width `img` box (0-38px, 1284px+ at 1366), outside the fitted picture (101-1265), so it does nothing. Fix: `mask-size: 179.1svh 100%`, centred, no-repeat. (`polish`)

**P2 · The line still lands late.** Picture done at 653-783 ms; `/api/home` returns at 1236-1300 ms because the server builds the whole dashboard, then trims. Was 1353-1657 ms and 11.1 MB. The moment is about 1.3 s, not 600 ms. Fix: cache the three facts or inline them in the HTML. (`optimize`)

**P2 · Retry target 153x27px** (measured on a clone; failed state not triggered live). Fix: `inline-flex min-h-11 items-center`. (`harden`)

**P3** · Counts start at value minus 3: "2 accepted, 4 waiting" shows for 300 ms. · No preload; the picture waits for 284 KB of uncompressed JS (starts 336-465 ms). · The picture's 5 seals and 7 sealed letters match today's numbers and will drift. · `.dark` would put light text on the light picture.

## Passing
Contrast on picture pixels (1366): label 14.3:1, greeting 14.2, line 14.2 (worst 14.0), red 5.2, button text 15.0. Layout shift 0 (phone line 52px in 54px reserved). One `h1`, `main`, `lang`, alt text. No sideways scroll. Console clean. Image 79 KB. Text edge equals shelf edge (136 and 219px). Not verified: reduced motion (code only), frame timing (pane hidden).

## Critique 2: 33/40 (was 31)
| Heuristic | Was | Now | What moved |
|---|---|---|---|
| 1 Status | 3 | 3 | Line fades in, still 0.5 s after the picture |
| 2 Real world | 4 | 4 | Seals and letters match the numbers |
| 3 Control | 3 | 3 | Same |
| 4 Consistency | 3 | 3 | Label scales, text on shelf edge; seam is new |
| 5 Prevention | 3 | 3 | Same |
| 6 Recognition | 4 | 4 | Same |
| 7 Efficiency | 2 | 3 | Enter goes in from load; 11.1 MB to 92 bytes |
| 8 Minimal | 4 | 4 | Same |
| 9 Recovery | 2 | 3 | Plain retry message; small target |
| 10 Help | 3 | 3 | Same |

5-second test passes. Next: `/impeccable harden`, `polish` (seam), `optimize`, then `polish`.
