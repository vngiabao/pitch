# Ship the rebuilt Founder OS (Home + all 29 screens) to pitch.gbaonvo.com (Nov 12, 2026)

Claude built and tested it, GPT ships it. **This needs Bao's yes for this exact deploy first.** Code only: no
database import, no migration, no data change. This replaces `OPS-BRIEF-today-next-2026-11-11.md`, which was never
shipped and is retired.

## What changed
- Every screen is now the new React + shadcn app (source `web/`, built into `founder_os/ui/next/`). `/` is the Home
  screen (outbox wall picture, greeting, one live line, "Open today"); Today is at `/today`; the 22 list pages and 7
  detail pages keep their old addresses. The old screens are still there behind `?old=1` on any address.
- `founder_os/server.py`: serves the new app on those addresses, `/next/assets/<name>.(js|css|woff2|webp)`,
  `/next/logos/<name>.png`, and `/api/home`. No API payload changed; all 66 POST actions are the old ones.
- `founder_os/slide_deck.py`, `form_reader.py`, `planner.py`: one flag added to the headless Edge launch
  (`--edge-skip-compat-layer-relaunch`). Without it Edge 157 returns an empty page, so slide QA, form reading and PDF
  plans fail on the PC. No effect in the cloud (no browser there).
- `tools/research_worker.py` (PC only, not in the cloud bundle): a broad scan now asks for no more search families than the query limit allows (25 families against a limit of 24 had stopped every scan since Oct 25). Test added in `tests/test_hunter_runtime.py`. No live research run was made.
- Cloud behaviour: `pitch-cloud/cloud_adapter.py` already answers 503 with a plain message for run-now, research,
  read-form, report-now, connect and application-confirm, so those buttons in the new app do nothing harmful in the
  cloud. `build_bundle.py`'s text swaps only touch the old `app.js`; they are harmless now.
- Claude already copied the source into `deploy/cloud-build/pitch/founder_os` (0 files differ) and rebuilt
  `pitch-cloud/app_bundle.py` (checked Nov 12: it holds `ui/next/assets/index-DPeMvMPt.js`, `index-udLYWxJt.css`,
  the picture, 3 fonts, 5 logos and the patched `slide_deck.py`; no database inside).
- Tests: 279 run, 2 failures and 1 error, all known and stale (2 `test_reservation_drive`, the drive closed Nov 2;
  1 module needs `jwt`, not installed on this PC).

## Steps (in `deploy/cloud-build/pitch-cloud`)
1. `npx wrangler@4 whoami` shows gbao.n.vo@gmail.com.
2. `npx wrangler@4 deployments list --name pitch-cloud`: write down the active version id (the rollback point).
3. `npx wrangler@4 deploy`. Leave `workers_dev` false. Stop and report on any Durable Object migration or exports
   conflict.
4. List deployments again and confirm the new version is active.
5. Push to GitHub `vngiabao/pitch`, branch `main`: copy `founder_os/server.py`, `founder_os/slide_deck.py`,
   `founder_os/form_reader.py`, `founder_os/planner.py`, `tools/research_worker.py`, `tests/test_hunter_runtime.py`, `founder_os/ui/app.js`, `founder_os/ui/style.css`, the whole
   `founder_os/ui/next/` folder, `web/` (without `node_modules` and `dist`), `tests/test_assumption_coach.py`,
   `tests/test_product_desk.py`, `DESIGN.md`, `DESIGN-APPROVED.md`, `docs/rebuild/` and this brief. Stage only those,
   commit "Founder OS rebuilt on React + shadcn: Home and all screens", push. Never stage `data/`, databases,
   `.migration-key`, `app_bundle.py` or `deploy/private`. Never force-push.

## Done means
- https://pitch.gbaonvo.com/ shows the home picture, the greeting and "Open today" behind Access; `/today`,
  `/funding`, `/pitch-lab`, `/growth`, `/decisions` and `/activity` each show the new shell with their department tab
  lit.
- `/next/assets/index-DPeMvMPt.js` returns 200 behind Access.
- `/funding?old=1` still shows the old screen.
- The commit SHA is on `vngiabao/pitch` main.

## Rollback
`npx wrangler@4 rollback <version id from step 2>`. No data to undo.

## Don't touch
pitch-free, Access, DNS, routes, other Workers, secrets, Durable Object data.
