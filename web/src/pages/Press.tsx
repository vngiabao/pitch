import { useState } from "react"
import { ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useFeedback } from "@/components/app/feedback"
import { Empty, LoadGate, PageHead, Panel, Tag, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { PRESS_KIND_WORDS, stateWord, useRun, type PressData, type PressTarget } from "@/lib/customers"
import { day, plural, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

import { DraftBlock, Item, Limited, More } from "./Drive"

type Do = {
  busy: string | null
  setState: (t: PressTarget, state: PressTarget["state"]) => void
  draft: (t: PressTarget) => void
}

const missed = (t: PressTarget) => t.days_left !== null && t.days_left < 0

function deadlineTag(t: PressTarget) {
  if (!t.deadline) return <Tag>No deadline stated</Tag>
  if (missed(t)) return <Tag>Closed {day(t.deadline)}</Tag>
  return <Tag tone={t.days_left !== null && t.days_left <= 14 ? "urgent" : "quiet"}>Pitch by {day(t.deadline)}</Tag>
}

const sub = (t: PressTarget) => [PRESS_KIND_WORDS[t.kind] || t.kind, t.audience].filter(Boolean).join(" · ")

// One outlet: a row with its deadline and one action. The pitch, how to send it and the rest open under the row.
function OpenTarget({ t, lead, open, toggle, busy, setState, draft }: { t: PressTarget; lead: boolean; open: boolean; toggle: () => void } & Do) {
  const link = t.submit_url || t.url
  const on = (a: string) => busy === `${a}:${t.id}`
  const skip = <Button size="lg" variant="outline" disabled={!!busy} onClick={() => setState(t, "SKIPPED")}>{on("SKIPPED") ? "Saving…" : "Skip"}</Button>
  return (
    <Item title={t.outlet} sub={sub(t)} tag={deadlineTag(t)}
      actions={(
        <Button size="lg" variant={lead && !open ? "default" : "outline"} aria-expanded={open} onClick={toggle}>
          {open ? "Close" : t.draft ? "Open pitch" : "Open"}
        </Button>
      )}>
      {open && (
        <>
          {t.angle && <p className="max-w-[70ch] text-base">{t.angle}</p>}
          {(t.submit_method || link) && (
            <p className="max-w-[70ch] text-base break-words text-muted-foreground">
              {t.submit_method && <>How to pitch: {t.submit_method} </>}
              {link && (
                <a href={link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-primary underline underline-offset-4">
                  Open how to pitch<ExternalLink className="size-4" aria-hidden="true" />
                </a>
              )}
            </p>
          )}
          {t.draft
            ? (
              <DraftBlock draft={t.draft}>
                <div className="flex flex-wrap gap-2">
                  <Button size="lg" disabled={!!busy} onClick={() => setState(t, "PITCHED")}>{on("PITCHED") ? "Saving…" : "I sent it"}</Button>
                  {skip}
                </div>
                <More summary="More">
                  <div className="flex flex-wrap gap-2">
                    <Button size="lg" variant="outline" disabled={!!busy} onClick={() => draft(t)}>{on("draft") ? "Starting…" : "Write a new draft"}</Button>
                    {t.source_url && (
                      <Button size="lg" variant="outline" asChild>
                        <a href={t.source_url} target="_blank" rel="noopener noreferrer">Source<ExternalLink aria-hidden="true" /></a>
                      </Button>
                    )}
                  </div>
                </More>
              </DraftBlock>
            )
            : (
              <>
                <p className="text-base">
                  {t.drafting ? <><span className="font-semibold">Drafting.</span> This pitch is being written now.</> : <span className="font-semibold">No pitch yet.</span>}
                </p>
                <div className="flex flex-wrap gap-2">
                  {!t.drafting && <Button size="lg" disabled={!!busy} onClick={() => draft(t)}>{on("draft") ? "Starting…" : "Draft it now"}</Button>}
                  {skip}
                  {t.source_url && (
                    <Button size="lg" variant="outline" asChild>
                      <a href={t.source_url} target="_blank" rel="noopener noreferrer">Source<ExternalLink aria-hidden="true" /></a>
                    </Button>
                  )}
                </div>
              </>
            )}
        </>
      )}
    </Item>
  )
}

function DoneTarget({ t, busy, setState }: { t: PressTarget } & Do) {
  const on = (a: string) => busy === `${a}:${t.id}`
  return (
    <Item title={t.outlet} sub={sub(t)} tag={<Tag tone={t.state === "PUBLISHED" ? "good" : "quiet"}>{stateWord(t.state)}</Tag>}>
      <div className="flex flex-wrap gap-2">
        {t.state === "PITCHED" && <Button size="lg" variant="outline" disabled={!!busy} onClick={() => setState(t, "PUBLISHED")}>{on("PUBLISHED") ? "Saving…" : "It was published"}</Button>}
        <Button size="lg" variant="outline" disabled={!!busy} onClick={() => setState(t, "NEW")}>{on("NEW") ? "Saving…" : "Move back to open"}</Button>
      </div>
    </Item>
  )
}

export function PressPage() {
  const state = useLoad(() => api<PressData>("/api/press"))
  const { busy, run } = useRun(state.reload)
  const { confirm } = useFeedback()
  const [openId, setOpenId] = useState<string | null>(null)

  async function setState(t: PressTarget, next: PressTarget["state"]) {
    // "I sent it" records that Bao pitched the outlet himself; the old page did not ask first.
    if (next === "PITCHED" && !(await confirm({
      title: "Mark this pitch as sent?",
      body: <><strong className="font-semibold text-foreground">{t.outlet}.</strong> This records that you sent the pitch yourself. Founder OS sends nothing.</>,
      action: "Yes, I sent it",
    }))) return
    await run(`${next}:${t.id}`, async () => {
      await api("/api/press-state", { id: t.id, state: next })
      return next === "PITCHED" ? "Marked as pitched." : "Saved."
    })
  }
  const draft = (t: PressTarget) => run(`draft:${t.id}`, async () => {
    await api("/api/growth-draft", { kind: "press", id: t.id })
    return "The pitch is being drafted. It appears here in a few minutes."
  })
  const discover = () => run("discover", async () => {
    await api("/api/press-discover", {})
    return "Search started. New outlets appear here in about 15 minutes."
  })

  return (
    <Shell active="Customers" tab="/press" title="Press & gift guides">
      <LoadGate state={state}>{(r) => {
        const fresh = r.targets.filter((t) => t.state === "NEW")
        // Soonest live deadline first, then outlets with no deadline; passed deadlines go to their own group.
        const dated = fresh.filter((t) => t.deadline && !missed(t)).sort((a, b) => (a.days_left ?? 0) - (b.days_left ?? 0))
        const open = [...dated, ...fresh.filter((t) => !t.deadline)]
        const late = fresh.filter(missed)
        const done = r.targets.filter((t) => t.state !== "NEW")
        const lead = open[0]?.id
        const does: Do = { busy, setState, draft }
        const row = (t: PressTarget) => (
          <OpenTarget key={t.id} t={t} lead={t.id === lead && openId === null} open={openId === t.id} toggle={() => setOpenId(openId === t.id ? null : t.id)} {...does} />
        )
        const search = r.searching ? "A search is running now." : r.last_run ? `Last search ${stamp(r.last_run.at)}: ${r.last_run.found} new.` : "The next search runs Monday or Thursday morning."
        const side = done.length > 0
        return (
          <>
            <PageHead title="Press & gift guides"
              line={open.length
                ? `${plural(open.length, "outlet")} open to pitch${dated[0] ? `, next deadline ${day(dated[0].deadline)}` : ""}. ${search}`
                : `No open outlets. ${search}`}>
              <Button size="lg" variant={open.length ? "outline" : "default"} disabled={r.searching || !!busy} onClick={discover}>
                {r.searching ? "Searching…" : busy === "discover" ? "Starting…" : "Find more now"}
              </Button>
            </PageHead>
            <div ref={evenBottoms} className={side ? "grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]" : "flex flex-col gap-5"}>
              <div className="flex min-w-0 flex-col gap-5">
                <Panel title={`Open to pitch (${open.length})`}>
                  {open.length
                    ? <Limited items={open} limit={7} label="Open to pitch">{row}</Limited>
                    : <Empty>{r.searching ? "Results show up here in about 15 minutes." : "Use Find more now, or wait for the next search."}</Empty>}
                </Panel>
                {late.length > 0 && (
                  <Panel title={`Missed (${late.length})`}>
                    <Limited items={late} label="Missed">{row}</Limited>
                  </Panel>
                )}
              </div>
              {side && (
                <Panel title={`Pitched, published or skipped (${done.length})`}>
                  <Limited items={done} label="Pitched, published or skipped">{(t) => <DoneTarget key={t.id} t={t} {...does} />}</Limited>
                </Panel>
              )}
            </div>
          </>
        )
      }}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/press": () => <PressPage /> } }
