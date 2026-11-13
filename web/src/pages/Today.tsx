import { useEffect, useState } from "react"
import { ArrowRight, ChevronRight } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { evenBottoms } from "@/components/app/page"
import { cn } from "@/lib/utils"
import { loadToday, moreWords, type Lead, type Mark, type Row, type Today } from "@/lib/today"
import type { PageRoutes } from "@/lib/route-types"
import { ProgramMark, Shell } from "@/shell"

// The moment: the readiness ring draws to its value once (420ms, ease-out); the number shows at once.
export function Ring({ value, total, className }: { value: number; total: number; className?: string }) {
  const pct = total ? Math.round((value / total) * 100) : 0
  return (
    <svg viewBox="0 0 36 36" role="img" aria-label={`${value} of ${total} answers ready`} className={cn("shrink-0", className)}>
      <circle cx="18" cy="18" r="15.5" fill="none" strokeWidth="3.4" className="stroke-track" />
      <circle cx="18" cy="18" r="15.5" fill="none" strokeWidth="3.4" pathLength={100} strokeLinecap="round"
        strokeDasharray={`${pct} 100`} transform="rotate(-90 18 18)" className="ring-draw stroke-primary" />
    </svg>
  )
}

function Figure({ value, label, short }: { value: number; label: string; short: string }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-2">
      <span className="text-xl font-semibold">{value}</span>
      <span className="text-sm text-muted-foreground"><span className="sm:hidden">{short}</span><span className="hidden sm:inline">{label}</span></span>
    </div>
  )
}

