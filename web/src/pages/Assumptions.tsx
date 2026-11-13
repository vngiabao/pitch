import { Fragment, useEffect, useRef, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Disclosure, Empty, Fact, Field, LoadGate, PageHead, Panel, Tag, useLoad } from "@/components/app/page"
import { api } from "@/lib/api"
import { day, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

// Every number the deck depends on, what it rests on today, and this week's three cheapest tests (old assumptions.js).

type Status = "measured" | "modeled" | "assumed"
type Assumption = {
  key: string; statement: string; number: string; status: Status; slides: string[]
  measured?: { fact?: { text: string } | null; evidence?: { text: string }[] } | null
  status_changed_at?: string | null
  evidence_for: string[]; evidence_against: string[]; cheapest_test: string; owner_note: string
}
type Challenge = {
  created_at: string; edition_title?: string; measured: unknown[]; note?: string
  weakest: { key: string; statement: string; status: Status; why_weak: string; cheapest_test: string; judge_question: string }[]
  rejected: { key?: string; reason: string }[]
}
type Board = {
  counts: Record<Status, number>; slide_titles: Record<string, string>; researching: boolean; next_challenge: string
  challenge: Challenge | null; assumptions: Assumption[]
}

const STATUS_WORDS: Record<string, string> = { assumed: "Assumed", modeled: "Modeled", measured: "Measured" }
const StatusTag = ({ s }: { s: string }) => <Tag tone={s === "measured" ? "good" : s === "modeled" ? "quiet" : "review"}>{STATUS_WORDS[s] || s}</Tag>

// The order the table runs in, and how to say a number of each kind out loud
const ORDER: Status[] = ["measured", "modeled", "assumed"]
const HOW_TO_SAY: Record<Status, string> = {
  measured: "From channel math and the beta family journal, with the dates they cover. Say it as it is.",
  modeled: "Built from pricing and published inputs. Say “modeled”, never “we see”.",
  assumed: "An example input or a belief. Say “an assumption we are testing”; the cheapest test says how.",
}

const bullets = "flex list-disc flex-col gap-1 pl-5 text-base"
const subhead = "text-sm font-medium text-muted-foreground"
const rowId = (key: string) => `assumption-${key}`

function Lines({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="flex max-w-[70ch] min-w-0 flex-col gap-1">
      <h5 className={subhead}>{label}</h5>
      {items.length ? <ul className={bullets}>{items.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="text-base text-muted-foreground">Nothing recorded.</p>}
    </div>
  )
}
function Part({ label, children }: { label: string; children: string }) {
  return <div className="flex max-w-[70ch] flex-col gap-1"><h5 className={subhead}>{label}</h5><p className="text-base">{children}</p></div>
}

// The three weakest: the claim, its status and one line of the cheapest test. The reasoning sits behind one press.
function ChallengePanel({ b }: { b: Board }) {
  const c = b.challenge
  if (!c) return (
    <Panel title="This week’s three weakest">
      <Empty>No challenge yet. {b.next_challenge}{b.researching && " One is running now; it lands here in a few minutes."}</Empty>
    </Panel>
  )
  return (
    <Panel title="This week’s three weakest" aside={`Reviewed ${day(c.created_at)}`}>
      <ol className="flex flex-col">
        {c.weakest.map((w, i) => (
          <li key={w.key || i} className="flex flex-col gap-1 border-t py-4 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
              <h4 className="max-w-[60ch] text-base font-semibold"><span className="tabular-nums text-muted-foreground">{i + 1}.</span> {w.statement}</h4>
              <StatusTag s={w.status} />
            </div>
            <p className="max-w-[70ch] truncate text-base text-muted-foreground"><span className="font-medium text-foreground">Test this week:</span> {w.cheapest_test}</p>
            <Disclosure label="See why, and the full test">
              <Part label="Why it is weak">{w.why_weak}</Part>
              <Part label="Cheapest test this week">{w.cheapest_test}</Part>
              <Part label="A judge would ask">{`“${w.judge_question}”`}</Part>
              <a href={`#${rowId(w.key)}`} className="flex min-h-11 w-fit items-center rounded-md text-base font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">See the full row</a>
            </Disclosure>
          </li>
        ))}
      </ol>
      <Disclosure label="About this review">
        <p className="max-w-[70ch] text-base text-muted-foreground">
          Read from {c.edition_title || "the core deck"}{c.measured.length ? ` and ${plural(c.measured.length, "measured number")}` : " with nothing measured yet"}. {b.next_challenge}
        </p>
        {c.note && <p className="max-w-[70ch] text-base text-muted-foreground">{c.note}</p>}
        {c.rejected.length > 0 && (
          <div className="flex max-w-[70ch] flex-col gap-1">
            <h5 className={subhead}>{plural(c.rejected.length, "item")} set aside by the fact check</h5>
            <ul className={bullets}>{c.rejected.map((r, i) => <li key={i}>{r.key || "(no key)"}: {r.reason}</li>)}</ul>
          </div>
        )}
      </Disclosure>
    </Panel>
  )
}

function EditForm({ a, onSave, onCancel }: { a: Assumption; onSave: (body: Record<string, string>) => Promise<boolean>; onCancel: () => void }) {
  const [evidenceFor, setFor] = useState(a.evidence_for.join("\n"))
  const [evidenceAgainst, setAgainst] = useState(a.evidence_against.join("\n"))
  const [test, setTest] = useState(a.cheapest_test || "")
  const [note, setNote] = useState(a.owner_note || "")
  const [status, setStatus] = useState<string>(a.status)
  const [saving, setSaving] = useState(false)
  const id = (n: string) => `${n}-${a.key}`
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    // The status goes only for rows the data hasn't measured; a measured row follows its entries (old assumption-form).
    const body: Record<string, string> = { key: a.key, evidence_for: evidenceFor, evidence_against: evidenceAgainst, cheapest_test: test, owner_note: note }
    if (a.status !== "measured") body.status = status
    try { await onSave(body) } finally { setSaving(false) }
  }
  return (
    <form className="flex max-w-[60rem] flex-col gap-4 border-t pt-4" onSubmit={submit}>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Evidence for, one per line" htmlFor={id("for")}>
          <Textarea id={id("for")} className="md:text-base" maxLength={3000} value={evidenceFor} onChange={(e) => setFor(e.target.value)} />
        </Field>
        <Field label="Evidence against, one per line" htmlFor={id("against")}>
          <Textarea id={id("against")} className="md:text-base" maxLength={3000} value={evidenceAgainst} onChange={(e) => setAgainst(e.target.value)} />
        </Field>
      </div>
      <Field label="Cheapest test" htmlFor={id("test")}>
        <Input id={id("test")} maxLength={600} value={test} onChange={(e) => setTest(e.target.value)} />
      </Field>
      <Field label="Your note" htmlFor={id("note")}>
        <Textarea id={id("note")} className="md:text-base" maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      {a.status === "measured"
        ? <p className="text-sm text-muted-foreground">Measured by the data; the status follows the entries.</p>
        : (
          <Field label="Status" htmlFor={id("status")}>
            <NativeSelect id={id("status")} className="w-full max-w-[16rem] [&_select]:text-base" value={status} onChange={(e) => setStatus(e.target.value)}>
              <NativeSelectOption value="assumed">Assumed</NativeSelectOption>
              <NativeSelectOption value="modeled">Modeled</NativeSelectOption>
            </NativeSelect>
          </Field>
        )}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" variant="outline" size="lg" disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        <Button type="button" variant="ghost" size="lg" disabled={saving} onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

// Everything about one assumption, shown under its table row when the row is opened.
function Detail({ a, titles, onSave }: { a: Assumption; titles: Record<string, string>; onSave: (body: Record<string, string>) => Promise<boolean> }) {
  const [editing, setEditing] = useState(false)
  const slides = a.slides.map((s) => (titles[s] ? `${titles[s]} (${s})` : s)).join(" · ")
  const m = a.measured
  return (
    <div className="flex flex-col gap-4 py-2 whitespace-normal">
      <div className="grid items-start gap-x-8 gap-y-4 lg:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-3">
          <Part label="Cheapest test">{a.cheapest_test}</Part>
          <Part label="On the deck">{slides || "No slide"}</Part>
          {m?.fact && <Part label="Measured">{m.fact.text}</Part>}
          {!!m?.evidence?.length && <Part label="Measured nearby">{m.evidence.map((e) => e.text).join(" ")}</Part>}
          {a.status_changed_at && (
            <p className="text-sm text-muted-foreground">
              Status changed {day(a.status_changed_at)}{a.status === "measured" ? " when the measured number arrived" : " when its measured entries were removed"}.
            </p>
          )}
          {a.owner_note && <Part label="Your note">{a.owner_note}</Part>}
          <Part label="How to say it">{HOW_TO_SAY[a.status] || ""}</Part>
        </div>
        <div className="flex min-w-0 flex-col gap-3">
          <Lines label="For" items={a.evidence_for} />
          <Lines label="Against" items={a.evidence_against} />
        </div>
      </div>
      {editing
        ? <EditForm a={a} onCancel={() => setEditing(false)} onSave={async (body) => { const ok = await onSave(body); if (ok) setEditing(false); return ok }} />
        : <Button variant="outline" size="lg" className="self-start" onClick={() => setEditing(true)}>Edit</Button>}
    </div>
  )
}

function AssumptionTable({ b, open, toggle, onSave }: { b: Board; open: Set<string>; toggle: (key: string) => void; onSave: (body: Record<string, string>) => Promise<boolean> }) {
  const rows = [...b.assumptions].sort((x, y) => ORDER.indexOf(x.status) - ORDER.indexOf(y.status))
  return (
    <Panel title={`All ${plural(rows.length, "assumption")}`} aside="Measured first, then modeled, then assumed" id="all">
      {rows.length ? (
        <Table className="min-w-[52rem] table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[34%]">What the deck says</TableHead>
              <TableHead className="w-[12%]">Number</TableHead>
              <TableHead className="w-[10rem]">Status</TableHead>
              <TableHead>Cheapest test</TableHead>
              <TableHead className="w-[9rem]"><span className="sr-only">Open the row</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((a) => {
              const isOpen = open.has(a.key)
              return (
                <Fragment key={a.key}>
                  <TableRow id={rowId(a.key)} className="scroll-mt-4">
                    <TableCell className="font-semibold whitespace-normal">{a.statement}</TableCell>
                    <TableCell className="font-semibold whitespace-normal tabular-nums">{a.number}</TableCell>
                    <TableCell><StatusTag s={a.status} /></TableCell>
                    <TableCell className="truncate text-muted-foreground">{a.cheapest_test}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="lg" aria-expanded={isOpen} aria-controls={`${rowId(a.key)}-detail`} onClick={() => toggle(a.key)}>{isOpen ? "Close" : "Open"}</Button>
                    </TableCell>
                  </TableRow>
                  {isOpen && (
                    <TableRow id={`${rowId(a.key)}-detail`} className="bg-secondary/60 hover:bg-secondary/60">
                      <TableCell colSpan={5}><Detail a={a} titles={b.slide_titles} onSave={onSave} /></TableCell>
                    </TableRow>
                  )}
                </Fragment>
              )
            })}
          </TableBody>
        </Table>
      ) : <Empty>None yet.</Empty>}
    </Panel>
  )
}

export function AssumptionsPage() {
  const { toast } = useFeedback()
  const state = useLoad(() => api<Board>("/api/assumptions"))
  const [asking, setAsking] = useState(false)
  const [open, setOpen] = useState<Set<string>>(new Set())
  const ready = !!state.data

  // #assumption-<key> opens that row and brings it into view, on arrival and when a link on the page is pressed.
  useEffect(() => {
    if (!ready) return
    const go = () => {
      let id = ""
      try { id = decodeURIComponent(location.hash.slice(1)) } catch { return }
      if (!id) return
      if (id.startsWith("assumption-")) {
        const key = id.slice("assumption-".length)
        setOpen((s) => (s.has(key) ? s : new Set(s).add(key)))
      }
      requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: "start" }))
    }
    go()
    window.addEventListener("hashchange", go)
    return () => window.removeEventListener("hashchange", go)
  }, [ready])

  // Opening the page marks its alerts as seen, once, without waiting (old assumptions.js:44).
  const seen = useRef(false)
  useEffect(() => {
    if (!ready || seen.current) return
    seen.current = true
    api("/api/assumptions-seen", {}).catch(() => {})
  }, [ready])

  const toggle = (key: string) => setOpen((s) => { const n = new Set(s); if (n.has(key)) n.delete(key); else n.add(key); return n })
  const fail = (e: unknown) => toast(e instanceof Error ? e.message : "Unable to complete this action.", true)
  const challenge = async () => {
    setAsking(true)
    try {
      await api("/api/assumption-challenge", {})
      toast("Asked for a challenge. The three weakest assumptions land here in a few minutes.")
      await state.reload()
    } catch (e) { fail(e) } finally { setAsking(false) }
  }
  const save = async (body: Record<string, string>) => {
    try {
      await api("/api/assumption", body)
      toast("Saved. The next draft and review read this.")
      await state.reload()
      return true
    } catch (e) { fail(e); return false }
  }

  return (
    <Shell active="Pitch" tab="/assumptions" title="Assumptions">
      <LoadGate state={state}>
        {(b) => (
          <>
            <PageHead title="Assumptions" line="Every number the deck depends on, what each rests on today, and the cheapest test for it.">
              <Button size="lg" disabled={b.researching || asking} onClick={challenge}>{b.researching ? "Working on it…" : asking ? "Asking…" : "Challenge now"}</Button>
            </PageHead>

            <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <ChallengePanel b={b} />
              <div className="flex min-w-0 flex-col gap-5">
                <Panel title="Where the numbers stand" aside={plural(b.assumptions.length, "assumption")}>
                  <div className="grid grid-cols-3 gap-4">
                    <Fact label="Measured" tone="good"><span className="tabular-nums">{b.counts.measured}</span></Fact>
                    <Fact label="Modeled"><span className="tabular-nums">{b.counts.modeled}</span></Fact>
                    <Fact label="Assumed"><span className="tabular-nums">{b.counts.assumed}</span></Fact>
                  </div>
                  <Disclosure label="How this works">
                    <p className="max-w-[70ch] text-base text-muted-foreground">The rows come from the core deck’s own notes. Your edits are kept as yours.</p>
                    <p className="max-w-[70ch] text-base text-muted-foreground">A measured number from channel math or the family journal flips a row to measured on its own, with its as-of date; if those entries are removed the row goes back to what the deck said.</p>
                    <p className="max-w-[70ch] text-base text-muted-foreground">Every draft and pitch review reads this table, so a script says “modeled” or “measured” correctly, and the review asks about the weakest rows first.</p>
                    <p className="max-w-[70ch] text-base text-muted-foreground">Every Monday at 7:30 AM Eastern the review names the three weakest and the one cheapest test for each; it may not use a number that is not on this page.</p>
                  </Disclosure>
                </Panel>
              </div>
            </div>

            <AssumptionTable b={b} open={open} toggle={toggle} onSave={save} />
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/assumptions": () => <AssumptionsPage /> } }
