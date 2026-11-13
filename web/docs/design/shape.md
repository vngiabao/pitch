# impeccable shape · Founder OS Today (restart, Nov 9, 2026)

The discovery answers come from Bao's approved philosophy (DESIGN.md top, "Yes, both picks", Nov 9). Nothing here is newly asked of Bao. The direction is open: Bao picks it at gate 3.

1. **Job and audience.**
   - **Who:** Bao, alone, at a desk in Edge on a large display, most mornings and a few times a day. Mode: Operate.
   - **The need:** know in seconds what needs Bao today, by when and for how much, then reach it in one click.
2. **Outcome and proof.**
   - **Primary action:** start the one next step, today "Continue application" for Duquesne (up to $30,000, closes Nov 15).
   - **Success:** within 5 seconds Bao can say what, by when and for how much, without scrolling at 1366x650.
   - **Product truth no template has:** the next step is computed from money, deadline and how many answers are ready. Every figure is real data.
3. **Selected direction.** Open: three structurally different candidates for Bao (A Workbench, B Open record, C Fortnight). The focal moment in every candidate is the next-step panel. The implementation is shadcn/ui with The Turn theme via tweakcn, plus animate-ui.
4. **Scope and boundaries.**
   - **Scope:** Today only at this gate. The department pages follow the picked direction's shell.
   - **Untouched:** the logic and data (the six departments, the next-step choice, the research-failure cause, closed programs hidden, load-failure states).
   - **Anti-goals:**
     - poster type and sentences that state counts
     - a dashboard of equal tiles
     - beige pages with underlined links
     - disclaimers
5. **States and ranges.**
   - **Next step:** 0 or 1 at a time. "Nothing needs you" is a real empty state, and "Part of your work didn't load" is a real error state.
   - **Tasks left:** 0 to 30 (show 5, then "N more").
   - **Later moves:** 0 to 3.
   - **Deadlines in the next 3 weeks:** 0 to about 6.
   - **Figures:** 3.
   - **Research:** running, stopped (cause known) or last run on a date.
6. **Interaction and layout.**
   - The next step is the largest panel on the first screen at both sizes.
   - Every item leads with a visual of its own state: a ring for answers ready, a marker for a deadline, a bar or spark for a figure.
   - Text runs in three levels: the name, one line, then the detail.
   - Buttons never sit beside wrapping text.
   - Keyboard: J and K in lists, and Ctrl K for search.
   - The phone gets its own layout (DESIGN-TASTE: web and phone built separately).

## Zone maps (first screen, 1366x650; 1920x880 adds width, not new zones)
| Direction | Zones in reading order (share of the first screen) |
|---|---|
| A Workbench | Department rail on the left (19%, 256px) · header (9%) · next-step panel (about 45%: ring and title, 3 fact tiles, 5 task rows, button) · right column (27%): After that, figures, research |
| B Open record | Department tabs on top (9%) · ranked list on the left (about 45%: 8 rows, then a figure strip at the foot) · open record on the right (about 46%: title, 3 fact tiles, tasks, button) |
| C Fortnight | Department tabs (9%) · 3-week deadline strip across the full width (about 22%, markers sized by prize) · next-step panel on the left (about 46%) · department tiles on the right (about 23%) |

7. **Constraints and open decisions.**
   - **Constraints:** Bao's calls of 16, 20 and 14px; CSP style-src needs one narrow change for the injected styles of shadcn parts; Switzer is self-hosted.
   - **Open, for Bao:** which direction.
