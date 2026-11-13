import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react"
import { ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Disclosure, Empty, Field, LoadGate, PageHead, Panel, Row, Rows, Tag, useHashScroll, useLoad } from "@/components/app/page"
import { api } from "@/lib/api"
import { cleanName, day, plural } from "@/lib/format"
import { LAB_AGENTS, displayTitle, itemLine, lessonFor, programOf, sortLab, stageTag, type Lab, type LabItem, type LabOptions } from "@/lib/lab"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

// ---- Parts the lab item page uses too ----

// Shows the first few of a list, then one "Show all N" control.
export function ShowAll<T>({ items, first = 6, noun = "", children }: { items: T[]; first?: number; noun?: string; children: (shown: T[]) => ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      {children(open ? items : items.slice(0, first))}
      {!open && items.length > first && (
        <Button variant="outline" size="lg" className="self-start" onClick={() => setOpen(true)}>Show all {items.length}{noun && ` ${noun}`}</Button>
      )}
    </>
  )
}

export function StageTag({ it }: { it: Pick<LabItem, "stage" | "stage_words" | "round" | "error"> }) {
  const t = stageTag(it)
  return <Tag tone={t.tone}>{t.words}</Tag>
}

// ---- The list page ----

function ItemRow({ it, quietWhenReady }: { it: LabItem; quietWhenReady?: boolean }) {
  const showTag = !(quietWhenReady && it.stage === "READY" && !it.error)
  return (
    <Row href={`/pitch-lab/${encodeURIComponent(it.id)}`} title={displayTitle(it.title)} line={itemLine(it)}
      meta={<span className="flex items-center gap-3">{showTag && <StageTag it={it} />}{day(it.updated_at || it.created_at)}<ChevronRight className="size-4 shrink-0" aria-hidden="true" /></span>} />
  )
}

function ReadyList({ groups }: { groups: LabItem[][] }) {
  return (
    <ShowAll items={groups} first={6} noun="programs">
      {(shown) => (
        <Rows label="Ready for you">
          {shown.map((g) => (
            <Fragment key={g[0].id}>
              <ItemRow it={g[0]} quietWhenReady />
              {g.length > 1 && (
                <li className="pb-2">
                  <Disclosure label={`${plural(g.length - 1, "more draft")} for ${programOf(g[0])}`}>
                    <ul className="flex flex-col pl-6">{g.slice(1).map((it) => <ItemRow key={it.id} it={it} quietWhenReady />)}</ul>
                  </Disclosure>
                </li>
              )}
            </Fragment>
          ))}
        </Rows>
      )}
    </ShowAll>
  )
}

const selectClass = "w-full [&_select]:text-base"

