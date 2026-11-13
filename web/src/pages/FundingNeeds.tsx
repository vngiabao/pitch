import { useState } from "react"
import { ArrowRight, ChevronRight, Download, ExternalLink } from "lucide-react"

import { Empty, LoadGate, PageHead, Panel, Row, Rows, Tag, useHashScroll, useLoad } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { closingWords } from "@/lib/format"
import {
  accessTone, accessWords, appUrl, daysLeft, daysPct, isSoon, loadFundingNeeds, moneyWords, outcomeTone, plainName, programNotes,
  trackedHref, trackedLine, type AppRow, type FundingNeeds, type LeadCard, type NeedRow, type Opp, type Tracked,
} from "@/lib/funding"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { NextStep } from "@/pages/Today"
import { ProgramMark, Shell } from "@/shell"

const linkClass = "rounded-md font-medium text-foreground underline underline-offset-4 hover:text-primary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"
const outside = (external?: boolean) => (external ? { target: "_blank", rel: "noopener noreferrer" } : {})
// Reading text is capped near 70 characters a line (56ch of this face's wide zero).
const READ = "max-w-[56ch]"

// A next step that isn't an application with answers left (every answer ready, a program closing, a form that needs
// Bao's login, a credit date): the title, the money and the date, one line, and the button right under them.
function OtherStep({ lead }: { lead: LeadCard }) {
  return (
    <Panel>
      <div className="flex flex-col gap-1">
        <span className="text-sm text-muted-foreground">Do next</span>
        <h3 className="text-2xl leading-tight font-semibold tracking-tight">{lead.title}</h3>
      </div>
      {lead.money && (
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 text-xl font-semibold">
          <span className={cn(lead.money.known ? "text-money" : "text-muted-foreground")}>{lead.money.text}</span>
          <span className={cn(lead.soon ? "text-deadline" : "text-muted-foreground")}>{lead.closing}</span>
          {lead.investment && <span className="text-base font-normal text-muted-foreground">Investment, not a grant</span>}
        </div>
      )}
      <p className={cn(READ, "text-base text-muted-foreground")}>{lead.body}</p>
      <div>
        <Button size="lg" asChild>
          <a href={lead.href} {...outside(lead.external)}>
            {lead.label}{lead.external ? <ExternalLink aria-hidden="true" /> : <ArrowRight aria-hidden="true" />}
          </a>
        </Button>
      </div>
    </Panel>
  )
}

// Everything else Funding needs, as one list of rows in one shape. Applications being drafted also show their
// bar and "12 of 36 ready".
function AfterThat({ data }: { data: FundingNeeds }) {
  const [all, setAll] = useState(false)
  const total = data.after.length
  const rows = all ? data.after : data.after.slice(0, 6)
  return (
    <Panel title="After that">
      <ul aria-label="After that" className="flex flex-col">
        {rows.map((r) => <NeedLink key={r.key} r={r} />)}
      </ul>
      {total > 6 && !all && <div><Button size="lg" variant="outline" onClick={() => setAll(true)}>Show all {total}</Button></div>}
    </Panel>
  )
}

// One thing that needs Bao: the program's mark and name on the panel's left edge, one line under it (a deadline
// within 14 days in red, first), and the whole row opens it. Today's CompanyRow shape, without its dot column.
function NeedLink({ r }: { r: NeedRow }) {
  const pct = r.total ? Math.round(((r.ready || 0) / r.total) * 100) : 0
  return (
    <li className="border-t first:border-t-0">
      <a href={r.href} {...outside(r.external)}
        className="-mx-2 flex min-h-16 items-center gap-3 rounded-lg px-2 py-2 hover:bg-secondary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex items-center gap-2 text-base font-semibold"><ProgramMark name={r.name} />{r.name}</span>
          {(r.closing || r.line) && (
            <span className="text-base text-muted-foreground">
              {r.closing && <span className="font-semibold text-deadline">{r.closing}</span>}
              {r.closing && r.line ? " · " : ""}{r.line}
            </span>
          )}
        </span>
        {r.total ? (
          <span className="flex shrink-0 items-center gap-3">
            <Progress value={pct} className="hidden h-1 w-20 sm:block" aria-label={`${r.ready} of ${r.total} answers ready`} />
            <span className="text-right text-sm whitespace-nowrap text-muted-foreground tabular-nums">{r.ready} of {r.total} ready</span>
          </span>
        ) : null}
        <span className="sr-only">{r.label}</span>
        {r.external
          ? <ExternalLink className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          : <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />}
      </a>
    </li>
  )
}

