import { useEffect, useState } from "react"
import { Check } from "lucide-react"

import { useFeedback } from "@/components/app/feedback"
import { Disclosure, LoadGate, PageHead, Panel, Tag, useHashScroll, useLoad } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api } from "@/lib/api"
import { cleanName, closingWords, usd } from "@/lib/format"
import {
  LINK, MOVE_STATES, SEG, SEG_ON, SEG_TRAY, closingSoon, loadMoney, pitchStageWords, programDone, programStatus, rankLine,
  type ApplyFirst, type Category, type Move, type MoveState, type Program, type RankRow,
} from "@/lib/money"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { ProgramMark, Shell } from "@/shell"

const NAME = "inline-flex min-h-11 items-center gap-2 rounded-md text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"
const READ = "max-w-[60ch] text-base text-muted-foreground"

// ---------- Apply to these first: expected money per founder hour ----------
function RankItem({ r, i, max }: { r: RankRow; i: number; max: number }) {
  const p = r.preparation || {}
  const l = r.likelihood, u = r.urgency
  const line = rankLine(r)
  const answers = p.application_id && p.questions ? `/application/${p.application_id}` : null
  return (
    <li className="grid grid-cols-[2ch_minmax(0,1fr)] gap-x-4 border-t py-4 first:border-t-0 first:pt-0 last:pb-0">
      <span className="pt-2.5 text-base font-semibold text-muted-foreground tabular-nums" aria-hidden="true">{i + 1}</span>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-start justify-between gap-x-6">
          <a href={`/opportunity/${r.opportunity_id}`} className={NAME}><ProgramMark name={r.name} />{cleanName(r.name)}</a>
          <span className="flex items-baseline gap-2 pt-2 whitespace-nowrap">
            <span className="text-xl font-semibold text-money tabular-nums">{usd(r.per_hour)}</span>
            <span className="text-sm text-muted-foreground">per hour, modeled</span>
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-track" aria-hidden="true">
          <div className="h-full min-w-1 rounded-full bg-foreground/60" style={{ width: `${max ? (r.per_hour / max) * 100 : 0}%` }} />
        </div>
        <p className={cn(READ, "pt-1")}>
          <span className="font-semibold text-money">{usd(line.amount)}</span>{line.credits ? " in credits" : ""} possible for {line.work}.{line.prep ? ` ${line.prep}` : ""}
        </p>
        <div className="flex flex-wrap items-center gap-x-5">
          {r.deadline && u.days != null && (
            <span className={cn("flex min-h-11 items-center text-sm", closingSoon(u.days) ? "font-semibold text-deadline" : "text-muted-foreground")}>{closingWords(u.days, r.deadline)}</span>
          )}
          {answers && <a href={answers} className={LINK}>Prepared answers</a>}
          {p.edition && <a href={`/pitch-lab/${p.edition.id}`} className={LINK}>Pitch edition</a>}
        </div>
        <Disclosure label="How this was figured">
          <p className={cn(READ, "text-sm")}>{r.reason}</p>
          <ul className="flex max-w-[60ch] flex-col gap-1 text-sm text-muted-foreground">
            <li>Money: <span className="font-semibold text-money">{usd(r.money.counted)}</span> counted ({r.money.basis})</li>
            <li>Likelihood: {Math.round(l.value * 100)}% (fit {l.fit_known ? l.fit : `about ${l.fit}`}, {l.eligibility.toLowerCase()}{l.eligibility_factor < 1 ? ", halved" : ""})</li>
            <li>Hours: {r.hours.value} ({r.hours.source})</li>
            <li>Urgency: x{u.factor}{u.days != null ? ` (${u.days} days left)` : ""}</li>
            <li>Expected value: <span className="font-semibold text-money">{usd(r.expected_value)}</span></li>
          </ul>
        </Disclosure>
      </div>
    </li>
  )
}

