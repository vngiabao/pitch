import { useMemo, useState } from "react"

import { useFeedback } from "@/components/app/feedback"
import { CopyBox, Empty, Panel, Tag } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { day, stamp, usd } from "@/lib/format"
import { CLOSED_STAGES, DEAL_MOVES, DRAFT_STAGES, NOTE_STAGES, STAGE_CONFIRM, type Deal, type Stage } from "@/lib/growth"

import { Act, Area, ExtLink, FormGrid, In, More, Note, Pick, SubHead, useAsked, useDesk, useSubmit } from "./parts"

const IN_VIEW = 6

// Move a deal to another stage. "I sent it", "Won" and "Lost" are confirmed first: they record what happened
// outside Founder OS, and nothing here sends anything.
function useMove() {
  const { act } = useDesk()
  const { confirm, ask, toast } = useFeedback()
  return async (d: Deal, stage: string, label: string) => {
    const c = STAGE_CONFIRM[stage]
    if (c && !(await confirm(c))) return
    let note = ""
    if (NOTE_STAGES.includes(stage)) {
      const said = await ask({ title: `${d.name}: ${label.toLowerCase()}`, body: "Leave it empty to save without a note.", label: "One line on what happened (optional)", action: "Save" })
      if (said === null) { toast("Not saved."); return }
      note = said
    }
    await act(`stage:${d.id}:${stage}`, () => api("/api/deal-stage", { id: d.id, stage, note }), "Saved.")
  }
}

function DealNote({ d }: { d: Deal }) {
  const { act } = useDesk()
  if (d.draft) return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-muted-foreground">Subject</span>
      <CopyBox text={d.draft.title || "(no subject)"} label="Copy subject" />
      <span className="text-sm text-muted-foreground">Message</span>
      <CopyBox text={d.draft.body} label="Copy message" />
      {d.draft.note && <p className="max-w-[70ch] text-sm text-muted-foreground">{d.draft.note}</p>}
      {d.open && d.stage !== "SENT" && <p className="max-w-[70ch] text-base text-muted-foreground">Copy it and send it from your own email, then press I sent it.</p>}
    </div>
  )
  if (d.drafting) return <Note lead="Drafting.">The agent is writing this note now.</Note>
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg bg-secondary px-4 py-3 text-base">
      <span className="font-semibold">No note yet.</span>
      <Act k={`draft:${d.id}`} busyLabel="Starting…" onClick={() => draftNote(act, d)}>Draft it now</Act>
    </div>
  )
}

const draftNote = (act: ReturnType<typeof useDesk>["act"], d: Deal) =>
  act(`draft:${d.id}`, () => api("/api/deal-draft", { id: d.id }), "The agent is drafting the note. It appears here in a few minutes, checked and in your voice.")

