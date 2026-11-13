// Shared data code for the three application pages (Applications, the answers sheet, the application plan).
// Ported from the old app (app.js: accessShort, cycleLabel, STATE_WORDS, ACCESS_GROUPS, SOURCE_WORDS, RESULTS,
// the read-form handler and copyText) so the pages say and do the same things.
import { useState } from "react"

import { api } from "@/lib/api"
import { day, prettyKey, stamp } from "@/lib/format"
import { leftForYou } from "@/lib/today"

export type AccessLevel = "READY" | "DRAFTING" | "BLOCKED" | "NOT_CHECKED" | "FINISHED"
export type Access = { level: AccessLevel; label: string; detail: string }

export type AppListItem = {
  application_id: string; opportunity_id: string; program: string
  questions: number; answered: number; outcome: string | null; url: string | null; access: Access
}

export type Authorization = { id: string; scope: string; revoked_at: string | null }
export type Confirmation = { id: string; decision: string; email_state: string; payload_json: string }
export type Report = { id: string; local_date: string; state: string; error: string | null }
export type Autonomy = {
  authorizations: Authorization[]
  confirmations: Confirmation[]
  reports: Report[]
  mail_delivery?: { mode?: string; account?: string; smtp_fallback?: { enabled?: boolean; after_minutes?: number } }
  mail_connected: boolean
  smtp_fallback_connected: boolean
  report_schedule: { hour?: number | null; minute?: number | null }
}

export type Outcome = { outcome: string; occurred_at: string; note: string | null }
export type Answer = { body: string; status: string; provenance: string; notes?: string[] }
export type Question = {
  id: string; label: string | null; prompt: string; type: string; options?: string[]
  limit: number | null; unit: "words" | "characters" | null; needs_you: string | null; answer: Answer | null
}
export type Application = {
  id: string; program: string; cycle: string | null; opportunity_id: string
  application_url: string | null; official_url: string | null
  access?: Access | null; outcomes: Outcome[]; questions: Question[]
}

export type LabItem = {
  id: string; kind: string; subject_id: string; stage: string; stage_words: string; round: number
  error?: string | null; summary?: { avg?: number | null; low?: number | null } | null
}

export type PlanReview = { application_id?: string | null; program: string; cycle: string | null; url: string | null; blockers: string[] }

// The addresses the old page named in its copy.
export const REPORT_EMAIL = "gbao.n.vo@gmail.com"
export const COMPANY_EMAIL = "bao@astoryapp.com"

export const RESULTS = ["Advanced", "Finalist", "Won", "Accepted", "Rejected", "Withdrawn"]

// Hides "unknown"; "rolling" reads as "Rolling admissions".
export const cycleLabel = (c?: string | null) => (!c || c === "unknown" ? "" : c === "rolling" ? "Rolling admissions" : c)

// Run and report states in plain words.
const STATE_WORDS: Record<string, string> = {
  complete: "Complete", partial: "Partly complete", failed: "Failed", running: "Running", sent: "Sent",
  superseded: "Replaced by a newer report", sending: "Sending", delivery_unknown: "Delivery not confirmed",
  connector_pending: "Waiting for the mail sender", mail_connection_required: "Saved here; email not connected",
}
export const humanState = (s?: string | null) => { const k = String(s || "").toLowerCase(); return STATE_WORDS[k] || prettyKey(k) }
export const stateTone = (s?: string | null): "good" | "urgent" | "quiet" => {
  const k = String(s || "").toLowerCase()
  return k === "sent" || k === "complete" ? "good" : k === "failed" ? "urgent" : "quiet"
}

// The short name of an application's access state.
const ACCESS_SHORT: Record<string, string> = { READY: "Answers ready", DRAFTING: "Agent drafting", NOT_CHECKED: "Form not read yet", FINISHED: "Finished" }
export const accessShort = (a: Access) =>
  a.level === "BLOCKED" ? a.label.replace(/^Blocked:\s*/, "").replace(/^./, (c) => c.toUpperCase()) : ACCESS_SHORT[a.level] || a.label

