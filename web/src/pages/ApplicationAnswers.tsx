import { useEffect, useState, type FormEvent } from "react"
import { Check, Copy, ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { Disclosure, Empty, Field, LoadGate, PageHead, Panel, Row, Rows, Tag, useHashScroll, useLoad, evenBottoms } from "@/components/app/page"
import { useFeedback } from "@/components/app/feedback"
import { api } from "@/lib/api"
import {
  RESULTS, accessShort, copyAnswer, cycleLabel, external, needsWords, needsYou, numberedTasks, outcomeTone, plain, plainTask,
  questionLabel, readForm, sourceWords, useLimit,
  type Application, type LabItem, type Question,
} from "@/lib/applications"
import { countLabel, countWords, day, plural, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"

type Act = (key: string, fn: () => Promise<void>) => Promise<void>
const errorText = (e: unknown) => (e instanceof Error ? e.message : "Unable to complete this action.")

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <Button variant="outline" size="lg" className="shrink-0"
      onClick={async () => { if (await copyAnswer(text)) { setDone(true); setTimeout(() => setDone(false), 1600) } }}>
      {done ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{done ? "Copied" : "Copy"}
    </Button>
  )
}

// The old answerBox(): a short answer sits on one line with its Copy button; a long or limited one gets a box and a count.
function AnswerBox({ body, limit, unit }: { body: string; limit: number | null; unit: "words" | "characters" | null }) {
  const u = unit === "characters" ? "characters" : "words"
  const short = !limit && !body.includes("\n") && body.length <= 80
  if (short) return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-secondary py-2 pr-2 pl-4">
      <span className="text-base">{body}</span>
      <CopyButton text={body} />
    </div>
  )
  const over = !!limit && (u === "words" ? countWords(body) : body.length) > limit
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-secondary p-4">
      <p className="max-w-[70ch] text-base whitespace-pre-wrap">{body}</p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className={cn("text-sm", over ? "font-semibold text-deadline" : "text-muted-foreground")}>{countLabel(body, limit, u)}</span>
        <CopyButton text={body} />
      </div>
    </div>
  )
}

// An answered question keeps the form's own wording (Bao matches it to the field he pastes into). An unanswered one
// leads with the plain task, the same words as Today, and shows the form's wording as a quiet second line.
function QuestionBlock({ q, numbered }: { q: Question; numbered?: string }) {
  const options = q.options || []
  const wording = plain(questionLabel(q))
  const task = q.answer ? wording : numbered || plainTask(q).label
  return (
    <div id={"q-" + q.id} className="flex scroll-mt-4 flex-col gap-2 border-t py-4 first:border-t-0 first:pt-0">
      <div className="flex flex-col gap-0.5">
        <h4 className="max-w-[70ch] text-base font-semibold">{task}</h4>
        {task !== wording && <p className="max-w-[70ch] text-sm text-muted-foreground">On the form: {wording}</p>}
      </div>
      {options.length > 0 && !q.answer && (
        <p className="max-w-[70ch] text-sm text-muted-foreground">Options: {options.slice(0, 12).map(plain).join(" · ")}{options.length > 12 ? " …" : ""}</p>
      )}
      {q.answer ? (
        <>
          <AnswerBox body={String(q.answer.body ?? "")} limit={q.limit} unit={q.unit} />
          <p className="max-w-[70ch] text-sm text-muted-foreground">
            {sourceWords(q.answer)}{(q.answer.notes || []).length ? " · " + plain(q.answer.notes!.join(" ")) : ""}
          </p>
        </>
      ) : (
        <p className="max-w-[70ch] rounded-lg bg-primary/10 px-4 py-3 text-base">
          <strong className="font-semibold text-primary">Needs you.</strong>{" "}
          {q.needs_you ? needsWords(q.needs_you) : q.type === "file" ? "Upload this file yourself on the official form." : "No saved answer yet."}
        </p>
      )}
    </div>
  )
}

