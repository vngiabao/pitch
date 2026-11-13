import { useState } from "react"

import { CopyBox, Fact, Panel, Tag } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { day, usd } from "@/lib/format"
import { CAMPAIGN_STATE, channelLabel, type Campaign, type Draft, type FieldVoice, type Plan } from "@/lib/growth"
import { cn } from "@/lib/utils"

import { Act, Area, ExtLink, FormGrid, In, More, Note, SubHead, Words, useAsked, useDesk, useSubmit } from "./parts"

const inVoice = (d?: Draft | null) => /Voice/.test(d?.note || "")

// Objections families raised online, beside the script for the day. Evidence about the market, not our customers.
function FieldVoiceBlock({ v }: { v: FieldVoice }) {
  const { go } = useDesk()
  return (
    <div className="flex flex-col gap-3">
      <SubHead>What they may say</SubHead>
      <p className="max-w-[70ch] text-base text-muted-foreground">
        Objections families raised online{v.as_of ? ` as of ${day(v.as_of)}` : ""}, not our customers.{" "}
        <a href="#families-say" onClick={() => go("families-say")} className="font-medium text-primary underline-offset-4 hover:underline">See all of it</a>
      </p>
      {v.objections.length > 0 && (
        <ul className="flex flex-col">
          {v.objections.map((o) => (
            <li key={o.objection} className="flex flex-col gap-0.5 border-t py-3 first:border-t-0">
              <span className="text-base font-semibold">{o.objection}</span>
              {o.quote && <span className="max-w-[70ch] text-base text-muted-foreground">“{o.quote}”</span>}
              {o.quote && o.url && <ExtLink href={o.url}>Source</ExtLink>}
            </li>
          ))}
        </ul>
      )}
      <Words words={v.words} />
    </div>
  )
}

