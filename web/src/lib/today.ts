// Today's model, built from the same Founder OS APIs and the same next-step logic as the old screen (app.js doNext,
// leftForYou, customerAlerts, researchCause), so the restart changes the look, not what Bao is told to do.
/* eslint-disable @typescript-eslint/no-explicit-any */

const TZ = "America/New_York"

export async function get<T = any>(path: string): Promise<T> {
  const r = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" } })
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

export const usd = (v: number | null | undefined) =>
  v == null ? "" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v)

export const dayLabel = (iso: string, opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }) =>
  new Date(/^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso + "T12:00:00" : iso).toLocaleDateString("en-US", { ...opts, timeZone: TZ })

// Each program's own mark, fetched once from its site and served by the app (Bao's yes, Nov 11).
// A program with no saved mark gets its first letter instead.
const LOGOS: [RegExp, string][] = [
  [/duquesne/i, "duquesne"], [/techstars/i, "techstars"], [/agentware/i, "agentware"],
  [/runware/i, "runware"], [/free ai/i, "freeai"],
]
export const logoFor = (name: string) => {
  const hit = LOGOS.find(([re]) => re.test(name))
  return hit ? `/next/logos/${hit[1]}.png` : ""
}

const plural = (n: number, w: string, p = w + "s") => `${n} ${n === 1 ? w : p}`

export type Task = { label: string; count: number; profile?: boolean }
export type Lead = {
  program: string; href: string; prize: string; deadline: string; days: number | null
  answered: number; questions: number; left: number; tasks: Task[]; more: number; dateLeft: boolean
}
export type Mark = { day: number; name: string; prize: string; amount: number; date: string; soon: boolean }
export type Row = { name: string; line: string; href: string; tone: "due" | "live" | "idle"; ready?: number; total?: number }
export type Research = { state: "stopped" | "running" | "ok" | "none"; date: string; cause: string; href: string }
export type Today = {
  date: string; lead: Lead | null; marks: Mark[]; rows: Row[]; research: Research
  figures: { accepted: number; waiting: number; cashOpen: number }; partial: boolean
}

const CAUSES: Record<string, string> = {
  "Research budget exceeded": "Each run came back larger than the app allows, so its results were set aside.",
}

