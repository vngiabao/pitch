import { useState } from "react"
import { ArrowRight, ExternalLink } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Disclosure, Empty, LoadGate, PageHead, Panel, Row, Rows, Tag, useHashScroll, useLoad, evenBottoms } from "@/components/app/page"
import { useFeedback } from "@/components/app/feedback"
import { api, apiOnce } from "@/lib/api"
import {
  ACCESS_GROUPS, COMPANY_EMAIL, REPORT_EMAIL, accessShort, external, humanState, outcomeTone, plain, readForm,
  scheduleTime, stateTone, tellApart, useLimit,
  type AppListItem, type Autonomy, type Confirmation, type Report,
} from "@/lib/applications"
import { closingWords, shortDay } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { ProgramMark, Shell } from "@/shell"

type Tab = "work" | "reports" | "settings"
// "Closes in 3 days · Nov 15" for every program whose deadline is within 14 days, by opportunity id
/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
function soonClosing(opps?: any[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const d of opps || []) {
    const days = d?.analysis?.scoring?.dates?.days_remaining, deadline = d?.data?.dates?.deadline
    if (deadline && typeof days === "number" && days >= 0 && days <= 14) out[d.opportunity_id] = closingWords(days, deadline)
  }
  return out
}

type Data = { list: AppListItem[]; auto: Autonomy; noFacts: boolean; apart: Record<string, string>; closing: Record<string, string> }
type Act = (key: string, fn: () => Promise<void>) => Promise<void>

const TABS: [Tab, string][] = [["work", "To do"], ["reports", "Daily email"], ["settings", "Agent settings"]]
const currentTab = (): Tab => {
  const t = new URLSearchParams(location.search).get("tab")
  return t === "reports" || t === "settings" ? t : "work"
}
const answersUrl = (x: AppListItem) => (x.questions ? "/application/" + x.application_id : null)
const errorText = (e: unknown) => (e instanceof Error ? e.message : "Unable to complete this action.")

function TabRow({ tab }: { tab: Tab }) {
  return (
    <nav aria-label="Application workspace" className="flex w-fit max-w-full flex-wrap gap-1 rounded-lg bg-secondary p-1">
      {TABS.map(([key, title]) => (
        <a key={key} href={"/applications?tab=" + key} aria-current={tab === key ? "page" : undefined}
          className={cn("flex h-11 items-center rounded-md px-4 text-base font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid",
            tab === key && "bg-card font-semibold text-foreground ring-1 ring-foreground/10")}>
          {title}
        </a>
      ))}
    </nav>
  )
}

// The old notice(): shown only when no company fact has been approved yet.
function FactsNotice({ show }: { show: boolean }) {
  if (!show) return null
  return (
    <Alert>
      <AlertTitle className="text-base font-semibold">Company eligibility needs confirmation</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3 text-base">
        No company facts have been approved yet. The agent can verify programs, but whether A Story fits stays open.
        <Button size="lg" variant="outline" asChild><a href="/memory">Review company facts</a></Button>
      </AlertDescription>
    </Alert>
  )
}

function ShowAll({ hidden, total, onClick }: { hidden: number; total: number; onClick: () => void }) {
  if (!hidden) return null
  return <Button size="lg" variant="outline" className="self-start" onClick={onClick}>Show all {total}</Button>
}

// ---- To do ---------------------------------------------------------------------------------------------------