function ApplyFirstPanel({ data }: { data: ApplyFirst }) {
  const max = Math.max(...data.rows.map((r) => r.per_hour))
  const unpriced = data.unpriced || []
  return (
    <Panel id="apply-first" className="scroll-mt-4" title="Apply to these first" aside="Expected money per hour of your time">
      <ol className="flex flex-col">{data.rows.map((r, i) => <RankItem key={r.opportunity_id} r={r} i={i} max={max} />)}</ol>
      <Disclosure label="How this number is made" className="border-t pt-2">
        <p className={cn(READ, "text-sm")}>
          Cash prize maximum, or credit face value counted at 25 percent, times a win likelihood from the fit score (fit above 40 scaled to a
          60 percent ceiling, halved while eligibility is unknown), divided by the estimated hours of your time (3 when there is no estimate),
          times an urgency factor for programs closing within 14 days (up to 2x on the closing day). The number orders the work.
        </p>
        {unpriced.length > 0 && <p className={cn(READ, "text-sm")}>Not ranked because no amount is published: {unpriced.map((x) => cleanName(x.name)).join(", ")}.</p>}
      </Disclosure>
    </Panel>
  )
}

// ---------- Your money moves: To do / Doing / Done ----------
function MoveItem({ m, busy, onSet }: { m: Move; busy: boolean; onSet: (m: Move, s: MoveState) => void }) {
  return (
    <li className="flex flex-col gap-2 border-t py-4 first:border-t-0 first:pt-1">
      <div className="flex flex-col gap-0.5">
        <span className={cn("text-base font-semibold", m.state === "DONE" && "text-muted-foreground")}>{cleanName(m.title)}</span>
        <span className={READ}>{cleanName(m.detail)}</span>
      </div>
      <div role="group" aria-label={`Status of ${m.title}`} className={cn(SEG_TRAY, "self-start")}>
        {MOVE_STATES.map(([v, label]) => {
          const on = m.state === v
          return (
            <button key={v} type="button" aria-pressed={on} disabled={busy} onClick={() => { if (!on) onSet(m, v) }}
              className={cn(SEG, on && SEG_ON, on && v === "DONE" && "text-good")}>
              {on && v === "DONE" && <Check className="size-4" aria-hidden="true" />}{label}
            </button>
          )
        })}
      </div>
    </li>
  )
}

function MovesPanel({ moves, busy, onSet }: { moves: Move[]; busy: string | null; onSet: (m: Move, s: MoveState) => void }) {
  const groups = [...new Set(moves.map((m) => m.grp))]
  return (
    <Panel id="moves" className="scroll-mt-4" title="Your money moves" aside="The fastest money doesn’t need a judge">
      {groups.map((g) => (
        <section key={g} className="flex flex-col" aria-label={g}>
          <h4 className="border-b pb-2 text-sm font-medium text-muted-foreground">{g}</h4>
          <ul className="flex flex-col">
            {moves.filter((m) => m.grp === g).map((m) => <MoveItem key={m.id} m={m} busy={busy === m.id} onSet={onSet} />)}
          </ul>
        </section>
      ))}
    </Panel>
  )
}

// ---------- Programs by group: one group at a time ----------
const IN_VIEW = 7

function ProgramRow({ p }: { p: Program }) {
  const done = programDone(p)
  const status = programStatus(p)
  const closes = p.deadline ? closingWords(p.days, p.deadline) : p.rolling ? "Rolling" : "No deadline published"
  return (
    <TableRow>
      <TableCell className="py-1">
        <a href={`/opportunity/${p.id}`} className={cn(NAME, done && "font-medium text-muted-foreground")}><ProgramMark name={p.name} />{cleanName(p.name)}</a>
      </TableCell>
      <TableCell className={cn("py-1 text-right whitespace-nowrap tabular-nums", p.amount ? "font-semibold text-money" : "text-sm text-muted-foreground")}>
        {p.amount || (p.kind === "CREDITS" ? "Credit value unknown" : "Amount unknown")}
      </TableCell>
      <TableCell className={cn("py-1 text-sm whitespace-nowrap", !done && closingSoon(p.days) && p.deadline ? "font-semibold text-deadline" : "text-muted-foreground")}>{closes}</TableCell>
      <TableCell className="py-1"><Tag tone={status.tone}>{status.text}</Tag></TableCell>
      <TableCell className="py-1 whitespace-nowrap">{p.application_id && <a href={`/application/${p.application_id}`} className={LINK}>Answers</a>}</TableCell>
      <TableCell className="py-1 whitespace-nowrap">
        {p.edition
          ? <a href={`/pitch-lab/${p.edition.id}`} className={LINK}>Pitch {pitchStageWords(p.edition.stage)}</a>
          : !done && <a href={`/pitch-lab?program=${p.id}`} className={LINK}>Tailor the pitch</a>}
      </TableCell>
    </TableRow>
  )
}

