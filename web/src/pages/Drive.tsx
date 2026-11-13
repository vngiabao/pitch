import { useRef, useState, type FormEvent, type ReactNode } from "react"
import { Check, Copy, ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { CopyBox, Fact, Field, LoadGate, PageHead, Panel, Tag, useLoad, Disclosure, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { DRIVE_CSV_HELP, draftNote, hasHash, useHashScroll, useRun, type Draft, type DriveData, type DriveImportResult, type DriveMember, type DriveShown } from "@/lib/customers"
import { copyText, day, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

// ---------- Parts the Customers pages share (People, Press and Families import them from here) ----------

// One person, family or outlet inside a panel: a name, one line, then a status and its actions at the right,
// then its content. Items are separated by space and a hairline; `id` keeps the old #anchors working.
export function Item({ id, title, sub, tag, actions, children }: { id?: string; title: string; sub?: ReactNode; tag?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (
    <li id={id} className="flex scroll-mt-4 flex-col gap-3 border-t py-4 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex min-w-0 flex-1 basis-64 flex-col gap-0.5">
          <h4 className="text-base font-semibold">{title}</h4>
          {sub && <p className="text-base break-words text-muted-foreground">{sub}</p>}
        </div>
        {(tag || actions) && <div className="flex flex-wrap items-center gap-2">{tag}{actions}</div>}
      </div>
      {children}
    </li>
  )
}

// A list that shows its first few items, with one control for the rest.
export function Limited<T>({ items, limit = 6, label, children }: { items: T[]; limit?: number; label?: string; children: (item: T, index: number) => ReactNode }) {
  const [all, setAll] = useState(hasHash)
  const shown = all ? items : items.slice(0, limit)
  return (
    <>
      <ul aria-label={label} className="flex flex-col">{shown.map(children)}</ul>
      {!all && items.length > limit && (
        <Button variant="outline" size="lg" className="self-start" onClick={() => setAll(true)}>Show all {items.length}</Button>
      )}
    </>
  )
}

// A form or a longer note behind one labelled control.
export function More({ summary, open, children }: { summary: string; open?: boolean; children: ReactNode }) {
  return <Disclosure label={summary} open={open}>{children}</Disclosure>
}

// A drafted note Bao copies and sends himself. The message fills the wide side; the subject, the checker's
// note and the actions (`children`) sit beside it, so a wide panel has no empty strip.
// `plain` shows the message without its own Copy button, for an item whose header row already has one.
export function DraftBlock({ draft, plain, children }: { draft: Draft; plain?: boolean; children?: ReactNode }) {
  const note = draftNote(draft.note)
  return (
    <div ref={evenBottoms} className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-2">
        <span className="text-sm text-muted-foreground">Message</span>
        {plain
          ? <p className="rounded-lg bg-secondary p-4 text-base whitespace-pre-wrap">{draft.body}</p>
          : <CopyBox text={draft.body} label="Copy message" />}
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-sm text-muted-foreground">Subject</span>
        <CopyBox text={draft.title || "(no subject)"} unit="characters" label="Copy subject" />
        {note && <p className="text-base text-muted-foreground"><span className="font-semibold text-foreground">Check before sending.</span> {note}</p>}
        {children}
      </div>
    </div>
  )
}

// Copies a draft's message from the item's header row.
export function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false)
  return (
    <Button variant="outline" size="lg" onClick={async () => { if (await copyText(text)) { setDone(true); setTimeout(() => setDone(false), 1600) } }}>
      {done ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{done ? "Copied" : label}
    </Button>
  )
}

// "Open email": opens Bao's own mail program. The app sends nothing.
export function MailLink({ email, subject }: { email: string; subject?: string | null }) {
  return (
    <Button size="lg" variant="outline" asChild>
      <a href={`mailto:${email}${subject ? "?subject=" + encodeURIComponent(subject) : ""}`}>Open email<ExternalLink aria-hidden="true" /></a>
    </Button>
  )
}

// The loader for the reservation drive: a CSV file read in the browser, or pasted rows.
function DriveLoader({ onLoaded, primary, note }: { onLoaded: () => Promise<unknown>; primary?: boolean; note?: string }) {
  const { toast } = useFeedback()
  const [busy, setBusy] = useState(false)
  const [csv, setCsv] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)
  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      let text = csv
      const file = fileRef.current?.files?.[0]
      if (file) {
        if (file.size > 60000) throw new Error("That file is larger than 60 KB. Split it into two.")
        text = await file.text()
      }
      const r = await api<DriveImportResult>("/api/drive-import", { csv: text })
      const bits = [
        r.created ? plural(r.created, "new person", "new people") : "",
        r.enrolled ? plural(r.enrolled, "known contact") + " enrolled" : "",
        r.skipped ? plural(r.skipped, "duplicate") + " skipped" : "",
        r.rejected.length ? plural(r.rejected.length, "row") + " rejected (" + r.rejected.slice(0, 3).map((x) => "row " + x.row + ": " + x.reason).join("; ") + ")" : "",
      ].filter(Boolean)
      toast(bits.length ? bits.join(", ") + "." : "Nothing to load.", Boolean(r.rejected.length && !r.created && !r.enrolled))
      if (location.pathname !== "/drive" && (r.created || r.enrolled)) { location.href = "/drive"; return }
      setCsv("")
      if (fileRef.current) fileRef.current.value = ""
      await onLoaded()
    } catch (err) {
      toast(err instanceof Error ? err.message : "Unable to complete this action.", true)
    } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <Field label="Your CSV file" htmlFor="drive-file">
        <Input id="drive-file" ref={fileRef} type="file" name="file" accept=".csv,text/csv" className="py-2" />
      </Field>
      <Field label="Or paste the rows" htmlFor="drive-csv"
        hint={<>{DRIVE_CSV_HELP} Someone already in People with the same email is enrolled, not copied; a repeated email is skipped.</>}>
        <Textarea id="drive-csv" name="csv" rows={5} maxLength={60000} value={csv} onChange={(e) => setCsv(e.target.value)}
          placeholder={"name,email,context,kind\nLinh Pham,linh@example.com,Signed up after the Columbus demo night,Lead\nThe Tran family,tran@example.com,Beta since September; grandma talked about Hue,Beta family"} />
      </Field>
      <Button type="submit" size="lg" variant={primary ? "default" : "outline"} className="self-start" disabled={busy}>{busy ? "Loading…" : "Load these people"}</Button>
      {note && <p className="text-sm text-muted-foreground">{note}</p>}
    </form>
  )
}