function StartForms({ opts, go }: { opts: LabOptions; go: (path: string, body: unknown, key: string) => Promise<void> }) {
  const q = new URLSearchParams(location.search)
  const pick = (id: string | null, ids: string[]) => (id && ids.includes(id) ? id : "")
  const [program, setProgram] = useState(pick(q.get("program"), opts.programs.map((p) => p.id)))
  const [minutes, setMinutes] = useState("3")
  const [slideLimit, setSlideLimit] = useState("")
  const [note, setNote] = useState("")
  const [pitch, setPitch] = useState(pick(q.get("coach"), opts.pitches.map((p) => p.id)))
  const [application, setApplication] = useState("")
  const [busy, setBusy] = useState("")

  const submit = (key: string, path: string, body: unknown) => async (e: FormEvent) => {
    e.preventDefault()
    setBusy(key)
    try { await go(path, body, key) } finally { setBusy("") }
  }

  return (
    <>
      <Panel title="Tailor for a program" id="start">
        <form className="flex flex-col gap-4" onSubmit={submit("edition", "/api/lab-edition", { opportunity_id: program, minutes: Number(minutes), slide_limit: slideLimit ? Number(slideLimit) : null, note })}>
          <Field label="Program" htmlFor="lab-program">
            <NativeSelect id="lab-program" className={selectClass} required value={program} onChange={(e) => setProgram(e.target.value)}>
              <NativeSelectOption value="">Choose a program…</NativeSelectOption>
              {opts.programs.map((p) => <NativeSelectOption key={p.id} value={p.id}>{cleanName(p.name)}</NativeSelectOption>)}
            </NativeSelect>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Minutes on stage" htmlFor="lab-minutes">
              <Input id="lab-minutes" type="number" min={0.5} max={30} step={0.5} required value={minutes} onChange={(e) => setMinutes(e.target.value)} />
            </Field>
            <Field label="Slide limit, if any" htmlFor="lab-slides">
              <Input id="lab-slides" type="number" min={1} max={40} placeholder="From the rules" value={slideLimit} onChange={(e) => setSlideLimit(e.target.value)} />
            </Field>
          </div>
          <Field label="Anything else to know" htmlFor="lab-note">
            <Textarea id="lab-note" rows={2} className="min-h-16 md:text-base" maxLength={1000} placeholder="e.g. Judges are angel investors; Daniel presents; demo allowed" value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          <Button type="submit" size="lg" className="self-start" disabled={!!busy}>{busy === "edition" ? "Starting…" : "Tailor the pitch"}</Button>
        </form>
      </Panel>

      <Panel title="Coach a saved pitch">
        <form className="flex flex-col gap-4" onSubmit={submit("review", "/api/lab-review", { pitch_id: pitch })}>
          <Field label="Pitch" htmlFor="lab-pitch">
            <NativeSelect id="lab-pitch" className={selectClass} required value={pitch} onChange={(e) => setPitch(e.target.value)}>
              <NativeSelectOption value="">Choose a pitch…</NativeSelectOption>
              {opts.pitches.map((p) => <NativeSelectOption key={p.id} value={p.id}>{cleanName(p.title)}</NativeSelectOption>)}
            </NativeSelect>
          </Field>
          <Button type="submit" size="lg" variant="outline" className="self-start" disabled={!!busy}>{busy === "review" ? "Starting…" : "Get coached"}</Button>
        </form>
      </Panel>

      <Panel title="Review application answers">
        <form className="flex flex-col gap-4" onSubmit={submit("application", "/api/lab-application", { application_id: application })}>
          <Field label="Application" htmlFor="lab-application">
            <NativeSelect id="lab-application" className={selectClass} required value={application} onChange={(e) => setApplication(e.target.value)}>
              <NativeSelectOption value="">Choose an application…</NativeSelectOption>
              {opts.applications.map((a) => <NativeSelectOption key={a.id} value={a.id}>{cleanName(a.program)}</NativeSelectOption>)}
            </NativeSelect>
          </Field>
          <Button type="submit" size="lg" variant="outline" className="self-start" disabled={!!busy}>{busy === "application" ? "Starting…" : "Review answers"}</Button>
        </form>
      </Panel>
    </>
  )
}

function HowItIsMade({ lab }: { lab: Lab }) {
  return (
    <Panel title="How every draft is made" aside={`Learned from ${plural(lab.voice_examples, "of your edits", "of your edits")}`}>
      <p className="max-w-[70ch] text-base text-muted-foreground">Every draft is fact-checked, put in your voice and coached before it reaches you. Nothing is submitted or sent for you.</p>
      <Disclosure label={`See the ${LAB_AGENTS.length} steps`}>
        <ol className="flex flex-col">
          {LAB_AGENTS.map(([key, name, what], i) => (
            <li key={key} className="flex items-baseline gap-3 border-t py-3 first:border-t-0">
              <span className="w-6 shrink-0 text-base font-semibold tabular-nums text-muted-foreground">{i + 1}.</span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="text-base font-semibold">{name}</span>
                <span className="text-base text-muted-foreground">{what}</span>
              </span>
              {lab.stages?.[key] ? <span className="shrink-0 text-sm tabular-nums text-muted-foreground">{plural(lab.stages[key], "draft")} here</span> : null}
            </li>
          ))}
        </ol>
        <p className="text-sm text-muted-foreground">One step runs every few minutes, on your ChatGPT plan.</p>
      </Disclosure>
    </Panel>
  )
}

