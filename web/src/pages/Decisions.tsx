import { useState, type FormEvent, type ReactNode } from "react"
import { Download } from "lucide-react"

import { Button } from "@/components/ui/button"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Field, LoadGate, PageHead, Panel, Row, Rows, Tag, useLoad, Disclosure as SharedDisclosure, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import {
  KIND_WORDS, OUTCOME_CHOICES, decidedLine, decisionTitle, factValue, noDash, recentDecisions,
  type Approval, type Dashboard, type Inbox, type InboxMail,
} from "@/lib/company"
import { day, plural, prettyKey, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

// A "read more" disclosure: one line to open it, 44px tall, the detail under it. Shared by the Company and Agents pages.
export function Disclosure({ summary, children }: { summary: ReactNode; children: ReactNode }) {
  return <SharedDisclosure label={summary}>{children}</SharedDisclosure>
}

// A long list shows its first few rows and one "Show all N" control.
export function useShowAll<T>(items: T[], limit = 6) {
  const [all, setAll] = useState(false)
  const shown = all ? items : items.slice(0, limit)
  const more = !all && items.length > limit
    ? <Button variant="outline" size="lg" className="self-start" onClick={() => setAll(true)}>Show all {items.length}</Button>
    : null
  return { shown, more }
}

const errorText = (e: unknown) => (e instanceof Error ? e.message : "Unable to complete this action.")

type Acts = {
  busy: string | null
  decide: (a: Approval, decision: "approved" | "rejected") => void
  saveEdit: (a: Approval, body: string) => Promise<boolean>
  confirmMail: (m: InboxMail, outcome?: string) => void
  dismissMail: (m: InboxMail) => void
  connect: (account: string) => void
}

// One fact or reminder waiting for Bao: what it says, why it matters, what approving changes, then the decision.
function FactItem({ a, lead, acts }: { a: Approval; lead: boolean; acts: Acts }) {
  const c = a.card!
  const reminder = c.kind === "REMINDER"
  const [editing, setEditing] = useState(false)
  const [body, setBody] = useState(c.sentence)
  const working = acts.busy === a.id
  const submit = async (e: FormEvent) => { e.preventDefault(); if (body.trim() && await acts.saveEdit(a, body)) setEditing(false) }
  return (
    <li id={`card-${a.id}`} className="flex flex-col gap-3 border-t py-5 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span className="text-sm text-muted-foreground">{prettyKey(c.topic || "company")} · {noDash(c.label)}</span>
        <Tag tone={reminder ? "quiet" : "review"}>{KIND_WORDS[c.kind] || c.kind}</Tag>
      </div>
      <p className="max-w-[70ch] text-base font-semibold">{noDash(c.sentence)}</p>
      {c.why && <p className="max-w-[70ch] text-base text-muted-foreground">{noDash(c.why)}</p>}
      {!!c.unlocks?.length && (
        <p className="max-w-[70ch] text-base"><span className="font-semibold">Approving lets the agents check</span> {c.unlocks.join(", ")}.</p>
      )}
      {!!c.replaces?.length && (
        <div className="flex flex-col gap-1 rounded-lg bg-secondary px-4 py-3 text-base">
          <span className="font-semibold">Changes your current facts</span>
          {c.replaces.map((r) => <span key={r.fact}>{prettyKey(r.fact)}: {factValue(r.current)} → {factValue(r.proposed)}</span>)}
        </div>
      )}
      {c.source && (
        <Disclosure summary="Where this came from">
          <p className="text-sm break-words text-muted-foreground">{c.source}{c.locator && <><br />{c.locator}</>}</p>
        </Disclosure>
      )}
      <div className="flex flex-wrap gap-3">
        {reminder
          ? <Button size="lg" variant="outline" disabled={working} onClick={() => acts.decide(a, "rejected")}>{working ? "Saving…" : "Dismiss"}</Button>
          : (
            <>
              <Button size="lg" variant={lead ? "default" : "outline"} disabled={working} onClick={() => acts.decide(a, "approved")}>{working ? "Saving…" : "Approve"}</Button>
              {c.editable && <Button size="lg" variant="outline" aria-expanded={editing} disabled={working} onClick={() => setEditing((v) => !v)}>Edit</Button>}
              <Button size="lg" variant="outline" disabled={working} onClick={() => acts.decide(a, "rejected")}>Reject</Button>
            </>
          )}
      </div>
      {c.editable && !reminder && editing && (
        <form onSubmit={submit} className="flex flex-col gap-3 rounded-lg bg-secondary p-4">
          <Field label="Write it the way it is true" htmlFor={`edit-${a.id}`}>
            <Textarea id={`edit-${a.id}`} value={body} required autoFocus onChange={(e) => setBody(e.target.value)}
              onFocus={(e) => e.target.setSelectionRange(e.target.value.length, e.target.value.length)} />
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button type="submit" size="lg" variant="outline" disabled={working || !body.trim()}>{working ? "Saving…" : "Save and approve"}</Button>
            <Button type="button" size="lg" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </form>
      )}
    </li>
  )
}

// One email the inbox reader thinks matters: a program result to record, or a reply on a deal.
function MailItem({ m, acts }: { m: InboxMail; acts: Acts }) {
  const [outcome, setOutcome] = useState(OUTCOME_CHOICES.includes(m.proposed_outcome || "") ? m.proposed_outcome! : OUTCOME_CHOICES[0])
  const working = acts.busy === m.id
  const reply = !!m.deal_id
  const moved = reply && m.deal_stage !== "SENT"
  return (
    <li className="flex flex-col gap-2 border-t py-5 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span className="text-base font-semibold">{reply ? m.deal : m.program || "Unmatched email"}</span>
        <Tag tone="review">{reply ? "They replied" : m.state === "PROPOSED" ? m.proposed_outcome : "Review"}</Tag>
      </div>
      <p className="text-sm text-muted-foreground">{m.sender} to {m.account} · <time dateTime={m.received_at}>{stamp(m.received_at)}</time></p>
      <p className="max-w-[70ch] text-base font-medium">{m.subject}</p>
      <p className="max-w-[70ch] text-base text-muted-foreground">{m.snippet}</p>
      {!reply && m.reason && <p className="max-w-[70ch] text-sm text-muted-foreground">{m.reason}</p>}
      {reply && (
        <p className="max-w-[70ch] text-sm text-muted-foreground">
          {moved ? "You already moved this deal past Sent; confirming only logs the email on it." : "Confirming moves this deal to They replied and logs the email on it. Nothing is sent."}
        </p>
      )}
      <div className="flex flex-wrap items-end gap-3 pt-1">
        {reply ? (
          <>
            <Button size="lg" variant="outline" disabled={working} onClick={() => acts.confirmMail(m)}>{working ? "Saving…" : moved ? "Log this email" : "They replied"}</Button>
            <Button size="lg" variant="outline" asChild><a href={`/growth#deal-${m.deal_id}`}>Open the deal</a></Button>
            <Button size="lg" variant="outline" disabled={working} onClick={() => acts.dismissMail(m)}>Not a reply</Button>
          </>
        ) : (
          <>
            {m.opportunity_id ? (
              <>
                <Field label="Record as" htmlFor={`outcome-${m.id}`}>
                  <NativeSelect id={`outcome-${m.id}`} value={outcome} onChange={(e) => setOutcome(e.target.value)} className="w-40">
                    {OUTCOME_CHOICES.map((o) => <NativeSelectOption key={o} value={o}>{o}</NativeSelectOption>)}
                  </NativeSelect>
                </Field>
                <Button size="lg" variant="outline" disabled={working} onClick={() => acts.confirmMail(m, outcome)}>{working ? "Saving…" : "Confirm"}</Button>
              </>
            ) : <Button size="lg" variant="outline" asChild><a href="/opportunities">Find the program</a></Button>}
            <Button size="lg" variant="outline" disabled={working} onClick={() => acts.dismissMail(m)}>Not relevant</Button>
          </>
        )}
      </div>
    </li>
  )
}

function Mailboxes({ inbox, acts }: { inbox: Inbox; acts: Acts }) {
  return (
    <Panel title="Mailboxes" aside="Read every 30 minutes">
      <Rows label="Mailboxes">
        {inbox.accounts.map((a) => (
          <Row key={a.account} title={<span className="break-all">{a.account}</span>}
            line={a.connected
              ? <>{a.last_checked ? <>Checked <time dateTime={a.last_checked}>{stamp(a.last_checked)}</time></> : "Connected · first check within 5 minutes"}{a.last_error ? ` · ${a.last_error}` : ""}</>
              : "Not connected yet"}>
            {a.connected
              ? <Tag>Read-only</Tag>
              : <Button size="lg" variant="outline" disabled={acts.busy === a.account} onClick={() => acts.connect(a.account)}>{acts.busy === a.account ? "Opening…" : "Connect"}</Button>}
          </Row>
        ))}
      </Rows>
      {inbox.pending.length === 0 && inbox.accounts.some((a) => a.connected) && (
        <p className="text-base text-muted-foreground">No new program emails to confirm.</p>
      )}
    </Panel>
  )
}

// What was decided lately: the name, one line of what it says, the day it was decided, and how it went.
// It takes the main column when nothing is waiting, and the side column otherwise.
function Decided({ list, main }: { list: ReturnType<typeof recentDecisions>; main: boolean }) {
  const { shown, more } = useShowAll(list, main ? 8 : 5)
  if (!list.length) return null
  return (
    <Panel title="Recently decided" aside={plural(list.length, "decision")}>
      <Rows label="Recently decided">
        {shown.map((r) => (
          <Row key={r.label} title={decisionTitle(r.label)}
            line={decidedLine(r.sentence) ? <span className={main ? "line-clamp-2 max-w-[70ch]" : "line-clamp-2"}>{decidedLine(r.sentence)}</span> : undefined}
            meta={<>Decided <time dateTime={r.decided_at}>{day(r.decided_at)}</time></>}>
            <Tag tone={r.state === "approved" ? "good" : "quiet"}>{r.state === "approved" ? "Approved" : "Rejected"}</Tag>
          </Row>
        ))}
      </Rows>
      {more}
    </Panel>
  )
}

export function DecisionsPage() {
  const state = useLoad(() => api<Dashboard>("/api/dashboard"))
  const { toast, confirm } = useFeedback()
  const [busy, setBusy] = useState<string | null>(null)

  // The old app's pattern: do it, read the page again, then say what happened.
  const act = async (key: string, run: () => Promise<unknown>, done: string, reload = true) => {
    setBusy(key)
    try { await run(); if (reload) await state.reload(); toast(done); return true }
    catch (e) { toast(errorText(e), true); return false }
    finally { setBusy(null) }
  }

  const acts: Acts = {
    busy,
    decide: async (a, decision) => {
      const c = a.card!
      const reminder = c.kind === "REMINDER"
      const quote = <p className="text-foreground">{noDash(c.sentence)}</p>
      const ok = await confirm(decision === "approved"
        ? {
          title: "Approve this fact?", action: "Approve",
          body: <div className="flex flex-col gap-2">{quote}<p>The agents will treat this as true from now on.{c.replaces?.length ? " It replaces what your current facts say." : ""}</p></div>,
        }
        : reminder
          ? { title: "Dismiss this reminder?", action: "Dismiss", body: <div className="flex flex-col gap-2">{quote}<p>The agents stop keeping this note in mind.</p></div> }
          : { title: "Reject this fact?", action: "Reject", danger: true, body: <div className="flex flex-col gap-2">{quote}<p>It is recorded as rejected. The agents will not treat it as true.</p></div> })
      if (!ok) return
      await act(a.id, () => api("/api/approval", { approval_id: a.id, decision, confirmed: true }), "Your decision is recorded.")
    },
    saveEdit: async (a, body) => {
      const ok = await confirm({
        title: "Save this wording as a confirmed company fact?", action: "Save and approve",
        body: <div className="flex flex-col gap-2"><p className="text-foreground">{body}</p><p>The agents will treat your wording as true from now on.</p></div>,
      })
      if (!ok) return false
      return act(a.id, () => api("/api/approval-edit", { approval_id: a.id, body, confirmed: true }), "Saved your wording as a confirmed fact.")
    },
    confirmMail: async (m, outcome) => {
      if (m.deal_id) {
        const ok = await confirm({ title: `Mark ${m.deal} as replied?`, action: "Log the reply", body: "This email is logged on the deal. Nothing is sent." })
        if (!ok) return
        await act(m.id, () => api("/api/inbox-decision", { id: m.id, decision: "confirm", confirmed: true }), "Logged on the deal. Answer them from your own email.")
        return
      }
      const ok = await confirm({
        title: `Record ${m.program || "this program"} as ${outcome}?`, action: `Record as ${outcome}`,
        body: <div className="flex flex-col gap-2"><p className="text-foreground">{m.subject}</p><p>This email is kept as the evidence for the result.</p></div>,
      })
      if (!ok) return
      await act(m.id, () => api("/api/inbox-decision", { id: m.id, decision: "confirm", outcome, confirmed: true }), "Outcome recorded with the email as evidence.")
    },
    dismissMail: async (m) => {
      const ok = await confirm({
        title: "Set this email aside?", action: "Set it aside",
        body: <div className="flex flex-col gap-2"><p className="text-foreground">{m.subject}</p><p>Nothing is recorded, and the email will not come back to this list.</p></div>,
      })
      if (!ok) return
      await act(m.id, () => api("/api/inbox-decision", { id: m.id, decision: "dismiss", confirmed: true }), "Email set aside. Nothing was recorded.")
    },
    connect: (account) => {
      void act(account, () => api("/api/connect-inbox", { account }), "Secure inbox setup opened on this PC. Enter the Google app password there, never in chat.", false)
    },
  }

  return (
    <Shell active="Company" tab="/decisions" title="Decisions">
      <LoadGate state={state}>
        {(dash) => {
          const cards = dash.needs_decision.filter((a) => a.card)
          const open = cards.filter((a) => a.card!.kind !== "REMINDER")
          const reminders = cards.filter((a) => a.card!.kind === "REMINDER")
          const inbox = dash.inbox || null
          const inboxWaiting = inbox ? inbox.proposed + inbox.review : 0
          const clear = !open.length && !inboxWaiting && !reminders.length
          const decided = recentDecisions(dash.recent_decisions)
          const approved = decided.filter((r) => r.state === "approved").length
          return (
            <>
              <PageHead title="Decisions"
                line={clear
                  ? decided.length
                    ? `Nothing is waiting. ${plural(approved, "fact")} approved lately, the last on ${day(decided[0].decided_at)}.`
                    : "Nothing is waiting."
                  : `${plural(open.length, "fact")} to confirm, ${inboxWaiting} from your inboxes, ${plural(reminders.length, "reminder")}.`}>
                {inbox && <Button size="lg" variant="outline" asChild><a href="/api/tracker/export.csv"><Download aria-hidden="true" />Export tracker (CSV)</a></Button>}
              </PageHead>
              <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="flex flex-col gap-5">
                  {open.length > 0 && (
                    <Panel title="Facts to confirm" aside={plural(open.length, "fact")}>
                      <ul aria-label="Facts to confirm" className="flex flex-col">
                        {open.map((a, i) => <FactItem key={a.id} a={a} lead={i === 0} acts={acts} />)}
                      </ul>
                    </Panel>
                  )}
                  {inbox && inbox.pending.length > 0 && (
                    <Panel title="From your inboxes" aside={`${inbox.pending.length} to confirm`}>
                      <p className="max-w-[70ch] text-base text-muted-foreground">Nothing is recorded until you confirm, and nothing in the mailbox is changed.</p>
                      <ul aria-label="Emails to confirm" className="flex flex-col">{inbox.pending.map((m) => <MailItem key={m.id} m={m} acts={acts} />)}</ul>
                    </Panel>
                  )}
                  {reminders.length > 0 && (
                    <Panel title="Reminders" aside={plural(reminders.length, "reminder")}>
                      <p className="max-w-[70ch] text-base text-muted-foreground">Notes the agents keep in mind. They are not facts, so they can only be dismissed.</p>
                      <ul aria-label="Reminders" className="flex flex-col">
                        {reminders.map((a) => <FactItem key={a.id} a={a} lead={false} acts={acts} />)}
                      </ul>
                    </Panel>
                  )}
                  {clear && <Decided list={decided} main />}
                  {clear && !decided.length && (
                    <Panel title="Nothing to decide yet">
                      <p className="max-w-[70ch] text-base text-muted-foreground">New facts from research, your notes or your inboxes will appear here.</p>
                    </Panel>
                  )}
                </div>
                <div className="flex flex-col gap-5">
                  {inbox && <Mailboxes inbox={inbox} acts={acts} />}
                  {!clear && <Decided list={decided} main={false} />}
                </div>
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/decisions": () => <DecisionsPage /> } }