function DealDetail({ d }: { d: Deal }) {
  const { act } = useDesk()
  const move = useMove()
  const submit = useSubmit()
  const moves = DEAL_MOVES[d.stage] || []
  const showDraft = DRAFT_STAGES.includes(d.stage)
  const last = d.events[0]
  return (
    <div className="flex flex-col gap-4 pb-2">
      {d.why && <p className="max-w-[70ch] text-base">{d.why}</p>}
      {d.angle && <p className="max-w-[70ch] text-base text-muted-foreground"><span className="font-medium text-foreground">Open with:</span> {d.angle}</p>}
      {d.contact_route && <p className="max-w-[70ch] text-base text-muted-foreground"><span className="font-medium text-foreground">Reach them:</span> {d.contact_route}</p>}
      {(d.url || (d.source_url && d.source === "partner_scout")) && (
        <div className="flex flex-wrap gap-x-6">
          {d.url && <ExtLink href={d.url}>Their page</ExtLink>}
          {d.source_url && d.source === "partner_scout" && <ExtLink href={d.source_url}>Source</ExtLink>}
        </div>
      )}
      {last && <p className="max-w-[70ch] text-base text-muted-foreground"><span className="font-medium text-foreground">Last:</span> {day(last.occurred_on)}, {last.summary}</p>}
      {d.reply_proposal && (
        <div className="flex flex-col items-start gap-3 rounded-lg bg-secondary px-4 py-3 text-base">
          <p className="max-w-[70ch]">
            <span className="font-semibold">A reply may be in your inbox.</span> {d.reply_proposal.sender} wrote “{d.reply_proposal.subject}” on {day(d.reply_proposal.received_at)}. Nothing moves until you confirm it.
          </p>
          <Button variant="outline" size="lg" asChild><a href="/decisions">Confirm it in Decisions</a></Button>
        </div>
      )}
      {showDraft && <DealNote d={d} />}
      {d.open && moves.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {moves.map(([stage, label]) => (
            <Act key={stage} k={`stage:${d.id}:${stage}`} onClick={() => move(d, stage, label)}>{label}</Act>
          ))}
        </div>
      )}
      <More label="Log, edit or move">
        <form className="flex flex-col gap-4" onSubmit={submit(`event:${d.id}`, "/api/deal-event", { id: d.id }, "Logged.")}>
          <SubHead>Log what happened</SubHead>
          <Area label="What happened" name="summary" required maxLength={2000} placeholder="e.g. Spoke to their benefits lead; wants pricing for 40 families" />
          <FormGrid>
            <In label="Date" name="occurred_on" type="date" />
            <In label="Next step" name="next_step" maxLength={300} />
            <In key={d.next_on || ""} label="Next step date" name="next_on" type="date" defaultValue={d.next_on || ""} />
          </FormGrid>
          <Act k={`event:${d.id}`} type="submit" className="self-start">Save what happened</Act>
        </form>
        <form key={`${d.value_usd}|${d.value_note}|${d.contact_route}`} className="flex flex-col gap-4 border-t pt-4" onSubmit={submit(`edit:${d.id}`, "/api/deal-update", { id: d.id }, "Saved.")}>
          <SubHead>Deal details</SubHead>
          <FormGrid>
            <In label="Worth (USD, a year)" name="value_usd" type="number" min={0} defaultValue={d.value_usd ?? ""} />
            <In label="What it is worth" name="value_note" maxLength={200} defaultValue={d.value_note || ""} placeholder="e.g. 40 gift passes" />
            <In label="How to reach them" name="contact_route" maxLength={300} defaultValue={d.contact_route || ""} />
          </FormGrid>
          <Act k={`edit:${d.id}`} type="submit" className="self-start">Save details</Act>
        </form>
        {d.events.length > 1 && (
          <div className="flex flex-col gap-2 border-t pt-4">
            <SubHead>Earlier</SubHead>
            <ul className="flex flex-col gap-1">
              {d.events.slice(1, 6).map((e, i) => <li key={i} className="max-w-[70ch] text-base text-muted-foreground">{day(e.occurred_on)} · {e.summary}</li>)}
            </ul>
          </div>
        )}
        <div className="flex flex-wrap gap-3 border-t pt-4">
          {d.draft && showDraft && <Act k={`draft:${d.id}`} busyLabel="Starting…" onClick={() => draftNote(act, d)}>Write a new note</Act>}
          {d.open ? (
            <>
              <Act k={`stage:${d.id}:PARKED`} onClick={() => move(d, "PARKED", "Park")}>Park</Act>
              <Act k={`stage:${d.id}:LOST`} onClick={() => move(d, "LOST", "Lost")}>Lost</Act>
            </>
          ) : (
            <Act k={`stage:${d.id}:${d.draft ? "DRAFTED" : "FOUND"}`} onClick={() => move(d, d.draft ? "DRAFTED" : "FOUND", "Move back to open")}>Move back to open</Act>
          )}
        </div>
      </More>
    </div>
  )
}

function DealRow({ d }: { d: Deal }) {
  const [open, setOpen] = useState(d.due)
  useAsked("deal-" + d.id, () => setOpen(true))
  const status = d.due ? `Due ${day(d.next_on)}`.trim() : `${d.stage_words}${d.next_on && d.open ? " · " + day(d.next_on) : ""}`
  const tone = d.due ? "urgent" : d.stage === "WON" ? "good" : d.open && (d.draft || d.reply_proposal) ? "review" : "quiet"
  const facts = [d.due ? `Next: ${d.next_step || d.stage_words}` : "", d.kind_words, d.region].filter(Boolean).join(" · ")
  return (
    <li id={`deal-${d.id}`} className="flex scroll-mt-4 flex-col gap-4 border-t py-3 first:border-t-0">
      <div className="flex min-h-12 flex-wrap items-center gap-x-4 gap-y-2">
        <span className="flex min-w-0 flex-1 basis-64 flex-col gap-0.5">
          <span className="text-base font-semibold">{d.name}</span>
          <span className="text-base text-muted-foreground">
            {facts}
            {d.value_usd ? <> · <span className="font-semibold text-money">{usd(d.value_usd)}</span></> : null}
            {d.value_note ? ` · ${d.value_note}` : ""}
          </span>
        </span>
        <Tag tone={tone}>{status}</Tag>
        <Button type="button" variant="outline" size="lg" aria-expanded={open} className="w-24" onClick={() => setOpen((v) => !v)}>
          {open ? "Close" : "Open"}<span className="sr-only"> {d.name}</span>
        </Button>
      </div>
      {open && <DealDetail d={d} />}
    </li>
  )
}

function StageGroup({ label, total, deals }: { label: string; total: number; deals: Deal[] }) {
  return (
    <section className="flex flex-col gap-1">
      <h4 className="text-sm font-medium text-muted-foreground">{label} · {total}</h4>
      <ul aria-label={label} className="flex flex-col">{deals.map((d) => <DealRow key={d.id} d={d} />)}</ul>
    </section>
  )
}

