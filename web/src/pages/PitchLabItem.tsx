import { useState, type FormEvent, type ReactNode } from "react"
import { Check, Copy, Download, ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { CopyBox as WideCopyBox, Disclosure, Empty, Field, LoadGate, PageHead, Panel, Tag, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { copyText, countWords, day, plural, prettyKey, stamp } from "@/lib/format"
import { agentName, daysUntil, displayTitle, fromWords, kindWords, progressOf, qaSummary, spokenMinutes, stageWords, stepName, verdictTag, wholeScript, type Coach, type LabDetail, type Review } from "@/lib/lab"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"
import { ShowAll, StageTag } from "@/pages/PitchLab"

const unitOf = (u?: string | null) => (u === "characters" ? "characters" : "words")
const bullets = "flex max-w-[70ch] list-disc flex-col gap-2 pl-5 text-base"
const subhead = "text-base font-semibold"

// Text to copy, held to a readable line (about 70 characters) however wide its panel is
function CopyBox(props: Parameters<typeof WideCopyBox>[0]) {
  return <div className="w-full max-w-[calc(70ch+2rem)]"><WideCopyBox {...props} /></div>
}
// A short fact from the program's rules: a 14px label over 16px text (these are sentences, not figures)
function Rule({ label, children, tone }: { label: string; children: ReactNode; tone?: "money" | "deadline" }) {
  return (
    <div className="flex max-w-[70ch] flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn("text-base font-semibold", tone === "money" && "text-money", tone === "deadline" && "text-deadline")}>{children}</span>
    </div>
  )
}

// Where the item stands: the stage as a word, "Step 2 of 5", and a bar. The step names sit one press away.
function StatusPanel({ it }: { it: LabDetail }) {
  const ready = ["READY", "APPROVED"].includes(it.stage)
  const p = progressOf(it)
  const unresolved = it.payload.unresolved || []
  const title = it.error ? "An agent step stopped" : it.stage === "APPROVED" ? "You approved this" : it.stage === "READY" ? "Ready for you" : stageWords(it)
  return (
    <Panel title={title} aside={<StageTag it={it} />}>
      {p.words && (
        <div className="flex flex-col gap-2">
          <span className="text-sm text-muted-foreground">{p.words}</span>
          <Progress value={p.pct} className="h-1.5 max-w-[28rem]" aria-label={p.words} />
        </div>
      )}
      {it.error && (
        <p className="max-w-[70ch] text-base text-deadline">{it.error.slice(0, 300)}</p>
      )}
      {it.error && <p className="max-w-[70ch] text-base text-muted-foreground">Ask for another round to try the step again.</p>}
      {!ready && !it.error && (
        <p className="max-w-[70ch] text-base text-muted-foreground">This page fills in as each step finishes. One step runs every few minutes.</p>
      )}
      {ready && (
        <p className="max-w-[70ch] text-base text-muted-foreground">
          {it.kind === "PITCH_EDITION"
            ? "Save the script to Pitch Studio to rehearse and edit it. Your edits teach the next draft how you write."
            : "Copy what you need. Your own rewrites teach the next draft how you write."}
        </p>
      )}
      {ready && unresolved.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className={subhead}>Still needs your eyes</h4>
          <ul className="flex flex-col">
            {unresolved.map((u, i) => (
              <li key={i} className="max-w-[70ch] border-t py-3 text-base first:border-t-0">
                <span className="font-semibold">{fromWords(u.from)}</span> {u.text}{u.where && <span className="text-muted-foreground"> ({u.where})</span>}
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">These could not be fixed without you. Fix them yourself or run another round.</p>
        </div>
      )}
      {it.flow.length > 0 && (
        <Disclosure label={`See all ${plural(it.flow.length, "step")}`}>
          <ol className="flex flex-col">
            {it.flow.map((s, i) => {
              const done = it.stage === "APPROVED" || (p.at >= 0 && i < p.at), current = i === p.at && it.stage !== "APPROVED"
              return (
                <li key={s + i} className="flex min-h-11 items-center gap-3 border-t text-base first:border-t-0">
                  <span className="w-6 shrink-0 tabular-nums text-muted-foreground">{i + 1}.</span>
                  <span className={cn("flex-1", current && "font-semibold")}>{stepName(s)}</span>
                  {done && <Tag tone="good">Done</Tag>}
                  {current && <Tag tone={it.error ? "urgent" : "review"}>{it.error ? "Stopped" : "Now"}</Tag>}
                </li>
              )
            })}
          </ol>
        </Disclosure>
      )}
    </Panel>
  )
}

function DeckPanel({ it, busy, onBuild }: { it: LabDetail; busy: string; onBuild: () => void }) {
  const e = it.payload.edition
  const building = busy === "build"
  if (!e) return (
    <Panel title="The deck">
      <p className="max-w-[70ch] text-base text-muted-foreground">This edition was made before decks were built here. Build it from the core deck’s own slides and check every slide.</p>
      <Button variant="outline" size="lg" className="self-start" disabled={!!busy} onClick={onBuild}>{building ? "Building and checking…" : "Build the deck"}</Button>
    </Panel>
  )
  const qa = qaSummary(it.payload.slide_qa)
  const fresh = e.new_slides?.length || 0
  return (
    <Panel title="The deck" aside={plural(e.slides.length, "slide")}>
      <p className="text-base font-semibold">{qa.head}</p>
      <p className="max-w-[70ch] text-base text-muted-foreground">
        Built from the core deck ({e.core}) in round {e.round}. Core slides keep their design; only order, notes and page numbers change.
        {fresh > 0 && ` ${plural(fresh, "new slide")} drafted from a plain template: design ${fresh > 1 ? "them" : "it"} before you present.`}
      </p>
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" size="lg" asChild>
          <a href={`/edition/${encodeURIComponent(it.id)}`} target="_blank" rel="noopener"><ExternalLink aria-hidden="true" />Open the deck preview</a>
        </Button>
        <Button variant="outline" size="lg" asChild>
          <a href={`/api/lab/${encodeURIComponent(it.id)}/edition.zip`}><Download aria-hidden="true" />Download the deck files</a>
        </Button>
        <Button variant="outline" size="lg" disabled={!!busy} onClick={onBuild}>{building ? "Building and checking…" : "Rebuild and check again"}</Button>
      </div>
      {qa.issues.length > 0 && (
        <>
          <ul className="flex flex-col">
            {qa.issues.slice(0, 12).map((i, k) => (
              <li key={k} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t py-3 text-base first:border-t-0">
                <span className="w-16 shrink-0 font-semibold">Slide {i.n}</span>
                <span className="max-w-[70ch] min-w-0 flex-1">{i.text}</span>
                {i.severity === "block" && <Tag tone="review">Fix before you present</Tag>}
              </li>
            ))}
          </ul>
          {qa.issues.length > 12 && <p className="text-sm text-muted-foreground">{qa.issues.length - 12} more in the preview.</p>}
        </>
      )}
    </Panel>
  )
}

function Dots({ n }: { n: number }) {
  return (
    <span className="flex items-center gap-2 whitespace-nowrap">
      <span className="flex gap-1" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((i) => <i key={i} className={cn("size-2 rounded-full", i <= n ? "bg-primary" : "bg-track")} />)}
      </span>
      <span className="text-sm tabular-nums text-muted-foreground">{n} of 5</span>
    </span>
  )
}

function CoachPanels({ c }: { c: Coach }) {
  const fixes = c.top_fixes || [], scores = c.scores || [], hard = c.hard_questions || []
  return (
    <>
      <Panel title="Pitch review" aside="A YC partner’s read">
        {c.summary && <p className="max-w-[70ch] text-base">{c.summary}</p>}
        {fixes.length > 0 && (
          <div className="flex flex-col gap-2">
            <h4 className={subhead}>The {fixes.length === 3 ? "three " : ""}fixes that matter most</h4>
            <ol className="flex max-w-[70ch] list-decimal flex-col gap-2 pl-5 text-base">{fixes.map((f, i) => <li key={i}>{f}</li>)}</ol>
          </div>
        )}
        {scores.length > 0 && (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow><TableHead>What is scored</TableHead><TableHead>Score</TableHead><TableHead>Why, and the fix</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {scores.map((s) => (
                  <TableRow key={s.criterion}>
                    <TableCell className="align-top font-semibold">{s.criterion}</TableCell>
                    <TableCell className="align-top"><Dots n={s.score} /></TableCell>
                    <TableCell className="min-w-[18rem] align-top whitespace-normal">
                      <p className="max-w-[70ch] text-base text-muted-foreground">{s.why}</p>
                      {s.score < 5 && s.fix && <p className="max-w-[70ch] pt-1 text-base"><span className="font-semibold">Fix:</span> {s.fix}</p>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Panel>
      {hard.length > 0 && (
        <Panel title="Questions they will ask" aside="Rehearse these">
          <ShowAll items={hard} first={5} noun="questions">
            {(shown) => (
              <ul className="flex flex-col">
                {shown.map((h, i) => (
                  <li key={i} className="flex flex-col gap-2 border-t py-4 first:border-t-0 first:pt-0">
                    <h4 className={cn(subhead, "max-w-[70ch]")}>{h.question}</h4>
                    <CopyBox text={h.answer} />
                    {h.gap && <p className="max-w-[70ch] text-sm text-muted-foreground"><span className="font-semibold text-foreground">Missing proof:</span> {h.gap}</p>}
                  </li>
                ))}
              </ul>
            )}
          </ShowAll>
        </Panel>
      )}
    </>
  )
}

function CopyAll({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <Button variant="outline" size="lg" className="self-start" onClick={async () => { if (await copyText(text)) { setDone(true); setTimeout(() => setDone(false), 1600) } }}>
      {done ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{done ? "Copied" : "Copy the whole script"}
    </Button>
  )
}

function ScriptPanel({ it }: { it: LabDetail }) {
  const p = it.payload, script = p.brief?.script || []
  return (
    <Panel title="Timed script" aside={p.timing ? `${p.timing.words} words · about ${spokenMinutes(p.timing.seconds)} of ${p.minutes} min` : undefined}>
      <CopyAll text={wholeScript(script)} />
      <ul className="flex flex-col">
        {script.map((x, i) => (
          <li key={i} className="flex flex-col gap-2 border-t py-4 first:border-t-0">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h4 className={subhead}><span className="tabular-nums text-muted-foreground">{i + 1}.</span> {x.title}</h4>
              <span className="text-sm tabular-nums text-muted-foreground">{x.seconds ? `${x.seconds} sec · ` : ""}{plural(countWords(x.text), "word")}</span>
            </div>
            <CopyBox text={x.text} />
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function SlidePlanPanel({ it }: { it: LabDetail }) {
  const plan = it.payload.brief?.slide_plan || []
  return (
    <Panel title="Slide plan">
      {plan.length ? (
        <ul className="flex flex-col">
          {plan.map((x, i) => (
            <li key={i} className="flex flex-col gap-1 border-t py-3 first:border-t-0">
              <div className="flex flex-wrap items-center gap-3">
                <Tag>{prettyKey(x.action)}</Tag>
                <span className="text-base font-semibold">{x.slide_id}</span>
              </div>
              <p className="max-w-[70ch] text-base">{x.change}</p>
              <p className="max-w-[70ch] text-base text-muted-foreground">{x.why}</p>
            </li>
          ))}
        </ul>
      ) : <Empty>No slide changes planned.</Empty>}
    </Panel>
  )
}

function RulesPanel({ it }: { it: LabDetail }) {
  const rules = it.payload.brief?.rules || {}
  const days = daysUntil(rules.deadline), iso = days !== null
  const facts: [string, string | number | null | undefined, ("money" | "deadline")?][] = [
    ["Format", rules.format], ["Slide limit", rules.slide_limit], ["Prize", rules.prize, "money"], ["Terms", rules.equity],
    ["Deadline", rules.deadline ? (iso ? day(rules.deadline) : rules.deadline) : "", days !== null && days >= 0 && days <= 14 ? "deadline" : undefined],
  ]
  const urls = rules.source_urls || []
  return (
    <Panel title="The program’s rules" aside={rules.minutes ? `${rules.minutes} min` : undefined}>
      <div className="flex flex-col gap-4">
        {facts.filter((f) => f[1]).map(([k, v, tone]) => <Rule key={k} label={k} tone={tone}>{v}</Rule>)}
      </div>
      {(rules.judging_criteria || []).length > 0 && (
        <div className="flex flex-col gap-2"><h4 className={subhead}>What judges score</h4><ul className={bullets}>{rules.judging_criteria!.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
      )}
      {(rules.required_sections || []).length > 0 && (
        <div className="flex flex-col gap-2"><h4 className={subhead}>Required sections</h4><ul className={bullets}>{rules.required_sections!.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
      )}
      {urls.length ? (
        <ul className="flex flex-col">
          {urls.map((u) => (
            <li key={u}>
              <a href={u} target="_blank" rel="noopener noreferrer" className="flex min-h-11 items-center gap-2 rounded-md text-base font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
                <ExternalLink className="size-4 shrink-0" aria-hidden="true" /><span className="truncate">{u.replace(/^https?:\/\//, "").slice(0, 60)}</span>
              </a>
            </li>
          ))}
        </ul>
      ) : <p className="text-base text-muted-foreground">Rules not read from an official page yet. Confirm them before you pitch.</p>}
    </Panel>
  )
}

function AnswersPanel({ it }: { it: LabDetail }) {
  const p = it.payload, answers = p.answers || []
  return (
    <Panel title="Answers, in your voice" aside="Copy the version you prefer">
      <ShowAll items={answers} first={6} noun="answers">
        {(shown) => (
          <ul className="flex flex-col">
            {shown.map((a) => {
              const issues = (p.fact_issues || []).filter((i) => i.where === a.question_id && i.severity !== "fixed")
              const voiced = !!a.suggested && a.suggested !== a.text
              return (
                <li key={a.question_id} className="flex flex-col gap-2 border-t py-4 first:border-t-0 first:pt-0">
                  <h4 className={cn(subhead, "max-w-[70ch]")}>{a.question}</h4>
                  {voiced ? (
                    <>
                      <span className="text-sm text-muted-foreground">In your voice</span>
                      <CopyBox text={a.suggested!} limit={a.limit} unit={unitOf(a.unit)} />
                      <Disclosure label="Original draft"><CopyBox text={a.text} limit={a.limit} unit={unitOf(a.unit)} /></Disclosure>
                    </>
                  ) : <CopyBox text={a.text} limit={a.limit} unit={unitOf(a.unit)} />}
                  {issues.map((i, k) => <p key={k} className={cn("max-w-[70ch] text-sm", i.severity === "block" ? "font-semibold text-foreground" : "text-muted-foreground")}>{i.text}</p>)}
                </li>
              )
            })}
          </ul>
        )}
      </ShowAll>
    </Panel>
  )
}

function reviewLine(r: Review) {
  const issues = r.detail.issues || []
  return [
    `Round ${r.round}`,
    issues.length ? plural(issues.length, "note") : "",
    r.detail.changed ? `${plural(r.detail.changed.length, "part")} reworded` : "",
  ].filter(Boolean).join(" · ")
}

function HistoryPanel({ reviews }: { reviews: Review[] }) {
  return (
    <Panel title="How it was made" aside={reviews.length ? plural(reviews.length, "step") : undefined}>
      {reviews.length ? (
        <ShowAll items={reviews} first={6} noun="steps">
          {(shown) => (
            <ol className="flex flex-col">
              {shown.map((r, k) => {
                const issues = r.detail.issues || [], answers = r.detail.answers_to_feedback || []
                return (
                  <li key={k} className="flex flex-col gap-1 border-t py-3 first:border-t-0">
                    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                      <span className="text-base font-semibold">{agentName(r.agent)}</span>
                      <Tag tone={verdictTag(r.verdict).tone}>{verdictTag(r.verdict).words}</Tag>
                    </div>
                    <span className="text-sm text-muted-foreground">{reviewLine(r)} · {stamp(r.created_at)}</span>
                    {(issues.length > 0 || answers.length > 0) && (
                      <Disclosure label="What it said">
                        <ul className={bullets}>
                          {issues.slice(0, 6).map((i, n) => <li key={"i" + n}>{typeof i === "string" ? i : i.text}</li>)}
                          {answers.map((x, n) => <li key={"a" + n}>{x}</li>)}
                        </ul>
                      </Disclosure>
                    )}
                  </li>
                )
              })}
            </ol>
          )}
        </ShowAll>
      ) : <Empty>Nothing yet.</Empty>}
    </Panel>
  )
}

function RerunPanel({ busy, onRerun }: { busy: string; onRerun: (note: string) => Promise<boolean> }) {
  const [note, setNote] = useState("")
  const submit = async (e: FormEvent) => { e.preventDefault(); if (await onRerun(note)) setNote("") }
  return (
    <Panel title="Ask for another round">
      <form className="flex flex-col gap-4" onSubmit={submit}>
        <Field label="What should change" htmlFor="rerun-note">
          <Textarea id="rerun-note" className="md:text-base" maxLength={1000} placeholder="e.g. Lead with the habit insight; judges here care about traction" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <Button type="submit" variant="outline" size="lg" className="self-start" disabled={!!busy}>{busy === "rerun" ? "Starting…" : "Run another round"}</Button>
      </form>
    </Panel>
  )
}

export function PitchLabItemPage({ id }: { id: string }) {
  const { toast } = useFeedback()
  const state = useLoad(() => api<LabDetail>(`/api/lab/${encodeURIComponent(id)}`), [id])
  const [busy, setBusy] = useState("")
  const fail = (e: unknown) => toast(e instanceof Error ? e.message : "Unable to complete this action.", true)

  const save = async () => {
    setBusy("save")
    try { const r = await api<{ pitch_id: string }>("/api/lab-save", { id }); location.href = `/pitch/${encodeURIComponent(r.pitch_id)}` } catch (e) { fail(e); setBusy("") }
  }
  const approve = async () => {
    setBusy("approve")
    try { await api("/api/lab-approve", { id }); await state.reload(); toast("Approved. Submit it yourself when you’re ready.") } catch (e) { fail(e) } finally { setBusy("") }
  }
  // The build runs on the server while the request waits and can outlast the 20 second limit; reload either way.
  const build = async () => {
    setBusy("build")
    try { await api("/api/lab-build", { id }); await state.reload(); toast("The deck is built and checked.") } catch (e) { fail(e); await state.reload() } finally { setBusy("") }
  }
  const rerun = async (note: string) => {
    setBusy("rerun")
    try { await api("/api/lab-rerun", { id, note }); await state.reload(); toast("Another round started."); return true } catch (e) { fail(e); return false } finally { setBusy("") }
  }

  const name = displayTitle(state.data?.title || "") || "Draft"
  return (
    <Shell active="Pitch" tab="/pitch-lab" crumb={name} title={name}>
      <LoadGate state={state}>
        {(it) => {
          const p = it.payload, brief = p.brief || {}
          const ready = ["READY", "APPROVED"].includes(it.stage)
          const edition = it.kind === "PITCH_EDITION"
          const full = edition && !!brief.script
          const line = `${kindWords(it.kind)} · round ${it.round}`
          return (
            <>
              <PageHead title={name} line={line}>
                {ready && edition && <Button size="lg" disabled={!!busy} onClick={save}>{busy === "save" ? "Saving…" : "Save script to Pitch Studio"}</Button>}
                {it.stage === "READY" && <Button size="lg" variant={edition ? "outline" : "default"} disabled={!!busy} onClick={approve}>{busy === "approve" ? "Approving…" : "Approve"}</Button>}
                {!ready && !it.error && <Button size="lg" variant="outline" onClick={() => state.reload()}>Check again</Button>}
              </PageHead>
              <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="flex min-w-0 flex-col gap-5">
                  <StatusPanel it={it} />
                  {full && ready && <DeckPanel it={it} busy={busy} onBuild={build} />}
                  {it.coach && <CoachPanels c={it.coach} />}
                  {full && <ScriptPanel it={it} />}
                  {full && <SlidePlanPanel it={it} />}
                  {it.kind === "APPLICATION_SET" && <AnswersPanel it={it} />}
                  {it.kind === "PITCH_REVIEW" && <Panel title="The pitch reviewed"><CopyBox text={p.text || ""} /></Panel>}
                  {it.kind === "GROWTH_DRAFT" && <Panel title="The draft"><CopyBox text={p.body || ""} /></Panel>}
                  {["OUTCOME_LESSON", "VOICE_RULES"].includes(it.kind) && (
                    <Panel title="Lessons from this">
                      <p className="max-w-[70ch] text-base text-muted-foreground">New lessons from this appear in Lessons for you to approve.</p>
                      <Button variant="outline" size="lg" className="self-start" asChild><a href="/pitch-lab#lessons">Open Lessons</a></Button>
                    </Panel>
                  )}
                </div>
                <div className="flex min-w-0 flex-col gap-5">
                  {full && <RulesPanel it={it} />}
                  {full && brief.strategy && <Panel title="Strategy for this program"><p className="max-w-[70ch] text-base">{brief.strategy}</p></Panel>}
                  {full && <Panel title="The ask"><p className="max-w-[70ch] text-base">{brief.ask || "No ask written yet."}</p></Panel>}
                  {full && (
                    <Panel title="Materials to prepare">
                      {(brief.materials || []).length ? <ul className={bullets}>{brief.materials!.map((m, i) => <li key={i}>{m}</li>)}</ul> : <Empty>Nothing to prepare.</Empty>}
                    </Panel>
                  )}
                  {full && (brief.open_questions || []).length > 0 && (
                    <Panel title="Only you can answer"><ul className={bullets}>{brief.open_questions!.map((q, i) => <li key={i}>{q}</li>)}</ul></Panel>
                  )}
                  <RerunPanel busy={busy} onRerun={rerun} />
                  <HistoryPanel reviews={it.reviews} />
                </div>
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/pitch-lab/": (id) => <PitchLabItemPage id={id} /> } }