const DAYS = 22
function Strip({ marks, figures }: { marks: Mark[]; figures: Today["figures"] }) {
  const rows: number[] = []
  marks.forEach((m, i) => { rows[i] = i > 0 && rows[i - 1] === 0 && m.day - marks[i - 1].day < 6 ? 1 : 0 })
  const twoRows = rows.includes(1)
  const start = new Date()
  const days = Array.from({ length: DAYS }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    return { n: d.getDate() === 1 ? d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) : String(d.getDate()), week: d.getDay() === 1 }
  })
  return (
    <Card className="gap-2 py-4">
      <CardHeader className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <CardTitle className="text-xl font-semibold tracking-tight"><h2>Next three weeks</h2></CardTitle>
        <div className="grid w-full grid-cols-3 gap-3 sm:ml-auto sm:flex sm:w-auto sm:flex-wrap sm:gap-x-6 sm:gap-y-1">
          <Figure value={figures.accepted} label="applications accepted" short="accepted" />
          <Figure value={figures.waiting} label="waiting on results" short="waiting" />
          <Figure value={figures.cashOpen} label="cash programs open" short="cash open" />
        </div>
      </CardHeader>
      <CardContent>
        {/* Desktop: the real calendar strip. Phone: the same deadlines as a list. */}
        <div className={cn("relative hidden md:block", twoRows ? "h-28" : "h-20")}>
          {marks.map((m, i) => (
            <a key={m.name} href="/funding" aria-label={`${m.name}, ${m.prize}, closes ${m.date}`}
              className={cn("absolute flex min-h-11 items-center rounded-lg focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none",
                rows[i] ? "top-8" : "top-0", m.day > DAYS - 3 && "-translate-x-full")}
              style={{ left: `${(m.day / DAYS) * 100}%` }}>
              <span className="flex items-center gap-2 text-base whitespace-nowrap">
                <ProgramMark name={m.name} />
                <span className="font-medium">{m.name}</span>
                <span className="font-semibold text-money">{m.prize}</span>
              </span>
            </a>
          ))}
          {marks.map((m) => (
            <i key={m.name + "-dot"} aria-hidden="true"
              className={cn("absolute block size-2 -translate-x-1/2 translate-y-1/2 rounded-full", m.soon ? "bg-deadline" : "bg-muted-foreground")}
              style={{ left: `${(m.day / DAYS) * 100}%`, bottom: "2.25rem" }} />
          ))}
          <div aria-hidden="true" className="absolute inset-x-0 bottom-0 grid border-t" style={{ gridTemplateColumns: `repeat(${DAYS}, minmax(0, 1fr))` }}>
            {days.map((d, i) => (
              <div key={i} className={cn("text-sm relative pt-2 text-left text-muted-foreground before:absolute before:top-0 before:left-0 before:h-1.5 before:w-px before:bg-border",
                d.week && "before:h-3 before:bg-foreground/30")}>
                {i === 0
                  ? <span className="inline-flex h-6 items-center rounded-md bg-primary px-2 font-semibold text-primary-foreground">{d.n}</span>
                  : d.n}
              </div>
            ))}
          </div>
        </div>
        <ul className="flex flex-col md:hidden">
          {marks.map((m) => (
            <li key={m.name} className="flex min-h-11 items-center gap-3 border-t first:border-t-0">
              <i className={cn("size-2 shrink-0 rounded-full", m.soon ? "bg-deadline" : "bg-muted-foreground")} aria-hidden="true" />
              <ProgramMark name={m.name} />
              <span className="flex min-w-0 flex-col">
                <span className="font-medium">{m.name}</span>
                <span className="text-sm font-semibold text-money">{m.prize}</span>
              </span>
              <span className={cn("ml-auto text-sm whitespace-nowrap", m.soon ? "font-semibold text-deadline" : "text-muted-foreground")}>{m.date}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

export function Stat({ label, value, tone, short, shortLabel }: { label: string; value: string; tone?: "money" | "deadline"; short?: string; shortLabel?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground"><span className="sm:hidden">{shortLabel || label}</span><span className="hidden sm:inline">{label}</span></span>
      <span className={cn("text-base font-semibold sm:text-xl", tone === "money" && "text-money", tone === "deadline" && "text-deadline")}><span className="sm:hidden">{short || value}</span><span className="hidden sm:inline">{value}</span></span>
    </div>
  )
}

export function NextStep({ lead }: { lead: Lead }) {
  const soon = lead.days !== null && lead.days >= 0 && lead.days <= 14
  const closes = lead.deadline
    ? `${lead.deadline}${lead.days !== null && lead.days >= 0 ? ` · ${lead.days} ${lead.days === 1 ? "day" : "days"}` : ""}`
    : "Date not published"
  const more = moreWords(lead)
  return (
    <Card className="gap-5 py-5">
      <CardHeader className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4 gap-y-1">
        <Ring value={lead.answered} total={lead.questions} className="size-10 sm:row-span-2 sm:size-14" />
        <CardDescription className="text-sm sm:self-end">Do next</CardDescription>
        <div className="col-span-2 min-w-0 sm:col-span-1 sm:col-start-2">
          <CardTitle className="text-2xl leading-tight font-semibold tracking-tight"><h2>Finish the {lead.program}</h2></CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid grid-cols-3 gap-3 sm:gap-6">
          {lead.prize && <Stat label="Prize" value={lead.prize} tone="money" shortLabel="Prize, up to" short={lead.prize.replace(/^Up to /, "")} />}
          <Stat label="Closes" value={closes} tone={soon ? "deadline" : undefined} shortLabel={lead.deadline ? `Closes ${lead.deadline}` : "Closes"} short={lead.days !== null && lead.days >= 0 ? `${lead.days} ${lead.days === 1 ? "day" : "days"}` : closes} />
          <Stat label="Answers ready" value={`${lead.answered} of ${lead.questions}`} />
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Button size="lg" asChild><a href={lead.href}>Continue application</a></Button>
          <Button size="lg" variant="outline" asChild><a href={lead.href}>See all {lead.questions} answers</a></Button>
        </div>
        <div className="flex flex-col">
          <span className="text-sm pb-2 text-muted-foreground">{lead.left} answers left for you</span>
          <ul className="flex flex-col">
            {lead.tasks.map((t) => (
              <li key={t.label} className="flex min-h-12 items-center gap-3 border-t py-1">
                <span className="text-base font-semibold">{t.label}</span>
                <Button size="lg" variant="outline" className="ml-auto w-auto justify-center bg-transparent sm:w-40" asChild>
                  <a href={t.profile ? "/founder-profile" : lead.href}>{t.profile ? "Add to profile" : "Answer"}</a>
                </Button>
              </li>
            ))}
            {more && (
              <li className="border-t">
                <a href={lead.href} className="flex min-h-11 items-center gap-2 rounded-lg font-medium hover:bg-secondary focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none">
                  {more[0].toUpperCase() + more.slice(1)}<ArrowRight className="size-4" aria-hidden="true" />
                </a>
              </li>
            )}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}

export function CompanyRow({ row }: { row: Row }) {
  const pct = row.total ? Math.round(((row.ready || 0) / row.total) * 100) : 0
  return (
    <a href={row.href} className="flex min-h-16 items-center gap-3 rounded-lg border-t px-1 first:border-t-0 hover:bg-secondary focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none">
      <i className={cn("size-2 shrink-0 rounded-full", row.tone === "due" ? "bg-deadline" : "bg-transparent")} aria-hidden="true" />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="flex items-center gap-2 text-base font-semibold">{row.total ? <ProgramMark name={row.name} /> : null}{row.name}</span>
        {row.line && <span className="truncate text-base text-muted-foreground">{row.line}</span>}
      </span>
      {row.total ? (
        <span className="ml-auto flex shrink-0 items-center gap-3">
          <Progress value={pct} className="h-1 w-20" aria-label={`${row.ready} of ${row.total} answers ready`} />
          <span className="w-[6.5rem] text-right text-sm whitespace-nowrap text-muted-foreground">{row.ready} of {row.total} ready</span>
        </span>
      ) : null}
      <ChevronRight className={cn("size-4 shrink-0 text-muted-foreground", !row.total && "ml-auto")} aria-hidden="true" />
    </a>
  )
}

function ResearchNote({ research }: { research: Today["research"] }) {
  if (research.state !== "stopped") return null
  return (
    <Card role="status" className="gap-3 py-5">
      <CardHeader><CardTitle className="text-xl font-semibold tracking-tight"><h2>Research stopped {research.date}</h2></CardTitle></CardHeader>
      <CardContent className="flex flex-col items-start gap-3">
        <p className="max-w-[65ch] text-base text-muted-foreground">{research.cause || "The last run failed."} The research agent needs a fix before the next run.</p>
        <Button size="lg" variant="outline" asChild><a href={research.href}>See what failed</a></Button>
      </CardContent>
    </Card>
  )
}

function Company({ rows }: { rows: Row[] }) {
  return (
    <Card className="gap-4 py-5">
      <CardHeader><CardTitle className="pl-6 text-xl font-semibold tracking-tight"><h2>The company today</h2></CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-4">
        <nav aria-label="The company today" className="flex flex-col">
          {rows.filter((r) => !r.total).map((r) => <CompanyRow key={r.name + r.line} row={r} />)}
        </nav>
        {rows.some((r) => r.total) && (
          <nav aria-label="Drafts in progress" className="flex flex-col">
            <span className="pb-1 pl-6 text-sm text-muted-foreground">Drafts in progress</span>
            {rows.filter((r) => r.total).map((r) => <CompanyRow key={r.name} row={r} />)}
          </nav>
        )}
      </CardContent>
    </Card>
  )
}

export function TodayPage() {
  const [today, setToday] = useState<Today | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => { loadToday().then(setToday).catch(() => setError(true)) }, [])
  return (
    <Shell active="Today" title="Today">
        {error && (
          <Alert>
            <AlertTitle>Today didn’t load</AlertTitle>
            <AlertDescription className="flex items-center gap-2">
              The Founder OS server didn’t answer.
              <Button variant="link" className="h-auto p-0" onClick={() => location.reload()}>Load it again</Button>
            </AlertDescription>
          </Alert>
        )}
        {!today && !error && <div className="flex flex-col gap-5"><Skeleton className="h-36" /><Skeleton className="h-96" /></div>}
        {today && (
          <>
            {today.marks.length > 0 && <Strip marks={today.marks} figures={today.figures} />}
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <div className="flex flex-col gap-5">
                {today.lead
                  ? <NextStep lead={today.lead} />
                  : (
                    <Card className="py-6">
                      <CardHeader>
                        <CardTitle className="text-2xl font-semibold tracking-tight">{today.partial ? "Part of your work didn’t load" : "Nothing needs you right now"}</CardTitle>
                      </CardHeader>
                    </Card>
                  )}
                <ResearchNote research={today.research} />
              </div>
              <Company rows={today.rows} />
            </div>
          </>
        )}
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/today": () => <TodayPage />, "/next/today": () => <TodayPage /> } }
