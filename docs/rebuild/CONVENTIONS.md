# Rebuilding Founder OS pages in the new app: the rules every builder follows

Bao, Nov 11, 2026: "did you only fix the home screen but not the rest? rebuild the rest to this new standard too (can
bypass past rules) and ensure the whole website match this theme". Home and Today are done. Every other page is
rebuilt in `web/` (React 19, TypeScript, Tailwind v4, shadcn) so the whole site is one product.

## What "done" means for a page
1. **Every function of the old page works**, with the same endpoints and payloads (`docs/rebuild/INVENTORY.md` has
   each page's reads, actions, forms and states with file:line; the old source in `founder_os/ui/*.js` is the truth).
   Nothing is dropped silently. If something truly can't be carried over, say so in your report.
2. **It looks and reads like Today** (`web/src/pages/Today.tsx` is the model; screenshot:
   `docs/design-concepts/2026-11-11-today-batch2/1920x880.jpg`). Home: `docs/design-concepts/2026-11-11-home-build/1920x880.jpg`.
3. `npx tsc --noEmit -p tsconfig.app.json` passes and the page opens at http://localhost:8806 with no console errors.

## Files: who owns what
- You own only the files your brief names (your pages under `web/src/pages/` and, if you need one, a data file under
  `web/src/lib/`). Create nothing else. **Never edit** `shell.tsx`, `routes.tsx`, `App.tsx`, `index.css`,
  `components/ui/*`, `components/app/*`, `lib/api.ts`, `lib/format.ts`, `lib/today.ts`, `server.py`, or another
  builder's pages. Other builders are working in this folder at the same time.
- Need something shared that doesn't exist (a helper, a component, a token, a server change)? Don't add it to a
  shared file. Put it in your own file for now and list it in your report under "Shared changes wanted".
- Do not run `npm run build` (it writes the shared output folder while others build). Typecheck only.
- **Routes:** every page file exports `routes` and is picked up automatically (no shared file to edit):
  ```tsx
  import type { PageRoutes } from "@/lib/route-types"
  export const routes: PageRoutes = {
    exact: { "/opportunities": () => <PipelinePage /> },
    prefix: { "/opportunity/": (id) => <OpportunityPage id={id} /> },
  }
  ```
  Use the old app's paths exactly. The coordinator switches the server over to your pages after reviewing them.

## The foundation you build on
- `import { Shell } from "@/shell"`: `<Shell active="Funding" tab="/opportunities" title="Pipeline">…</Shell>`.
  `active` is the department, `tab` the path of the department page that is open. On a detail page pass the parent
  list's path as `tab` and the detail's name as `crumb` (it draws the breadcrumb). The shell sets the document title.
- `import { api, apiOnce } from "@/lib/api"`: `api(path)` is a GET; `api(path, body)` is a POST with the CSRF token.
  Send `{}` for actions with no fields (the server refuses an empty body). It throws `ApiError` with a plain message.
- `import { useLoad, LoadGate, PageHead, Panel, Rows, Row, Tag, Empty, Field, Fact, CopyBox } from "@/components/app/page"`.
  `const state = useLoad(() => api("/api/…"))`, then `<LoadGate state={state}>{(data) => …}</LoadGate>`.
  After an action: `await api(...)`, then `await state.reload()`, then a toast. That is the old app's `boot()` pattern.
- `import { useFeedback } from "@/components/app/feedback"`: `const { toast, confirm, ask } = useFeedback()`.
  - `toast("Saved.")`, `toast(message, true)` for an error. Catch every action's error and toast its message.
  - `await confirm({ title, body, action, danger })` replaces every old `confirm()`. Keep **every** confirmation the
    old page had, in plain words that say what will happen. `danger: true` for deletes.
  - `await ask({ title, label, action, required })` replaces every old `prompt()`.
  - Where the server wants `confirmed: true`, send it only after `confirm()` resolves true.
- `import { money, usd, deadlineLabel, shortDay, dayLabel, readableDate, fmtDay, closingWords, plural, prettyKey, … } from "@/lib/format"`.
  Read the file first; use these instead of writing new formatters.
- shadcn components in `web/src/components/ui/`: button, card, alert, badge, progress, separator, skeleton, tooltip,
  dialog, input, textarea, label, table, tabs, checkbox, native-select. Icons: `lucide-react`, 16px, always beside a
  text label, never alone, never in a tinted tile.
- `ProgramMark` from `@/shell` shows a program's logo (or its first letter) before its name.

## Hard technical limits
- **CSP:** `script-src 'self'; style-src 'self'`. No inline `<style>`, no `dangerouslySetInnerHTML` with styles, no
  libraries that inject style tags. React's `style={{…}}` prop is fine (it sets properties, not an attribute); use it
  only for computed values (a bar's width).
- **No client-side router.** Links are plain `<a href>`; every navigation is a page load, as in the old app. Read
  ids and query strings from `location`. Keep the old URLs, query parameters and `#anchors` working.
- Dates are shown in America/New_York (the format helpers do this).
- Server-rendered pages and files (`/edition/<id>`, `/plan/<id>.pdf`, `/plan/<id>.html`, exports, downloads) stay as
  links that open the server's own page. Don't rebuild or iframe them.

## Testing without harm
- The server at http://localhost:8806 runs on a **copy** of Bao's data. You may open pages there, and you may try
  actions that only change records in that copy.
- **Never call, even to test:** `/api/application-confirm`, `/api/report-now`, `/api/connect-report-email`,
  `/api/connect-inbox`, or any endpoint in INVENTORY sections 1.7 and 6.1 (they start background agents, can send
  email, submit an application, or open windows on Bao's PC). Wire them exactly as the old page did and verify by
  reading the code.
- Use your own tab in the built-in browser (`tabs_create`, then `navigate`); never the tab other agents use. Reset
  any viewport size you set (`resize_window` preset "desktop") and close your tab when done.
- You cannot see your page live while you build (the shared build output is the coordinator's). Typecheck, read real
  responses with curl to get the data shapes right (`curl -s -c ck http://localhost:8806/ -o /dev/null` once for the
  session cookie, then `curl -s -b ck http://localhost:8806/api/...`), and re-read your JSX against the layout rules.
  The coordinator builds, opens every page at 1366 and 1920, and sends you fix notes.

## How a page is laid out (Bao's taste, as rules)
- **Desktop first:** 1366, 1920 and 2560 wide. Phone only must not break (no sideways scroll). Use the width: a
  main column and a side column (`lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]`, `items-start`, `gap-5`) when there
  are two kinds of content; tables and long lists may run full width.
- **Open on what needs Bao.** The first thing on the page is the one next step or the state in one line
  (`PageHead` with a line of at most about 20 words), with the main action as a `size="lg"` primary button. Only one
  primary button per screen. Other actions are `variant="outline"`.
- **Things to do are a list, never a sentence:** each on its own row (`Rows`/`Row`), the thing in semibold, one line
  under it, its action at the right. At most 5 to 7 in view; the rest behind one "Show all N" control.
- **Every region is a `Panel`** with a 20px title. Nothing floats on the page ground. No panels inside panels; inside
  a panel separate with space and the row hairlines.
- **Tables for data** (shadcn `Table`): left-aligned text, right-aligned numbers with `tabular-nums`, a status `Tag`,
  one row action. Wide tables scroll inside their panel (`overflow-x-auto`).
- **Type:** only `text-sm` (14, labels, meta), `text-base` (16, rows and body), `text-xl` (20, panel titles),
  `text-2xl` (24, the page's title or one next step). Weights 400/500/600. Nothing under 14px, ever. Sentence case.
  No letter-spaced capitals. Lines of 45 to 80 characters (`max-w-[70ch]`).
- **Colour means something (the highlight key):** navy `primary` = the action and what's in progress; brass
  `text-money` = money amounts only; red `text-deadline` = a deadline within 14 days or a failure, nothing else;
  green `text-good` = done, accepted, confirmed only; `text-muted-foreground` = secondary text. Never raw colours;
  tokens only. Grounds: page = dot-grid paper (from the shell), panels = `bg-card`, quiet insets = `bg-secondary`.
- **Controls:** every button, link-button, input and select is at least 44px tall (`size="lg"` buttons, `h-11`
  inputs). A button sits beside text only when the text is one or two short lines; otherwise it goes under the text
  on the same left edge. Never a row of more than three buttons: put the rest behind "More".
- **States are designed:** loading (the `LoadGate` skeleton), empty (`Empty`: one sentence and one action), error
  (toast or the gate's retry), success (toast). Disable a button while its action runs and say what is happening
  ("Saving…").
- **Words:** plain and short, in Bao's voice. Buttons say what happens ("Mark as sent", not "Submit"). No jargon, no
  internal names, no disclaimers, no "AI-generated" notes, no em dashes (use a comma, a period, or " - "). Keep the
  old page's wording where it is already plain; fix it where it isn't.
- **Never:** three icon cards in a row, gradients, glows, shadows on things at rest, tinted squares with an initial
  for a person, connector-line steppers, decorative icons, `transition-all`, text under 14px, a wall of text. Long
  explanations go behind one "Read more" disclosure (`<details>`) or one click away.
- **Motion:** none beyond what the components already do. No new animation on these pages.

## Report back (under 300 words)
1. Files written. 2. Path -> exported component for each page (with the `tab` and department). 3. Every old action
and whether it is wired (a checklist). 4. Anything not carried over, and why. 5. Shared changes wanted. 6. What you
tested live and what you only read. Do not claim a check you did not run.
