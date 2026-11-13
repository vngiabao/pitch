# Approved design for this app (Founder OS Today on React + shadcn)

This app is the rebuild of Founder OS's screens. The full record lives one level up in `../DESIGN-APPROVED.md`, `../DESIGN.md` and `../HANDOFF.md`. In short:

- **Nov 9, 2026, philosophy and foundation:** Bao: **"Yes, both picks"**. That approves the philosophy at the top of `../DESIGN.md`, with 16px list rows, 20px reading text and 14px labels, plus React + shadcn built with Vite and served by the same server.
- **Nov 9, 2026, Today direction:** Bao picked **"C+F"**, Fortnight's three-week strip on top with Split desk below it. Comp: `../docs/design-concepts/2026-11-09-restart/g-fortnight-split.html`.
- **Nov 9, 2026, elements:** Bao on the C+F build: **"layout is decent but elements are horrible compared to what we talk so far. if need, as gpt to do direction and design and feed to it"**. Keep the layout and rebuild the elements to GPT's direction (`../docs/gpt/2026-11-09-review-today-elements.md`), merged by Bao's Brain: shadcn Cards, the Switzer 24/20/16/14 scale, uniform timeline markers, 48px task rows, one button system, a company list with Progress, and a 420ms readiness ring.
- **impeccable `shape` brief:** `docs/design/shape.md` (a copy of `../docs/design/2026-11-09-shape-today.md`).

## Motion (Nov 11, 2026)
- **emil-design-eng review:** keep the ring draw (420ms, played once, reduced motion shows the full arc). The press (0.97) and the progress bar (250ms) move on the house curve, cubic-bezier(0.23,1,0.32,1).
- **animate-ui:** its rules were applied, but the `@animate-ui/react` package isn't installed. This screen has no overlay or menu for it to animate: the only motion is one CSS keyframe plus press transitions. `tw-animate-css` stays for shadcn's Tooltip open and close, the one other piece of CSS motion. Install the package when a department page adds a dialog, sheet or menu.

## Home screen (Nov 11, 2026)
- Bao's rule, in his words: "from now on all my website need a good landing screen/motion homescreen/theme loading homepage or whatever before going into the content"; "not need to be a multi second load like my personal website, but at least the home screen doesnt take you to the dashboard of what to do like pitch agent and serial startup rn."
- Reference and method: Serial Startup's paper-model home; "i want you to brainstorm like it, not copy this btw. can ask brain". The logo: "you dont care about that logo too fyi. can scrap it."
- **Bao's pick, Nov 11: "2 · Outbox wall"**, from three scenes shown as pictures (docs/design-concepts/2026-11-11-opening/home-scenes.jpg). Shape brief: web/docs/design/shape-home.md.
- Desktop first: "care less about phone app design for now".