// A day of selling in person: the count so far, what to say, and the tally form.
function FieldDay({ c }: { c: Campaign }) {
  const submit = useSubmit()
  const f = c.field!
  const script = c.drafts.find((d) => d.title === "Cold approach script")
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-4">
        <Fact label="Approached">{f.approached}</Fact>
        <Fact label="Emails">{f.emails}</Fact>
        <Fact label="$1 reservations">{f.reservations}</Fact>
      </div>
      {script && (
        <div className="flex flex-col gap-2">
          <span className="text-sm text-muted-foreground">What to say{inVoice(script) ? ", in your voice" : ""}. Read it out loud once before you go.</span>
          <CopyBox text={script.body} label="Copy script" />
        </div>
      )}
      {c.voice && <FieldVoiceBlock v={c.voice} />}
      <form className="flex flex-col gap-4 border-t pt-4" onSubmit={submit(`field:${c.key}`, "/api/field-day", { key: c.key }, "Tally saved. It counts in channel math under events.")}>
        <SubHead>Tally the day</SubHead>
        <FormGrid>
          <In label="People approached" name="approached" type="number" min={0} defaultValue={0} />
          <In label="Real conversations" name="conversations" type="number" min={0} defaultValue={0} />
          <In label="Emails collected" name="emails" type="number" min={0} defaultValue={0} />
          <In label="$1 reservations" name="reservations" type="number" min={0} defaultValue={0} />
          <In label="Date" name="on" type="date" />
          <In label="Note" name="note" maxLength={200} placeholder="e.g. lunch rush at the student center" />
        </FormGrid>
        <Act k={`field:${c.key}`} type="submit" className="self-start">Save tally</Act>
      </form>
      {f.entries.length > 0 && (
        <ul className="flex flex-col border-t">
          {f.entries.slice(0, 6).map((e, i) => (
            <li key={i} className="flex flex-col gap-0.5 border-t py-3 first:border-t-0">
              <span className="text-base font-semibold">{day(e.week_start)} week</span>
              <span className="max-w-[70ch] text-base text-muted-foreground">
                {e.visits} approached · {e.signups} emails · {e.purchases} reservations{e.note ? ` · ${e.note}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const Said = ({ label, children }: { label: string; children: string }) => (
  <div className="flex flex-col gap-1">
    <span className="text-sm text-muted-foreground">{label}</span>
    <p className="max-w-[70ch] text-base">{children}</p>
  </div>
)

// The dated plan: goal, who, the offer, then each channel with the message to copy.
function PlanBlock({ c, p }: { c: Campaign; p: Plan }) {
  const { b, act } = useDesk()
  const latest: Record<string, Draft> = {}
  for (const d of c.drafts) if (d.title && !latest[d.title]) latest[d.title] = d
  const setState = (state: string) => act(`campaign:${c.key}:${state}`, () => api("/api/campaign-state", { key: c.key, state }), "Saved.")
  return (
    <div className={cn("flex flex-col gap-4", c.field && "border-t pt-4")}>
      <div className="grid gap-4 xl:grid-cols-3">
        <Said label="Goal">{p.goal}</Said>
        <Said label="Who">{p.audience}</Said>
        <Said label="The offer">{p.offer}</Said>
      </div>
      {c.issues.length > 0 && (
        <ul className="flex flex-col gap-2">
          {c.issues.map((i, n) => (
            <li key={n} className="max-w-[70ch] rounded-lg bg-secondary px-4 py-3 text-base">
              <span className={cn("font-semibold", i.severity === "block" && "text-deadline")}>Fact check:</span> {i.text} <span className="text-muted-foreground">({i.where})</span>
            </li>
          ))}
        </ul>
      )}
      <ul className="flex flex-col">
        {p.channels.map((ch, n) => {
          const name = channelLabel(b.channel_words, ch.channel)
          const d = latest[name]
          const when = `${ch.start_on ? day(ch.start_on) : ""}${ch.end_on ? " to " + day(ch.end_on) : ""}`.trim()
          const message = d ? d.body : ch.message
          return (
            <li key={n} className="flex flex-col gap-3 border-t py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <SubHead>{name}</SubHead>
                <span className="text-sm text-muted-foreground">
                  {when}{ch.spend_cap_usd ? <>{when ? " · " : ""}cap <span className="font-semibold text-money">{usd(ch.spend_cap_usd)}</span></> : null}
                </span>
              </div>
              <p className="max-w-[70ch] text-base">{ch.what}</p>
              {message && (
                <div className="flex flex-col gap-2">
                  <span className="text-sm text-muted-foreground">Lead message{d && inVoice(d) ? ", in your voice" : ""}</span>
                  <CopyBox text={message} label="Copy message" />
                </div>
              )}
              <p className="max-w-[70ch] text-base text-muted-foreground">
                <span className="font-medium text-foreground">Success:</span> {ch.success_metric}
                {ch.needs_from_bao ? <> · <span className="font-medium text-foreground">You supply:</span> {ch.needs_from_bao}</> : null}
              </p>
            </li>
          )
        })}
      </ul>
      {(p.checkpoints.length > 0 || p.open_questions.length > 0) && (
        <div className="grid gap-4 border-t pt-4 xl:grid-cols-2">
          {p.checkpoints.length > 0 && (
            <div className="flex flex-col gap-2">
              <SubHead>Checkpoints</SubHead>
              <ul className="flex flex-col gap-2">
                {p.checkpoints.map((x, n) => <li key={n} className="max-w-[70ch] text-base">{x.on && <span className="font-semibold">{day(x.on)} · </span>}{x.check}</li>)}
              </ul>
            </div>
          )}
          {p.open_questions.length > 0 && (
            <div className="flex flex-col gap-2">
              <SubHead>Only you can answer</SubHead>
              <ul className="flex flex-col gap-2">
                {p.open_questions.map((q, n) => <li key={n} className="max-w-[70ch] text-base">{q}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
      {p.risks.length > 0 && (
        <More label={`Risks (${p.risks.length})`}>
          <ul className="flex flex-col gap-2">{p.risks.map((r, n) => <li key={n} className="max-w-[70ch] text-base">{r}</li>)}</ul>
        </More>
      )}
      {c.state === "PLANNED" && <Act k={`campaign:${c.key}:RUNNING`} className="self-start" onClick={() => setState("RUNNING")}>Mark it running</Act>}
      {c.state === "RUNNING" && <Act k={`campaign:${c.key}:DONE`} className="self-start" onClick={() => setState("DONE")}>Mark it done</Act>}
    </div>
  )
}

function CampaignDetail({ c }: { c: Campaign }) {
  const submit = useSubmit()
  const p = c.plan
  return (
    <div className="flex flex-col gap-4 pb-2">
      {c.field && <FieldDay c={c} />}
      {p
        ? <PlanBlock c={c} p={p} />
        : c.planning
          ? <Note lead="Planning.">The agent is writing the plan now; it appears here in a few minutes.</Note>
          : <Note lead="No plan yet.">Add anything the planner should know, then plan it.</Note>}
      <More label={p ? "Plan it again" : "Plan it"} defaultOpen={!p} className={cn(p && "border-t pt-4")}>
        <form key={c.owner_note || ""} className="flex flex-col gap-4" onSubmit={submit(`plan:${c.key}`, "/api/campaign-plan", { key: c.key }, "Campaign Planner started. The plan appears here in a few minutes.")}>
          <Area label="Anything the planner should know" name="note" maxLength={1000} defaultValue={c.owner_note || ""}
            placeholder="e.g. $300 budget for paid social; Daniel can film two short videos; Rose will post to her family group" />
          <Act k={`plan:${c.key}`} type="submit" busyLabel="Starting…" disabled={c.planning} className="self-start">{p ? "Plan again" : "Plan it now"}</Act>
        </form>
      </More>
    </div>
  )
}

function CampaignRow({ c }: { c: Campaign }) {
  const [open, setOpen] = useState(false)
  useAsked("campaign-" + c.key, () => setOpen(true))
  const word = c.planning ? "Planning…" : CAMPAIGN_STATE[c.state] || c.state
  const tone = c.planning ? "review" : c.state === "DONE" ? "good" : c.state === "NEW" ? "quiet" : "review"
  return (
    <li id={`campaign-${c.key}`} className="flex scroll-mt-4 flex-col gap-4 border-t py-3 first:border-t-0">
      <div className="flex min-h-12 flex-wrap items-center gap-x-4 gap-y-2">
        <span className="flex min-w-0 flex-1 basis-64 flex-col gap-0.5">
          <span className="text-base font-semibold">{c.title}</span>
          <span className="max-w-[70ch] text-base text-muted-foreground">{c.brief}</span>
        </span>
        <Tag tone={tone}>{word}</Tag>
        <Button type="button" variant="outline" size="lg" aria-expanded={open} className="w-24" onClick={() => setOpen((v) => !v)}>
          {open ? "Close" : "Open"}<span className="sr-only"> {c.title}</span>
        </Button>
      </div>
      {open && <CampaignDetail c={c} />}
    </li>
  )
}

// Campaigns as rows; each plan, script and tally sits behind its own Open.
export function CampaignsPanel() {
  const { b } = useDesk()
  if (!b.campaigns.length) return null
  return (
    <Panel id="campaigns" title="Campaigns" aside="Messages are checked against your facts">
      <ul aria-label="Campaigns" className="flex flex-col">{b.campaigns.map((c) => <CampaignRow key={c.key} c={c} />)}</ul>
    </Panel>
  )
}
