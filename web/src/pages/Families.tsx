import { type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Empty, Fact, Field, LoadGate, PageHead, Panel, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { METRIC_NEEDS, pointValue, rangeWords, todayEastern, useHashScroll, useRun, type Family, type FamilyEvent, type Intake, type Metric, type Pair, type ProductData } from "@/lib/customers"
import { day, fileSize, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

import { CopyButton, Item, Limited, More } from "./Drive"

type Run = ReturnType<typeof useRun>["run"]
type Do = { busy: string | null; run: Run }

const fields = (form: HTMLFormElement) => Object.fromEntries(new FormData(form)) as Record<string, string>

function Options({ pairs }: { pairs: Pair[] }) {
  return <>{pairs.map(([v, l]) => <NativeSelectOption key={v} value={v}>{l}</NativeSelectOption>)}</>
}

function Measured({ metrics }: { metrics: Metric[] }) {
  return (
    <dl className="flex flex-col">
      {metrics.map((m) => (
        <div key={m.key} className="flex flex-col gap-0.5 border-t py-3 first:border-t-0 first:pt-0">
          <dt className="text-sm text-muted-foreground">{m.label}</dt>
          {m.measurable
            ? (
              <dd className="flex flex-col gap-0.5">
                <span className="text-base">
                  <span className="font-semibold">{m.numerator} of {m.denominator}</span> {m.denominator_label} ({m.percent}%){m.calls !== undefined ? `, ${plural(m.calls, "call")} in all` : ""}
                </span>
                <span className="text-sm text-muted-foreground">{rangeWords(m.range)} · {m.sources.join(" and ")} entries</span>
              </dd>
            )
            : <dd className="text-base text-muted-foreground">Not measurable yet. Needs {METRIC_NEEDS[m.key] || m.denominator_label}.</dd>}
        </div>
      ))}
    </dl>
  )
}

function FamilyItem({ f, kinds, states, busy, run, removeEvent }: { f: Family; kinds: Pair[]; states: Pair[]; removeEvent: (e: FamilyEvent, f: Family) => void } & Do) {
  const today = todayEastern()
  const facts = [
    f.storyteller ? "Storyteller: " + f.storyteller : "", f.adult_child ? "Adult child: " + f.adult_child : "",
    f.enrolled_on ? "Enrolled " + day(f.enrolled_on) : "Enrolled date not set", plural(f.events.length, "event"),
  ].filter(Boolean).join(" · ")
  async function logEvent(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    if (await run(`event:${f.id}`, async () => { await api("/api/family-event", { family_id: f.id, ...fields(form) }); return "Logged. The measured numbers are updated." })) form.reset()
  }
  const setStatus = (status: string) => run(`status:${f.id}`, async () => { await api("/api/family-update", { id: f.id, status }); return "Status saved." })
  return (
    <Item id={`family-${f.id}`} title={f.label} sub={facts}
      tag={(
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          {busy === `status:${f.id}` ? "Saving…" : "Status"}
          <NativeSelect value={f.status} disabled={!!busy} aria-label={`Status of ${f.label}`} onChange={(e) => setStatus(e.target.value)}>
            <Options pairs={states} />
          </NativeSelect>
        </label>
      )}>
      {f.notes && <p className="max-w-[70ch] text-base text-muted-foreground">{f.notes}</p>}
      {f.events.length
        ? (
          <ul aria-label={`Events for ${f.label}`} className="flex flex-col">
            {f.events.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center gap-x-4 border-t py-1 first:border-t-0">
                <span className="min-w-0 flex-1 text-base">
                  <span className="text-muted-foreground">{day(e.at)} · </span>
                  <span className="font-semibold">{e.kind_words}</span>
                  {e.detail ? ` · ${e.detail}` : ""}{e.source === "import" ? <span className="text-muted-foreground"> · imported</span> : null}
                </span>
                <Button size="lg" variant="ghost" disabled={!!busy} onClick={() => removeEvent(e, f)}>{busy === `remove:${e.id}` ? "Removing…" : "Remove"}</Button>
              </li>
            ))}
          </ul>
        )
        : <p className="text-base text-muted-foreground">No events yet. Log the first call when it happens.</p>}
      <More summary="Log an event">
        <form onSubmit={logEvent} className="flex max-w-[44rem] flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="What happened" htmlFor={`event-kind-${f.id}`}>
              <NativeSelect id={`event-kind-${f.id}`} name="kind" className="w-full"><Options pairs={kinds} /></NativeSelect>
            </Field>
            <Field label="Day" htmlFor={`event-at-${f.id}`}><Input id={`event-at-${f.id}`} type="date" name="at" required defaultValue={today} max={today} /></Field>
          </div>
          <Field label="Detail (optional)" htmlFor={`event-detail-${f.id}`}>
            <Input id={`event-detail-${f.id}`} name="detail" maxLength={1000} placeholder="e.g. Grandma talked for 40 minutes about the move from Hue" />
          </Field>
          <Button type="submit" size="lg" variant="outline" className="self-start" disabled={!!busy}>{busy === `event:${f.id}` ? "Logging…" : "Log it"}</Button>
        </form>
      </More>
    </Item>
  )
}

