// Data for the three Funding pages (Needs you, Pipeline, one program), ported from the old app so the rebuild
// changes the look, not what Bao is told: app.js doNext / fundingItems / leadCard / leftForYou / tocRow / rows /
// dedupe / date / benefits / stageStrip, and scouts.js winSection.
/* eslint-disable @typescript-eslint/no-explicit-any */

import { api, apiOnce } from "@/lib/api"
import { cleanName, closingWords, day, dayLabel, isClosed, money, plural, prettyKey } from "@/lib/format"
import { leftForYou, type Lead, type Task } from "@/lib/today"

export type Access = { level: string; label: string; detail: string }
export type AppRow = {
  application_id: string; opportunity_id: string; program: string; questions: number; answered: number
  url?: string | null; access: Access
}
export type Opp = any
export type Tracked = {
  opportunity_id: string; application_id: string | null; canonical_name: string; outcome: string
  occurred_at: string; next_date: string | null; waiting: boolean
}

// ---------- words shared by the three pages ----------

export const cycleLabel = (c?: string | null) => (!c || c === "unknown" ? "" : c === "rolling" ? "Rolling admissions" : c)

const ACCESS_SHORT: Record<string, string> = { READY: "Answers ready", DRAFTING: "Agent drafting", NOT_CHECKED: "Form not read yet", FINISHED: "Finished" }
const upperFirst = (s: string) => s.replace(/^./, (c) => c.toUpperCase())
export const accessShort = (a: Access) =>
  a.level === "BLOCKED" ? upperFirst(a.label.replace(/^Blocked:\s*/, "")) : ACCESS_SHORT[a.level] || a.label
export const accessWords = (a?: Access | null) => (a ? accessShort(a) : "Not started")
// Colour follows the highlight key: navy = in progress or needs Bao (a form that needs his login is not a failure),
// green = done. Red stays for deadlines.
export const accessTone = (a?: Access | null): "urgent" | "good" | "review" | "quiet" =>
  !a ? "quiet" : a.level === "FINISHED" ? "good" : ["READY", "DRAFTING", "BLOCKED"].includes(a.level) ? "review" : "quiet"

// Program names as written, with " - " where the source used a long dash between words.
export const plainName = (name: string) => cleanName(name)

export const appUrl = (x?: AppRow | null) => (x && x.questions ? `/application/${x.application_id}` : null)

export const outcomeTone = (o: string): "urgent" | "good" | "review" | "quiet" =>
  ["Accepted", "Won"].includes(o) ? "good" : ["Applied", "Advanced", "Finalist"].includes(o) ? "review" : "quiet"

// "Up to $30,000", "Up to $5,000 credits", or that the amount is unknown (old moneyFigure, from analysis.money).
export function moneyWords(d: Opp): { text: string; known: boolean } {
  const m = d.analysis.money
  if (m.cash_max) return { text: `Up to ${money(m.cash_max)}`, known: true }
  if (m.credits_face_value) return { text: `Up to ${money(m.credits_face_value)} credits`, known: true }
  return { text: m.kind === "CREDITS" ? "Credit value unknown" : "Amount unknown", known: false }
}

export const daysLeft = (d: Opp): number | null => d.analysis.scoring.dates.days_remaining ?? null
// Red is for a deadline within 14 days, nothing else.
export const isSoon = (days: number | null) => days !== null && days >= 0 && days <= 14
// The day bar: how much of 60 days is left (old paintDays).
export const daysPct = (days: number | null) => (days === null ? null : Math.max(4, Math.min(100, (100 * days) / 60)))

// The one note a program row carries. (Credit rows used to show a bare priority word, "Cost savings", with no
// label; the panel's own line already says how credits are ranked.)
export function programNotes(d: Opp): string[] {
  return d.analysis.money.kind === "INVESTMENT" ? ["Investment, not a grant"] : []
}

// ---------- Needs you ----------

export type Item = {
  title: string; detail: string; href: string; label: string; external?: boolean
  program?: string; opp?: string; appId?: string; answered?: number; questions?: number; left?: number
  // For the "After that" rows: the program's own name and the one line under it (the title above is a sentence)
  // `dateOpp` names the program whose deadline the row shows when the item has no `opp` of its own.
  name?: string; line?: string; dateOpp?: string
}

// One row of "After that": the program's mark and name, one line, and where it goes. `closing` is set (and shown
// red) only when the program closes within 14 days; those rows sort to the top, soonest first.
export type NeedRow = {
  key: string; name: string; line: string; href: string; label: string; external: boolean
  days: number | null; soon: boolean; closing: string; ready?: number; total?: number
}