export const ACCESS_GROUPS: [AccessLevel, string, string][] = [
  ["READY", "Ready to copy", "Answers are prepared from your facts. Copy them in and submit yourself."],
  ["DRAFTING", "Agent is drafting", "The questions are read; the agent is writing the open answers."],
  ["BLOCKED", "Blocked", "The agent cannot see these forms. Open them yourself to apply."],
  ["NOT_CHECKED", "Not read yet", "The agent reads one form every few minutes, or you can start one now."],
]

// Where an answer came from.
const SOURCE_WORDS: Record<string, string> = {
  auto_filled: "From your facts", founder_profile: "From your founder profile", agent_draft: "Agent draft",
  owner_written: "Your wording", drafted: "Draft",
}
export const sourceWords = (a: Answer) => (a.status === "approved" ? "Approved" : SOURCE_WORDS[a.provenance] || "Draft")

// A status word's colour: green only for won or accepted, navy for what is in progress or waiting on Bao.
export const outcomeTone = (s?: string | null): "good" | "review" | "quiet" =>
  ["Won", "Accepted", "ACCEPTED", "APPROVED"].includes(String(s)) ? "good"
    : ["Applied", "Advanced", "Finalist", "Waiting for you", "PENDING"].includes(String(s)) ? "review" : "quiet"

export const questionLabel = (q: Question) => q.label || q.prompt.split(" [")[0]

// "09:00" from the report schedule (9:00 when unset), plus minutes for the fallback sender.
export function scheduleTime(s: Autonomy["report_schedule"], plusMinutes = 0) {
  const m = (s.hour ?? 9) * 60 + (s.minute ?? 0) + plusMinutes
  return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0")
}

// Ask the agent to read a program's live form (old [data-read-form] handler). Returns the toast to show; when the
// questions were read and the caller is not already on an answers page, it goes to that page instead.
export async function readForm(opportunityId: string): Promise<{ message: string; error: boolean } | null> {
  const res = await api("/api/read-form", { opportunity_id: opportunityId })
  if (res.state === "QUESTIONS_READ" && res.application_id && !location.pathname.startsWith("/application")) {
    location.href = "/application/" + res.application_id
    return null
  }
  return res.state === "QUESTIONS_READ"
    ? { message: `Read ${res.questions} questions and filled ${res.filled} from your facts.${res.draft_queued ? " The agent is drafting the rest." : ""}`, error: false }
    : { message: "The agent could not read this form: " + (res.reason || res.state), error: true }
}

// Clipboard with the old app's fallback for browsers that refuse navigator.clipboard.
export async function copyAnswer(text: string) {
  try { await navigator.clipboard.writeText(text); return true } catch { /* fall through */ }
  try {
    const t = document.createElement("textarea")
    t.value = text
    t.setAttribute("readonly", "")
    t.className = "sr-only"
    document.body.appendChild(t)
    t.select()
    const ok = document.execCommand("copy")
    t.remove()
    return ok
  } catch { return false }
}

// A long list shows its first `n`; one control shows the rest.
export function useLimit<T>(items: T[], n: number) {
  const [all, setAll] = useState(false)
  return { shown: all ? items : items.slice(0, n), hidden: all ? 0 : Math.max(0, items.length - n), showAll: () => setAll(true) }
}

export const external = { target: "_blank", rel: "noopener noreferrer" } as const

// Program names, labels and notes come from scraped forms; an em dash in them reads as " - " (never in an answer's
// own text, which is copied as written).
export const plain = (s?: string | null) => String(s ?? "").replace(/\s*—\s*/g, " - ")

// The words for an unanswered question, the same as Today uses ("Zip code", "Phone number", "Agreement to accept").
export function plainTask(q: Question) {
  const t = leftForYou([{ label: q.label || q.prompt }])[0]
  return { label: plain(t?.label || questionLabel(q)), profile: !!t?.profile }
}