// What Bao must supply, grouped and counted (old app.js leftForYou, with counts kept so the list adds up).
export function leftForYou(questions: any[]): Task[] {
  const out: Task[] = []
  const add = (label: string, profile = false) => {
    const hit = out.find((x) => x.label === label)
    if (hit) hit.count++
    else out.push({ label, count: 1, profile })
  }
  for (const q of questions.filter((q) => !(q.body || q.answer || q.value))) {
    const t = String(q.question || q.label || ""), s = t.toLowerCase()
    if (/video/.test(s)) add("Video link")
    else if (/browse files|drag and drop|upload/.test(s)) add("File to upload")
    else if (/agree/.test(s)) add("Agreement to accept")
    else if (/^date\b/.test(s)) add("Today's date")
    else if (/phone/.test(s)) add("Phone number", true)
    else if (/zip|postal/.test(s)) add("Zip code", true)
    else { const c = t.split(/\s\*|\?|\(|:/)[0].trim(); if (c) add(c) }
  }
  return out.map((x) =>
    x.label === "Agreement to accept" && x.count > 1 ? { ...x, label: `${x.count} agreements to accept` }
    : x.label === "Video link" && x.count > 1 ? { ...x, label: `${x.count} video links` }
    : x)
}

const isFundingAlert = (x: any) => /^\/credits|^\/opportunity\//.test(String(x.url || ""))
const isPitchAlert = (x: any) => /^\/assumptions/.test(String(x.url || ""))

export async function loadToday(): Promise<Today> {
  const dash = await get("/api/dashboard")
  const got = await Promise.all(
    ["/api/application-list", "/api/growth-alerts", "/api/founder-profile"].map((p) => get(p).catch(() => null)),
  )
  const partial = got.includes(null)
  const [apps, growth, profile] = [got[0] || [], got[1] || [], got[2]] as [any[], any[], any]
  const board = dash.money_board
  const byOpp = Object.fromEntries([...board.cash, ...board.credits].map((d: any) => [d.opportunity_id, d]))

  // Next step: applications being drafted, in the order the server ranks them (old doNext, first branch).
  const drafting = apps.filter((x) => ["READY", "DRAFTING"].includes(x.access?.level) && x.questions)
  let lead: Lead | null = null
  if (drafting.length) {
    const x = drafting[0], d = byOpp[x.opportunity_id]
    const left = x.questions - x.answered
    let tasks: Task[] = []
    try { tasks = leftForYou((await get(`/api/application/${encodeURIComponent(x.application_id)}`)).questions || []) } catch { /* keep the counts only */ }
    const dated = tasks.filter((t) => t.label === "Today's date")
    const mine = tasks.filter((t) => t.label !== "Today's date")
    const shown = mine.slice(0, 4)
    const covered = shown.reduce((s, t) => s + t.count, 0)
    const days = d ? d.analysis.scoring.dates.days_remaining : null
    lead = {
      program: x.program, href: `/application/${x.application_id}`,
      prize: d?.data.funding.cash_prize_max != null ? `Up to ${usd(d.data.funding.cash_prize_max)}` : d?.data.funding.credits_value != null ? `Up to ${usd(d.data.funding.credits_value)} in credits` : "",
      deadline: d?.data.dates.deadline ? dayLabel(d.data.dates.deadline) : "", days,
      answered: x.answered, questions: x.questions, left, tasks: shown,
      more: Math.max(0, left - covered), dateLeft: dated.length > 0,
    }
  }

  // Next three weeks: every program with a known deadline from today to day 21.
  const marks: Mark[] = [...board.cash, ...board.credits]
    .map((d: any) => ({ d, n: d.analysis.scoring.dates.days_remaining }))
    .filter(({ n }) => n !== null && n >= 0 && n <= 21)
    .sort((a, b) => a.n - b.n)
    .map(({ d, n }) => ({
      day: n, name: String(d.data.canonical_name).split(" - ")[0].replace(/ (New Venture Challenge|Accelerator)$/, ""),
      prize: usd(d.data.funding.cash_prize_max ?? d.data.funding.credits_value), amount: Number(d.data.funding.cash_prize_max ?? d.data.funding.credits_value ?? 0), date: dayLabel(d.data.dates.deadline), soon: n <= 14,
    }))

  // The company today: the next deadline that isn't the lead, the next three drafts, then Customers and Company.
  const rows: Row[] = []
  const nextDeadline = marks.find((m) => !lead || !lead.program.startsWith(m.name))
  if (nextDeadline) rows.push({ name: "Funding", line: `${nextDeadline.name} closes ${nextDeadline.date}`, href: "/funding", tone: nextDeadline.soon ? "due" : "live" })
  for (const x of drafting.slice(1, 4)) rows.push({ name: x.program, line: "", href: `/application/${x.application_id}`, tone: "live", ready: x.answered, total: x.questions })
  const cust = growth.filter((x) => !isFundingAlert(x) && !isPitchAlert(x))[0]
  if (cust) rows.push({ name: "Customers", line: cust.title, href: cust.url || "/growth", tone: "live" })
  const waiting = (dash.needs_decision?.length || 0) + (dash.inbox ? (dash.inbox.proposed || 0) + (dash.inbox.review || 0) : 0)
  if (waiting) rows.push({ name: "Company", line: `${waiting} ${waiting === 1 ? "decision is" : "decisions are"} waiting for you`, href: "/decisions", tone: "due" })
  else if (profile && profile.total > profile.filled) rows.push({ name: "Company", line: "Fill your founder profile", href: "/founder-profile", tone: "live" })

  const run = dash.agent_activity?.[0]
  const st = run ? String(run.state).toLowerCase() : ""
  const msg = String(run?.report?.errors?.[0]?.message || "")
  const research: Research = run
    ? { state: st === "failed" ? "stopped" : st === "running" ? "running" : "ok", date: dayLabel(run.completed_at || run.started_at), cause: CAUSES[msg] || msg, href: `/run/${run.id}` }
    : { state: "none", date: "", cause: "", href: "/activity" }

  const tracked = board.tracked || []
  return {
    date: new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: TZ }),
    lead, marks, rows, research, partial,
    figures: {
      accepted: tracked.filter((t: any) => !t.waiting && ["Accepted", "Won"].includes(t.outcome)).length,
      waiting: tracked.filter((t: any) => t.waiting).length,
      cashOpen: board.cash.length,
    },
  }
}

export const leftWords = (lead: Lead) => `${plural(lead.left, "answer")} left for you`
export const moreWords = (lead: Lead) =>
  lead.more ? `${lead.more} more on the answers page${lead.dateLeft ? ", including today's date" : ""}` : ""

// Home: the one line on where things stand, from the dashboard alone so it arrives fast.
export type HomeFacts = { accepted: number; waiting: number; next: { name: string; days: number } | null }
export async function loadHome(): Promise<HomeFacts> {
  const f = await get("/api/home")
  return { ...f, next: f.next ? { ...f.next, name: String(f.next.name).split(" - ")[0].replace(/ (New Venture Challenge|Accelerator)$/, "") } : null }
}