// ---------- The reservation drive ----------

const GROUPS: [DriveShown, string, string][] = [
  ["READY", "Ready to send", "Copy the note, send it from your own email, then press “I sent it”."],
  ["SENT", "Sent, waiting", "Record what happens: a reply, a reservation, a referral."],
  ["REPLIED", "They replied", "Answer them from your email; record a reservation or a referral here."],
  ["NEW", "Still being written", "One note is written per cycle, then checked against your facts and your voice."],
  ["RESERVED", "Reserved", "Each one is a $1 reservation, counted as a purchase for the email channel."],
]

type DriveAction = "sent" | "replied" | "reserved" | "referred"
const ASK: Record<Exclude<DriveAction, "referred">, { title: string; body: string; action: string }> = {
  sent: { title: "Log that you sent this note?", body: "This records that you sent it from your own email. Founder OS sends nothing.", action: "Yes, I sent it" },
  replied: { title: "Log that they replied?", body: "The note moves to “They replied”.", action: "Yes, they replied" },
  reserved: { title: "Record that they reserved A Story for $1?", body: "This adds one purchase to the email channel this week.", action: "Record the reservation" },
}
const SAID: Record<DriveAction, string> = {
  sent: "Logged. Record the reply or the reservation when it comes.",
  replied: "Logged. Answer them from your email.",
  reserved: "Reservation recorded. Channel math has it.",
  referred: "Referral recorded under the referrals channel. Add the new family in People when you have their details.",
}

type Acts = { m: DriveMember; busy: string | null; act: (m: DriveMember, a: DriveAction) => void }

function Act({ m, a, busy, act, children, primary }: Acts & { a: DriveAction; children: string; primary?: boolean }) {
  return (
    <Button size="lg" variant={primary ? "default" : "outline"} disabled={!!busy} onClick={() => act(m, a)}>{busy === `${a}:${m.contact_id}` ? "Saving…" : children}</Button>
  )
}

