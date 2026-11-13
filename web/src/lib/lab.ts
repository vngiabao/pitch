// Pitch Lab data: the shapes /api/lab and /api/lab/<id> return, and the words the old app used for them
// (app.js LAB_KIND_WORDS, LAB_AGENTS, AGENT_WORDS, stageChip, labGroups, labCard).
/* eslint-disable @typescript-eslint/no-explicit-any */
import { cleanName, plural, prettyKey } from "@/lib/format"

export type LabSummary = { low?: number; avg?: number; timing?: { seconds: number; words?: number } }
export type LabItem = {
  id: string; kind: string; title: string; stage: string; stage_words: string; round: number
  error?: string | null; summary?: LabSummary | null; updated_at?: string; created_at?: string; subject_id?: string | null
}
export type Lesson = { id: string; state: string; body: string; evidence?: string; applies_to: string }
export type Lab = { items: LabItem[]; lessons: Lesson[]; stages?: Record<string, number>; voice_examples: number }
export type LabOptions = {
  programs: { id: string; name: string }[]
  pitches: { id: string; title: string }[]
  applications: { id: string; program: string }[]
}

export type CoachScore = { criterion: string; score: number; why: string; fix: string }
export type Coach = {
  summary?: string; top_fixes?: string[]; scores?: CoachScore[]
  hard_questions?: { question: string; answer: string; gap?: string }[]
}
export type Review = {
  agent: string; round: number; verdict: string; created_at: string
  detail: { issues?: ({ text?: string } | string)[]; changed?: string[]; answers_to_feedback?: string[] }
}
export type Rules = {
  minutes?: number | string; format?: string; slide_limit?: number | string | null; prize?: string; equity?: string
  deadline?: string; judging_criteria?: string[]; required_sections?: string[]; source_urls?: string[]
}
export type Brief = {
  rules?: Rules; strategy?: string
  script?: { title: string; text: string; seconds?: number }[]
  slide_plan?: { action: string; slide_id: string; change: string; why: string }[]
  ask?: string; materials?: string[]; open_questions?: string[]
}
export type SlideQa = {
  available?: boolean; blocking?: number; warnings?: number; reason?: string
  slides?: { n: number; id: string; issues: { severity: string; text: string }[] }[]
}
export type LabDetail = LabItem & {
  flow: string[]
  coach?: Coach | null
  reviews: Review[]
  payload: {
    minutes?: number
    timing?: { words: number; seconds: number }
    unresolved?: { from: string; text: string; where?: string }[]
    brief?: Brief
    edition?: { slides: any[]; core: string; round: number; new_slides?: any[] }
    slide_qa?: SlideQa
    answers?: { question_id: string; question: string; text: string; suggested?: string; limit?: number | null; unit?: string | null }[]
    fact_issues?: { where: string; severity: string; text: string }[]
    text?: string; title?: string; body?: string
  }
}

export const LAB_KIND_WORDS: Record<string, string> = {
  PITCH_EDITION: "Program edition", PITCH_REVIEW: "Pitch review", APPLICATION_SET: "Application answers",
  GROWTH_DRAFT: "Outreach draft", OUTCOME_LESSON: "Lessons from a result", VOICE_RULES: "Lessons from your edits",
}
export const kindWords = (kind: string) => LAB_KIND_WORDS[kind] || prettyKey(kind)