// "Deepgram: credits expire Dec 1" -> ["Deepgram", "Credits expire Dec 1"]; a title with no colon is all name.
function nameAndLine(title: string, detail: string): [string, string] {
  const at = title.indexOf(": ")
  if (at < 0) return [title, detail]
  const rest = title.slice(at + 2).trim()
  return [title.slice(0, at), rest ? rest[0].toUpperCase() + rest.slice(1) + (/[.!?]$/.test(rest) ? "" : ".") : detail]
}

// Funding's own to-do list (old doNext with fundingOnly, then fundingItems): applications with answers ready,
// programs closing within a week, forms that need Bao's login, then credit dates and program news.
export function fundingItems(board: any, apps: AppRow[], growth: any[]): Item[] {
  const items: Item[] = []
  const byOpp: Record<string, AppRow> = Object.fromEntries(apps.map((x) => [x.opportunity_id, x]))
  const seen = new Set<string>()
  for (const x of apps.filter((x) => ["READY", "DRAFTING"].includes(x.access.level) && x.questions)) {
    const left = x.questions - x.answered
    seen.add(x.opportunity_id)
    items.push({
      title: left ? `${x.program}: ${x.answered} of ${x.questions} answers ready` : `${x.program}: every answer is ready`,
      detail: left ? `${plural(left, "question")} need${left === 1 ? "s" : ""} you. Copy the rest into the official form and submit.` : "Copy them into the official form, submit, then mark it submitted.",
      href: `/application/${x.application_id}`, label: "Open answers",
      program: x.program, opp: x.opportunity_id, appId: x.application_id, answered: x.answered, questions: x.questions, left,
    })
  }
  for (const d of [...board.cash, ...board.credits]) {
    const n = daysLeft(d)
    if (n === null || n < 0 || n > 7 || seen.has(d.opportunity_id)) continue
    const x = byOpp[d.opportunity_id]
    seen.add(d.opportunity_id)
    const closing = closingWords(n, d.data.dates.deadline)
    items.push({
      title: `${d.data.canonical_name}: ${closing[0].toLowerCase()}${closing.slice(1)}`,
      detail: x ? `${accessShort(x.access)}.` : "The agent has not read this form yet.",
      href: appUrl(x) || `/opportunity/${d.opportunity_id}`, label: "Open", opp: d.opportunity_id,
      name: d.data.canonical_name, line: x ? `${accessShort(x.access)}.` : "The agent has not read this form yet.",
    })
  }
  for (const x of apps.filter((x) => x.access.level === "BLOCKED" && /login/i.test(x.access.label) && x.url).slice(0, 2)) {
    items.push({
      title: `${x.program}: sign in to see the questions`, detail: "The form needs your login, so the agent cannot read it. Open it, sign in and apply.", href: x.url!, label: "Open the form", external: true,
      name: x.program, line: "Sign in to see the questions. The agent cannot read this form.", dateOpp: x.opportunity_id,
    })
  }
  const alerts = (growth || []).filter((x) => /^\/(credits|opportunity\/)/.test(String(x.url || ""))).map((x): Item => {
    if (String(x.url || "").startsWith("/opportunity/")) {
      const name = String(x.title).split(": ")[0]
      return { title: `${name}: research found something new`, detail: "The program page shows what changed.", href: x.url, label: "See what changed", name, line: "Research found something new.", dateOpp: String(x.url).split("/opportunity/")[1]?.split(/[?#]/)[0] }
    }
    const [name, line] = nameAndLine(String(x.title || ""), String(x.detail || ""))
    return { title: x.title, detail: x.detail, href: x.url, label: x.link || "Open", name, line }
  })
  return [...items, ...alerts]
}

// The lead when it is an application with answers left: the same Lead that Today shows, so the same task reads the
// same on both pages (tasks from today.ts leftForYou; four shown, the rest counted).
async function appLead(item: Item, board: any): Promise<Lead> {
  const d = [...board.cash, ...board.credits].find((x: Opp) => x.opportunity_id === item.opp)
  let tasks: Task[] = []
  try { tasks = leftForYou((await api(`/api/application/${encodeURIComponent(item.appId!)}`)).questions || []) } catch { /* keep the counts only */ }
  const dated = tasks.filter((t) => t.label === "Today's date"), shown = tasks.filter((t) => t.label !== "Today's date").slice(0, 4)
  const covered = shown.reduce((n, t) => n + t.count, 0), f = d?.data.funding
  return {
    program: item.program!, href: item.href,
    prize: f?.cash_prize_max != null ? `Up to ${money(f.cash_prize_max)}` : f?.credits_value != null ? `Up to ${money(f.credits_value)} in credits` : "",
    deadline: d?.data.dates.deadline ? dayLabel(d.data.dates.deadline) : "", days: d ? daysLeft(d) : null,
    answered: item.answered!, questions: item.questions!, left: item.left!, tasks: shown,
    more: Math.max(0, item.left! - covered), dateLeft: dated.length > 0,
  }
}

// Any other lead (every answer ready, a program closing, a form that needs Bao's login, a credit date).
export type LeadCard = {
  title: string; body: string; href: string; label: string; external: boolean
  money: { text: string; known: boolean } | null; closing: string; soon: boolean; investment: boolean
}
function otherLead(item: Item, board: any): LeadCard {
  const d = item.opp ? [...board.cash, ...board.credits].find((x: Opp) => x.opportunity_id === item.opp) : null
  const days = d ? daysLeft(d) : null
  return {
    title: item.program ? `Submit the ${item.program}` : item.title,
    body: item.program ? `${item.answered} of ${item.questions} answers are ready. Copy them into the official form and submit.` : item.detail,
    href: item.href, external: !!item.external, label: item.label,
    money: d ? moneyWords(d) : null, closing: d ? closingWords(days, d.data.dates.deadline) : "", soon: isSoon(days),
    investment: !!d && d.analysis.money.kind === "INVESTMENT",
  }
}

export type FundingNeeds = {
  count: number; lead: Lead | null; card: LeadCard | null
  after: NeedRow[]
  cash: { d: Opp; app?: AppRow }[]; credits: { d: Opp; app?: AppRow }[]
  waiting: Tracked[]; decided: Tracked[]; inbox: "none" | "connected" | "connect"
}

export async function loadFundingNeeds(): Promise<FundingNeeds> {
  const [dash, apps, growth] = await Promise.all([
    api("/api/dashboard"),
    apiOnce<AppRow[]>("/api/application-list").catch(() => [] as AppRow[]),
    apiOnce<any[]>("/api/growth-alerts").catch(() => [] as any[]),
  ])
  const board = dash.money_board
  const byOpp: Record<string, AppRow> = Object.fromEntries(apps.map((x) => [x.opportunity_id, x]))
  const days: Record<string, number | null> = Object.fromEntries([...board.cash, ...board.credits].map((d: Opp) => [d.opportunity_id, daysLeft(d)]))
  const items = fundingItems(board, apps, growth)
  const todo = new Set(items.map((x) => x.opp).filter(Boolean))
  const more = (list: Opp[]) => list.filter((d) => !todo.has(d.opportunity_id)).slice(0, 5).map((d) => ({ d, app: byOpp[d.opportunity_id] }))
  const tracked: Tracked[] = board.tracked || []
  const first = items[0], after = items.slice(1)
  const asApp = !!first && !!first.appId && !!first.left
  const deadlines: Record<string, string | null> = Object.fromEntries([...board.cash, ...board.credits].map((d: Opp) => [d.opportunity_id, d.data.dates.deadline ?? null]))
  // Every row has the same shape: the program's mark and name, one line, and (for a draft) "12 of 36 ready".
  const rowOf = (x: Item): NeedRow => {
    const opp = x.opp || x.dateOpp, n = opp ? days[opp] ?? null : null, soon = isSoon(n)
    return {
      key: x.title + x.href, name: plainName(x.name || x.program || x.title), line: x.appId ? "" : x.line ?? x.detail,
      href: x.href, label: x.label, external: !!x.external, days: n, soon,
      closing: soon && opp ? closingWords(n, deadlines[opp]) : "",
      ready: x.appId ? x.answered : undefined, total: x.appId ? x.questions : undefined,
    }
  }
  return {
    count: items.length,
    lead: asApp ? await appLead(first, board) : null, card: first && !asApp ? otherLead(first, board) : null,
    // A deadline within 14 days goes first, soonest first; the rest keep their order (drafts, then the others).
    after: after.map(rowOf).sort((a, b) => Number(b.soon) - Number(a.soon) || (a.soon && b.soon ? a.days! - b.days! : 0)),
    cash: more(board.cash), credits: more(board.credits),
    waiting: tracked.filter((t) => t.waiting), decided: tracked.filter((t) => !t.waiting),
    inbox: !dash.inbox ? "none" : dash.inbox.accounts.some((a: any) => a.connected) ? "connected" : "connect",
  }
}

export const trackedHref = (t: Tracked) => (t.application_id ? `/application/${t.application_id}` : `/opportunity/${t.opportunity_id}`)
export const trackedLine = (t: Tracked) =>
  `${t.outcome} ${day(t.occurred_at)}${t.next_date ? ` · next: ${day(t.next_date)}` : " · next date not published"}`

// ---------- Pipeline ----------

export const VIEWS = ["Recommended", "Apply Now", "Watching", "Applied", "All"]
export const MORE_VIEWS = ["New", "Prepare", "Accepted", "Rejected", "Skipped", "Expired"]
export const viewLabel = (v: string) => (v === "Apply Now" ? "Apply now" : v)
export const FILTER_KEYS = ["type", "min_cash", "deadline_before", "non_dilutive", "effort", "location", "category", "min_score"] as const
export type Filters = Record<(typeof FILTER_KEYS)[number], string>
export const EFFORTS = ["Very Low", "Low", "Medium", "High", "Very High", "UNKNOWN"]
const BASE_TYPES = ["pitch_competition", "grant", "accelerator", "incubator", "startup_program", "credits", "credits_grant", "fellowship", "award"]
export const typeOptions = (dash: any | null) => [...new Set([...BASE_TYPES, ...((dash?.opportunities || []) as Opp[]).map((d) => d.data.opportunity_type)])]

export const pipelineQuery = (view: string, filters: Filters) => {
  const p = new URLSearchParams({ view })
  for (const k of FILTER_KEYS) if (filters[k]) p.set(k, filters[k])
  return p.toString()
}

export type PipelineRow = { d: Opp; others: number; app?: AppRow }

// One row per program name, with a count of its other cycles (old dedupe), and its application if there is one.
export async function loadPipeline(view: string, query: string): Promise<PipelineRow[]> {
  const [items, apps] = await Promise.all([
    api<Opp[]>(`/api/opportunities?${query}`),
    apiOnce<AppRow[]>("/api/application-list").catch(() => [] as AppRow[]),
  ])
  const byOpp: Record<string, AppRow> = Object.fromEntries(apps.map((x) => [x.opportunity_id, x]))
  // Recommended and Apply now never show a program whose deadline has passed.
  const open = ["Recommended", "Apply Now"].includes(view) ? items.filter((d) => !(d.data.dates.deadline && isClosed(d.data.dates.deadline))) : items
  const seen: Record<string, PipelineRow> = {}
  const rows: PipelineRow[] = []
  for (const d of open) {
    const k = String(d.data.canonical_name).trim().toLowerCase()
    if (seen[k]) { seen[k].others++; continue }
    rows.push((seen[k] = { d, others: 0, app: byOpp[d.opportunity_id] }))
  }
  return rows
}

export const programSub = (r: PipelineRow) =>
  upperFirst([String(r.d.data.opportunity_type).replace(/_/g, " "), cycleLabel(r.d.data.cycle)].filter(Boolean).join(" · ")) +
  (r.others ? ` · ${plural(r.others, "other cycle")}` : "")

const TYPE_WORDS: Record<string, string> = { credits_grant: "API credit grant", startup_support: "Startup support program", pitch_competition: "Pitch competition", grant: "Grant", accelerator: "Accelerator" }
// The Value column (old benefits). The value slot always holds an amount or "Value unknown"; what the program
// gives sits under it as a quiet line.
export function valueWords(d: Opp): { main: string; sub: string; amount: boolean } {
  const f = d.data.funding
  if (f.cash_prize_max != null) return { main: money(f.cash_prize_max), sub: f.award_scope || "Award terms need review", amount: true }
  if (f.credits_value != null) return { main: `Up to ${money(f.credits_value)}`, sub: "Credits, depends on the tier", amount: true }
  const text = f.other_benefits || f.award_scope || TYPE_WORDS[d.data.opportunity_type] || String(d.data.opportunity_type).replace(/_/g, " ")
  return { main: "Value unknown", sub: String(text).slice(0, 150), amount: false }
}

// The Deadline column (old date()).
export function deadlineWords(d: Opp): { main: string; sub: string; soon: boolean; quiet: boolean } {
  const dl = d.data.dates.deadline, days = daysLeft(d)
  if (dl && isClosed(dl)) return { main: `Closed ${day(dl)}`, sub: "", soon: false, quiet: true }
  if (dl) return { main: day(dl), sub: days === null ? "Exact time not published" : `${plural(days, "day")} remaining`, soon: isSoon(days), quiet: false }
  return { main: d.data.cycle_kind === "rolling" || d.data.cycle === "rolling" ? "Rolling, no deadline" : "No deadline published", sub: "", soon: false, quiet: true }
}

// "Under an hour", "About 1 hour", "About 3.5 hours" (the old words, with the plural right).
export function effortWords(h: number) {
  if (h < 1) return "Under an hour"
  const r = Math.round(h * 2) / 2
  return `About ${r} ${r === 1 ? "hour" : "hours"}`
}

// The page's one line of state: how many programs, and how many close within 14 days.
export function pipelineState(rows: PipelineRow[], view: string, filtered: boolean) {
  const soon = rows.filter((r) => isSoon(daysLeft(r.d))).sort((a, b) => daysLeft(a.d)! - daysLeft(b.d)!)
  return `${plural(rows.length, "program")} in ${viewLabel(view)}${filtered ? ", filtered" : ""}.` +
    (soon.length ? ` ${soon.length === 1 ? "1 closes" : `${soon.length} close`} within 14 days, the first on ${day(soon[0].d.data.dates.deadline)}.` : "")
}

// ---------- One program ----------

export type Win = { brief: any | null; researching: boolean; checked_at: string | null; runs: number; changes: string[]; seen: boolean }
export type ProgramPage = { d: Opp; app?: AppRow; win: Win | null }

export async function loadProgram(id: string): Promise<ProgramPage> {
  const [d, apps, win] = await Promise.all([
    api(`/api/opportunity/${encodeURIComponent(id)}`),
    api<AppRow[]>("/api/application-list").catch(() => [] as AppRow[]),
    api<Win>(`/api/win/${encodeURIComponent(id)}`).catch(() => null),
  ])
  return { d, app: apps.find((r) => r.opportunity_id === id), win }
}

export const isApplied = (d: Opp) => d.recommendation === "ALREADY APPLIED" || d.outcomes.length > 0

// The one status line, from the latest thing that happened (the old page showed an access line and a stage strip
// that could disagree): a result if there is one, else where the form stands, else not started.
export function statusOf(d: Opp, app?: AppRow): { tag: string; tone: "urgent" | "good" | "review" | "quiet"; line: string } {
  const o = d.outcomes[0]
  if (o?.outcome) return { tag: o.outcome, tone: outcomeTone(o.outcome), line: o.occurred_at ? `Recorded ${day(o.occurred_at)}.` : "" }
  if (app?.access) return { tag: accessShort(app.access), tone: accessTone(app.access), line: app.access.detail }
  return { tag: d.applications.length ? "Preparing" : "Not started", tone: d.applications.length ? "review" : "quiet", line: "The agent has not read this application form yet." }
}

const CREDIT_LABELS: Record<string, string> = {
  provider: "Provider", tier: "Award tier", category: "Usage category", referral_required: "Referral required",
  company_email_required: "Company email required", paid_account_required: "Paid account required", deposit_required: "Deposit required",
  minimum_spend: "Minimum spend", expiration_months: "Expires after (months)", eligible_products: "Eligible products",
  excluded_products: "Excluded products", renewal_behavior: "After credits expire", stacking_restrictions: "Stacking restrictions",
  terms_acceptance_required: "Terms acceptance required",
}
// Credits and their conditions (old creditConditions); null when the program gives no credits.
export function creditConditions(d: Opp): { status: string; known: [string, string][]; unknown: number; note: string } | null {
  const b = d.data.credit_benefits || {}
  if (!b.provider && d.data.funding.credits_value == null) return null
  const known = Object.entries(CREDIT_LABELS).filter(([k]) => b[k] != null)
    .map(([k, l]): [string, string] => [l, typeof b[k] === "boolean" ? (b[k] ? "Yes" : "No") : String(b[k])])
  return {
    status: d.analysis.credits?.cost_status || "Payment conditions need review", known,
    unknown: Object.keys(CREDIT_LABELS).length - known.length,
    note: d.analysis.credits?.value_note || "Credits are restricted benefits, not cash.",
  }
}

// A source's site name; the old page threw on a malformed link, this one shows the link as written.
export const hostOf = (url: string) => { try { return new URL(url).hostname } catch { return String(url || "Source") } }

const APPLIES_WORDS: Record<string, string> = { pitch: "In the pitch", application: "In the application", qa: "In Q&A", demo: "In the demo", materials: "In the materials" }
export const winGroups = (brief: any): [string, any[]][] =>
  Object.keys(APPLIES_WORDS).map((k): [string, any[]] => [APPLIES_WORDS[k], (brief.how_we_win || []).filter((m: any) => m.applies_to === k)]).filter((x) => x[1].length)
export function winRules(brief: any): [string, string][] {
  const r = brief.rules || {}
  const all: [string, string][] = [["Format", r.format], ["Time", r.time_limit], ["Slides", r.slide_limit], ["Q&A", r.qa], ["Audience", r.audience], ["Where", r.where], ["Event", r.event_date]]
  return all.filter((x) => x[1] && !/not published/i.test(x[1]))
}

export { prettyKey }
