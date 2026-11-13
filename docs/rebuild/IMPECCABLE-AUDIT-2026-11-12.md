# impeccable audit: the rebuilt screens (`web/src/pages`), Nov 12, 2026

Run as `/impeccable audit web/src/pages` after the steward's defects were fixed. Diagnostic only. Evidence: headless
Chromium at 1366x650 on all 29 pages (scripts `a11y.mjs` and `targets.mjs` in the session scratchpad), the detector,
and greps. Phone was not audited (Bao: "care less about phone app design for now").

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 3 | No text under 4.5:1 on any page; every input labelled; one `h1` and ordered headings on every page; `lang` and one `main`; focus-visible on links, buttons and summaries. Gap: keyboard order and screen-reader output were read from code, not exercised |
| 2 | Performance | 3 | One 669 KB script (all 29 pages load eagerly), 73 KB CSS, 3 fonts at 17-20 KB, the Home picture 145 KB with width, height and `decoding="async"`. No layout-property animation, no `will-change`, one small `backdrop-blur` on the header |
| 3 | Theming | 3 | Tokens only (0 raw hex in components); colour key held. The app is light-only by design; the `.dark` tokens from the shadcn preset are present but unused and unchecked |
| 4 | Responsive | 3 | No sideways scroll at 1366, 1920, 2560; every link and button in `main` is 44px or taller (was 24-32px on 5 pages, fixed); primary button above the fold on every page at 1366x650 (Pitch Lab and Families fixed). Phone not checked, by Bao's decision |
| 5 | Implementation integrity | 4 | Detector `[]` on `src/pages`, `src/components/app`, `src/shell.tsx`; one shell, one panel, one row shape, one disclosure, one button system |
| **Total** | | **16/20** | **Good** |

## Findings
| Sev | Finding | Where | Suggested command |
|---|---|---|---|
| P2 | The whole app ships as one 669 KB script | `web/src/routes.tsx` (`import.meta.glob(..., { eager: true })`) | `optimize`: load each page on demand |
| P2 | Dialog and tooltip fades had no reduced-motion path | `components/ui/dialog.tsx`, `tooltip.tsx` | Fixed in this pass (`index.css`: shown at once under reduced motion) |
| P3 | Hand-rolled segmented buttons where `tabs.tsx` exists | `MoneyMap.tsx`, `Pipeline.tsx` | `extract` into one shared control |
| P3 | Unused `.dark` tokens | `index.css` | Remove or check when a dark theme is wanted |
| P3 | Keyboard path and screen reader not exercised | all pages | manual pass before a public launch (`accessibility-review`) |

False readings: links and buttons inside closed disclosures report no text and a size, because Chromium keeps their
boxes; they are named and hidden correctly.
