// Data and words for the Agents department (Activity, a research run, Scouts, Plans), ported from the old app
// (app.js activityList, researchAlert, errorView, usageView; scouts.js; plans.js).
/* eslint-disable @typescript-eslint/no-explicit-any */
import { TZ, day } from "@/lib/format"

// ---------- Research runs ----------
export type RunError = { state?: string; message?: string; program?: string } | string
export type RunReport = {
  errors?: RunError[]; candidates_discovered?: number; verified?: number; new_programs?: number
  records_created?: number; duplicates_removed?: number
  queries_used?: (string | { query: string })[]; sources_checked?: string[]; usage?: Usage
  [k: string]: any
}
export type Usage = { runner?: string; research_runner?: string; api_key_used?: boolean; tokens?: { input_tokens?: number; output_tokens?: number }; model_api_cost?: number | string | null }
export type Run = { id: string; started_at: string; completed_at?: string | null; state: string; report: RunReport; usage_json?: string | null }

// "RESEARCH_INCOMPLETE" -> "Research incomplete" (the old prettyKey, which lowercases first)
export const plainKey = (k: unknown) => { const s = String(k ?? "").replace(/_/g, " ").toLowerCase(); return s ? s[0].toUpperCase() + s.slice(1) : "" }

const STATE_WORDS: Record<string, string> = {
  complete: "Complete", partial: "Partly complete", failed: "Failed", running: "Running", sent: "Sent",
  superseded: "Replaced by a newer report", sending: "Sending", delivery_unknown: "Delivery not confirmed",
  connector_pending: "Waiting for the mail sender", mail_connection_required: "Saved here; email not connected",
}
export const humanState = (s: unknown) => { const k = String(s || "").toLowerCase(); return STATE_WORDS[k] || plainKey(k) }
export const runTone = (s: unknown): "urgent" | "good" | "review" | "quiet" => {
  const k = String(s || "").toLowerCase()
  return k === "failed" ? "urgent" : k === "complete" ? "good" : k === "running" ? "review" : "quiet"
}

// Failures with a known cause: a rerun stops the same way, so "Run research now" is paused until the agent is fixed.
const RESEARCH_CAUSES: Record<string, string> = { "Research budget exceeded": "Each run came back larger than the app allows, so its results were set aside." }
const firstError = (run?: Run | null) => (run?.report?.errors || [])[0]
const errorMessage = (e: RunError) => String(typeof e === "string" ? e : e.message || "")
export const errorCause = (e: RunError) => { const m = errorMessage(e); return RESEARCH_CAUSES[m] || m || String(e) }
export const errorState = (e: RunError) => (typeof e === "string" ? "" : e.state || "")
export const errorProgram = (e: RunError) => (typeof e === "string" ? "" : e.program || "")
export const isFailed = (run?: Run | null) => !!run && String(run.state).toLowerCase() === "failed"
export const isRunning = (run?: Run | null) => !!run && String(run.state).toLowerCase() === "running"
export function researchCause(run?: Run | null) { const e = firstError(run); return e ? errorCause(e) : "" }
// Causes whose fix is already in the code: a new run no longer stops the same way, so "Run research now" is open again.
// (Nov 12, 2026: a broad scan asked for 25 queries against a limit of 24; the scan now stays within the limit.)
// Only runs from before the fix count as fixed; the same failure on a later run is a new problem and pauses again.
const FIXED_CAUSES: Record<string, string> = { "Research budget exceeded": "2026-11-13T00:00:00Z" }
const wasFixed = (run: Run | null | undefined, cause: string) => !!run && !!FIXED_CAUSES[cause] && new Date(run.started_at).getTime() < new Date(FIXED_CAUSES[cause]).getTime()
export function fixedCause(run?: Run | null) { const e = firstError(run); return !!e && wasFixed(run, errorMessage(e)) }
export function knownCause(run?: Run | null) { const e = firstError(run); return !!e && !!RESEARCH_CAUSES[errorMessage(e)] && !wasFixed(run, errorMessage(e)) }
export const runDay = (run: Run) => day(run.completed_at || run.started_at)
export const RUN_PAUSED = "Paused until the research agent is fixed"

export function runUsage(run: Run): Usage {
  if (run.report?.usage) return run.report.usage
  try { return JSON.parse(run.usage_json || "{}") || {} } catch { return {} }
}