function Redraft({ m, busy, draft, children }: { m: DriveMember; busy: string | null; draft: (m: DriveMember) => void; children: string }) {
  return <Button size="lg" variant="outline" disabled={!!busy} onClick={() => draft(m)}>{busy === `draft:${m.contact_id}` ? "Starting…" : children}</Button>
}

function Member({ m, lead, busy, act, draft }: Acts & { lead: boolean; draft: (m: DriveMember) => void }) {
  const last = m.touches[0]
  const when = m.reserved_on ? " " + day(m.reserved_on) : m.sent_on && m.shown === "SENT" ? " " + day(m.sent_on) : ""
  const acts = { m, busy, act }
  const outcomes = <><Act {...acts} a="reserved">They reserved</Act><Act {...acts} a="referred">They referred someone</Act></>
  return (
    <Item id={`drive-${m.contact_id}`} title={m.name}
      sub={[m.kind_words, m.email, m.referrals ? plural(m.referrals, "referral") : ""].filter(Boolean).join(" · ")}
      tag={<Tag tone={m.shown === "READY" ? "review" : m.shown === "RESERVED" ? "good" : "quiet"}>{m.state_words}{when}</Tag>}
      actions={m.shown === "READY"
        ? <>{m.draft && <CopyButton text={m.draft.body} label="Copy message" />}<Act {...acts} a="sent" primary={lead}>I sent it</Act></>
        : m.shown === "SENT" ? <Act {...acts} a="replied">They replied</Act> : undefined}>
      {m.context && <p className="max-w-[70ch] text-base">{m.context}</p>}
      {last && <p className="max-w-[70ch] text-base text-muted-foreground">Last: {day(last.occurred_on)}, {last.summary}</p>}
      {m.shown === "NEW" && (m.drafting
        ? <p className="text-base"><span className="font-semibold">Drafting.</span> This note is being written now.</p>
        : (
          <>
            <p className="text-base"><span className="font-semibold">Not yet written.</span> One note is written per cycle.</p>
            <div className="flex flex-wrap gap-2"><Redraft m={m} busy={busy} draft={draft}>Draft it now</Redraft></div>
          </>
        ))}
      {m.shown === "READY" && (m.draft
        ? (
          <DraftBlock draft={m.draft} plain>
            <div className="flex flex-wrap gap-2">
              {m.email && <MailLink email={m.email} subject={m.draft.title} />}
              <Redraft m={m} busy={busy} draft={draft}>Write a new draft</Redraft>
            </div>
          </DraftBlock>
        )
        : (
          <div className="flex flex-wrap gap-2">
            {m.email && <MailLink email={m.email} />}
            <Redraft m={m} busy={busy} draft={draft}>Write a new draft</Redraft>
          </div>
        ))}
      {m.shown === "SENT" && (
        <>
          {m.draft && (
            <DraftBlock draft={m.draft}>
              <p className="text-base text-muted-foreground">A reminder is drafted. Send it only if they have not answered.</p>
              <div className="flex flex-wrap gap-2"><Act {...acts} a="sent">I sent the reminder</Act></div>
            </DraftBlock>
          )}
          <div className="flex flex-wrap gap-2">{outcomes}</div>
        </>
      )}
      {m.shown === "REPLIED" && <div className="flex flex-wrap gap-2">{outcomes}</div>}
      {m.shown === "RESERVED" && <div className="flex flex-wrap gap-2"><Act {...acts} a="referred">They referred someone</Act></div>}
    </Item>
  )
}