// Unanswered questions grouped the way Today groups them, in the form's order: one row per kind of task.
export function needsYou(questions: Question[]) {
  const groups: { key: string; profile: boolean; items: Question[] }[] = []
  for (const q of questions) {
    const t = plainTask(q)
    const hit = groups.find((g) => g.key === t.label)
    if (hit) hit.items.push(q)
    else groups.push({ key: t.label, profile: t.profile, items: [q] })
  }
  return groups.map((g) => {
    const label = plain(leftForYou(g.items.map((q) => ({ label: q.label || q.prompt })))[0]?.label || g.key)
    return {
      // A task the form asks for more than once is one row with its count ("Today's date, 3 places"), unless the
      // words already carry the count ("2 agreements to accept").
      label: g.items.length > 1 && !/^\d/.test(label) ? `${label}, ${g.items.length} places` : label,
      profile: g.profile, first: g.items[0].id, count: g.items.length,
    }
  })
}

// In the question list a task the form asks for several times ("Today's date" three times) is numbered, so the
// rows read as different questions: { questionId: "Today's date, 2 of 3" }.
export function numberedTasks(questions: Question[]): Record<string, string> {
  const groups = new Map<string, Question[]>()
  for (const q of questions.filter((q) => !q.answer)) {
    const k = plainTask(q).label
    groups.set(k, [...(groups.get(k) || []), q])
  }
  const out: Record<string, string> = {}
  for (const [label, items] of groups) if (items.length > 1) items.forEach((q, i) => { out[q.id] = `${label}, ${i + 1} of ${items.length}` })
  return out
}

// Server notes name an internal agent; on the page it is simply Bao's to fill.
export const needsWords = (s: string) => plain(s).replace(/\b(?:to be )?filled by the Form Filler\b/gi, "for you to fill in").replace(/\bthe Form Filler\b/gi, "you")

// Two rows with the same program name read as a bug. Where a name repeats, each row gets the cycle that tells it
// apart, or the day the program was found when the cycles don't.
// When neither does (two "Rolling admissions" found the same day), the day its result was recorded, then the
// exact time it was found.
/* eslint-disable @typescript-eslint/no-explicit-any */
export function tellApart(list: AppListItem[], opportunities: any[] | null | undefined, tracked?: any[] | null): Record<string, string> {
  const byOpp = new Map((opportunities || []).map((o) => [o.opportunity_id, o]))
  const recorded = new Map<string, string>()
  for (const t of tracked || []) if (t.application_id && t.occurred_at && !recorded.has(t.application_id)) recorded.set(t.application_id, t.occurred_at)
  const distinct = (v: string[]) => v.every(Boolean) && new Set(v).size === v.length
  const join = (...parts: string[]) => parts.filter(Boolean).join(", ")
  const names = new Map<string, AppListItem[]>()
  for (const x of list) names.set(x.program, [...(names.get(x.program) || []), x])
  const out: Record<string, string> = {}
  for (const group of names.values()) {
    if (group.length < 2) continue
    const cycles = group.map((x) => plain(cycleLabel(byOpp.get(x.opportunity_id)?.data?.cycle).split(";")[0].trim()))
    const found = group.map((x) => byOpp.get(x.opportunity_id)?.discovered_at as string | undefined)
    // A cycle every row shares tells nothing apart, so it is left out
    const cycle = (i: number) => (new Set(cycles).size === 1 ? "" : cycles[i])
    const dated = (when: (v?: string | null) => string) => group.map((x, i) =>
      join(cycle(i), recorded.has(x.application_id) ? "result recorded " + when(recorded.get(x.application_id)) : found[i] ? "found " + when(found[i]) : ""))
    const byDay = dated(day)
    const words = distinct(cycles) ? cycles : distinct(byDay) ? byDay : dated(stamp)
    group.forEach((x, i) => { out[x.application_id] = words[i] })
  }
  return out
}
/* eslint-enable @typescript-eslint/no-explicit-any */
