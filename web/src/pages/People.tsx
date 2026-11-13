import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { useFeedback } from "@/components/app/feedback"
import { Empty, Field, LoadGate, PageHead, Panel, Tag, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { CONTACT_KINDS, stateWord, useHashScroll, useRun, type DriveData, type Person } from "@/lib/customers"
import { day, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

import { CopyButton, DraftBlock, Item, Limited, MailLink } from "./Drive"

type Run = ReturnType<typeof useRun>["run"]
type Do = { busy: string | null; run: Run; sent: (c: Person) => void }

const fields = (form: HTMLFormElement) => Object.fromEntries(new FormData(form)) as Record<string, string>

// A person who is due sits under "Follow up now", so the panel's title is their status.
function statusTag(c: Person) {
  if (c.due) return undefined
  if (c.state !== "ACTIVE") return <Tag>{stateWord(c.state)}</Tag>
  if (!c.next_followup_on) return <Tag>No follow-up set</Tag>
  return <Tag>Next {day(c.next_followup_on)}</Tag>
}

function PersonItem({ c, lead, busy, run, sent }: { c: Person; lead: boolean } & Do) {
  const [logging, setLogging] = useState(false)
  const last = c.touches[0]
  const on = (a: string) => busy === `${a}:${c.id}`
  const draft = () => run(`draft:${c.id}`, async () => {
    await api("/api/growth-draft", { kind: "contact", id: c.id })
    return "The note is being drafted. It appears here in a few minutes."
  })
  const flip = () => run(`state:${c.id}`, async () => {
    await api("/api/person-update", { id: c.id, state: c.state === "ACTIVE" ? "PAUSED" : "ACTIVE" })
    return "Saved."
  })
  async function logTouch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    if (await run(`touch:${c.id}`, async () => { await api("/api/person-touch", { id: c.id, ...fields(form) }); return "Conversation logged." })) { form.reset(); setLogging(false) }
  }
  const redraft = (label: string, primary?: boolean) => (
    <Button size="lg" variant={primary ? "default" : "outline"} disabled={!!busy} onClick={draft}>{on("draft") ? "Starting…" : label}</Button>
  )
  return (
    <Item id={`person-${c.id}`} title={c.name} sub={[c.org, c.kind, c.email].filter(Boolean).join(" · ")} tag={statusTag(c)}
      actions={c.due && c.draft
        ? (
          <>
            <CopyButton text={c.draft.body} label="Copy message" />
            <Button size="lg" variant={lead ? "default" : "outline"} disabled={!!busy} onClick={() => sent(c)}>{on("sent") ? "Saving…" : "I sent it"}</Button>
          </>
        )
        : c.due && !c.drafting ? redraft("Draft it now", lead) : undefined}>
      {c.context && <p className="max-w-[70ch] text-base">{c.context}</p>}
      {last && <p className="max-w-[70ch] text-base text-muted-foreground">Last: {day(last.occurred_on)}, {last.summary}</p>}
      {c.due && c.draft && (
        <DraftBlock draft={c.draft} plain>
          <div className="flex flex-wrap gap-2">
            {c.email && <MailLink email={c.email} />}
            {redraft("Write a new draft")}
          </div>
        </DraftBlock>
      )}
      {c.due && !c.draft && (
        <p className="text-base">
          {c.drafting ? <><span className="font-semibold">Drafting.</span> This note is being written now.</> : <span className="font-semibold">No draft yet.</span>}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button size="lg" variant="outline" aria-expanded={logging} onClick={() => setLogging(!logging)}>{logging ? "Close the log" : "Log a conversation"}</Button>
        <Button size="lg" variant="outline" disabled={!!busy} onClick={flip}>
          {on("state") ? "Saving…" : c.state === "ACTIVE" ? "Pause follow-ups" : "Resume follow-ups"}
        </Button>
        {c.touches.length > 1 && <span className="text-sm text-muted-foreground">{c.touches.length} conversations logged</span>}
      </div>
      {logging && (
        <form onSubmit={logTouch} className="flex flex-col gap-4 rounded-lg bg-secondary p-4">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
            <Field label="What happened" htmlFor={`touch-summary-${c.id}`}>
              <Textarea id={`touch-summary-${c.id}`} name="summary" required maxLength={2000} placeholder="e.g. Coffee chat; they want a demo after launch" />
            </Field>
            <div className="flex flex-col gap-4">
              <Field label="Date" htmlFor={`touch-date-${c.id}`}><Input id={`touch-date-${c.id}`} type="date" name="occurred_on" /></Field>
              <Field label="Next follow-up" htmlFor={`touch-next-${c.id}`} hint={`Leave it empty to use ${plural(c.cadence_days, "day")}.`}>
                <Input id={`touch-next-${c.id}`} type="date" name="next_followup_on" />
              </Field>
            </div>
          </div>
          <Button type="submit" size="lg" variant="outline" className="self-start" disabled={!!busy}>{on("touch") ? "Saving…" : "Save the conversation"}</Button>
        </form>
      )}
    </Item>
  )
}

function AddPerson({ busy, run, primary }: { busy: string | null; run: Run; primary: boolean }) {
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const body: Record<string, string | number> = fields(form)
    if (body.cadence_days) body.cadence_days = Number(body.cadence_days)
    if (await run("add-person", async () => { await api("/api/person", body); return "Added. A note is drafted when the follow-up date arrives." })) form.reset()
  }
  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name" htmlFor="person-name"><Input id="person-name" name="name" required maxLength={120} /></Field>
        <Field label="Organization" htmlFor="person-org"><Input id="person-org" name="org" maxLength={120} /></Field>
        <Field label="Type" htmlFor="person-kind">
          <NativeSelect id="person-kind" name="kind" className="w-full">
            {CONTACT_KINDS.map((k) => <NativeSelectOption key={k} value={k}>{k}</NativeSelectOption>)}
          </NativeSelect>
        </Field>
        <Field label="Email (optional)" htmlFor="person-email"><Input id="person-email" type="email" name="email" maxLength={200} /></Field>
        <Field label="First follow-up" htmlFor="person-next"><Input id="person-next" type="date" name="next_followup_on" /></Field>
        <Field label="Follow up every (days)" htmlFor="person-cadence"><Input id="person-cadence" type="number" name="cadence_days" min={1} max={180} defaultValue={14} /></Field>
      </div>
      <Field label="How you know them" htmlFor="person-context">
        <Textarea id="person-context" name="context" maxLength={2000} placeholder="e.g. Judge at Startup World Cup Columbus; liked the family archive" />
      </Field>
      <Field label="Last conversation (optional)" htmlFor="person-summary"><Textarea id="person-summary" name="summary" maxLength={2000} /></Field>
      <Button type="submit" size="lg" variant={primary ? "default" : "outline"} className="self-start" disabled={!!busy}>{busy === "add-person" ? "Adding…" : "Add person"}</Button>
    </form>
  )
}

export function PeoplePage() {
  const state = useLoad(() => api<Person[]>("/api/people"))
  // Only to say whether the reservation drive is still open. The side panel waits for it and stays away without it.
  const drive = useLoad(() => api<DriveData>("/api/drive"))
  const { busy, run } = useRun(state.reload)
  const { confirm } = useFeedback()
  useHashScroll(!!state.data)

  async function sent(c: Person) {
    if (!(await confirm({
      title: "Log that you sent this follow-up?",
      body: <><strong className="font-semibold text-foreground">{c.name}.</strong> This records that you sent it yourself. The next follow-up is scheduled automatically.</>,
      action: "Yes, I sent it",
    }))) return
    await run(`sent:${c.id}`, async () => {
      await api("/api/person-touch", { id: c.id, summary: "Sent the follow-up email." })
      return "Logged. The next follow-up is scheduled."
    })
  }

  return (
    <Shell active="Customers" tab="/people" title="People">
      <LoadGate state={state}>{(list) => {
        const due = list.filter((c) => c.due), rest = list.filter((c) => !c.due)
        const lead = due.find((c) => c.draft || !c.drafting)?.id
        const next = rest.map((c) => (c.state === "ACTIVE" && c.next_followup_on) || "").filter(Boolean).sort()[0]
        const does: Do = { busy, run, sent }
        return (
          <>
            <PageHead title="People"
              line={!list.length ? "No one here yet."
                : due.length ? `${plural(due.length, "follow-up")} due${rest.length ? `, ${rest.length} more ${rest.length === 1 ? "person" : "people"} on schedule` : ""}.`
                  : `No follow-ups due. ${plural(list.length, "person", "people")}${next ? `, next follow-up ${day(next)}` : ""}.`} />
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <div className="flex min-w-0 flex-col gap-5">
                {due.length > 0 && (
                  <Panel title={`Follow up now (${due.length})`}>
                    <Limited items={due} label="Follow up now">{(c) => <PersonItem key={c.id} c={c} lead={c.id === lead} {...does} />}</Limited>
                  </Panel>
                )}
                {rest.length > 0 && (
                  <Panel title={due.length ? `Everyone else (${rest.length})` : `Everyone (${rest.length})`}>
                    <Limited items={rest} label="Everyone else">{(c) => <PersonItem key={c.id} c={c} lead={false} {...does} />}</Limited>
                  </Panel>
                )}
                {!list.length && <Panel title="Follow up now"><Empty>Add the first person, and a note is drafted when their follow-up date arrives.</Empty></Panel>}
              </div>
              <div className="flex min-w-0 flex-col gap-5">
                <Panel title="Add a person">
                  <AddPerson busy={busy} run={run} primary={!lead} />
                </Panel>
                {drive.data && (
                  <Panel id="drive-loader" title="Reservation drive" className="scroll-mt-4">
                    {drive.data.days_left < 0
                      ? (
                        <p className="flex min-h-11 flex-wrap items-center gap-x-4 gap-y-1 text-base text-muted-foreground">
                          Closed{drive.data.deadline ? ` ${day(drive.data.deadline)}` : ""}
                          <a href="/drive" className="inline-flex min-h-11 items-center font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">See the drive</a>
                        </p>
                      )
                      : (
                        <>
                          <p className="text-base text-muted-foreground">Leads and beta families for the $1 reservation are loaded on the drive's own page.</p>
                          <Button size="lg" variant="outline" className="self-start" asChild><a href="/drive#drive-loader">Load people for the drive</a></Button>
                        </>
                      )}
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

export const routes: PageRoutes = { exact: { "/people": () => <PeoplePage /> } }
