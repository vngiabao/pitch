// Data for the customer desk (/growth): deals, campaigns, what families say online, and channel math.
// Ported from founder_os/ui/growth.js. Agents find, draft and plan; Bao sends, meets and closes.
import { api } from "@/lib/api"
import { day, plural } from "@/lib/format"

export type Draft = { title?: string | null; body: string; note?: string | null }
export type DealEvent = { occurred_on: string; summary: string }
export type Deal = {
  id: string; name: string; kind: string; kind_words: string; region?: string | null
  value_usd?: number | null; value_note?: string | null
  stage: string; stage_words: string; due: boolean; open: boolean
  next_step?: string | null; next_on?: string | null
  why?: string | null; angle?: string | null; contact_route?: string | null
  url?: string | null; source?: string | null; source_url?: string | null
  events: DealEvent[]
  reply_proposal?: { sender: string; subject: string; received_at: string } | null
  draft?: Draft | null; drafting?: boolean
}
export type Stage = { key: string; label: string; deals: Deal[] }
export type Kind = { key: string; label: string }

export type PlanChannel = {
  channel: string; what: string; message?: string | null; start_on?: string | null; end_on?: string | null
  spend_cap_usd?: number | null; success_metric?: string | null; needs_from_bao?: string | null
}
export type Plan = {
  goal: string; audience: string; offer: string; channels: PlanChannel[]
  checkpoints: { on?: string | null; check: string }[]; open_questions: string[]; risks: string[]
}
export type FieldEntry = { week_start: string; visits: number; signups: number; purchases: number; note?: string | null }
export type FieldVoice = { as_of?: string | null; objections: { objection: string; quote?: string | null; url?: string | null }[]; words: string[] }
export type Campaign = {
  key: string; title: string; brief: string; state: string; planning: boolean; owner_note?: string | null
  issues: { severity: string; text: string; where: string }[]
  drafts: Draft[]; plan?: Plan | null
  field?: { approached: number; emails: number; reservations: number; entries: FieldEntry[] } | null
  voice?: FieldVoice | null
}

export type Quote = { text: string; who?: string | null; url?: string | null }
export type VoiceReport = {
  threads_read?: number; places_read: string[]
  themes: { theme: string; threads: number; summary?: string | null; quotes: Quote[] }[]
  tried: { what: string; threads?: number; said?: string | null; quote?: Quote | null }[]
  objections: { objection: string; threads?: number; quote?: Quote | null }[]
  willing_to_pay: { said: string; url?: string | null }[]
  words: string[]; sources: string[]
}
export type Voice = {
  report?: VoiceReport | null; researching: boolean; run_on?: string | null; runs?: number; previous_on?: string | null
  movement?: { new?: string[]; up?: { theme: string; from: number }[]; down?: { theme: string; from: number }[] } | null
  movement_words?: string
}

export type ChannelTotals = {
  label: string; weeks: number; from?: string | null; to?: string | null; visits: number; signups: number; purchases: number
  signup_rate: number | null; conversion: number | null; cost_per_family: number | null
  spend_usd: number; revenue_usd: number; revenue_per_dollar: number | null
}
export type ChannelEntry = {
  id: string; channel: string; week_start: string; visits: number; signups: number; purchases: number
  spend_usd: number; revenue_usd: number; note?: string | null
}
export type ChannelMath = {
  totals: ChannelTotals
  deck_formula: { visits: number; rate: number; families: number; visits_needed_for_30?: number | null }
  channels: ChannelTotals[]; entries: ChannelEntry[]
}

export type Growth = {
  stages: Stage[]; kinds: Kind[]; open: number; due: Deal[]; ready_to_send: Deal[]
  searching: boolean; last_run?: { at: string; found: number } | null
  campaigns: Campaign[]; voice?: Voice | null; math: ChannelMath; channel_words: Record<string, string>
}

type Alert = { title: string; detail?: string; url?: string; link?: string }
export type NextItem = { title: string; detail: string; href: string; label: string }
export type Desk = { growth: Growth; next: NextItem[] }

