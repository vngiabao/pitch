// Data and words for the Company department (Decisions, Company facts, Founder profile), ported from the old app
// (app.js factsView, factCard, recentDecisions, inbox*; profile.js) so the pages say the same things.
/* eslint-disable @typescript-eslint/no-explicit-any */
import { api } from "@/lib/api"
import { day, prettyKey } from "@/lib/format"

// ---------- /api/dashboard, the parts these pages read ----------
export type Replace = { fact: string; current: unknown; proposed: unknown }
export type Card = {
  kind: "APPROVE" | "CHECK" | "ANSWER" | "REMINDER" | string
  topic?: string; label: string; sentence: string; why?: string
  unlocks?: string[]; replaces?: Replace[]; source?: string; locator?: string; editable?: boolean
}
export type Approval = { id: string; card?: Card | null }
export type InboxAccount = { account: string; connected: boolean; last_checked?: string | null; last_error?: string | null }
export type InboxMail = {
  id: string; program?: string | null; state: string; proposed_outcome?: string | null; sender: string; account: string
  received_at: string; subject: string; snippet: string; reason?: string | null
  opportunity_id?: string | null; deal_id?: string | null; deal?: string | null; deal_stage?: string | null
}
export type Inbox = { proposed: number; review: number; accounts: InboxAccount[]; pending: InboxMail[] }
export type Decided = { label: string; sentence?: string | null; state: string; decided_at: string }
export type FactRecord = { value: unknown; last_verified?: string | null }
export type Claim = { label: string; body: string }
export type Dashboard = {
  needs_decision: Approval[]
  inbox?: Inbox | null
  recent_decisions?: Decided[]
  company_memory: { attributes: Record<string, FactRecord>; canonical_claims: Claim[] }
  agent_activity: any[]
}

// Text from the records, as it is shown: a spaced hyphen where the record has an em dash.
export const noDash = (s?: string | null) => String(s || "").replace(/\s*—\s*/g, " - ")

// ---------- Decisions ----------
export const KIND_WORDS: Record<string, string> = { APPROVE: "Approve", CHECK: "Check it is still true", ANSWER: "Needs your answer", REMINDER: "Reminder" }
export const OUTCOME_CHOICES = ["Applied", "Advanced", "Finalist", "Accepted", "Rejected"]

// A fact's value in a "changes your current facts" line (old factValue)
export const factValue = (v: unknown) => (Array.isArray(v) ? v.join(", ") : typeof v === "boolean" ? (v ? "Yes" : "No") : String(v))

// The recent decisions, one per label, newest first as the server sends them (old recentDecisions)
export function recentDecisions(list?: Decided[] | null) {
  const seen = new Set<string>()
  return (list || []).filter((r) => { const k = String(r.label).toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true })
}
// A decision's name without the date it carries ("Beta traction - confirmed Oct 14, 2026" -> "Beta traction").
// The row shows one date, the day it was decided.
export const decisionTitle = (label: string) =>
  noDash(label).replace(/\s+-\s+(confirmed\s+)?[A-Z][a-z]+\.? \d{1,2}, \d{4}$/, "")
// A cut-off sentence ends on a whole word and an ellipsis; a raw record shows as "Company profile updated"
export function decidedLine(sentence?: string | null) {
  if (!sentence) return ""
  if (sentence.trim().startsWith("{")) return "Company profile updated"
  const s = noDash(sentence)
  return /[.!?)"”]$/.test(s.trim()) ? s : s.replace(/\s+\S*$/, "") + "…"
}

