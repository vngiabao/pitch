import { useEffect, useState, type FormEvent } from "react"
import { SlidersHorizontal } from "lucide-react"

import { useFeedback } from "@/components/app/feedback"
import { Empty, Field, LoadGate, PageHead, Panel, Tag, useLoad } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiOnce } from "@/lib/api"
import { prettyKey } from "@/lib/format"
import {
  EFFORTS, FILTER_KEYS, MORE_VIEWS, VIEWS, accessTone, accessWords, appUrl, deadlineWords, effortWords, loadPipeline, pipelineQuery,
  pipelineState, plainName, programSub, typeOptions, valueWords, viewLabel, type Filters, type PipelineRow,
} from "@/lib/funding"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { ProgramMark, Shell } from "@/shell"

const linkClass = "rounded-md font-medium text-foreground underline underline-offset-4 hover:text-primary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"

// The view and the filters live in the URL, as before: /opportunities?view=All&type=grant&min_cash=1000
function fromUrl(): { view: string; filters: Filters } {
  const q = new URLSearchParams(location.search)
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, q.get(k) || ""])) as Filters
  return { view: q.get("view") || "Recommended", filters }
}
const anyOn = (f: Filters) => FILTER_KEYS.some((k) => f[k])

function ProgramsTable({ rows }: { rows: PipelineRow[] }) {
  return (
    <Table className="min-w-[60rem]">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Program</TableHead><TableHead>Value</TableHead><TableHead>Deadline</TableHead><TableHead>Application</TableHead><TableHead>Your effort</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => {
          const { d, app } = r, value = valueWords(d), dl = deadlineWords(d), hours = d.analysis.materials.estimated_hours, answers = appUrl(app)
          return (
            <TableRow key={d.opportunity_id}>
              <TableCell className="max-w-[26rem] align-top whitespace-normal">
                <a href={`/opportunity/${d.opportunity_id}`} className="flex min-h-11 items-center gap-2 rounded-lg text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
                  <ProgramMark name={d.data.canonical_name} />{plainName(d.data.canonical_name)}
                </a>
                <span className="block text-sm text-muted-foreground">{programSub(r)}</span>
              </TableCell>
              <TableCell className="max-w-[22rem] align-top whitespace-normal">
                <span className={cn("block text-base tabular-nums", value.amount ? "font-semibold text-money" : "text-muted-foreground")}>{value.main}</span>
                <span className="line-clamp-2 text-sm text-muted-foreground">{value.sub}</span>
              </TableCell>
              <TableCell className="align-top whitespace-nowrap">
                <span className={cn("block text-base tabular-nums", dl.quiet && "text-muted-foreground")}>{dl.main}</span>
                {dl.sub && <span className={cn("block text-sm tabular-nums", dl.soon ? "font-semibold text-deadline" : "text-muted-foreground")}>{dl.sub}</span>}
              </TableCell>
              <TableCell className="align-top">
                <Tag tone={accessTone(app?.access)}>{accessWords(app?.access)}</Tag>
                {answers && <a href={answers} className={cn(linkClass, "flex min-h-11 items-center text-sm")} aria-label={`Open answers: ${d.data.canonical_name}`}>Open answers</a>}
              </TableCell>
              <TableCell className={cn("align-top whitespace-nowrap", hours == null && "text-muted-foreground")}>
                {hours == null ? "Not estimated" : effortWords(Number(hours))}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

export function PipelinePage() {
  const [start] = useState(fromUrl)
  const [view, setView] = useState(start.view)
  const [draft, setDraft] = useState<Filters>(start.filters) // what the form shows
  const [applied, setApplied] = useState<Filters>(start.filters) // what the list was asked for
  const [open, setOpen] = useState(anyOn(start.filters)) // the filters open by themselves when the URL has one
  const query = pipelineQuery(view, applied)

  const list = useLoad(() => loadPipeline(view, query), [view, query])
  // The dashboard is only needed for the list of program types and the company-facts notice; the table doesn't wait for it.
  const dash = useLoad(() => apiOnce("/api/dashboard"))
  useEffect(() => { history.replaceState(null, "", `/opportunities?${query}`) }, [query])
  // A list that fails to refresh keeps the last one on screen and says why (the old page's toast).
  const { toast } = useFeedback()
  const failed = list.data ? list.error : null
  useEffect(() => { if (failed) toast(failed, true) }, [failed, toast])

  // Changing the view also applies whatever is typed in the filters, as the old page did.
  const pick = (v: string) => { setView(v); setApplied(draft) }
  const submit = (e: FormEvent) => { e.preventDefault(); setApplied(draft) }
  const set = (k: keyof Filters) => (e: { target: { value: string } }) => setDraft((f) => ({ ...f, [k]: e.target.value }))
  const on = anyOn(applied)
  const noFacts = dash.data && dash.data.company_memory?.canonical_claims?.length === 0

  return (
    <Shell active="Funding" tab="/opportunities" title="Pipeline">
      <PageHead title="Pipeline" line={list.data ? pipelineState(list.data, view, on) : "Every program the agents track, and where each application stands."} />

      {noFacts && (
        <Panel title="Company eligibility needs confirmation">
          <p className="max-w-[56ch] text-base text-muted-foreground">No company facts have been approved yet. The agents can still verify programs, but whether A Story fits each one stays open.</p>
          <div><Button size="lg" variant="outline" asChild><a href="/memory">Review company facts</a></Button></div>
        </Panel>
      )}

      <Panel>
        <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
          <div role="group" aria-label="Views" className="flex flex-wrap gap-1 rounded-lg bg-secondary p-1">
            {VIEWS.map((v) => (
              <button key={v} type="button" aria-pressed={v === view} onClick={() => pick(v)}
                className={cn("flex h-11 items-center rounded-md px-4 text-base font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid",
                  v === view && "bg-card font-semibold text-foreground ring-1 ring-foreground/10")}>
                {viewLabel(v)}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm font-medium">
            More views
            <NativeSelect aria-label="More views" value={MORE_VIEWS.includes(view) ? view : ""} onChange={(e) => { if (e.target.value) pick(e.target.value) }}>
              <NativeSelectOption value="">Choose…</NativeSelectOption>
              {MORE_VIEWS.map((v) => <NativeSelectOption key={v} value={v}>{v}</NativeSelectOption>)}
            </NativeSelect>
          </label>
          <Button size="lg" variant="outline" className="ml-auto" aria-expanded={open} aria-controls="filters" onClick={() => setOpen((o) => !o)}>
            <SlidersHorizontal aria-hidden="true" />{on ? "Filters (on)" : "Filters"}
          </Button>
        </div>

        {open && (
          <form id="filters" onSubmit={submit} className="flex flex-col gap-4 rounded-lg bg-secondary p-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Type" htmlFor="f-type">
                <NativeSelect id="f-type" name="type" className="w-full" value={draft.type} onChange={set("type")}>
                  <NativeSelectOption value="">Any type</NativeSelectOption>
                  {typeOptions(dash.data).map((v) => <NativeSelectOption key={v} value={v}>{prettyKey(v)}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
              <Field label="Minimum cash" htmlFor="f-cash"><Input id="f-cash" name="min_cash" type="number" min={0} placeholder="Any" value={draft.min_cash} onChange={set("min_cash")} /></Field>
              <Field label="Deadline before" htmlFor="f-before"><Input id="f-before" name="deadline_before" type="date" value={draft.deadline_before} onChange={set("deadline_before")} /></Field>
              <Field label="Funding" htmlFor="f-terms">
                <NativeSelect id="f-terms" name="non_dilutive" className="w-full" value={draft.non_dilutive} onChange={set("non_dilutive")}>
                  <NativeSelectOption value="">All terms</NativeSelectOption>
                  <NativeSelectOption value="1">No equity taken only</NativeSelectOption>
                </NativeSelect>
              </Field>
              <Field label="Effort" htmlFor="f-effort">
                <NativeSelect id="f-effort" name="effort" className="w-full" value={draft.effort} onChange={set("effort")}>
                  <NativeSelectOption value="">Any effort</NativeSelectOption>
                  {EFFORTS.map((v) => <NativeSelectOption key={v} value={v}>{v === "UNKNOWN" ? "Not estimated" : v}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
              <Field label="Location" htmlFor="f-location"><Input id="f-location" name="location" placeholder="e.g. Michigan" value={draft.location} onChange={set("location")} /></Field>
              <Field label="Category" htmlFor="f-category"><Input id="f-category" name="category" placeholder="e.g. AI" value={draft.category} onChange={set("category")} /></Field>
              <Field label="Minimum fit (0 to 100)" htmlFor="f-score"><Input id="f-score" name="min_score" type="number" min={0} max={100} placeholder="Any" value={draft.min_score} onChange={set("min_score")} /></Field>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" size="lg" variant="outline" disabled={list.loading}>{list.loading ? "Reading…" : "Apply filters"}</Button>
              <Button size="lg" variant="ghost" asChild><a href="/opportunities">Clear</a></Button>
            </div>
          </form>
        )}

        <div id="opportunity-list" aria-busy={list.loading} className={cn("flex flex-col gap-3", list.loading && list.data && "opacity-60")}>
          <LoadGate state={list}>
            {(rows) => rows.length
              ? (
                <>
                  {list.loading && <p className="text-sm text-muted-foreground" role="status">Reading opportunities…</p>}
                  <ProgramsTable rows={rows} />
                </>
              )
              : (
                <Empty action={view !== "All"
                  ? <Button size="lg" variant="outline" onClick={() => pick("All")}>Show all programs</Button>
                  : on ? <Button size="lg" variant="outline" asChild><a href="/opportunities">Clear the filters</a></Button> : undefined}>
                  No programs in this view. Try All, or clear the filters.
                </Empty>
              )}
          </LoadGate>
        </div>
      </Panel>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/opportunities": () => <PipelinePage /> } }