function AddFamily({ states, busy, run, primary = true }: { states: Pair[]; primary?: boolean } & Do) {
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    if (await run("add-family", async () => { await api("/api/family", fields(form)); return "Family added. Log its first call when it happens." })) form.reset()
  }
  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Family name or label" htmlFor="family-label" className="sm:col-span-2 lg:col-span-1"><Input id="family-label" name="label" required maxLength={120} placeholder="e.g. The Tran family" /></Field>
        <Field label="Storyteller" htmlFor="family-storyteller"><Input id="family-storyteller" name="storyteller" maxLength={120} placeholder="Who is interviewed" /></Field>
        <Field label="Adult child" htmlFor="family-child"><Input id="family-child" name="adult_child" maxLength={120} placeholder="Who signed them up" /></Field>
        <Field label="Enrolled on" htmlFor="family-enrolled"><Input id="family-enrolled" type="date" name="enrolled_on" max={todayEastern()} /></Field>
        <Field label="Status" htmlFor="family-status">
          <NativeSelect id="family-status" name="status" className="w-full"><Options pairs={states} /></NativeSelect>
        </Field>
        <Field label="Notes" htmlFor="family-notes"><Textarea id="family-notes" name="notes" rows={1} className="min-h-11" maxLength={2000} /></Field>
      </div>
      <Button type="submit" size="lg" variant={primary ? "default" : "outline"} className="self-start" disabled={!!busy}>{busy === "add-family" ? "Adding…" : "Add family"}</Button>
    </form>
  )
}