// ---------- Company facts ----------
const FACT_LABELS: Record<string, string> = {
  us_company: "U.S. company", website_url: "Website", uses_ai: "Uses AI", cofounder_name: "Co-founder", cofounder_role: "Co-founder role",
  founder_display_name: "Founder (display name)", founder_name: "Founder legal name", institutional_equity_funding: "Institutional equity funding",
}
const FACT_GROUPS: [string, string[]][] = [
  ["Company", ["company_name", "website_url", "founded_date", "incorporated", "incorporation_date", "us_company", "headquarters", "location"]],
  ["Founders", ["founder_name", "founder_display_name", "founder_first_name", "founder_last_name", "founder_role", "cofounder_name", "cofounder_role", "team_size"]],
  ["Product and market", ["product_stage", "business_type", "customer_type", "industry", "uses_ai"]],
  ["Funding", ["funding_stage", "self_funded", "institutional_equity_funding", "previous_programs"]],
]
// Parts of a fact already shown in the same panel; they sit behind "Show all".
const MINOR_FACTS = new Set(["founder_first_name", "founder_last_name"])
export const factLabel = (k: string) => FACT_LABELS[k] || prettyKey(k)

// How a fact reads: lists joined, Yes/No, long dates, snake_case words in plain words (old factShown)
export function factShown(v: unknown) {
  if (Array.isArray(v)) return v.join(", ")
  if (typeof v === "boolean") return v ? "Yes" : "No"
  const t = String(v)
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return new Date(t + "T12:00:00").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
  if (/^\d{4}-\d{2}$/.test(t)) return new Date(t + "-15T12:00:00").toLocaleDateString("en-US", { month: "long", year: "numeric" })
  return /^[a-z]+(_[a-z]+)*$/.test(t) ? prettyKey(t).replace(/\bai\b/gi, "AI") : noDash(t)
}

export type FactLine = { key: string; label: string; value: string; verified: string; minor: boolean }
export type FactGroup = { title: string; verified: string; facts: FactLine[] }
// Facts in their groups. Each group names its most common verification day once; a fact carries a day only when
// its own differs (old factsView, applied per panel).
export function groupFacts(facts: Record<string, FactRecord>): FactGroup[] {
  const keys = Object.keys(facts)
  const placed = new Set(FACT_GROUPS.flatMap((g) => g[1]))
  const all: [string, string[]][] = [...FACT_GROUPS, ["Other", keys.filter((k) => !placed.has(k))]]
  return all.map(([title, ks]) => {
    const present = ks.filter((k) => facts[k])
    const counts: Record<string, number> = {}
    present.forEach((k) => { const d = day(facts[k].last_verified); counts[d] = (counts[d] || 0) + 1 })
    const common = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || ""
    return {
      title, verified: common,
      facts: present.map((k) => {
        const d = day(facts[k].last_verified)
        return { key: k, label: factLabel(k), value: factShown(facts[k].value), verified: d !== common ? d : "", minor: MINOR_FACTS.has(k) }
      }),
    }
  }).filter((g) => g.facts.length)
}

// ---------- Founder profile ----------
// Sensitive values never arrive with the page: `value` is null and `masked` is a row of dots until Bao presses Reveal.
export type ProfileField = {
  key: string; label: string; group: string; set: boolean; sensitive: boolean; masked?: string | null
  value?: string | null; updated_at?: string | null; used_for: string; custom: boolean
}
export type Profile = { filled: number; total: number; groups: string[]; fields: ProfileField[] }

// Only real dates get a date box: "revenue_to_date" and "funding_to_date" are amounts, not dates.
export const profileInputType = (k: string) =>
  (/_url$|_link$|website$/.test(k) ? "url" : /_dob$|^date_|(^|_)incorporation_date$|(^|_)founded_date$/.test(k) ? "date" : "text")

// A generic example that shows the format, for the few boxes where the format is the question. Never real data.
const PROFILE_EXAMPLES: Record<string, string> = { phone: "(555) 555-0100", country: "United States" }
export const profileExample = (k: string): string | undefined => PROFILE_EXAMPLES[k]