// Which stage a deal can move to from where it is, and what the button says (old DEAL_MOVES).
export const DEAL_MOVES: Record<string, [string, string][]> = {
  FOUND: [["SENT", "I sent it"]],
  DRAFTED: [["SENT", "I sent it"]],
  SENT: [["REPLIED", "They replied"], ["MEETING", "Meeting set"]],
  REPLIED: [["MEETING", "Meeting set"], ["PROPOSAL", "Proposal sent"], ["WON", "Won"]],
  MEETING: [["PROPOSAL", "Proposal sent"], ["WON", "Won"], ["REPLIED", "Still talking"]],
  PROPOSAL: [["WON", "Won"], ["LOST", "Lost"]],
}
export const CLOSED_STAGES = ["WON", "LOST", "PARKED"]
// Stages where the first note still matters, so the draft is shown.
export const DRAFT_STAGES = ["FOUND", "DRAFTED", "SENT"]
// Moves that ask for one optional line on what happened.
export const NOTE_STAGES = ["REPLIED", "MEETING", "PROPOSAL", "WON", "LOST"]
// Moves that record something outward or final: each keeps its confirmation.
export const STAGE_CONFIRM: Record<string, { title: string; body: string; action: string }> = {
  SENT: { title: "Log that you sent this note yourself?", body: "This only records it. Founder OS sends nothing. A follow-up is scheduled in a week.", action: "Yes, I sent it" },
  WON: { title: "Mark this deal won?", body: "It moves out of your open deals and counts as won.", action: "Mark as won" },
  LOST: { title: "Mark this deal lost?", body: "It moves out of your open deals. You can move it back to open later.", action: "Mark as lost" },
}

export const CAMPAIGN_STATE: Record<string, string> = { NEW: "Not planned yet", PLANNED: "Plan ready for you", RUNNING: "Running", DONE: "Done" }

// Alerts that belong to Funding or Pitch are shown on those desks, not here (old customerAlerts()).
const isFundingAlert = (x: Alert) => /^\/(credits|opportunity\/)/.test(String(x.url || ""))
const isPitchAlert = (x: Alert) => String(x.url || "").startsWith("/assumptions")

// The top three things for Bao: customer alerts, then deals that are due, then notes ready to send.
function nextItems(b: Growth, alerts: Alert[]): NextItem[] {
  const mine = alerts.filter((x) => !isFundingAlert(x) && !isPitchAlert(x))
  // When an alert already says "N outreach notes ready to send", the single notes are not listed again.
  const notesCovered = mine.some((x) => x.url === "/growth")
  return [
    ...mine
      .map((x) => ({ title: x.title, detail: x.detail || "", href: x.url || "/growth", label: x.link || "Open" })),
    ...b.due.map((d) => ({
      title: `${d.name}: ${d.next_step || d.stage_words}`,
      detail: `Due ${day(d.next_on)}.${d.draft ? " A note is ready below." : ""}`,
      href: "#deal-" + d.id, label: "Open",
    })),
    ...b.ready_to_send.filter((d) => !d.due && !notesCovered).map((d) => ({
      title: `Send the note to ${d.name}`,
      detail: d.why || "Copy it, send it from your own email, then press I sent it.",
      href: "#deal-" + d.id, label: "Open note",
    })),
  ].slice(0, 3)
}

export async function loadDesk(): Promise<Desk> {
  const [growth, alerts] = await Promise.all([
    api<Growth>("/api/growth"),
    api<Alert[]>("/api/growth-alerts").catch(() => [] as Alert[]),
  ])
  return { growth, next: nextItems(growth, Array.isArray(alerts) ? alerts : []) }
}

// The state of the desk in one line, for the top of the page.
export function deskLine(b: Growth) {
  if (!b.open) return "No open deals yet. Add the organizations you already talk to, or let Partner Scout find them."
  const parts = [plural(b.open, "open deal")]
  if (b.due.length) parts.push(`${b.due.length} due`)
  if (b.ready_to_send.length) parts.push(`${plural(b.ready_to_send.length, "note")} ready to send`)
  return `${parts.join(", ")}.`
}

export const threadsWords = (n?: number | null) => (n ? plural(n, "thread") : "")
export const channelLabel = (words: Record<string, string>, key: string) => words[key] || key
// A form's fields as the server expects them: every value a string, as the old page sent them.
export const formBody = (form: HTMLFormElement) => Object.fromEntries(new FormData(form)) as Record<string, string>