function IntakePanel({ i, busy, run }: { i: Intake } & Do) {
  const { toast } = useFeedback()
  const provider = (p: string) => i.providers[p] || p
  const keys = i.api.filter((a) => a.credential_present).map((a) => a.name)
  async function importFile(e: FormEvent<HTMLFormElement>, file: string) {
    e.preventDefault()
    const form = e.currentTarget
    await run(`import:${file}`, async () => {
      const r = await api<{ point_count: number; file_name: string }>("/api/metrics-import", { file, ...fields(form) })
      toast(`Imported ${plural(r.point_count, "number")} from ${r.file_name}.`)
    })
  }
  return (
    <Panel id="intake" title="Numbers from your exports" className="scroll-mt-4">
      <p className="max-w-[70ch] text-base text-muted-foreground">
        Save a CSV export from App Store Connect, Stripe or RevenueCat into the metrics folder on this PC, then import it here. Every number keeps its file and its day.
      </p>
      <div><CopyButton text={i.inbox} label="Copy the folder path" /></div>
      {i.files.length
        ? (
          <ul aria-label="Exports in the folder" className="flex flex-col">
            {i.files.map((f, n) => (
              <li key={f.name} className="flex flex-col gap-3 border-t py-4 first:border-t-0 first:pt-0">
                <div className="flex flex-col gap-0.5">
                  <span className="text-base font-semibold break-all">{f.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {fileSize(f.size)} · {day(f.modified)}{f.imported ? ` · Imported ${day(f.imported.imported_at)} as ${provider(f.imported.provider)}.` : ""}
                  </span>
                </div>
                {!f.imported && (
                  <form onSubmit={(e) => importFile(e, f.name)} className="flex flex-wrap items-end gap-4">
                    <Field label="Export from" htmlFor={`import-provider-${n}`}>
                      <NativeSelect id={`import-provider-${n}`} name="provider"><Options pairs={Object.entries(i.providers)} /></NativeSelect>
                    </Field>
                    <Field label="Note (optional)" htmlFor={`import-note-${n}`} className="min-w-56 flex-1 sm:max-w-md"><Input id={`import-note-${n}`} name="note" maxLength={500} /></Field>
                    <Button type="submit" size="lg" variant="outline" disabled={!!busy}>{busy === `import:${f.name}` ? "Importing…" : "Import this file"}</Button>
                  </form>
                )}
              </li>
            ))}
          </ul>
        )
        : <Empty>No exports waiting. Save a CSV from App Store Connect, Stripe or RevenueCat into the metrics folder, then reload.</Empty>}
      {i.sources.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-base font-semibold">Imported files</h4>
          <Table>
            <TableHeader><TableRow><TableHead>Export</TableHead><TableHead>File</TableHead><TableHead>Covers</TableHead><TableHead className="text-right">Numbers</TableHead><TableHead>Imported</TableHead></TableRow></TableHeader>
            <TableBody>
              {i.sources.map((s, n) => (
                <TableRow key={n}>
                  <TableCell>{provider(s.provider)}</TableCell><TableCell>{s.file_name}</TableCell>
                  <TableCell className="whitespace-nowrap">{rangeWords({ start: s.period_start, end: s.period_end })}</TableCell>
                  <TableCell className="text-right tabular-nums">{s.point_count}</TableCell><TableCell className="whitespace-nowrap">{day(s.imported_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {i.latest.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-base font-semibold">Latest value of every imported metric</h4>
          <Table>
            <TableHeader><TableRow><TableHead>Source</TableHead><TableHead>Metric</TableHead><TableHead>Day</TableHead><TableHead className="text-right">Value</TableHead><TableHead>From</TableHead></TableRow></TableHeader>
            <TableBody>
              {i.latest.map((p, n) => (
                <TableRow key={n}>
                  <TableCell>{provider(p.provider)}</TableCell><TableCell>{p.metric.replaceAll("_", " ")}</TableCell>
                  <TableCell className="whitespace-nowrap">{day(p.period)}</TableCell>
                  <TableCell className="text-right tabular-nums">{pointValue(p)}</TableCell><TableCell className="text-sm text-muted-foreground">{p.file_name}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <More summary="About automatic pulls">
        <p className="max-w-[70ch] text-base text-muted-foreground">
          Automatic pulls are not switched on, so numbers come only from the files you import. When they are switched on, each key is kept in Windows Credential Manager, not in Founder OS; {keys.length ? `a key is stored for ${keys.join(" and ")}.` : "no key is stored yet."}
        </p>
      </More>
    </Panel>
  )
}

export function FamiliesPage() {
  const state = useLoad(() => api<ProductData>("/api/product"))
  const { busy, run } = useRun(state.reload)
  const { confirm } = useFeedback()
  useHashScroll(!!state.data)

  async function removeEvent(e: FamilyEvent, f: Family) {
    if (!(await confirm({
      title: "Remove this event from the journal?",
      body: <><strong className="font-semibold text-foreground">{f.label}: {e.kind_words}, {day(e.at)}.</strong> The measured numbers change with it.</>,
      action: "Remove the event", danger: true,
    }))) return
    await run(`remove:${e.id}`, async () => { await api("/api/family-event-delete", { id: e.id }); return "Event removed." })
  }

  return (
    <Shell active="Customers" tab="/families" title="Beta families">
      <LoadGate state={state}>{(b) => {
        const c = b.counts, r = b.retention
        const intake = <IntakePanel i={b.intake} busy={busy} run={run} />
        // No families yet: one sentence and the form. Counts and rates appear once there is something to count.
        if (!b.families.length) return (
          <>
            <PageHead title="Beta families" line="No families yet. Add each one yourself; the numbers are counted from what you log." />
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <Panel title="Add the first family"><AddFamily states={b.family_states} busy={busy} run={run} /></Panel>
              {intake}
            </div>
          </>
        )
        const counted = c.first_calls + c.second_calls + c.contributing + c.issues > 0
        return (
          <>
            <PageHead title="Beta families"
              line={`${plural(c.families, "family", "families")}, ${c.first_calls} with a first call${c.issues ? `, ${plural(c.issues, "issue")} logged` : ""}.`} />
            {counted && (
              <Panel>
                <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
                  <Fact label="Families">{c.families}</Fact>
                  <Fact label="Had a first call">{c.first_calls}</Fact>
                  <Fact label="Had a second call">{c.second_calls}</Fact>
                  <Fact label="With a relative contributing">{c.contributing}</Fact>
                  {c.issues > 0 && <Fact label="Issues logged" tone="deadline">{c.issues}</Fact>}
                </div>
              </Panel>
            )}
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <Panel title="The journal">
                <Limited items={b.families} label="Beta families">
                  {(f) => <FamilyItem key={f.id} f={f} kinds={b.event_kinds} states={b.family_states} busy={busy} run={run} removeEvent={removeEvent} />}
                </Limited>
              </Panel>
              <div className="flex min-w-0 flex-col gap-5">
                <Panel title="Measured so far" aside={r.as_of ? `As of ${day(r.as_of)}` : "Nothing measured yet"}>
                  <Measured metrics={r.metrics} />
                  <More summary="How these are used">
                    <p className="text-base text-muted-foreground">These count as measured facts, dated, ahead of numbers you report yourself. A rate with nothing to divide by stays empty and never shows zero.</p>
                  </More>
                </Panel>
                <Panel title="Add a family"><AddFamily states={b.family_states} busy={busy} run={run} primary={false} /></Panel>
              </div>
            </div>
            {intake}
          </>
        )
      }}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/families": () => <FamiliesPage /> } }