export const GROUP_BLURBS: Record<string, string> = {
  Company: "Legal identity lines. The EIN and street addresses stay masked.",
  Contact: "Who gets your number is your call; this only saves typing it.",
  Founders: "Only for forms that ask. Dates of birth are stored, never listed.",
  Links: "Public links the forms keep asking for. Leave one empty and that question stays with you.",
  "Team and money": "Plain words work: “$0, bootstrapped” or “2 founders, no employees”.",
  Other: "Anything a form asks that is not above. A question is matched when its label contains every word of yours.",
}

// Which profile fact answers a form question. Checked in order; the first match wins ("" = none of them).
const QUESTION_FACTS: [RegExp, string][] = [
  [/phone type|email type/, ""],
  [/phone/, "phone"], [/zip|postal/, "zip_code"],
  [/linkedin.*(company|startup)|(company|startup).*linkedin/, "company_linkedin_url"],
  [/linkedin.*(co-?founder|member 2)|(co-?founder|member 2).*linkedin/, "cofounder_linkedin_url"],
  [/linkedin/, "linkedin_url"], [/twitter/, "company_twitter_url"], [/crunchbase/, "crunchbase_url"],
  [/pitch deck/, "deck_link"], [/video|multimedia url/, "demo_video_link"], [/app store|testflight/, "app_store_link"],
  [/\bein\b|tax id|employer identification/, "ein"], [/mailing address/, "mailing_address"], [/street address|registered address/, "legal_address"],
  [/date of birth|birth date/, "founder_dob"], [/citizenship|visa status|work authorization/, "founder_citizenship"],
  [/pronoun/, "pronouns"], [/state of incorporation/, "incorporation_state"], [/date of incorporation|incorporated on/, "incorporation_date"],
  [/^country/, "country"], [/^state\b|state\/province/, "state"], [/^city/, "city"],
  [/employees/, "employees"], [/team size/, "team_size"],
  [/revenue to date|total revenue/, "revenue_to_date"], [/funding raised|raised to date|total funding/, "funding_to_date"],
]
export type ProfileNeed = { field: ProfileField; programs: string[] }
export type ProfilePage = { profile: Profile; needs: ProfileNeed[]; fromApplications: boolean }

// The page's data: the profile and its "do next", the unfilled facts that the applications being worked on still
// ask for, most asked first (the same reading of the forms as Today's "left for you"). When no open form asks for
// one, it falls back to the first unfilled facts in the profile's own order.
export async function loadProfile(): Promise<ProfilePage> {
  const profile = await api<Profile>("/api/founder-profile")
  const unfilled = new Map(profile.fields.filter((f) => !f.set).map((f) => [f.key, f]))
  const asked = new Map<string, Set<string>>()
  try {
    const apps: any[] = await api("/api/application-list")
    const open = apps.filter((x) => ["READY", "DRAFTING"].includes(x.access?.level) && x.questions && x.application_id)
    const forms = await Promise.all(open.map((x) => api(`/api/application/${encodeURIComponent(x.application_id)}`).catch(() => null)))
    forms.forEach((form, i) => {
      for (const q of (form?.questions || []).filter((q: any) => !(q.body || q.answer || q.value))) {
        const text = String(q.question || q.label || q.prompt || "").toLowerCase()
        const key = QUESTION_FACTS.find(([re]) => re.test(text))?.[1]
        if (!key || !unfilled.has(key)) continue
        if (!asked.has(key)) asked.set(key, new Set())
        asked.get(key)!.add(String(open[i].program || "").split(" - ")[0])
      }
    })
  } catch { /* the profile still opens; "do next" falls back to the profile's own order */ }
  const needs = [...asked.entries()].map(([key, programs]) => ({ field: unfilled.get(key)!, programs: [...programs] }))
    .sort((a, b) => b.programs.length - a.programs.length).slice(0, 5)
  if (needs.length) return { profile, needs, fromApplications: true }
  return { profile, needs: [...unfilled.values()].filter((f) => f.used_for).slice(0, 5).map((field) => ({ field, programs: [] })), fromApplications: false }
}