// One open program: its name, the money, how long is left (the bar is days out of 60), where its form stands.
function ProgramRow({ d, app, why }: { d: Opp; app?: AppRow; why: boolean }) {
  const days = daysLeft(d), pct = daysPct(days), soon = isSoon(days), fig = moneyWords(d)
  const brief = d.analysis.founder_brief
  return (
    <li className="flex flex-col gap-1 border-t py-3 first:border-t-0">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
        <a href={appUrl(app) || `/opportunity/${d.opportunity_id}`}
          className="flex min-h-11 min-w-0 items-center gap-2 rounded-lg text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
          <ProgramMark name={d.data.canonical_name} />{plainName(d.data.canonical_name)}
        </a>
        <span className={cn("ml-auto text-base tabular-nums", fig.known ? "font-semibold text-money" : "text-muted-foreground")}>{fig.text}</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
        <span className={cn("flex items-center gap-2", soon && "font-semibold text-deadline")}>
          {pct !== null && days !== null && days >= 0 && (
            <span aria-hidden="true" className="block h-1 w-16 overflow-hidden rounded-full bg-track">
              <span className={cn("block h-full rounded-full", soon ? "bg-deadline" : "bg-primary")} style={{ width: `${pct}%` }} />
            </span>
          )}
          {closingWords(days, d.data.dates.deadline)}
        </span>
        <Tag tone={accessTone(app?.access)}>{accessWords(app?.access)}</Tag>
        {programNotes(d).map((n) => <span key={n}>{n}</span>)}
      </div>
      {why && brief?.how_it_helps && <p className={cn(READ, "text-base text-muted-foreground")}>{brief.how_it_helps}</p>}
    </li>
  )
}

function Programs({ id, title, note, link, rows, why, empty }: { id: string; title: string; note: string; link: [string, string]; rows: FundingNeeds["cash"]; why: boolean; empty: string }) {
  return (
    <Panel id={id} title={title} aside={<a className={cn(linkClass, "flex min-h-11 items-center")} href={link[0]}>{link[1]}</a>}>
      <p className={cn(READ, "text-base text-muted-foreground")}>{note}</p>
      {rows.length
        ? <ol className="flex flex-col">{rows.map(({ d, app }) => <ProgramRow key={d.opportunity_id} d={d} app={app} why={why} />)}</ol>
        : <Empty>{empty}</Empty>}
    </Panel>
  )
}

function TrackedRow({ t, line }: { t: Tracked; line: boolean }) {
  return (
    <Row title={<span className="flex items-center gap-2"><ProgramMark name={t.canonical_name} />{plainName(t.canonical_name)}</span>} line={line ? trackedLine(t) : undefined} href={trackedHref(t)}>
      <Tag tone={outcomeTone(t.outcome)}>{t.outcome}</Tag>
    </Row>
  )
}

// Applications that are in: the ones still waiting on a result, then the ones decided. Today links to this panel.
function Waiting({ data }: { data: FundingNeeds }) {
  const [all, setAll] = useState(false)
  const decided = all ? data.decided : data.decided.slice(0, 5)
  return (
    <Panel id="wait-results-title" title="Waiting on results" className="scroll-mt-4">
      {data.waiting.length
        ? <Rows label="Waiting on results">{data.waiting.map((t) => <TrackedRow key={t.opportunity_id + t.occurred_at} t={t} line />)}</Rows>
        : <Empty>Nothing pending. Mark an application submitted and it shows up here.</Empty>}
      {data.decided.length > 0 && (
        <div className="flex flex-col gap-1">
          <h4 className="text-base font-semibold">Decided</h4>
          <Rows label="Decided">{decided.map((t) => <TrackedRow key={t.opportunity_id + t.occurred_at} t={t} line={false} />)}</Rows>
          {data.decided.length > 5 && !all && <div><Button size="lg" variant="outline" onClick={() => setAll(true)}>Show all {data.decided.length}</Button></div>}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button size="lg" variant="outline" asChild>
          <a href="/api/tracker/export.csv"><Download aria-hidden="true" />Export tracker (CSV)</a>
        </Button>
        {data.inbox === "connected" && <span className="text-sm text-muted-foreground">Inboxes tracked read-only</span>}
        {data.inbox === "connect" && <a className={cn(linkClass, "flex min-h-11 items-center text-sm")} href="/decisions">Connect your inboxes</a>}
      </div>
    </Panel>
  )
}

function Page({ data }: { data: FundingNeeds }) {
  // Today links here with #wait-results-title; go to it once the page has its content (the old page did the same).
  useHashScroll(true)
  const n = data.count
  return (
    <>
      <PageHead title="Needs you" line={n ? `${n === 1 ? "1 thing in Funding needs" : `${n} things in Funding need`} you. Biggest first.` : "Nothing in Funding needs you right now."} />
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          {data.lead && <NextStep lead={data.lead} />}
          {data.card && <OtherStep lead={data.card} />}
          {data.after.length > 0 && <AfterThat data={data} />}
          <Programs id="cash-title" title="More cash on the table" link={["/opportunities", "Full pipeline"]} rows={data.cash} why
            note="Prizes, grants and fellowships, soonest deadline first."
            empty="Nothing else open with cash right now. Run research to look for new competitions and grants." />
          <Programs id="credit-title" title="More credits that cut real costs" link={["/credits", "Your credits"]} rows={data.credits} why={false}
            note="Ranked by how directly they cover the voice and AI services A Story runs on."
            empty="No other open credit programs." />
        </div>
        <Waiting data={data} />
      </div>
    </>
  )
}

export function FundingNeedsPage() {
  const state = useLoad(loadFundingNeeds)
  return (
    <Shell active="Funding" tab="/funding" title="Needs you">
      <LoadGate state={state}>{(data) => <Page data={data} />}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/funding": () => <FundingNeedsPage /> } }