// ---------- Scouts ----------
export type Schedule = { days?: string[]; hour: number; minute?: number }
export type LastRun = { at: string; found?: number | null; unit?: string; checked?: number }
export type Scout = {
  key: string; name: string; group: string; hunts: string; running: boolean; schedule?: Schedule | null
  lands_url: string; lands_label: string; last_run?: LastRun | null; next_run?: string | null; families?: string[]
}
export type Scouts = { scouts: Scout[]; broad_sweep: { name: string; hunts: string; running: boolean; schedule?: Schedule | null; last_run?: LastRun | null } }

const DAY_WORDS: Record<string, string> = { MO: "Mon", TU: "Tue", WE: "Wed", TH: "Thu", FR: "Fri", SA: "Sat", SU: "Sun" }
export function scheduleWords(s?: Schedule | null) {
  if (!s || !s.days) return "No schedule"
  if (s.days.length === 7 && s.hour === 8 && s.minute === 30) return "Weekly, for programs you are in"
  const days = s.days.length === 7 ? "Every day" : s.days.map((d) => DAY_WORDS[d] || d).join(" and ")
  const h = ((s.hour + 11) % 12) + 1, m = String(s.minute || 0).padStart(2, "0"), ap = s.hour < 12 ? "AM" : "PM"
  return `${days} at ${h}:${m} ${ap} Eastern`
}
// "Oct 26: 0 new of 10 checked"
export function lastRunWords(l?: LastRun | null) {
  if (!l) return "Has not run yet"
  if (l.found === null || l.found === undefined) return `Ran ${day(l.at)}`
  return `${day(l.at)}: ${l.found} ${l.unit || "new"}${l.checked ? ` of ${l.checked} checked` : ""}`
}

// The server's "next run" is only the calendar: /api/scouts sends it whether or not scheduled runs are switched
// on. So the page checks the record instead. A scout whose last scheduled time has passed (with 3 hours of grace)
// with no run since is not running on schedule, and the page says "Paused" rather than promise a run.
const DAY_CODES = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]
export function missedSchedule(s?: Schedule | null, last?: LastRun | null, now = new Date()) {
  if (!s?.days?.length || !last?.at) return false
  const wall = new Date(now.toLocaleString("en-US", { timeZone: TZ })) // the Eastern wall clock, read as local time
  const shift = wall.getTime() - now.getTime()
  for (let i = 0; i < 8; i++) {
    const slot = new Date(wall)
    slot.setDate(wall.getDate() - i)
    slot.setHours(s.hour, s.minute || 0, 0, 0)
    if (!s.days.includes(DAY_CODES[slot.getDay()]) || slot.getTime() > wall.getTime() - 3 * 3600 * 1000) continue
    return new Date(last.at).getTime() < slot.getTime() - shift
  }
  return false
}
// Scheduled runs are off when no scout with a record has kept its schedule.
export function schedulesPaused(scouts: { schedule?: Schedule | null; last_run?: LastRun | null }[]) {
  const known = scouts.filter((s) => s.schedule?.days?.length && s.last_run?.at)
  return known.length > 0 && known.every((s) => missedSchedule(s.schedule, s.last_run))
}

// ---------- Plans ----------
export type PlanReport = {
  bottom_line?: string
  moves?: { what: string; owner: string; by?: string; why?: string }[]
  decisions?: { decision: string; recommend: string; unblocks: string }[]
  numbers?: { value: string; label: string; source?: string }[]
  by_agent?: { agent: string; result: string; needs: string }[]
  risks?: string[]
  later?: { what: string; owner: string; by?: string }[]
  answer?: string[]
}
export type PlanItem = {
  id?: string; title?: string | null; question: string; created_at: string; finished_at?: string | null
  state: "READY" | "QUEUED" | "FAILED" | string; error?: string | null; auto?: number | boolean | null
  pdf_url?: string | null; html_url?: string | null; report?: PlanReport | null
}
export type Plans = { default_question: string; writing: boolean; latest?: PlanItem | null; items: PlanItem[] }

export const planStateWord = (x: PlanItem) => (x.state === "READY" ? "Ready" : x.state === "QUEUED" ? "Writing" : "Failed")

// ---------- Layout ----------
// Split groups into two columns of about the same weight, keeping their order (left column first).
export function twoColumns<T>(groups: T[], weight: (g: T) => number): [T[], T[]] {
  const total = groups.reduce((n, g) => n + weight(g), 0)
  const left: T[] = [], right: T[] = []
  let n = 0
  for (const g of groups) { if (n < total / 2) { left.push(g); n += weight(g) } else right.push(g) }
  return [left, right]
}