// Not yet submitted: the three steps, in order. "Mark submitted" is the page's one primary button.
function Steps({ a, busy, act }: { a: Application; busy: string | null; act: Act }) {
  const { toast, confirm } = useFeedback()
  const url = a.application_url || a.official_url
  const ready = a.questions.filter((q) => q.answer).length, needs = a.questions.length - ready
  // While answers still need Bao (or none are read yet), the next step is the form itself; marking it submitted
  // becomes the primary button only once every answer is ready.
  const formFirst = !!url && (needs > 0 || !a.questions.length)
  const read = () => act("read", async () => {
    const r = await readForm(a.opportunity_id)
    if (r) toast(r.message, r.error)
  })
  const markSubmitted = () => act("submitted", async () => {
    if (!(await confirm({
      title: "Record that you submitted this application?",
      body: "The agents will stop recommending it.",
      action: "Mark submitted",
    }))) return
    await api("/api/outcome", { opportunity_id: a.opportunity_id, outcome: "Applied", application_id: a.id || null, note: "Owner marked submitted in Founder OS." })
    toast("Marked submitted. It now appears under Waiting on results.")
  })
  return (
    <Panel title="Three steps to apply">
      <Rows label="Three steps to apply">
        <Row title="1. Open the official form" line={a.access?.level === "BLOCKED" ? accessShort(a.access) + "." : "Sign in there if it asks you to."}>
          {url
            ? <Button size="lg" variant={formFirst ? "default" : "outline"} asChild><a href={url} {...external}>Open the form<ExternalLink aria-hidden="true" /></a></Button>
            : <span className="text-sm text-muted-foreground">Link not found yet</span>}
        </Row>
        <Row title="2. Copy the answers below"
          line={a.questions.length
            ? `${ready} of ${a.questions.length} ready.${needs ? ` ${needs} need${needs === 1 ? "s" : ""} you.` : ""}`
            : "The agent has not read the questions yet."}>
          {!a.questions.length && (
            <Button size="lg" variant="outline" disabled={!!busy} onClick={read}>{busy === "read" ? "Reading the form…" : "Read the form now"}</Button>
          )}
        </Row>
        <Row title="3. Submit it there, then mark it here" line="The agents stop recommending it and track the result.">
          <Button size="lg" variant={formFirst ? "outline" : "default"} disabled={!!busy} onClick={markSubmitted}>{busy === "submitted" ? "Saving…" : "Mark submitted"}</Button>
        </Row>
      </Rows>
      {a.access && a.questions.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-4">
          <span className="text-base text-muted-foreground">{accessShort(a.access)}.</span>
          <Button size="lg" variant="outline" disabled={!!busy} onClick={read}>{busy === "read" ? "Reading the form…" : "Re-read the form"}</Button>
        </div>
      )}
    </Panel>
  )
}

