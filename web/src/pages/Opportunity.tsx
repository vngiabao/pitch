import { useState, type FormEvent, type ReactNode } from "react"
import { ArrowRight, ChevronRight, ExternalLink } from "lucide-react"

import { useFeedback } from "@/components/app/feedback"
import { Disclosure, Empty, Field, LoadGate, PageHead, Panel, Row, Rows, Tag, useLoad, evenBottoms } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Progress } from "@/components/ui/progress"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { day, hoursWords, money, plural, prettyKey, stamp } from "@/lib/format"
import {
  appUrl, creditConditions, cycleLabel, daysLeft, hostOf, isApplied, isSoon, loadProgram, outcomeTone, plainName, statusOf, winGroups, winRules,
  type Opp, type ProgramPage, type Win,
} from "@/lib/funding"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"

/* eslint-disable @typescript-eslint/no-explicit-any */

const linkClass = "rounded-md font-medium text-foreground underline underline-offset-4 hover:text-primary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"
const outside = { target: "_blank", rel: "noopener noreferrer" }
const Source = ({ href, children = "Source" }: { href: string; children?: ReactNode }) => (
  <a href={href} {...outside} className={cn(linkClass, "inline-flex min-h-11 items-center gap-1 text-sm")}>{children}<ExternalLink className="size-4" aria-hidden="true" /></a>
)

// Reading text is capped near 70 characters a line (56ch of this face's wide zero).
const Bullets = ({ items }: { items: ReactNode[] }) => (
  <ul className="flex max-w-[56ch] list-disc flex-col gap-1.5 pl-5 text-base">{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
)
const Sub = ({ children }: { children: ReactNode }) => <h4 className="text-base font-semibold">{children}</h4>
const Small = ({ children }: { children: ReactNode }) => <p className="max-w-[56ch] text-sm text-muted-foreground">{children}</p>

// A lead fact: the label, the fact, and one quiet line under it.
function LeadFact({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "money" | "deadline" }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn("text-xl font-semibold tabular-nums", tone === "money" && "text-money", tone === "deadline" && "text-deadline")}>{value}</span>
      {sub && <span className="line-clamp-3 text-sm text-muted-foreground">{sub}</span>}
    </div>
  )
}

function Facts({ d, page }: { d: Opp; page: ProgramPage }) {
  const f = d.data.funding, dl = d.data.dates.deadline, days = daysLeft(d), rolling = d.data.cycle_kind === "rolling" || d.data.cycle === "rolling"
  const status = statusOf(d, page.app)
  return (
    <Panel>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-base">
        <Tag tone={status.tone}>{status.tag}</Tag>
        {status.line && <span className="max-w-[56ch] text-muted-foreground">{status.line}</span>}
      </p>
      <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
        <LeadFact label="Value" tone={f.cash_prize_max != null || f.credits_value != null ? "money" : undefined}
          value={f.cash_prize_max != null ? money(f.cash_prize_max) : f.credits_value != null ? `Up to ${money(f.credits_value)}` : "Value unknown"}
          sub={f.credits_value != null ? "Credits, not cash" : f.award_scope || "Funding terms need verification"} />
        <LeadFact label="Deadline" tone={isSoon(days) ? "deadline" : undefined}
          value={dl ? day(dl) : rolling ? "Rolling" : "No deadline"}
          sub={days !== null ? `${plural(days, "day")} left` : dl ? "Closing time unverified" : "Apply any time"} />
        <LeadFact label="Terms" value={f.equity_required === false ? "No equity taken" : f.equity_required === true ? "Equity or investment" : "Terms unknown"} sub={f.investment_terms || ""} />
        <LeadFact label="A Story fit" value={d.fit_score == null ? "Not rated yet" : `${d.fit_score} of 100`} sub={d.fit_score == null ? "Needs confirmed eligibility" : ""} />
      </div>
    </Panel>
  )
}

// A choice Bao makes about this program: the whole row is the control (no button repeating its name).
function CallRow({ title, line, href, busy, onClick }: { title: string; line: string; href?: string; busy?: boolean; onClick?: () => void }) {
  // The words start on the panel title's left edge; the hover ground reaches 8px past it on both sides.
  const cls = "-mx-2 flex min-h-16 items-center gap-4 rounded-lg px-2 py-2 text-left hover:bg-secondary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid disabled:opacity-60"
  const body = (
    <>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-base font-semibold">{title}</span>
        <span className="text-base text-muted-foreground">{busy ? "Saving…" : line}</span>
      </span>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    </>
  )
  return (
    <div className="flex flex-col border-t first:border-t-0">
      {href ? <a href={href} className={cls}>{body}</a> : <button type="button" className={cls} disabled={busy} onClick={onClick}>{body}</button>}
    </div>
  )
}

