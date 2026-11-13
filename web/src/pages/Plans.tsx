import { useState, type FormEvent } from "react"
import { ExternalLink, FileDown } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Empty, Fact, Field, LoadGate, PageHead, Panel, Row, Rows, Tag, useLoad } from "@/components/app/page"
import { planStateWord, type PlanItem, type PlanReport, type Plans } from "@/lib/agents"
import { noDash } from "@/lib/company"
import { api } from "@/lib/api"
import { day, plural, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"
import { Disclosure, useShowAll } from "@/pages/Decisions"

// "Daniel · Nov 2": the parts that are there, with any year-month-day date in them written as a day.
const joined = (...parts: (string | undefined | null)[]) =>
  parts.filter(Boolean).join(" · ").replace(/\b\d{4}-\d{2}-\d{2}\b/g, (d) => day(d))

// A number that leads with money ("$39 across 11 families") shows the amount alone, in brass; the rest goes on the line under it.
function figure(n: { value: string; label: string }) {
  const m = /^(\$[\d,.]+[KMB]?)(?:\s+(?:across|from|over|for|in)\s+(.+))?$/i.exec(String(n.value).trim())
  if (!m) return { value: n.value, rest: "", money: false }
  return { value: m[1], rest: m[2] || "", money: true }
}

// The brief's own files stay on the server: the PDF downloads, the web version opens in a new tab.
function Files({ plan }: { plan: PlanItem }) {
  if (!plan.pdf_url && !plan.html_url) return null
  return (
    <div className="flex flex-wrap gap-3">
      {plan.pdf_url && <Button size="lg" variant="outline" asChild><a href={plan.pdf_url}><FileDown aria-hidden="true" />Open the PDF</a></Button>}
      {plan.html_url && <Button size="lg" variant="outline" asChild><a href={plan.html_url} target="_blank" rel="noopener"><ExternalLink aria-hidden="true" />Web version</a></Button>}
    </div>
  )
}

// The latest brief: the bottom line and its numbers, this week's moves, the decisions, then the rest one click away.
function Latest({ plan }: { plan: PlanItem }) {
  const p: PlanReport | null | undefined = plan.report
  if (!p) return null
  const asked = (
    <div className="flex flex-col gap-0.5 text-sm text-muted-foreground">
      <p className="max-w-[70ch]">You asked: {plan.question}</p>
      {plan.finished_at && <p>Written <time dateTime={plan.finished_at}>{stamp(plan.finished_at)}</time></p>}
    </div>
  )
  const title = noDash(plan.title) || "Plan"
  if (!p.bottom_line && p.answer) {
    return (
      <Panel title={title}>
        {asked}
        {p.answer.slice(0, 2).map((x, i) => <p key={i} className="max-w-[70ch] text-base">{x}</p>)}
        <p className="text-sm text-muted-foreground">An older long-form report. New reports are one-page briefs.</p>
        <Files plan={plan} />
      </Panel>
    )
  }
  const moves = p.moves || [], decisions = p.decisions || [], numbers = p.numbers || [], byAgent = p.by_agent || [], risks = p.risks || [], later = p.later || []
  return (
    <>
      <Panel title={title}>
        {asked}
        {p.bottom_line && <div className="rounded-lg bg-secondary px-4 py-3"><p className="max-w-[70ch] text-base font-medium">{noDash(p.bottom_line)}</p></div>}
        {numbers.length > 0 && (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            {numbers.map((n, i) => {
              const f = figure(n)
              return (
                <Fact key={i} label={n.label} tone={f.money ? "money" : undefined}>
                  <span className="tabular-nums">{f.value}</span>
                  {(f.rest || n.source) && <span className="block text-sm font-normal text-muted-foreground">{[f.rest, n.source].filter(Boolean).join(" · ")}</span>}
                </Fact>
              )
            })}
          </div>
        )}
        <Files plan={plan} />
      </Panel>
      {moves.length > 0 && (
        <Panel title="This week">
          <Rows label="This week">
            {moves.map((m, i) => <Row key={i} title={m.what} line={joined(m.owner, m.by, m.why)} />)}
          </Rows>
        </Panel>
      )}
      {decisions.length > 0 && (
        <Panel title="Decide">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader><TableRow><TableHead>Decision</TableHead><TableHead>Recommended</TableHead><TableHead>Unblocks</TableHead></TableRow></TableHeader>
              <TableBody>
                {decisions.map((d, i) => (
                  <TableRow key={i}>
                    <TableCell className="min-w-56 align-top font-semibold whitespace-normal">{d.decision}</TableCell>
                    <TableCell className="min-w-56 align-top whitespace-normal">{d.recommend}</TableCell>
                    <TableCell className="min-w-48 align-top whitespace-normal text-muted-foreground">{d.unblocks}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Panel>
      )}
      {(byAgent.length > 0 || risks.length > 0 || later.length > 0) && (
        <Panel title="More in this brief">
          <div className="flex flex-col">
            {byAgent.length > 0 && (
              <Disclosure summary={`By agent (${byAgent.length})`}>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>Agent</TableHead><TableHead>Result</TableHead><TableHead>Needs you</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {byAgent.map((a, i) => (
                        <TableRow key={i}>
                          <TableCell className="align-top font-semibold">{a.agent}</TableCell>
                          <TableCell className="min-w-56 align-top whitespace-normal">{a.result}</TableCell>
                          <TableCell className="min-w-48 align-top whitespace-normal text-muted-foreground">{a.needs}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Disclosure>
            )}
            {(risks.length > 0 || later.length > 0) && (
              <Disclosure summary="Risks and later">
                {risks.length > 0 && <ul className="flex max-w-[70ch] list-disc flex-col gap-1 pl-5 text-base">{risks.map((x, i) => <li key={i}>{x}</li>)}</ul>}
                {later.length > 0 && (
                  <ul className="flex max-w-[70ch] list-disc flex-col gap-1 pl-5 text-base">
                    {later.map((x, i) => <li key={i}>{x.what} <span className="text-sm text-muted-foreground">{joined(x.owner, x.by)}</span></li>)}
                  </ul>
                )}
              </Disclosure>
            )}
          </div>
        </Panel>
      )}
    </>
  )
}

function Past({ items }: { items: PlanItem[] }) {
  const { shown, more } = useShowAll(items, 6)
  if (!items.length) return null
  return (
    <Panel title="Past briefs" aside={plural(items.length, "brief")}>
      <Rows label="Past briefs">
        {shown.map((x, i) => (
          <Row key={x.id || i} title={noDash(x.title || x.question)}
            line={<><time dateTime={x.created_at}>{stamp(x.created_at)}</time>{x.auto ? " · weekly" : ""}{x.state === "FAILED" && x.error ? ` · ${x.error.slice(0, 80)}` : ""}</>}>
            <Tag tone={x.state === "READY" ? "good" : x.state === "QUEUED" ? "review" : "urgent"}>{planStateWord(x)}</Tag>
            {x.pdf_url
              ? <Button size="lg" variant="outline" asChild><a href={x.pdf_url} aria-label={`PDF: ${x.title || x.question}`}><FileDown aria-hidden="true" />PDF</a></Button>
              : x.state === "READY" && x.html_url
                ? <Button size="lg" variant="outline" asChild><a href={x.html_url} target="_blank" rel="noopener" aria-label={`Open: ${x.title || x.question}`}><ExternalLink aria-hidden="true" />Open</a></Button>
                : null}
          </Row>
        ))}
      </Rows>
      {more}
    </Panel>
  )
}

export function PlansPage() {
  const state = useLoad(() => api<Plans>("/api/plans"))
  const { toast } = useFeedback()
  const [question, setQuestion] = useState("")
  const [asking, setAsking] = useState(false)

  // An empty question is allowed: the server then uses the default one shown in the box.
  const ask = async (e: FormEvent) => {
    e.preventDefault()
    setAsking(true)
    try {
      await api("/api/plan", { question })
      await state.reload()
      setQuestion("")
      toast("The brief is being written. Reload in about 2 minutes; the PDF appears here.")
    } catch (err) { toast(err instanceof Error ? err.message : "Unable to complete this action.", true) } finally { setAsking(false) }
  }

  return (
    <Shell active="Agents" tab="/plans" title="Plans">
      <LoadGate state={state}>
        {(r) => (
          <>
            <PageHead title="Plans"
              line={r.writing ? "A brief is being written now. It appears here in about 2 minutes."
                : r.latest ? `${plural((r.items || []).length, "brief")}. The latest was written ${day(r.latest.finished_at || r.latest.created_at)}.`
                : "No brief yet. Ask a question to get the first one."} />
            <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <div className="flex flex-col gap-5">
                <Panel title="Ask for a brief" aside="A one-page PDF in about 2 minutes">
                  <form onSubmit={ask} className="flex flex-col gap-4">
                    <Field label="What do you want to know?" htmlFor="plan-question"
                      hint="You get the answer, three moves and the decisions only you can make. Leave it empty to ask the question shown.">
                      <Textarea id="plan-question" name="question" value={question} onChange={(e) => setQuestion(e.target.value)}
                        maxLength={600} placeholder={r.default_question} className="md:text-base" />
                    </Field>
                    <Button type="submit" size="lg" className="self-start" disabled={r.writing || asking}>{r.writing || asking ? "Writing…" : "Write the brief"}</Button>
                  </form>
                </Panel>
                {r.latest
                  ? <Latest plan={r.latest} />
                  : <Panel title="No brief yet"><Empty>Ask the question above, or wait for Monday.</Empty></Panel>}
              </div>
              <Past items={r.items || []} />
            </div>
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/plans": () => <PlansPage /> } }
