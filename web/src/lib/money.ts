// Data for the Credits and Money map pages: the shapes the server returns, the loaders, and the words the old
// pages used for a program's state (app.js credits(), moneyMap(); scouts.js stackSection; ranker.js applyFirst).
import { api } from "@/lib/api"

// ---------- Credits ----------
export type CreditState = "ACTIVE" | "NOT_ACTIVATED" | "USED_UP" | "ENDED"
export type Credit = {
  id: string
  provider: string
  level: "DONE" | "ACTIVATE" | "NEEDS_DATES" | "URGENT" | "SOON" | "OK" | string
  label: string
  allowance: string | null
  covers: string | null
  started_on: string | null
  ends_on: string | null
  expires_on: string | null
  days_left: number | null
  term_months: number | null
  after_expiry: string | null
  balance_note: string | null
  balance_checked_on: string | null
  balance_stale: boolean
  notes: string | null
  account_email: string | null
  state: CreditState
  program_url: string | null
}
export type StackItem = { id: string; item: string; provider: string | null; monthly_usd: number | null; covered_by: string | null }
export type Stack = { items: StackItem[]; credit_providers: string[]; monthly_uncovered: number; monthly_covered: number }

export const CREDIT_STATE_WORDS: [CreditState, string][] = [
  ["ACTIVE", "Active"], ["NOT_ACTIVATED", "Not activated yet"], ["USED_UP", "Used up"], ["ENDED", "Ended"],
]

// The stack is optional: when it fails the old page showed the credits without it.
export async function loadCredits(): Promise<{ credits: Credit[]; stack: Stack | null }> {
  const [credits, stack] = await Promise.all([api<Credit[]>("/api/credits"), api<Stack>("/api/stack").catch(() => null)])
  return { credits, stack }
}

// A credit that ends within 14 days is a deadline (the only time it is shown in red).
export const creditDue = (c: Credit) => c.level !== "DONE" && c.days_left != null && c.days_left >= 0 && c.days_left <= 14

export const creditTone = (c: Credit): "urgent" | "review" | "quiet" =>
  creditDue(c) ? "urgent" : c.level === "NEEDS_DATES" || c.level === "ACTIVATE" ? "review" : "quiet"

// The choices for "Covered by": not covered, every credit provider, and the saved value when it is no longer one.
export function coverChoices(providers: string[], current?: string | null) {
  const list = providers.filter((p) => p && p !== current)
  return current ? [...list, current] : list
}

// ---------- Money map ----------
export type Access = { level: string; label: string; detail?: string; application_id?: string }
export type Program = {
  id: string
  name: string
  amount: string
  kind: string
  deadline: string | null
  days: number | null
  rolling: boolean
  outcome: string | null
  access: Access | null
  application_id: string | null
  edition: { id: string; stage: string } | null
}
export type Category = { key: string; title: string; note: string; programs: Program[] }
export type MoveState = "TODO" | "DOING" | "DONE"
export type Move = { id: string; grp: string; title: string; detail: string; state: MoveState }
export type RankRow = {
  opportunity_id: string
  name: string
  kind?: string
  reason: string
  per_hour: number
  expected_value: number
  deadline?: string | null
  money: { amount?: number | null; counted: number; basis: string }
  likelihood: { value: number; fit: number; fit_known: boolean; eligibility: string; eligibility_factor: number }
  hours: { value: number; source: string }
  urgency: { factor: number; days: number | null }
  preparation?: { summary?: string; application_id?: string | null; questions?: number; edition?: { id: string } | null } | null
}
export type ApplyFirst = { rows: RankRow[]; unpriced?: { name: string }[] }
export type MoneyMap = { moves: Move[]; categories: Category[]; apply_first?: ApplyFirst | null }

export const MOVE_STATES: [MoveState, string][] = [["TODO", "To do"], ["DOING", "Doing"], ["DONE", "Done"]]

export const loadMoney = () => api<MoneyMap>("/api/money")

// A program is finished when it has an outcome or nothing is left to prepare.
export const programDone = (p: Program) => !!p.outcome || p.access?.level === "FINISHED"

const ACCESS_SHORT: Record<string, string> = { READY: "Answers ready", DRAFTING: "Agent drafting", NOT_CHECKED: "Form not read yet", FINISHED: "Finished" }

// The status word for a program and its tone: the outcome when there is one, else where the application stands.
export function programStatus(p: Program): { text: string; tone: "good" | "review" | "quiet" } {
  if (p.outcome) return { text: p.outcome, tone: ["Accepted", "Won", "ACCEPTED"].includes(p.outcome) ? "good" : "quiet" }
  const a = p.access
  if (!a) return { text: "Not started", tone: "quiet" }
  if (a.level === "BLOCKED") {
    const t = a.label.replace(/^Blocked:\s*/, "")
    // Blocked waits on Bao (a login, a link): that is "needs you", not a failure, so it is never red.
    return { text: t ? t[0].toUpperCase() + t.slice(1) : "Blocked", tone: "review" }
  }
  return { text: ACCESS_SHORT[a.level] || a.label, tone: a.level === "READY" || a.level === "DRAFTING" ? "review" : "quiet" }
}

export const pitchStageWords = (stage: string) => (stage === "READY" ? "ready" : stage === "APPROVED" ? "approved" : "in progress")

// A deadline is shown in red only when it is today or within the next 14 days.
export const closingSoon = (days: number | null | undefined) => days != null && days >= 0 && days <= 14

// A monthly cost, with cents only when it has them: "$20", "$12.50".
export const cost = (v: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: Number.isInteger(v) ? 0 : 2, maximumFractionDigits: 2 }).format(v)

// The one plain line for a ranked program: what is at stake, the work it takes, and where the preparation stands.
// The arithmetic behind the rank stays behind "How this was figured".
export function rankLine(r: RankRow) {
  const hours = r.hours.value
  const prep = (r.preparation?.summary || "").replace(/\s*Nothing left for the agents; the rest is yours\.\s*$/, "").trim()
  return { amount: r.money.amount ?? r.money.counted, credits: r.kind === "CREDITS", work: `about ${hours} ${hours === 1 ? "hour" : "hours"} of work`, prep }
}

// The one segmented control (the same as the Pipeline's views): a quiet tray, the chosen one raised.
export const SEG_TRAY = "flex flex-wrap gap-1 rounded-lg bg-secondary p-1"
export const SEG = "flex h-11 items-center gap-1.5 rounded-md px-4 text-base font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid disabled:opacity-50"
export const SEG_ON = "bg-card font-semibold text-foreground ring-1 ring-foreground/10"

// Links inside text and tables: navy, underlined, 44px tall to press.
export const LINK = "inline-flex min-h-11 items-center rounded-md font-medium text-primary underline underline-offset-4 hover:no-underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"
