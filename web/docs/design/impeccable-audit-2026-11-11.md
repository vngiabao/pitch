# impeccable audit · web/src/App.tsx (Founder OS Today, Nov 11, 2026)

**Run by name:** `Skill impeccable "audit web/src/App.tsx"`. The evidence comes from Assessment B's in-page measurements (two rounds), a code read, and `impeccable detect` (0 findings).

| Dimension | Score | Findings |
|---|---|---|
| Accessibility | 3 | AA contrast or better everywhere: muted 7.68:1, red 5.96:1, brass 6.53:1, white on navy 15:1. Reduced-motion paths exist for the ring, the press and the skeleton. Focus-visible rings on every link and button. **Gaps:** no heading structure, and the day axis was announced cell by cell. |
| Performance | 3 | One CSS keyframe on a 56px SVG; transitions on named properties only; a 90KB gzipped JS bundle. Seven shadcn components are installed and five are used. |
| Theming | 3 | Every colour is a token (the tweakcn The Turn theme, plus money and deadline tokens); App.tsx has no raw colours. Light only by choice: the dark switcher was removed because it inserted an inline style the CSP blocks. |
| Responsive | 3 | 44px targets; no overflow from 375 to 2560px; the phone gets its own strip layout and short figure forms; the nav wraps instead of hiding. |
| Implementation integrity | 4 | The detector finds 0. Real data only, and nothing invented. |
| **Total** | **16/20, Good** | |

**Passed to `polish`:**
- P2: heading structure. **Fixed:** a screen-reader h1 "Today", and h2s for the three regions.
- P3: hide the decorative day axis from screen readers. **Fixed:** `aria-hidden`; the deadline markers carry name, prize and date in their labels.