// How to win this program, from the research agent. The pitch review and the answer drafts use it.
function WinPanel({ win, busy, onResearch, onSeen }: { win: Win; busy: string; onResearch: () => void; onSeen: () => void }) {
  const b = win.brief
  const research = (label: string) => (
    <Button size="lg" variant="outline" disabled={win.researching || busy === "win"} onClick={onResearch}>
      {win.researching ? "Researching…" : busy === "win" ? "Starting…" : label}
    </Button>
  )
  if (!b) {
    return (
      <Panel title="How we win here">
        <p className="max-w-[56ch] text-base text-muted-foreground">The research agent reads the rules, the judges, past winners and this cycle’s other companies, then says what wins here. Your pitch and your answers for this program then use it.</p>
        <div>{research("Research how to win")}</div>
        {win.researching && <Small>Results land here in about 15 minutes.</Small>}
      </Panel>
    )
  }
  const groups = winGroups(b), rules = winRules(b)
  const list = (k: string): any[] => b[k] || []
  return (
    <Panel title="How we win here" aside={`Checked ${stamp(win.checked_at) || "not yet"}${win.runs > 1 ? ` · ${win.runs} checks` : ""}`}>
      {win.changes.length > 0 && !win.seen && (
        <div className="flex flex-col gap-2 rounded-lg bg-secondary p-4">
          <Sub>Changed since last time</Sub>
          <Bullets items={win.changes} />
          <div><Button size="lg" variant="outline" disabled={busy === "seen"} onClick={onSeen}>{busy === "seen" ? "Saving…" : "Got it"}</Button></div>
        </div>
      )}
      {groups.length
        ? groups.map(([name, moves]) => (
          <div key={name} className="flex flex-col gap-1">
            <Sub>{name}</Sub>
            <Rows label={name}>{moves.map((m, i) => <Row key={i} title={m.move} line={m.why} />)}</Rows>
          </div>
        ))
        : <Empty>No specific moves found. The program publishes little.</Empty>}
      {list("unstated").length > 0 && (
        <div className="flex flex-col gap-2">
          <Sub>What nobody writes down</Sub>
          <Bullets items={list("unstated").map((u) => <>{u.insight}{u.evidence && <span className="text-sm text-muted-foreground"> ({u.evidence})</span>}</>)} />
        </div>
      )}
      {list("criteria").length > 0 && (
        <div className="flex flex-col gap-1">
          <Sub>What judges score</Sub>
          <Rows label="What judges score">
            {list("criteria").map((c, i) => <Row key={i} title={c.name} line={c.evidence} meta={c.weight && !/not published/i.test(c.weight) ? c.weight : undefined} />)}
          </Rows>
        </div>
      )}
      {rules.length > 0 && (
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          {rules.map(([k, v]) => <div key={k} className="flex flex-col gap-0.5"><dt className="text-sm text-muted-foreground">{k}</dt><dd className="text-base">{v}</dd></div>)}
        </dl>
      )}
      <div className="flex flex-col">
        {list("judges").length > 0 && (
          <Disclosure label={`Judges (${list("judges").length})`}>
            <Rows label="Judges">{list("judges").map((j, i) => (
              <Row key={i} title={<>{j.name}{j.role && <span className="font-normal text-muted-foreground">, {j.role}</span>}</>} line={j.cares_about}>{j.source_url && <Source href={j.source_url} />}</Row>
            ))}</Rows>
          </Disclosure>
        )}
        {list("competitors").length > 0 && (
          <Disclosure label={`Other companies this cycle (${list("competitors").length})`}>
            <Rows label="Other companies this cycle">{list("competitors").map((c, i) => (
              <Row key={i} title={<>{c.name}{c.stage && <span className="font-normal text-muted-foreground"> · {c.stage}</span>}</>} line={`${c.what_they_do || ""}${c.strength ? ` Strength: ${c.strength}` : ""}`}>{c.source_url && <Source href={c.source_url} />}</Row>
            ))}</Rows>
          </Disclosure>
        )}
        {list("past_winners").length > 0 && (
          <Disclosure label={`Past winners (${list("past_winners").length})`}>
            <Rows label="Past winners">{list("past_winners").map((x, i) => (
              <Row key={i} title={`${x.year || ""} ${x.company || ""}`.trim()} line={`${x.what_they_did || ""} ${x.why_it_won || ""}`.trim()}>{x.source_url && <Source href={x.source_url} />}</Row>
            ))}</Rows>
          </Disclosure>
        )}
        {(list("risks").length > 0 || list("open_questions").length > 0) && (
          <Disclosure label="Risks and open questions">
            {list("risks").length > 0 && <Bullets items={list("risks")} />}
            {list("open_questions").length > 0 && <><Small>Only you can answer:</Small><Bullets items={list("open_questions")} /></>}
          </Disclosure>
        )}
      </div>
      <div>{research("Research again")}</div>
      {list("sources").length > 0 && (
        <p className="flex flex-wrap gap-x-4">
          {list("sources").slice(0, 6).map((u: string) => <Source key={u} href={u}>{u.replace(/^https?:\/\//, "").slice(0, 48)}</Source>)}
        </p>
      )}
    </Panel>
  )
}

function MaterialList({ label, items }: { label: string; items: any[] }) {
  return (
    <div className="flex flex-col gap-1">
      <Sub>{label}</Sub>
      {items.length
        ? <Bullets items={items.map((m) => <>{m.label}{m.reason && <span className="block text-sm text-muted-foreground">{m.reason}</span>}</>)} />
        : <Small>None confirmed.</Small>}
    </div>
  )
}

function Page({ id, page, reload }: { id: string; page: ProgramPage; reload: () => Promise<unknown> }) {
  const { toast, confirm, ask } = useFeedback()
  const [busy, setBusy] = useState("")
  const [choice, setChoice] = useState("APPLY")
  const [reason, setReason] = useState("")
  const { d, app, win } = page, a = d.analysis, m = a.materials
  const applied = isApplied(d), answers = appUrl(app), url = d.data.application_url || d.data.official_url
  const credits = creditConditions(d)

  // Every action: say it is running, do it, and show the server's own words when it fails.
  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key)
    try { await fn() } catch (e) { toast(e instanceof Error ? e.message : "Unable to complete this action.", true) } finally { setBusy("") }
  }

  const readForm = () => run("read", async () => {
    const res = await api("/api/read-form", { opportunity_id: id })
    if (res.state === "QUESTIONS_READ" && res.application_id) { location.href = `/application/${res.application_id}`; return }
    await reload()
    toast(res.state === "QUESTIONS_READ"
      ? `Read ${res.questions} questions and filled ${res.filled} from your facts.${res.draft_queued ? " The agent is drafting the rest." : ""}`
      : `The agent could not read this form: ${res.reason || res.state}`, res.state !== "QUESTIONS_READ")
  })
  const markSubmitted = async () => {
    if (!(await confirm({ title: "Record that you submitted this application?", body: "The agents will stop recommending it, and it moves to Waiting on results.", action: "Mark as submitted" }))) return
    await run("applied", async () => {
      await api("/api/outcome", { opportunity_id: id, outcome: "Applied", application_id: null, note: "Owner marked submitted in Founder OS." })
      await reload()
      toast("Marked submitted. It now appears under Waiting on results.")
    })
  }
  const quickDecision = async (decision: "WATCH" | "SKIP") => {
    const word = decision.toLowerCase()
    const why = await ask({ title: decision === "WATCH" ? "Watch this program?" : "Skip this program?", label: `Reason for your ${word} decision`, action: decision === "WATCH" ? "Watch it" : "Skip it", required: true })
    if (!why) return
    await run(word, async () => {
      await api("/api/decision", { opportunity_id: id, decision, reason: why })
      await reload()
      toast("Decision saved with the agent recommendation.")
    })
  }
  const recheck = () => run("research", async () => {
    await api("/api/research", { opportunity_id: id })
    toast("Re-verification request saved for this opportunity.")
  })
  const saveDecision = (e: FormEvent) => {
    e.preventDefault()
    if (!reason.trim()) return
    void run("decision", async () => {
      await api("/api/decision", { opportunity_id: id, decision: choice, reason })
      await reload()
      setReason("")
      toast("Decision saved. Scoring weights remain unchanged.")
    })
  }
  const winResearch = () => run("win", async () => {
    await api("/api/win-research", { opportunity_id: id })
    await reload()
    toast("Research started. The brief lands on this page in about 15 minutes.")
  })
  const winSeen = () => run("seen", async () => { await api("/api/win-seen", { opportunity_id: id }); await reload() })

  return (
    <>
      <PageHead title={plainName(d.data.canonical_name)} line={[cycleLabel(d.data.cycle), d.data.organizer].filter(Boolean).join(" · ") || "Program"}>
        {!applied && (answers
          ? <Button size="lg" asChild><a href={answers}>Open answers · {app!.answered} of {app!.questions} ready<ArrowRight aria-hidden="true" /></a></Button>
          : <Button size="lg" disabled={busy === "read"} onClick={readForm}>{busy === "read" ? "Reading the form…" : "Read the form and prepare answers"}</Button>)}
        {url && <Button size="lg" variant="outline" asChild><a href={url} {...outside}>{d.data.application_url ? "Official form" : "Official program"}<ExternalLink aria-hidden="true" /></a></Button>}
        {!applied && <Button size="lg" variant="outline" disabled={busy === "applied"} onClick={markSubmitted}>{busy === "applied" ? "Saving…" : "Mark as submitted"}</Button>}
      </PageHead>

      <Facts d={d} page={page} />

      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          {win && <WinPanel win={win} busy={busy} onResearch={winResearch} onSeen={winSeen} />}

          <Panel title="Why it may fit A Story">
            {a.why_fit.length ? <Bullets items={a.why_fit} /> : <p className="max-w-[56ch] text-base text-muted-foreground">Fit requires verified program focus and approved company facts.</p>}
            {a.why_not_fit.length > 0 && <div className="flex flex-col gap-2"><Sub>Why it may not fit</Sub><Bullets items={a.why_not_fit} /></div>}
            {a.risks.length > 0 && <div className="flex flex-col gap-2"><Sub>Risks</Sub><Bullets items={a.risks} /></div>}
          </Panel>

          <Panel title="Eligibility">
            {a.eligibility.checks.length
              ? (
                <Rows label="Eligibility checks">
                  {a.eligibility.checks.map((c: any, i: number) => (
                    <li key={i} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t py-3 first:border-t-0">
                      <Tag tone={c.result === "PASS" ? "good" : c.result === "FAIL" ? "urgent" : "quiet"}>{c.result === "PASS" ? "Meets" : c.result === "FAIL" ? "Fails" : "Unknown"}</Tag>
                      <span className="min-w-0 flex-1 basis-64 text-base">{c.requirement}</span>
                      {c.source_url && <Source href={c.source_url} />}
                    </li>
                  ))}
                </Rows>
              )
              : <Empty>No published requirements recorded.</Empty>}
            {a.eligibility.missing.length > 0 && <div className="flex flex-col gap-2"><Sub>Still to verify</Sub><Bullets items={a.eligibility.missing} /></div>}
          </Panel>
        </div>

        <div className="flex min-w-0 flex-col gap-5">
          <Panel title="Application readiness" aside={m.estimated_hours == null ? "Time estimate pending" : `${hoursWords(Number(m.estimated_hours))} of your time`}>
            <div className="flex flex-col gap-2">
              <span className="text-base font-semibold">{m.percentage == null ? "Requirements still unknown" : `${m.percentage}% ready`}</span>
              {m.percentage != null && <Progress value={m.percentage} className="h-1.5" aria-label="Application material readiness" />}
            </div>
            <MaterialList label="Ready" items={m.ready} />
            <MaterialList label="Needs adaptation" items={m.needs_adaptation} />
            <MaterialList label="Missing" items={m.missing} />
          </Panel>

          <Panel title="Your call">
            <div className="flex flex-col">
              <CallRow title="Watch" line="Keep it on the list for later. You give a reason." busy={busy === "watch"} onClick={() => quickDecision("WATCH")} />
              <CallRow title="Skip" line="Stop recommending it. You give a reason." busy={busy === "skip"} onClick={() => quickDecision("SKIP")} />
              <CallRow title="Check the program again" line="The research agent re-reads the official page." busy={busy === "research"} onClick={recheck} />
              <CallRow title="Tailor the pitch" line="Open this program in Pitch Lab." href={`/pitch-lab?program=${encodeURIComponent(id)}`} />
            </div>
            <div className="flex flex-col">
              <Disclosure label="Record a decision with a reason">
                <form id="decision-form" onSubmit={saveDecision} className="flex flex-col gap-4">
                  <Field label="Decision" htmlFor="choice">
                    <NativeSelect id="choice" name="decision" value={choice} onChange={(e) => setChoice(e.target.value)}>
                      <NativeSelectOption value="APPLY">Apply</NativeSelectOption>
                      <NativeSelectOption value="PREPARE">Prepare</NativeSelectOption>
                      <NativeSelectOption value="WATCH">Watch</NativeSelectOption>
                      <NativeSelectOption value="SKIP">Skip</NativeSelectOption>
                    </NativeSelect>
                  </Field>
                  <Field label="Reason" htmlFor="reason">
                    <Textarea id="reason" name="reason" required value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What makes this worth the time, or not?" />
                  </Field>
                  <div><Button type="submit" size="lg" variant="outline" disabled={busy === "decision" || !reason.trim()}>{busy === "decision" ? "Saving…" : "Save decision"}</Button></div>
                </form>
                {d.decisions.map((c: any, i: number) => <Small key={i}>{prettyKey(c.decision)} · {c.reason}</Small>)}
              </Disclosure>
            </div>
          </Panel>

          <Panel title="More about this program">
            <div className="flex flex-col">
              {credits && (
                <Disclosure label="Credits and conditions">
                  <Small>{credits.status}</Small>
                  {credits.known.length > 0 && (
                    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                      {credits.known.map(([l, v]) => <div key={l} className="flex flex-col gap-0.5"><dt className="text-sm text-muted-foreground">{l}</dt><dd className="text-base">{v}</dd></div>)}
                    </dl>
                  )}
                  {credits.unknown > 0 && <Small>{plural(credits.unknown, "condition")} not published yet.</Small>}
                  <Small>{credits.note}</Small>
                </Disclosure>
              )}
              <Disclosure label="How the fit score works">
                <ul className="flex flex-col">
                  {Object.entries(a.scoring.components as Record<string, any>).map(([key, c]) => (
                    <li key={key} className="flex items-start gap-4 border-t py-2.5 first:border-t-0">
                      <span className="flex min-w-0 flex-1 flex-col"><span className="text-base font-medium">{prettyKey(key)}</span><span className="text-sm text-muted-foreground">{c.reason}</span></span>
                      <span className="shrink-0 text-base font-semibold tabular-nums">{c.points == null ? "?" : c.points} of {c.weight}</span>
                    </li>
                  ))}
                </ul>
                <Small>{a.scoring.coverage}% of the evidence is in. Unknown points stay unknown.</Small>
              </Disclosure>
              <Disclosure label="Sources and verification">
                <Small>Last verified {stamp(d.last_verified) || "not yet"}</Small>
                {d.source_provenance.length
                  ? d.source_provenance.map((s: any, i: number) => (
                    <div key={i} className="flex flex-col border-t pt-2">
                      <span className="flex flex-wrap items-center gap-x-2"><Source href={s.url}>{hostOf(s.url)}</Source><span className="text-sm text-muted-foreground">{String(s.role || "").replace(/_/g, " ")}</span></span>
                      <p className="max-w-[56ch] text-base">{s.excerpt}</p>
                      <span className="text-sm text-muted-foreground">Checked {stamp(s.checked_at) || "not yet"}</span>
                    </div>
                  ))
                  : <Small>Historical record. Current official verification is pending.</Small>}
                {d.data.notes && <Small>{d.data.notes}</Small>}
              </Disclosure>
              <Disclosure label="Program history">
                {d.history.length
                  ? d.history.map((h: any, i: number) => (
                    <div key={i} className="flex flex-col gap-0.5">
                      <span className="text-base font-semibold">{prettyKey(h.kind)}</span>
                      <p className="max-w-[56ch] text-base">{h.note}</p>
                    </div>
                  ))
                  : <Small>No earlier history for this program.</Small>}
                {d.outcomes.map((o: any, i: number) => (
                  <p key={i} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-base">
                    <Tag tone={outcomeTone(o.outcome)}>{o.outcome}</Tag>
                    <span className="max-w-[56ch]">{o.evidence_note}</span>
                  </p>
                ))}
              </Disclosure>
              {d.history.some((h: any) => h.original_path) && (
                <Disclosure label="Show where the history files are">
                  {d.history.filter((h: any) => h.original_path).map((h: any, i: number) => <span key={i} className="text-sm break-all text-muted-foreground">{h.original_path}</span>)}
                </Disclosure>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </>
  )
}

export function OpportunityPage({ id }: { id: string }) {
  const state = useLoad(() => loadProgram(id), [id])
  return (
    <Shell active="Funding" tab="/opportunities" crumb={plainName(state.data?.d.data.canonical_name || "Program")} title={plainName(state.data?.d.data.canonical_name || "Program")}>
      <LoadGate state={state}>{(page) => <Page id={id} page={page} reload={state.reload} />}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/opportunity/": (id) => <OpportunityPage id={id} /> } }
