// Words, dates and money, ported from the old app's helpers (app.js lines 1-79) so every page says things the same way.
// All dates are shown in America/New_York.
/* eslint-disable @typescript-eslint/no-explicit-any */

export const TZ = "America/New_York"

export const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`

export const money = (v: number | null | undefined, unknown = "Unknown") =>
  v == null ? unknown : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v)
export const usd = (v: number | null | undefined) => money(v, "")

// Date-only strings are pinned to noon so the day never shifts across time zones.
const asDate = (v: string) => new Date(/^\d{4}-\d{2}-\d{2}$/.test(v) ? v + "T12:00:00" : v)

// "Nov 2, 2026"
export const deadlineLabel = (v?: string | null) =>
  v ? asDate(v).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: TZ }) : ""
// "Tue, Nov 11"
export const shortDay = (v?: string | null) =>
  v ? asDate(v).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: TZ }) : ""
// "Nov 11"
export const dayLabel = (v?: string | null) =>
  v ? asDate(v).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: TZ }) : ""
// "Nov 11, 2026, 9:00 AM EST"; "Not yet verified" when empty
export const readableDate = (v?: string | null) =>
  v ? asDate(v).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short", timeZone: TZ }) : "Not yet verified"
// A moment, short: "Oct 26, 9:12 AM" this year, "Oct 26, 2025, 9:12 AM" in another year. No time zone (all Eastern).
export function stamp(v?: string | null) {
  if (!v) return ""
  const d = asDate(v)
  const sameYear = d.toLocaleDateString("en-US", { year: "numeric", timeZone: TZ }) === new Date().toLocaleDateString("en-US", { year: "numeric", timeZone: TZ })
  return d.toLocaleString("en-US", { month: "short", day: "numeric", ...(sameYear ? {} : { year: "numeric" }), hour: "numeric", minute: "2-digit", timeZone: TZ })
}
// A day, short: "Oct 26" this year, "Oct 26, 2025" in another year
export function day(v?: string | null) {
  if (!v) return ""
  const d = asDate(String(v).length > 10 ? v : String(v).slice(0, 10))
  const sameYear = d.toLocaleDateString("en-US", { year: "numeric", timeZone: TZ }) === new Date().toLocaleDateString("en-US", { year: "numeric", timeZone: TZ })
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", ...(sameYear ? {} : { year: "numeric" }), timeZone: TZ })
}
// "Nov 11, 2026" from the first 10 characters (old fmtDay)
export const fmtDay = (v?: string | null) => (v ? deadlineLabel(String(v).slice(0, 10)) : "")

// The deadline has passed (end of that day, local time)
export const isClosed = (iso?: string | null) => !!iso && new Date(String(iso).slice(0, 10) + "T23:59:59").getTime() < Date.now()

// "Closes today / tomorrow / in N days · Nov 2", "Closed", "No deadline published", "Closing time unverified"
export function closingWords(days: number | null | undefined, deadline?: string | null) {
  if (!deadline) return "No deadline published"
  if (days == null) return "Closing time unverified"
  if (days < 0) return "Closed"
  const when = days === 0 ? "Closes today" : days === 1 ? "Closes tomorrow" : `Closes in ${days} days`
  return `${when} · ${dayLabel(deadline)}`
}

export const hoursWords = (h?: number | null) => (h == null ? "" : h < 1 ? "Under an hour" : `About ${Math.round(h * 2) / 2} ${Math.round(h * 2) / 2 === 1 ? "hour" : "hours"}`)

// snake_case -> "Snake case"
export const prettyKey = (k: string) => { const s = String(k || "").replace(/_/g, " ").trim(); return s ? s[0].toUpperCase() + s.slice(1) : "" }

export const fileSize = (b?: number | null) => (b == null ? "" : b < 1024 * 1024 ? `${Math.max(1, Math.round(b / 1024))} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`)

// seconds -> "30 sec", "3 min", "1 min 30 sec"
export function pitchLength(s?: number | null) {
  if (!s) return ""
  const m = Math.floor(s / 60), r = s % 60
  return [m ? `${m} min` : "", r ? `${r} sec` : ""].filter(Boolean).join(" ")
}

// Word or character count against a limit
export const countWords = (t: string) => (String(t || "").trim().match(/\S+/g) || []).length
export function countLabel(text: string, limit?: number | null, unit: "words" | "characters" = "words") {
  const n = unit === "words" ? countWords(text) : String(text || "").length
  if (!limit) return `${n} ${unit}`
  return `${n} of ${limit} ${unit}${n > limit ? ", over limit" : ""}`
}

// "Up to $X", "Up to $X credits", "Amount unknown"
export function moneyFigure(d: any) {
  const f = d?.data?.funding || {}
  if (f.cash_prize_max != null) return `Up to ${money(f.cash_prize_max)}`
  if (f.credits_value != null) return `Up to ${money(f.credits_value)} credits`
  return "Amount unknown"
}

// A program's short name: "Duquesne New Venture Challenge - 2026" -> "Duquesne New Venture Challenge"
export const programName = (name: string) => String(name || "").split(" - ")[0]

// A program's or pitch's name as shown: a long dash between words reads as " - " (the house style has no em dashes).
export const cleanName = (name?: string | null) => String(name ?? "").replace(/\s*—\s*/g, " - ")

// Clipboard, with the old app's fallback for browsers that refuse navigator.clipboard.
export async function copyText(text: string) {
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