function GroupTable({ c }: { c: Category }) {
  const [all, setAll] = useState(false)
  const rows = all ? c.programs : c.programs.slice(0, IN_VIEW)
  return (
    <div id={`cat-${c.key}`} role="tabpanel" aria-label={c.title} className="flex scroll-mt-4 flex-col gap-4">
      <p className={READ}>{c.note}</p>
      <Table className="min-w-[60rem] table-fixed">
        <colgroup><col /><col className="w-44" /><col className="w-56" /><col className="w-56" /><col className="w-28" /><col className="w-44" /></colgroup>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Program</TableHead><TableHead className="text-right">Amount</TableHead><TableHead>Closes</TableHead>
            <TableHead>Status</TableHead><TableHead>Answers</TableHead><TableHead>Pitch</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>{rows.map((p) => <ProgramRow key={p.id} p={p} />)}</TableBody>
      </Table>
      {c.programs.length > IN_VIEW && !all && (
        <Button size="lg" variant="outline" className="self-start" onClick={() => setAll(true)}>Show all {c.programs.length}</Button>
      )}
    </div>
  )
}

// The group named by the address (#cat-grants), when there is one
const hashGroup = (groups: Category[]) => {
  let id = ""
  try { id = decodeURIComponent(location.hash.slice(1)) } catch { /* a broken address opens the first group */ }
  return groups.find((c) => `cat-${c.key}` === id)?.key
}

function GroupsPanel({ groups }: { groups: Category[] }) {
  const [active, setActive] = useState(() => hashGroup(groups) || groups[0].key)
  // An old link or the back button to #cat-<key> opens that group
  useEffect(() => {
    const onHash = () => { const k = hashGroup(groups); if (k) setActive(k) }
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [groups])
  const pick = (key: string) => { setActive(key); history.replaceState(null, "", `#cat-${key}`) }
  const current = groups.find((c) => c.key === active) || groups[0]
  return (
    <Panel id="groups" className="scroll-mt-4" title="Every program, by group" aside={`${groups.reduce((n, c) => n + c.programs.length, 0)} programs`}>
      <div role="tablist" aria-label="Money categories" className={cn(SEG_TRAY, "self-start")}>
        {groups.map((c) => (
          <button key={c.key} type="button" role="tab" aria-selected={c.key === current.key} onClick={() => pick(c.key)}
            className={cn(SEG, "px-3", c.key === current.key && SEG_ON)}>
            {c.title}<span className="text-sm font-normal text-muted-foreground tabular-nums">{c.programs.length}</span>
          </button>
        ))}
      </div>
      <GroupTable key={current.key} c={current} />
    </Panel>
  )
}

// ---------- The page ----------
export function MoneyMapPage() {
  const state = useLoad(loadMoney)
  const { toast } = useFeedback()
  const [busy, setBusy] = useState<string | null>(null)
  useHashScroll(!!state.data)

  async function setMove(m: Move, s: MoveState) {
    setBusy(m.id)
    try {
      await api("/api/money-move", { id: m.id, state: s })
      await state.reload()
    } catch (e) { toast(e instanceof Error ? e.message : "Unable to complete this action.", true) } finally { setBusy(null) }
  }

  return (
    <Shell active="Funding" tab="/money" title="Money map">
      <LoadGate state={state}>
        {(m) => {
          const used = m.categories.filter((c) => c.programs.length)
          const rank = m.apply_first && m.apply_first.rows.length ? m.apply_first : null
          const top = rank?.rows[0]
          return (
            <>
              <PageHead title="Money map"
                line={top
                  ? <>Start with <span className="font-semibold text-foreground">{cleanName(top.name)}</span>: <span className="font-semibold text-money">{usd(top.per_hour)}</span> per hour of your time, modeled.</>
                  : "Every route to money: what to sell, what to apply to, and where each pitch stands."}>
                {top && <Button size="lg" asChild><a href={`/opportunity/${top.opportunity_id}`}>Open the top program</a></Button>}
              </PageHead>
              <div className={cn("grid items-start gap-5", rank && "lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]")}>
                {rank && <ApplyFirstPanel data={rank} />}
                <MovesPanel moves={m.moves} busy={busy} onSet={setMove} />
              </div>
              {used.length > 0 && <GroupsPanel groups={used} />}
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/money": () => <MoneyMapPage /> } }