// Submitted: where it stands, and the form that records what came back.
function Status({ a, busy, act }: { a: Application; busy: string | null; act: Act }) {
  const { toast } = useFeedback()
  const latest = a.outcomes[0]
  const [outcome, setOutcome] = useState(RESULTS[0])
  const [link, setLink] = useState("")
  const [note, setNote] = useState("")
  const save = (e: FormEvent) => {
    e.preventDefault()
    void act("result", async () => {
      await api("/api/outcome", { opportunity_id: a.opportunity_id, application_id: a.id, outcome, note: note || "", evidence_url: link || null })
      setOutcome(RESULTS[0]); setLink(""); setNote("")
      toast("Result saved.")
    })
  }
  return (
    <Panel title={`${latest.outcome} ${day(latest.occurred_at)}`} aside={<Tag tone={outcomeTone(latest.outcome)}>{latest.outcome}</Tag>}>
      {latest.note && <p className="max-w-[70ch] text-base text-muted-foreground">{plain(latest.note)}</p>}
      <form id="outcome-form" onSubmit={save} className="flex flex-col gap-4 border-t pt-4">
        <h4 className="text-base font-semibold">Record a result</h4>
        <div className="grid gap-4 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
          <Field label="Result" htmlFor="result-outcome">
            <NativeSelect id="result-outcome" name="outcome" className="w-full" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
              {RESULTS.map((r) => <NativeSelectOption key={r} value={r}>{r}</NativeSelectOption>)}
            </NativeSelect>
          </Field>
          <Field label="Receipt or announcement link (optional)" htmlFor="result-link">
            <Input id="result-link" name="evidence_url" type="url" placeholder="https://" className="h-11" value={link} onChange={(e) => setLink(e.target.value)} />
          </Field>
        </div>
        <Field label="Note" htmlFor="result-note">
          <Textarea id="result-note" name="note" placeholder="What happened, and anything worth remembering for next time" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <Button type="submit" size="lg" className="self-start" disabled={!!busy}>{busy === "result" ? "Saving…" : "Save result"}</Button>
      </form>
      {a.outcomes.length > 1 && (
        <Disclosure label={`History (${a.outcomes.length})`} className="border-t pt-2">
          <ul className="flex flex-col">
            {a.outcomes.map((o, i) => (
              <li key={i} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t py-2 first:border-t-0">
                <Tag tone={outcomeTone(o.outcome)}>{o.outcome}</Tag>
                <span className="text-sm text-muted-foreground">{stamp(o.occurred_at)}</span>
                {o.note && <span className="w-full max-w-[70ch] text-sm text-muted-foreground">{plain(o.note)}</span>}
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </Panel>
  )
}

// What is left for Bao, grouped and worded as on Today. Each row jumps to its question; details that belong in the
// founder profile also offer the way there, so the next application fills them in by itself.
function NeedsYou({ needs }: { needs: Question[] }) {
  const tasks = needsYou(needs)
  const { shown, hidden, showAll } = useLimit(tasks, 5)
  return (
    <Panel title="Needs you" aside={tasks.length === needs.length ? plural(needs.length, "answer") : `${plural(needs.length, "answer")} in ${plural(tasks.length, "task")}`}>
      <Rows label="Answers that need you">
        {shown.map((t) => (
          <Row key={t.first} title={t.label}>
            {t.profile && <Button size="lg" variant="outline" asChild><a href="/founder-profile">Add to profile</a></Button>}
            <Button size="lg" variant="outline" asChild><a href={"#q-" + t.first} aria-label={`Answer: ${t.label}`}>Answer</a></Button>
          </Row>
        ))}
      </Rows>
      {hidden > 0 && <Button size="lg" variant="outline" className="self-start" onClick={showAll}>Show all {plural(tasks.length, "task")}</Button>}
    </Panel>
  )
}

// The old fillLabPanel(): the coach and voice review for these answers. It stays off the page if /api/lab fails.
function LabPanel({ appId }: { appId: string }) {
  const { toast } = useFeedback()
  const [item, setItem] = useState<LabItem | null | undefined>(undefined)
  const [failed, setFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let live = true
    api("/api/lab")
      .then((b) => { if (live) setItem((b.items || []).find((x: LabItem) => x.kind === "APPLICATION_SET" && x.subject_id === appId) || null) })
      .catch(() => { if (live) setFailed(true) })
    return () => { live = false }
  }, [appId])
  if (failed || item === undefined) return null
  const review = async () => {
    setBusy(true)
    try {
      const r = await api("/api/lab-application", { application_id: appId })
      location.href = "/pitch-lab/" + r.id
    } catch (e) { toast(errorText(e), true); setBusy(false) }
  }
  if (!item) return (
    <Panel id="lab-panel" title="Coach and voice review">
      <p className="max-w-[70ch] text-base text-muted-foreground">The pitch review checks these answers for facts, your voice and strength before you paste them.</p>
      <Button size="lg" variant="outline" className="self-start" disabled={busy} onClick={review}>{busy ? "Starting the review…" : "Review these answers"}</Button>
    </Panel>
  )
  const done = item.stage === "APPROVED"
  const chip = (item.error ? "Stopped: needs a retry" : item.stage === "READY" ? "Ready for review" : item.stage_words) + (item.round > 1 && !done ? " · round " + item.round : "")
  return (
    <Panel id="lab-panel" title="Coach and voice review" aside={<Tag tone={item.error ? "urgent" : done ? "good" : "review"}>{chip}</Tag>}>
      <p className="max-w-[70ch] text-base text-muted-foreground">
        {item.summary?.avg ? `Scored ${item.summary.avg} of 5${item.summary.low ? `, ${plural(item.summary.low, "note")} open` : ""}. ` : ""}
        Rewrites in your voice and fact notes for every answer.
      </p>
      <Button size="lg" variant="outline" className="self-start" asChild><a href={"/pitch-lab/" + item.id}>Open the review</a></Button>
    </Panel>
  )
}

export function ApplicationAnswersPage({ id }: { id: string }) {
  const { toast } = useFeedback()
  const state = useLoad<Application>(() => api("/api/application/" + encodeURIComponent(id)), [id])
  const [busy, setBusy] = useState<string | null>(null)
  // One action at a time, then reload the page's data (the old app's boot()); every error becomes a toast.
  const act: Act = async (key, fn) => {
    if (busy) return
    setBusy(key)
    try { await fn(); await state.reload() } catch (e) { toast(errorText(e), true) } finally { setBusy(null) }
  }
  useHashScroll(!!state.data)
  const program = state.data ? plain(state.data.program) : undefined
  return (
    <Shell active="Funding" tab="/applications" crumb={program} title={program || "Application"}>
      <LoadGate state={state}>
        {(a) => {
          const submitted = a.outcomes.some((o) => o.outcome !== "Withdrawn")
          const ready = a.questions.filter((q) => q.answer).length
          const needs = a.questions.filter((q) => !q.answer)
          const numbered = numberedTasks(a.questions)
          const where = submitted ? "Submitted. Record the result when it comes back."
            : a.questions.length ? `${ready} of ${a.questions.length} answers ready to copy into the official form.`
              : "The agent has not read this form yet."
          return (
            <>
              <PageHead title={plain(a.program)} line={[plain(cycleLabel(a.cycle)), where].filter(Boolean).join(" · ")} />
              <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="flex flex-col gap-5">
                  {submitted ? <Status a={a} busy={busy} act={act} /> : <Steps a={a} busy={busy} act={act} />}
                  <Panel title="Questions and answers" aside="In the order the form asks them">
                    {a.questions.length
                      ? <div className="flex flex-col">{a.questions.map((q) => <QuestionBlock key={q.id} q={q} numbered={numbered[q.id]} />)}</div>
                      : <Empty>No questions saved for this application yet.</Empty>}
                  </Panel>
                </div>
                <div className="flex flex-col gap-5">
                  {!submitted && needs.length > 0 && <NeedsYou needs={needs} />}
                  <LabPanel appId={id} />
                </div>
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/application/": (id) => <ApplicationAnswersPage id={id} /> } }