function AddDeal({ open }: { open: boolean }) {
  const { b } = useDesk()
  const submit = useSubmit()
  return (
    <More label="Add a deal" defaultOpen={open} className="border-t pt-4">
      <form className="flex flex-col gap-4" onSubmit={submit("deal:add", "/api/deal", {}, "Added. The agent drafts a first note; you send it.")}>
        <FormGrid>
          <In label="Organization or person" name="name" required maxLength={160} />
          <Pick label="Type" name="kind" options={b.kinds.map((k) => [k.key, k.label])} />
          <In label="Region" name="region" maxLength={80} placeholder="e.g. Ann Arbor" />
          <In label="Their page" name="url" type="url" placeholder="https://" />
          <In label="How to reach them" name="contact_route" maxLength={300} placeholder="e.g. partnerships form, intro from Rose" />
          <In label="Worth (USD, a year)" name="value_usd" type="number" min={0} />
          <In label="Next step date" name="next_on" type="date" />
        </FormGrid>
        <Area label="Why them" name="why" maxLength={600} placeholder="e.g. 2,000 alumni over 60; runs a holiday gift shop" />
        <Area label="What already happened (optional)" name="summary" maxLength={2000} />
        <Act k="deal:add" type="submit" busyLabel="Adding…" className="self-start">Add deal</Act>
      </form>
    </More>
  )
}

// Deals as rows, grouped by stage. Six in view; the rest behind one control. Each deal's note, history and
// forms sit behind its own Open.
export function DealsPanel() {
  const { b, target } = useDesk()
  const [kind, setKind] = useState("")
  const [all, setAll] = useState(false)
  const [closedAsked, setClosedAsked] = useState(false)

  const openStages = b.stages.filter((s) => !CLOSED_STAGES.includes(s.key))
  const closed = b.stages.filter((s) => CLOSED_STAGES.includes(s.key) && s.deals.length)
  const closedN = closed.reduce((n, s) => n + s.deals.length, 0)

  // A link to #deal-<id> shows that deal wherever it sits: past the first six, under another type, or closed.
  // Compared during render (not in an effect), once per ask.
  const [seen, setSeen] = useState(-1)
  if (target.id.startsWith("deal-") && seen !== target.n) {
    setSeen(target.n)
    const stage = b.stages.find((s) => s.deals.some((d) => "deal-" + d.id === target.id))
    if (stage) {
      setKind("")
      if (CLOSED_STAGES.includes(stage.key)) setClosedAsked(true)
      else setAll(true)
    }
  }

  const { groups, shown, matching } = useMemo(() => {
    let room = all ? Infinity : IN_VIEW, shown = 0, matching = 0
    const groups: (Stage & { total: number })[] = []
    for (const s of openStages) {
      const mine = s.deals.filter((d) => !kind || d.kind === kind)
      matching += mine.length
      const take = mine.slice(0, room)
      room -= take.length
      shown += take.length
      if (take.length) groups.push({ ...s, deals: take, total: mine.length })
    }
    return { groups, shown, matching }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [b, kind, all])

  const scout = b.last_run
    ? `Partner Scout last ran ${stamp(b.last_run.at)}: ${b.last_run.found} new.`
    : "Partner Scout runs Tuesday mornings until mid-December, or now on request."

  return (
    <Panel id="deals" className="scroll-mt-4" title="Deals" aside={`${scout}${b.searching ? " A search is running now; new deals appear in about 15 minutes." : ""}`}>
      {b.open ? (
        <>
          <Pick label="Show" name="deal-kind" className="max-w-xs" value={kind} onChange={(e) => setKind(e.target.value)}
            options={[["", `All types (${b.open})`], ...b.kinds.map((k): [string, string] => [k.key, k.label])]} />
          {groups.length
            ? groups.map((s) => <StageGroup key={s.key} label={s.label} total={s.total} deals={s.deals} />)
            : <Empty>No open deals of this type.</Empty>}
          {matching > shown && (
            <Button type="button" variant="outline" size="lg" className="self-start" onClick={() => setAll(true)}>
              Show all {matching} open deals
            </Button>
          )}
          {all && matching > IN_VIEW && (
            <Button type="button" variant="outline" size="lg" className="self-start" onClick={() => setAll(false)}>
              Show the first {IN_VIEW} only
            </Button>
          )}
        </>
      ) : (
        <Empty>No deals yet. Add the organizations you already talk to, or let Partner Scout find who reaches adult children and gift buyers near you.</Empty>
      )}
      <AddDeal open={!b.open} />
      {closedN > 0 && (
        <More label={`Won, lost or parked (${closedN})`} open={closedAsked} className="border-t pt-4">
          {closed.map((s) => <StageGroup key={s.key} label={s.label} total={s.deals.length} deals={s.deals} />)}
        </More>
      )}
    </Panel>
  )
}