function PreviewPanel({ c, busy, act, primary }: { c: Confirmation; busy: string | null; act: Act; primary: boolean }) {
  const { toast, confirm } = useFeedback()
  let p: { email?: string; application_url?: string; fields?: Record<string, unknown> } = {}
  try { p = JSON.parse(c.payload_json) || {} } catch { /* shown as an empty preview */ }
  const fields = Object.entries(p.fields || {})
  const sent = c.email_state === "SENT"
  const decide = (decision: "APPROVED" | "REJECTED") => act(c.id + decision, async () => {
    const ok = decision === "APPROVED"
      ? await confirm({
        title: "Submit this exact emailed application preview?",
        body: "Founder OS submits these fields to the program for you, exactly as shown here and in the preview email. A submitted application can’t be taken back.",
        action: "Submit application",
      })
      : await confirm({
        title: "Decline this exact application preview?",
        body: "This preview will not be submitted.",
        action: "Decline application",
      })
    if (!ok) return
    await api("/api/application-confirm", { confirmation_id: c.id, decision, confirmed: true })
    toast("Your exact application decision is saved.")
  })
  return (
    <Panel id={c.id} className="scroll-mt-4" title="Filled application preview"
      aside={<Tag tone={outcomeTone(c.decision)}>{c.decision === "PENDING" ? "Waiting for you" : c.decision}</Tag>}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-base">
        <span className="font-semibold">{p.email}</span>
        <Tag tone={sent ? "good" : "quiet"}>Preview email {String(c.email_state || "").replace(/_/g, " ").toLowerCase()}</Tag>
      </div>
      {p.application_url && (
        <Button size="lg" variant="outline" className="self-start" asChild>
          <a href={p.application_url} {...external}>Official application<ExternalLink aria-hidden="true" /></a>
        </Button>
      )}
      {fields.length > 0 && (
        <dl className="grid gap-x-6 sm:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
          {fields.map(([k, v]) => (
            <div key={k} className="col-span-full grid grid-cols-subgrid gap-y-0.5 border-t py-3">
              <dt className="text-sm text-muted-foreground">{k}</dt>
              <dd className="max-w-[70ch] text-base whitespace-pre-wrap">{typeof v === "string" ? v : JSON.stringify(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="max-w-[70ch] text-sm text-muted-foreground">
        No files, payments or terms acceptance. Changes to these fields or current company facts require a new preview.
      </p>
      {c.decision === "PENDING" && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-3">
            <Button size="lg" variant={primary ? "default" : "outline"} disabled={!sent || !!busy} onClick={() => decide("APPROVED")}>
              {busy === c.id + "APPROVED" ? "Saving…" : "Confirm these fields and submit"}
            </Button>
            <Button size="lg" variant="outline" disabled={!sent || !!busy} onClick={() => decide("REJECTED")}>
              {busy === c.id + "REJECTED" ? "Saving…" : "Decline this application"}
            </Button>
          </div>
          {!sent && <p className="text-sm text-muted-foreground">Both buttons unlock once the preview email has been sent to you.</p>}
        </div>
      )}
    </Panel>
  )
}

// One application: its name and where it stands across the full width, and one action. A short row keeps its
// action at the right; a blocked row (a reason that wraps) puts it underneath on the same left edge.
function AppRow({ x, apart, closing, busy, act }: { x: AppListItem; apart?: string; closing?: string; busy: string | null; act: Act }) {
  const { toast } = useFeedback()
  const level = x.access.level, open = answersUrl(x), left = x.questions - x.answered
  const blocked = level === "BLOCKED"
  const reading = busy === "read" + x.application_id
  const read = () => act("read" + x.application_id, async () => {
    const r = await readForm(x.opportunity_id)
    if (r) toast(r.message, r.error)
  })
  const readButton = (label: string) => (
    <Button size="lg" variant="outline" disabled={!!busy} onClick={read}>{reading ? "Reading the form…" : label}</Button>
  )
  const ready = x.questions ? `${x.answered} of ${x.questions} ready${left > 0 ? ` · ${left} need${left === 1 ? "s" : ""} you` : ""}` : ""
  const action = blocked
    ? x.url
      ? (
        <Button size="lg" variant="outline" asChild>
          <a href={x.url} {...external}>{/no form link/i.test(x.access.label) ? "Open the program page" : "Open the official form"}<ExternalLink aria-hidden="true" /></a>
        </Button>
      )
      : readButton("Try reading it again")
    : level === "NOT_CHECKED" ? readButton("Read the form now")
      : open ? <Button size="lg" variant="outline" asChild><a href={open}>Open answers<ArrowRight aria-hidden="true" /></a></Button>
        : readButton("Re-read the form")
  return (
    <li className={cn("flex flex-col items-start gap-x-4 gap-y-3 border-t py-3 first:border-t-0", !blocked && "sm:min-h-16 sm:flex-row sm:items-center")}>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <a href={open || "/opportunity/" + x.opportunity_id}
          className="flex min-h-11 w-fit max-w-full items-center gap-2 rounded-md text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
          <ProgramMark name={x.program} />
          <span className="min-w-0">{plain(x.program)}{apart && <span className="font-normal text-muted-foreground"> · {apart[0].toUpperCase() + apart.slice(1)}</span>}</span>
        </a>
        {blocked && (
          <div className="flex flex-col items-start gap-1">
            <Tag tone="review">{accessShort(x.access)}</Tag>
            {/* "No form link" already says it; the sentence under it repeated the tag */}
            {!/no form link/i.test(x.access.label) && (
              <p className="max-w-[70ch] text-base text-muted-foreground">{plain(x.access.detail.replace(/ Open the official form.*$/, ""))}</p>
            )}
          </div>
        )}
        {/* A deadline within 14 days is the first thing on the meta line, in red (the highlight key) */}
        {(closing || ready) && (
          <span className="text-sm text-muted-foreground tabular-nums">
            {closing && <span className="font-medium text-deadline">{closing}</span>}{closing && ready && " · "}{ready}
          </span>
        )}
      </div>
      {blocked ? (
        <div className="flex flex-col items-start gap-1">
          {action}
          {x.url && (
            <Disclosure label="More">
              <div>{readButton("Try reading it again")}</div>
            </Disclosure>
          )}
        </div>
      ) : <div className="shrink-0">{action}</div>}
    </li>
  )
}

function Group({ title, note, rows, apart, closing, busy, act }: { title: string; note: string; rows: AppListItem[]; apart: Record<string, string>; closing: Record<string, string>; busy: string | null; act: Act }) {
  const { shown, hidden, showAll } = useLimit(rows, 6)
  return (
    <Panel title={title} aside={rows.length}>
      <p className="max-w-[70ch] text-base text-muted-foreground">{note}</p>
      <Rows label={title}>{shown.map((x) => <AppRow key={x.application_id} x={x} apart={apart[x.application_id]} closing={closing[x.opportunity_id]} busy={busy} act={act} />)}</Rows>
      <ShowAll hidden={hidden} total={rows.length} onClick={showAll} />
    </Panel>
  )
}

function Finished({ rows, apart }: { rows: AppListItem[]; apart: Record<string, string> }) {
  const { shown, hidden, showAll } = useLimit(rows, 7)
  return (
    <Panel title="Finished and not pursuing" aside={rows.length}>
      {rows.length ? (
        <Rows label="Finished and not pursuing">
          {shown.map((x) => (
            <Row key={x.application_id} href={"/application/" + x.application_id}
              title={<span className="flex items-center gap-2"><ProgramMark name={x.program} />{plain(x.program)}</span>}
              line={apart[x.application_id] ? apart[x.application_id][0].toUpperCase() + apart[x.application_id].slice(1) : undefined}>
              <Tag tone={outcomeTone(x.outcome)}>{x.outcome || x.access.label}</Tag>
            </Row>
          ))}
        </Rows>
      ) : <Empty>Nothing finished yet.</Empty>}
      <ShowAll hidden={hidden} total={rows.length} onClick={showAll} />
    </Panel>
  )
}

function Work({ data, busy, act }: { data: Data; busy: string | null; act: Act }) {
  const open = data.list.filter((x) => x.access.level !== "FINISHED")
  const finished = data.list.filter((x) => x.access.level === "FINISHED")
  const previews = data.auto.confirmations || []
  const groups = ACCESS_GROUPS.map(([level, title, note]) => ({ title, note, rows: open.filter((x) => x.access.level === level) })).filter((g) => g.rows.length)
  // One primary button on the screen: the submit decision when a preview is waiting, otherwise the first set of answers.
  const waiting = previews.find((c) => c.decision === "PENDING")
  const next = waiting ? null : open.find((x) => x.access.level === "READY" && answersUrl(x))
  return (
    <>
      <PageHead title="Applications" line="Copy the prepared answers into each official form, then mark it submitted.">
        {next && <Button size="lg" asChild><a href={answersUrl(next)!}>Open {plain(next.program)} answers</a></Button>}
      </PageHead>
      <FactsNotice show={data.noFacts} />
      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-5">
          {previews.map((c) => <PreviewPanel key={c.id} c={c} busy={busy} act={act} primary={c.id === waiting?.id} />)}
          {groups.map((g) => <Group key={g.title} {...g} apart={data.apart} closing={data.closing} busy={busy} act={act} />)}
          {!groups.length && (
            <Panel title="Open applications">
              <Empty>No open applications. New programs appear here once the agent finds and reads their forms.</Empty>
            </Panel>
          )}
        </div>
        <Finished rows={finished} apart={data.apart} />
      </div>
    </>
  )
}

// ---- Daily email ---------------------------------------------------------------------------------------------

function ReportRow({ r }: { r: Report }) {
  const { toast } = useFeedback()
  const [body, setBody] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const toggle = async () => {
    if (body !== null) { setBody(null); return }
    setLoading(true)
    try { setBody(String((await api("/api/report/" + encodeURIComponent(r.id))).body ?? "")) }
    catch (e) { toast(errorText(e), true) }
    finally { setLoading(false) }
  }
  return (
    <li className="flex flex-col border-t first:border-t-0">
      <div className="flex min-h-12 flex-wrap items-center gap-x-4 gap-y-1 py-0.5">
        <span className="w-28 shrink-0 text-base font-semibold">{shortDay(r.local_date)}</span>
        <Tag tone={stateTone(r.state)}>{humanState(r.state)}</Tag>
        {r.error && <span className="min-w-0 flex-1 text-sm text-deadline">{r.error}</span>}
        <Button size="lg" variant="outline" className="ml-auto" disabled={loading} onClick={toggle} aria-expanded={body !== null} aria-controls={"report-" + r.id}>
          {loading ? "Opening…" : body !== null ? "Close report" : "Open report"}
        </Button>
      </div>
      <div id={"report-" + r.id}>
        {body !== null && <pre className="mb-3 overflow-x-auto rounded-lg bg-secondary p-4 font-sans text-base whitespace-pre-wrap">{body}</pre>}
      </div>
    </li>
  )
}

function Reports({ data, busy, act }: { data: Data; busy: string | null; act: Act }) {
  const { toast, confirm } = useFeedback()
  const auto = data.auto
  const active = auto.authorizations.filter((a) => !a.revoked_at && a.scope === "daily_email_report")
  const connector = auto.mail_delivery?.mode === "gmail_connector"
  const at = scheduleTime(auto.report_schedule)
  const reports = (auto.reports || []).slice(0, 14)
  const { shown, hidden, showAll } = useLimit(reports, 7)
  const last = reports[0]

  // This opens a setup window on Bao's PC, so it asks first
  const connect = () => act("connect", async () => {
    if (!(await confirm({ title: "Open the Gmail setup on this PC?", body: "A setup window opens on this PC. Enter the Google app password there, never in chat.", action: "Open setup" }))) return
    await api("/api/connect-report-email", {})
    toast("Secure Gmail setup opened on this PC. Enter the Google app password there, never in chat.")
  })
  const reportNow = () => act("report", async () => {
    if (!(await confirm({
      title: "Prepare today’s report now?",
      body: `The report is saved here, and the sender emails it to ${REPORT_EMAIL} when the mail account is connected.`,
      action: "Prepare report",
    }))) return
    await api("/api/report-now", {})
    toast("Today’s report is saved. The sender will use the connected mail account when available.")
  })
  const pause = (id: string) => act("pause" + id, async () => {
    await api("/api/autonomy-pause", { authorization_id: id })
    toast("Automatic action paused.")
  })
  const resume = () => act("resume", async () => {
    if (!(await confirm({
      title: "Resume this previously authorized agent with the same limits?",
      body: `Daily reports go out again at ${at} Eastern to ${REPORT_EMAIL}, under the limits you approved before.`,
      action: "Resume daily reports",
    }))) return
    await api("/api/autonomy-resume", { scope: "daily_email_report", confirmed: true })
    toast("Automatic action resumed with the existing limits.")
  })

  return (
    <>
      <PageHead title="Daily email"
        line={<>
          {active.length ? <>On, every day at {at} Eastern to <strong className="font-semibold text-foreground">{REPORT_EMAIL}</strong>.</> : "Paused. No report is sent until you resume."}
          {last ? ` Last report: ${shortDay(last.local_date)}, ${humanState(last.state).toLowerCase()}.` : ""}
        </>}>
        {!auto.mail_connected && (
          <Button size="lg" disabled={!!busy} onClick={connect}>{busy === "connect" ? "Opening setup…" : "Connect report email"}</Button>
        )}
        <Button size="lg" variant="outline" disabled={!!busy} onClick={reportNow}>{busy === "report" ? "Preparing…" : "Prepare today’s report"}</Button>
        {active.length
          ? active.map((a) => (
            <Button key={a.id} size="lg" variant="outline" disabled={!!busy} onClick={() => pause(a.id)}>{busy === "pause" + a.id ? "Pausing…" : "Pause email reports"}</Button>
          ))
          : <Button size="lg" variant="outline" disabled={!!busy} onClick={resume}>{busy === "resume" ? "Resuming…" : "Resume daily reports"}</Button>}
      </PageHead>
      <FactsNotice show={data.noFacts} />
      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title="Past reports" aside={reports.length || undefined}>
          {reports.length ? (
            <>
              <ul aria-label="Past reports" className="flex flex-col">{shown.map((r) => <ReportRow key={r.id} r={r} />)}</ul>
              {hidden > 0 && <Button size="lg" variant="outline" className="self-start" onClick={showAll}>Show all {reports.length}</Button>}
            </>
          ) : <Empty>No reports yet. The first one arrives at 9 AM.</Empty>}
        </Panel>
        <Panel title="How it is sent"
          aside={<Tag tone={auto.mail_connected ? "good" : "review"}>{auto.mail_connected ? (connector ? "Connected Gmail" : "Mail connection saved") : "Gmail connection needed"}</Tag>}>
          <div className="flex"><Tag tone={active.length ? "review" : "quiet"}>{active.length ? "Daily reports on" : "Daily reports paused"}</Tag></div>
          <p className="max-w-[70ch] text-base text-muted-foreground">
            {connector
              ? "Sent from your connected Gmail. Keep this PC awake and online for the scheduled send."
              : "The mail password stays in Windows Credential Manager. This PC must be awake, online and signed in."}
          </p>
          {connector && auto.mail_delivery?.smtp_fallback?.enabled && (
            <>
              <p className="max-w-[70ch] text-base text-muted-foreground">
                If it has not gone out by {scheduleTime(auto.report_schedule, auto.mail_delivery.smtp_fallback.after_minutes ?? 30)}, the backup sender on this PC sends it once
                {auto.smtp_fallback_connected ? "." : ", after you set it up."}
              </p>
              {!auto.smtp_fallback_connected && (
                <Disclosure label="How to set up the backup sender">
                  <p className="max-w-[70ch] text-base text-muted-foreground">Run Connect-Report-Email.ps1 on this PC and enter the Google app password there.</p>
                </Disclosure>
              )}
            </>
          )}
        </Panel>
      </div>
    </>
  )
}

// ---- Agent settings ------------------------------------------------------------------------------------------

function Settings({ data, busy, act }: { data: Data; busy: string | null; act: Act }) {
  const { toast, confirm } = useFeedback()
  const active = data.auto.authorizations.filter((a) => !a.revoked_at && a.scope === "free_application_pilot")
  const on = active.length > 0
  const pause = (id: string) => act("pause" + id, async () => {
    await api("/api/autonomy-pause", { authorization_id: id })
    toast("Automatic action paused.")
  })
  const resume = () => act("resume", async () => {
    if (!(await confirm({
      title: "Resume this previously authorized agent with the same limits?",
      body: "The agent reads official forms and prepares answers again, under the limits you approved before. It never submits for you.",
      action: "Resume preparation",
    }))) return
    await api("/api/autonomy-resume", { scope: "free_application_pilot", confirmed: true })
    toast("Automatic action resumed with the existing limits.")
  })
  return (
    <>
      <PageHead title="Agent settings" line={on ? "Application Pilot is on. It prepares answers, then waits for you." : "Application Pilot is paused. Nothing is being prepared."}>
        {on
          ? active.map((a) => (
            <Button key={a.id} size="lg" variant="outline" disabled={!!busy} onClick={() => pause(a.id)}>{busy === "pause" + a.id ? "Pausing…" : "Pause application preparation"}</Button>
          ))
          : <Button size="lg" disabled={!!busy} onClick={resume}>{busy === "resume" ? "Resuming…" : "Resume application preparation"}</Button>}
      </PageHead>
      <FactsNotice show={data.noFacts} />
      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title="Application Pilot" aside={<Tag tone={on ? "review" : "quiet"}>{on ? "On: prepares, then waits for you" : "Paused"}</Tag>}>
          <Rows label="What the agent does">
            <Row title="Reads official forms" line="It opens each program’s form and saves the questions." />
            <Row title="Prepares answers from approved facts" line="Answers come from your company facts and founder profile." />
            <Row title="Never submits for you" line="You copy the answers in and submit each form yourself." />
            <Row title="Waits for you when a form is closed to it" line="A login, a CAPTCHA, a file upload, a fee or new terms." />
          </Rows>
        </Panel>
        <Panel title="Email used on forms">
          <Rows label="Email used on forms">
            <Row title={REPORT_EMAIL} line="The default on every form." />
            <Row title={COMPANY_EMAIL} line="For forms that require a company address." />
          </Rows>
        </Panel>
      </div>
    </>
  )
}

export function ApplicationsPage() {
  const tab = currentTab()
  const { toast } = useFeedback()
  // The dashboard gives the company-facts notice and what tells same-named programs apart; the page opens without it.
  const state = useLoad<Data>(async () => {
    const [list, auto, dash] = await Promise.all([
      api<AppListItem[]>("/api/application-list"), api<Autonomy>("/api/autonomy"), apiOnce("/api/dashboard").catch(() => null),
    ])
    return {
      list, auto,
      noFacts: !!dash && (dash.company_memory?.canonical_claims || []).length === 0,
      apart: tellApart(list, dash?.opportunities, dash?.money_board?.tracked),
      closing: soonClosing(dash?.opportunities),
    }
  })
  const [busy, setBusy] = useState<string | null>(null)
  // Run one action at a time, then reload the page's data (the old app's boot()); every error becomes a toast.
  const act: Act = async (key, fn) => {
    if (busy) return
    setBusy(key)
    try { await fn(); await state.reload() } catch (e) { toast(errorText(e), true) } finally { setBusy(null) }
  }
  useHashScroll(!!state.data)
  return (
    <Shell active="Funding" tab="/applications" title="Applications">
      <TabRow tab={tab} />
      <LoadGate state={state}>
        {(data) => tab === "reports" ? <Reports data={data} busy={busy} act={act} />
          : tab === "settings" ? <Settings data={data} busy={busy} act={act} />
            : <Work data={data} busy={busy} act={act} />}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/applications": () => <ApplicationsPage /> } }