export function PitchLabPage() {
  const { toast, confirm } = useFeedback()
  const state = useLoad(() => Promise.all([api<Lab>("/api/lab"), api<LabOptions>("/api/lab-options")]))
  const [deciding, setDeciding] = useState("")
  useHashScroll(!!state.data)
  // Arriving with ?program= or ?coach= means "start one now": bring the forms into view (they sit below on a phone).
  const jumped = useRef(false)
  useEffect(() => {
    if (!state.data || jumped.current || location.hash) return
    jumped.current = true
    const q = new URLSearchParams(location.search)
    if (q.get("program") || q.get("coach")) document.getElementById("start")?.scrollIntoView({ block: "nearest" })
  }, [state.data])

  // Start an edition, a review or an answer review, then open the new item (old #lab-edition, #lab-review, #lab-application).
  const go = async (path: string, body: unknown) => {
    try {
      const r = await api<{ id: string }>(path, body)
      location.href = `/pitch-lab/${encodeURIComponent(r.id)}`
    } catch (e) { toast(e instanceof Error ? e.message : "Unable to start this.", true) }
  }

  const decide = async (id: string, body: string, decision: "APPROVED" | "REJECTED") => {
    if (decision === "APPROVED" && !(await confirm({ title: "Approve this lesson?", body: <p>“{body}” Every draft follows it from now on.</p>, action: "Approve lesson" }))) return
    setDeciding(id + decision)
    try {
      await api("/api/lesson", { id, decision })
      await state.reload()
      toast(decision === "APPROVED" ? "Every draft follows this from now on." : "Lesson rejected.")
    } catch (e) { toast(e instanceof Error ? e.message : "Unable to save this.", true) } finally { setDeciding("") }
  }

  return (
    <Shell active="Pitch" tab="/pitch-lab" title="Pitch Lab">
      <LoadGate state={state}>
        {([lab, opts]) => {
          const s = sortLab(lab)
          const line = s.ready.length
            ? `${plural(s.ready.length, "program has", "programs have")} a draft ready for you${s.working.length ? `, and ${s.working.length} more ${s.working.length === 1 ? "is" : "are"} being made` : ""}.`
            : s.working.length
              ? `${plural(s.working.length, "draft is", "drafts are")} being made. Nothing needs you yet.`
              : "Nothing is waiting on you. Tailor the pitch to a program to start a draft."
          return (
            <>
              <PageHead title="Pitch Lab" line={line} />
              <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="flex flex-col gap-5">
                  <Panel title="Ready for you" aside="Newest first, one per program">
                    {s.ready.length ? <ReadyList groups={s.ready} /> : <Empty>No draft is ready yet. A finished draft lands here.</Empty>}
                  </Panel>

                  {s.working.length > 0 && (
                    <Panel title="Being made now" aside="One step runs every few minutes">
                      <Rows label="Being made now">{s.working.map((it) => <ItemRow key={it.id} it={it} />)}</Rows>
                    </Panel>
                  )}

                  <Panel title="Lessons" id="lessons" aside="From results and your edits. Approved lessons guide every draft.">
                    {s.proposed.length ? (
                      <ShowAll items={s.proposed} first={5} noun="lessons">
                        {(shown) => (
                          <ul aria-label="Lessons to decide" className="flex flex-col">
                            {shown.map((l) => (
                              <li key={l.id} className="flex flex-col gap-3 border-t py-4 first:border-t-0 first:pt-0">
                                <div className="flex max-w-[70ch] flex-col gap-1">
                                  <span className="text-base font-semibold">{l.body}</span>
                                  {l.evidence && <span className="text-base text-muted-foreground">{l.evidence}</span>}
                                  <span className="text-sm text-muted-foreground">Applies to {lessonFor(l.applies_to)}</span>
                                </div>
                                <div className="flex flex-wrap gap-3">
                                  <Button variant="outline" size="lg" disabled={!!deciding} onClick={() => decide(l.id, l.body, "APPROVED")}>{deciding === l.id + "APPROVED" ? "Approving…" : "Approve"}</Button>
                                  <Button variant="outline" size="lg" disabled={!!deciding} onClick={() => decide(l.id, l.body, "REJECTED")}>{deciding === l.id + "REJECTED" ? "Rejecting…" : "Reject"}</Button>
                                </div>
                              </li>
                            ))}
                          </ul>
                        )}
                      </ShowAll>
                    ) : <Empty>No new lessons. They appear after a result comes in or after you edit three drafts.</Empty>}
                    {s.approvedLessons.length > 0 && (
                      <Disclosure label={`Approved lessons (${s.approvedLessons.length})`}>
                        <ul className="flex max-w-[70ch] list-disc flex-col gap-2 pl-5 text-base">{s.approvedLessons.map((l) => <li key={l.id}>{l.body}</li>)}</ul>
                      </Disclosure>
                    )}
                  </Panel>

                  {s.approved.length > 0 && (
                    <Panel title="Approved" aside={plural(s.approved.length, "draft")}>
                      <ShowAll items={s.approved} first={5} noun="approved">
                        {(shown) => <Rows label="Approved">{shown.map((it) => <ItemRow key={it.id} it={it} />)}</Rows>}
                      </ShowAll>
                    </Panel>
                  )}
                </div>

                <div className="flex flex-col gap-5">
                  <StartForms opts={opts} go={go} />
                  <HowItIsMade lab={lab} />
                </div>
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/pitch-lab": () => <PitchLabPage /> } }