// The nine steps every draft goes through, in plain words (no internal agent names): [stage key, the step, what it does]
export const LAB_AGENTS: [string, string, string][] = [
  ["TAILOR", "Draft", "Reads the program’s rules and builds the edition from the master deck"],
  ["FACT_CHECK", "Fact check", "Every number and claim traced to approved facts"],
  ["VOICE", "Your voice", "Rewrites the wording the way you write"],
  ["FACT_RECHECK", "Second fact check", "Makes sure the rewrite changed no facts"],
  ["COACH", "Pitch review", "Scores it like a YC partner and sends fixes back"],
  ["FORMAT", "Limits check", "Time, slide and word limits"],
  ["BUILD", "Deck build", "Builds the deck from the core deck’s own slides"],
  ["SLIDE_QA", "Slide check", "Renders every slide and checks the layout"],
  ["READY", "You", "Edit, approve, and submit it yourself"],
]
// Who did a step in an item's history, and who left a note, in the same plain words
export const AGENT_WORDS: Record<string, string> = {
  TAILOR: "Draft", FACT_GUARD: "Fact check", VOICE: "Your voice", COACH: "Pitch review", FORMAT: "Limits check",
  BUILDER: "Deck build", SLIDE_QA: "Slide check", OWNER: "You", LEARNER: "Lessons from the result",
}
export const agentName = (key: string) => AGENT_WORDS[key] || prettyKey(String(key).toLowerCase())
const FROM_WORDS: Record<string, string> = {
  "Fact Guard": "Fact check", "Format Check": "Limits check", "Edition Builder": "Deck build", "Slide QA": "Slide check",
  "Pitch Coach": "Pitch review", "Pitch Tailor": "Draft", "Bao’s Voice": "Your voice", Bao: "You",
}
export const fromWords = (from: string) => FROM_WORDS[from] || from
// What kind of work a lesson applies to
const LESSON_FOR: Record<string, string> = {
  TAILOR: "drafts", FACT_GUARD: "fact checks", VOICE: "your voice", COACH: "pitch reviews", FORMAT: "limit checks",
  BUILDER: "deck builds", SLIDE_QA: "slide checks", HUNTER: "program research", LEARNER: "lessons",
}
export const lessonFor = (key: string) => LESSON_FOR[key] || prettyKey(String(key).toLowerCase()).toLowerCase()
// The name of a step in an item's flow (old progressLine)
export const stepName = (stage: string) => (stage === "READY" ? "You" : LAB_AGENTS.find((a) => a[0] === stage)?.[1] || (stage === "LEARN" ? "Lessons from the result" : prettyKey(stage.toLowerCase())))

// What is happening at each stage, in plain words (the server's own words name the agents)
const STAGE_WORDS: Record<string, string> = {
  TAILOR: "Drafting", FACT_CHECK: "Checking the facts", VOICE: "Putting it in your voice", FACT_RECHECK: "Rechecking the facts",
  COACH: "Reviewing the pitch", FORMAT: "Checking time and limits", BUILD: "Building the deck", SLIDE_QA: "Checking every slide",
  LEARN: "Learning from the result", READY: "Ready for you", APPROVED: "Approved by you", ARCHIVED: "Archived",
}
export const stageWords = (it: { stage: string; stage_words?: string }) => STAGE_WORDS[it.stage] || it.stage_words || prettyKey(it.stage.toLowerCase())

// A draft's name without the "Answers:", "Voice:" or "Lessons:" prefix; the kind line under it already says which it is
export const displayTitle = (title: string) => cleanName(String(title || "").replace(/^(answers|voice|lessons):\s*/i, ""))

// How a step ended, as a status word (green = passed or done, navy = sent back for you or another round)
export function verdictTag(verdict: string): { tone: "urgent" | "good" | "review" | "quiet"; words: string } {
  const known: Record<string, { tone: "urgent" | "good" | "review" | "quiet"; words: string }> = {
    PASS: { tone: "good", words: "Passed" }, BUILT: { tone: "good", words: "Built" }, APPROVED: { tone: "good", words: "Approved" },
    EDITED: { tone: "quiet", words: "Reworded" }, DRAFTED: { tone: "quiet", words: "Drafted" },
    REVISE: { tone: "review", words: "Fixes sent back" }, PROPOSED: { tone: "review", words: "Lessons proposed" },
    BLOCK: { tone: "review", words: "Needs fixes" }, FAIL: { tone: "urgent", words: "Failed" }, FAILED: { tone: "urgent", words: "Failed" }, ERROR: { tone: "urgent", words: "Failed" },
  }
  return known[verdict] || { tone: "quiet", words: prettyKey(String(verdict).toLowerCase()) }
}

