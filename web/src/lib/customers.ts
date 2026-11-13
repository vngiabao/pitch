// Data shapes and small helpers shared by the Customers pages: Beta families, Reservation drive, Press, People.
// The endpoints and payloads are the old app's (founder_os/ui/product.js, drive.js, app.js people() and press()).
import { useCallback, useEffect, useState } from "react"

import { useFeedback } from "@/components/app/feedback"
import { day, TZ } from "@/lib/format"

export type Draft = { title?: string | null; body: string; note?: string | null }
export type Touch = { occurred_on: string; summary: string }

// ---- People (/api/people)
export type Person = {
  id: string; name: string; org?: string; kind?: string; email?: string; state: string; due: boolean
  next_followup_on?: string | null; cadence_days: number; context?: string
  touches: Touch[]; draft?: Draft | null; drafting?: boolean
}
export const CONTACT_KINDS = ["Investor", "Partner", "Program", "Press", "Mentor", "Customer", "Other"]

// ---- Press (/api/press)
export type PressTarget = {
  id: string; outlet: string; kind: string; audience?: string; deadline?: string | null; days_left: number | null
  angle?: string; submit_method?: string; submit_url?: string | null; url?: string | null; source_url?: string | null
  state: "NEW" | "PITCHED" | "PUBLISHED" | "SKIPPED"; draft?: Draft | null; drafting?: boolean
}
export type PressData = { targets: PressTarget[]; searching: boolean; last_run?: { at: string; found: number } | null }
export const PRESS_KIND_WORDS: Record<string, string> = {
  gift_guide: "Gift guide", newsletter: "Newsletter", podcast: "Podcast", journalist: "Journalist",
  local_news: "Local news", blog: "Blog", community: "Community",
}

// ---- Reservation drive (/api/drive)
export type DriveShown = "NEW" | "READY" | "SENT" | "REPLIED" | "RESERVED"
export type DriveMember = {
  contact_id: string; name: string; email?: string; kind_words: string; context?: string; shown: DriveShown
  state_words: string; drafting?: boolean; draft?: Draft | null; touches: Touch[]; referrals?: number
  reserved_on?: string | null; sent_on?: string | null
}
export type DriveData = {
  deadline?: string; days_left: number
  counts: { total: number; leads: number; beta: number; not_written: number; ready: number; sent: number; replied: number; reserved: number; referrals: number }
  members: DriveMember[]
  entries: { created_at: string; channel: string; purchases: number; note?: string }[]
  nudge_days: string[]
}
export type DriveImportResult = { created: number; enrolled: number; skipped: number; rejected: { row: number; reason: string }[] }
export const DRIVE_CSV_HELP = "A header row, then one person per line: name, email, context, kind. Kind is Lead or Beta family (empty means Lead). Context is how you know them, in a sentence; it goes into their note."

// ---- Beta families (/api/product)
export type Pair = [string, string]
export type FamilyEvent = { id: string; at: string; kind_words: string; detail?: string; source?: string }
export type Family = {
  id: string; label: string; storyteller?: string; adult_child?: string; enrolled_on?: string | null
  status: string; notes?: string; events: FamilyEvent[]
}
export type Range = { start?: string | null; end?: string | null }
export type Metric = {
  key: string; label: string; measurable: boolean; numerator: number; denominator: number; denominator_label: string
  percent: number | null; calls?: number; range: Range; sources: string[]
}
export type MetricPoint = { provider: string; metric: string; period: string; value: number; unit: string; file_name: string }
export type Intake = {
  inbox: string
  files: { name: string; size: number; modified: string; imported?: { imported_at: string; provider: string } | null }[]
  providers: Record<string, string>
  sources: { provider: string; file_name: string; period_start: string; period_end: string; point_count: number; imported_at: string }[]
  latest: MetricPoint[]
  api: { name: string; credential_present: boolean }[]
}
export type ProductData = {
  counts: { families: number; first_calls: number; second_calls: number; contributing: number; issues: number }
  retention: { as_of?: string | null; metrics: Metric[] }
  families: Family[]; event_kinds: Pair[]; family_states: Pair[]; intake: Intake
}
export const METRIC_NEEDS: Record<string, string> = {
  second_call_rate: "families with a first call",
  relatives_contributing: "families with a first call",
  calls_after_contribution: "a family where a relative contributed",
}

// Today's date in Eastern time, as YYYY-MM-DD (the default and the latest day a journal event can have).
export const todayEastern = () => new Date().toLocaleDateString("en-CA", { timeZone: TZ })

// "Nov 2, 2026 - Nov 9, 2026", one day when both ends match, "no dates yet" when empty.
export const rangeWords = (r?: Range | null) =>
  !r || !r.start ? "no dates yet" : r.start === r.end ? day(r.start) : `${day(r.start)} - ${day(r.end)}`

// An imported number in its own unit: a count, a percent, or money in its currency.
export function pointValue(p: MetricPoint) {
  if (p.unit === "count") return String(Math.round(p.value))
  if (p.unit === "percent") return p.value + "%"
  return new Intl.NumberFormat("en-US", { style: "currency", currency: p.unit.length === 3 ? p.unit.toUpperCase() : "USD", maximumFractionDigits: 2 }).format(p.value)
}

// "PITCHED" -> "Pitched"
export const stateWord = (s: string) => { const t = String(s || "").replace(/_/g, " ").toLowerCase(); return t ? t[0].toUpperCase() + t.slice(1) : "" }

// Run one action the way the old app did: call the server, reload the page's data, then say what happened.
// `busy` is the key of the action that is running, so its button can be disabled and say so.
export function useRun(reload: () => Promise<unknown>) {
  const { toast } = useFeedback()
  const [busy, setBusy] = useState<string | null>(null)
  const run = useCallback(async (key: string, work: () => Promise<string | void>) => {
    setBusy(key)
    try {
      const said = await work()
      await reload()
      if (said) toast(said)
      return true
    } catch (e) {
      toast(e instanceof Error ? e.message : "Unable to complete this action.", true)
      return false
    } finally { setBusy(null) }
  }, [reload, toast])
  return { busy, run }
}

// Old anchors (#person-<id>, #drive-<id>, #family-<id>, #intake, #drive-loader): once the page has its data,
// scroll to the element whose id matches the address.
export function useHashScroll(ready: boolean) {
  useEffect(() => {
    if (!ready || location.hash.length < 2) return
    let id = location.hash.slice(1)
    try { id = decodeURIComponent(id) } catch { /* keep the raw id */ }
    document.getElementById(id)?.scrollIntoView({ block: "start" })
  }, [ready])
}
// A list cut to its first few items shows everything when the address points at one item.
export const hasHash = () => location.hash.length > 1

// The checker note on a draft, without the checker name in front ("Bao’s Voice edit.").
export const draftNote = (note?: string | null) => String(note || "").replace(/^Bao.s Voice edit\.\s*/i, "").trim()