export function DrivePage() {
  const state = useLoad(() => api<DriveData>("/api/drive"))
  const { busy, run } = useRun(state.reload)
  const { confirm, ask } = useFeedback()
  useHashScroll(!!state.data)

  async function act(m: DriveMember, action: DriveAction) {
    const body: { id: string; action: DriveAction; who?: string } = { id: m.contact_id, action }
    if (action === "referred") {
      const who = await ask({ title: `Who did ${m.name} refer?`, label: "Their name. Leave it empty if you do not know yet.", action: "Record the referral" })
      if (who === null) return
      body.who = who
    } else if (!(await confirm({ ...ASK[action], body: <><strong className="font-semibold text-foreground">{m.name}.</strong> {ASK[action].body}</> }))) return
    await run(`${action}:${m.contact_id}`, async () => { await api("/api/drive-action", body); return SAID[action] })
  }
  const draft = (m: DriveMember) => run(`draft:${m.contact_id}`, async () => {
    await api("/api/growth-draft", { kind: "contact", id: m.contact_id })
    return "The note is being drafted. It appears here in a few minutes."
  })

  return (
    <Shell active="Customers" tab="/drive" title="Reservation drive">
      <LoadGate state={state}>{(b) => {
        const c = b.counts, left = b.days_left, closeDay = day(b.deadline || "2026-11-02"), closed = left < 0
        const when = left > 0 ? `${plural(left, "day")} to ${closeDay}` : left === 0 ? "Closes today" : `Closed ${closeDay}`
        const firstReady = b.members.find((m) => m.shown === "READY")?.contact_id
        const reminders = b.nudge_days.length ? `Today reminds you how many notes are still unsent on ${b.nudge_days.map((d) => day(d)).join(", ")}.` : undefined
        if (!c.total) return (
          <>
            <PageHead title="Reservation drive" line={closed ? `${when}. Nothing was loaded.` : `${when}. No one is loaded yet.`} />
            <Panel id="drive-loader" title={closed ? undefined : "Load leads and beta families"}>
              {closed
                ? <More summary="Load people anyway"><div className="max-w-[56rem]"><DriveLoader onLoaded={state.reload} note={reminders} /></div></More>
                : <div className="max-w-[56rem]"><DriveLoader onLoaded={state.reload} primary note={reminders} /></div>}
            </Panel>
          </>
        )
        return (
          <>
            <PageHead title="Reservation drive" line={`${c.ready ? `${plural(c.ready, "note")} ready to send. ` : ""}${when}. ${c.reserved} of ${c.total} reserved.`} />
            <Panel>
              <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4 xl:grid-cols-7">
                <Fact label={`People (${plural(c.leads, "lead")}, ${plural(c.beta, "beta family", "beta families")})`}>{c.total}</Fact>
                <Fact label="Not yet written">{c.not_written}</Fact>
                <Fact label="Ready to send">{c.ready}</Fact>
                <Fact label="Sent">{c.sent}</Fact>
                <Fact label="Replied">{c.replied}</Fact>
                <Fact label="Reserved" tone={c.reserved ? "good" : undefined}>{c.reserved}</Fact>
                <Fact label="Referrals">{c.referrals}</Fact>
              </div>
            </Panel>
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <div className="flex min-w-0 flex-col gap-5">
                {GROUPS.map(([key, title, note]) => {
                  const list = b.members.filter((m) => m.shown === key)
                  if (!list.length) return null
                  return (
                    <Panel key={key} title={`${title} (${list.length})`}>
                      <p className="max-w-[70ch] text-base text-muted-foreground">{note}</p>
                      <Limited items={list} label={title}>
                        {(m) => <Member key={m.contact_id} m={m} lead={m.contact_id === firstReady} busy={busy} act={act} draft={draft} />}
                      </Limited>
                    </Panel>
                  )
                })}
              </div>
              <div className="flex min-w-0 flex-col gap-5">
                <Panel id="drive-loader" title="Load more people">
                  <More summary="Load leads and beta families"><DriveLoader onLoaded={state.reload} note={reminders} /></More>
                </Panel>
                {b.entries.length > 0 && (
                  <Panel title="What channel math sees"
                    aside={<a href="/growth#channels" className="flex min-h-11 items-center font-medium text-primary underline-offset-4 hover:underline">Channel math</a>}>
                    <ul className="flex flex-col">
                      {b.entries.map((e, i) => (
                        <li key={i} className="border-t py-3 text-base first:border-t-0 first:pt-0">
                          {day(e.created_at)}{" · "}{e.channel === "referrals" ? "Referrals" : "Email"}{" · "}{e.purchases ? "1 purchase ($1)" : "1 signup"}
                          {e.note ? <span className="text-muted-foreground"> · {e.note}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </Panel>
                )}
              </div>
            </div>
          </>
        )
      }}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/drive": () => <DrivePage /> } }