// The status word for an item and its colour (old stageChip)
export function stageTag(it: Pick<LabItem, "stage" | "stage_words" | "round" | "error">): { tone: "urgent" | "good" | "review" | "quiet"; words: string } {
  const done = it.stage === "APPROVED"
  const words = (it.error ? "Stopped, needs a retry" : it.stage === "READY" ? "Ready for review" : stageWords(it)) + (it.round > 1 && !done ? ` · round ${it.round}` : "")
  return { tone: it.error ? "urgent" : done ? "good" : it.stage === "READY" ? "review" : "quiet", words }
}

// "about 1.1 min" from seconds, as the old app rounded it
export const spokenMinutes = (seconds: number) => Math.round(seconds / 6) / 10

// The line under an item's name (old labCard)
export function itemLine(it: LabItem) {
  const s = it.summary || {}
  return [
    kindWords(it.kind),
    s.low ? `${plural(s.low, "note")} to fix` : s.avg ? "Coach checked" : "",
    s.timing ? `about ${spokenMinutes(s.timing.seconds)} min spoken` : "",
  ].filter(Boolean).join(" · ")
}

const LIVE_KINDS = ["PITCH_EDITION", "PITCH_REVIEW", "APPLICATION_SET"]
const when = (it: LabItem) => String(it.updated_at || it.created_at || "")

// What the list page shows (old pitchLab): ready and in-progress drafts of the three kinds Bao starts, and the approved ones.
export function sortLab(lab: Lab) {
  const live = lab.items.filter((x) => !["APPROVED", "ARCHIVED"].includes(x.stage) && LIVE_KINDS.includes(x.kind))
  return {
    ready: groupByProgram(live.filter((x) => x.stage === "READY")),
    working: live.filter((x) => x.stage !== "READY"),
    approved: lab.items.filter((x) => x.stage === "APPROVED"),
    hasFinished: lab.items.some((x) => ["APPROVED", "ARCHIVED"].includes(x.stage)),
    proposed: lab.lessons.filter((l) => l.state === "PROPOSED"),
    approvedLessons: lab.lessons.filter((l) => l.state === "APPROVED"),
  }
}

// One group per program: the newest draft leads and older rounds fold behind it (old labGroups)
export function groupByProgram(items: LabItem[]): LabItem[][] {
  const groups = new Map<string, LabItem[]>()
  for (const it of [...items].sort((a, b) => when(b).localeCompare(when(a)))) {
    const k = String(it.title || "").replace(/^answers:\s*/i, "").replace(/\s+·.*$/, "").trim().toLowerCase()
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k)!.push(it)
  }
  return [...groups.values()]
}
export const programOf = (it: LabItem) => displayTitle(it.title)

// Where an item stands in its flow: "Step 2 of 5", the step's name, and a 0-100 value for the bar (old progressLine)
export function progressOf(it: Pick<LabDetail, "flow" | "stage">) {
  const total = it.flow.length, at = it.flow.indexOf(it.stage), approved = it.stage === "APPROVED"
  if (approved) return { words: `All ${plural(total, "step")} done`, pct: 100, at: total }
  if (at < 0) return { words: "", pct: 0, at: -1 }
  return { words: `Step ${at + 1} of ${total} · ${stepName(it.stage)}`, pct: Math.round(((at + 1) / total) * 100), at }
}

// The whole script as one text to copy (old pitchLabItem `whole`)
export const wholeScript = (script: NonNullable<Brief["script"]>) => script.map((x, i) => `SLIDE ${i + 1} - ${x.title}\n${x.text}`).join("\n\n")

// Slide QA in one line, and its issues in slide order (old deckSection)
export function qaSummary(q?: SlideQa) {
  const issues = (q?.slides || []).flatMap((s) => s.issues.map((i) => ({ ...i, n: s.n })))
  const head = q?.available
    ? (q.blocking ? `${plural(q.blocking, "layout problem")} to fix` : "No layout problems") + (q.warnings ? ` · ${plural(q.warnings, "thing")} to look at` : "")
    : "The slide check did not run" + (q?.reason ? `: ${q.reason}` : "")
  return { head, issues, bad: !!q?.blocking }
}

// Whole days until the end of a yyyy-mm-dd day; null when the rules give the deadline in words
export function daysUntil(day?: string) {
  if (!day || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return null
  return Math.ceil((new Date(day + "T23:59:59").getTime() - Date.now()) / 86400000)
}
