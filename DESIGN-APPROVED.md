# Approved design decisions

## Nov 9, 2026 · Gate 3: Today direction picked
- Bao picked **"C+F"**: Fortnight's three-week deadline strip across the top, with Split desk below it (the one job on the left, the company board on the right). Boards: docs/design-concepts/2026-11-09-restart/board.jpg and board-also-drawn.jpg.
- Flagged once: both reviewers ranked the Fortnight strip weakest. The combination keeps it, with the markers sized by prize area and no explainer label. Bao's call holds.
- Next: a C+F comp for Bao's OK, then the shadcn build.

## Nov 9, 2026 · Restart: philosophy approved (supersedes the Front Office look)
- Bao, Nov 9: "why others website looks like it's 10k usd while mine looks like it's from 2009", then "yeah, update from that" (restart the screens).
- Bao approved the philosophy in DESIGN.md (audience: Bao at a desk; job: decide fast; feeling: premium for a work tool, meaning precise, calm and dense) and both recommended calls: **"Yes, both picks"**.
  - **A:** 16px list and table rows, 20px reading text, labels never under 14px.
  - **B:** React + shadcn/ui built with Vite and served by the same Python server, with one narrow style-security change; a tweakcn theme from The Turn colours and Switzer; animate-ui for motion.
- Next gates: step 2 is the research board; step 3 is three structurally different Today directions, and the work stops there for Bao's pick.

# Design approved: Front Office

**Bao picked it on Nov 4, 2026:** "Build 2 Front Office"

Approved direction: idea 2, "Front Office", from the Gate 2 board (`docs/design-concepts/2026-11-04/board.html`). The comps are `2-front-office.html` (Today), `2b-front-office-funding.html` (a department page with sub-tabs) and `2c-front-office-menu.html` (the phone directory).

- **Structure.** A permanent navy department directory: Today, Funding, Pitch, Customers, Company, Agents. Each shows a one-line purpose and a status with a noun ("7 to do", "1 reply", "Failed"). The work area holds the page. On the phone, a Departments button opens the same directory full screen.
- **Department pages.** Purpose first, then sub-tabs under the title. The first tab is what needs Bao, biggest item first.
- **Today.** One line of state, a failure notice with its fix, the next step as the biggest element, then at most 3 moves.
- **Kept from Gate 1** (`docs/design/2026-11-04-CREATIVE-BRIEF.md`): The Turn palette and type, Bao's readability floor, the must-not list, and every existing function.
- **Borrowed, as Claude suggested on the board:** the next step opens in place and brings Bao back, and a change stays marked until seen.

Brainstorm record: `docs/design/2026-11-04-concept-roll.md`, `docs/design/2026-11-04-gemini-research.md`, `docs/gpt/2026-11-04-brainstorm-redesign.md`.

## Home screen (Nov 11, 2026)
- Bao's rule, in his words: "from now on all my website need a good landing screen/motion homescreen/theme loading homepage or whatever before going into the content"; "not need to be a multi second load like my personal website, but at least the home screen doesnt take you to the dashboard of what to do like pitch agent and serial startup rn."
- Reference and method: Serial Startup's paper-model home; "i want you to brainstorm like it, not copy this btw. can ask brain". The logo: "you dont care about that logo too fyi. can scrap it."
- **Bao's pick, Nov 11: "2 · Outbox wall"**, from three scenes shown as pictures (docs/design-concepts/2026-11-11-opening/home-scenes.jpg). Shape brief: web/docs/design/shape-home.md.
- Desktop first: "care less about phone app design for now".
