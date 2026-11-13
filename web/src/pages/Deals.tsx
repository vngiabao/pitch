import { useCallback, useEffect, useState } from "react"

import { useFeedback } from "@/components/app/feedback"
import { LoadGate, PageHead, Panel, Row, Rows, useLoad, evenBottoms } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { deskLine, loadDesk, type Desk } from "@/lib/growth"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

import { CampaignsPanel } from "./deals/Campaigns"
import { ChannelsPanel } from "./deals/Channels"
import { DealsPanel } from "./deals/DealsPanel"
import { Act, DeskProvider, type Target } from "./deals/parts"
import { VoicePanel } from "./deals/Voice"

// The customer desk. It opens on what needs Bao, then deals by stage, campaigns, what families say online,
// and channel math. Agents find, draft and plan; Bao sends every note and closes every deal.
function DeskView({ desk, reload }: { desk: Desk; reload: () => Promise<unknown> }) {
  const { toast } = useFeedback()
  const b = desk.growth
  const [busy, setBusy] = useState<string | null>(null)
  const [target, setTarget] = useState<Target>({ id: decodeURIComponent(location.hash.slice(1)), n: 0 })

  // The old page's pattern for every action: call the server, load the page's data again, then say what happened.
  const act = useCallback(async (key: string, run: () => Promise<unknown>, done: string) => {
    setBusy(key)
    try { await run(); await reload(); toast(done); return true }
    catch (e) { toast(e instanceof Error ? e.message : "Unable to complete this action.", true); return false }
    finally { setBusy(null) }
  }, [reload, toast])

  // Anchors keep working (#deal-<id>, #campaign-<key>, #families-say, #channels): the part opens itself, then the
  // page scrolls to it. `n` changes on every ask so the same link works twice.
  const go = useCallback((id: string) => setTarget((t) => ({ id, n: t.n + 1 })), [])
  useEffect(() => {
    const onHash = () => go(decodeURIComponent(location.hash.slice(1)))
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [go])
  useEffect(() => {
    if (!target.id) return
    const timer = setTimeout(() => document.getElementById(target.id)?.scrollIntoView({ block: "start" }), 120)
    return () => clearTimeout(timer)
  }, [target])

  return (
    <DeskProvider value={{ b, busy, act, target, go }}>
      <PageHead title="Deals & campaigns" line={deskLine(b)}>
        <Act k="discover" busyLabel="Starting…" disabled={b.searching}
          onClick={() => act("discover", () => api("/api/partner-discover", {}), "Partner Scout started. New deals appear in about 15 minutes.")}>
          {b.searching ? "Searching…" : "Find partners now"}
        </Act>
      </PageHead>

      {desk.next.length > 0 && (
        <Panel title="Do next">
          <Rows label="Do next">
            {desk.next.map((x, i) => {
              // An alert that points at this page goes to the deals below, not to a reload.
              const href = x.href === "/growth" ? "#deals" : x.href
              return (
                <Row key={x.href + x.title} title={x.title} line={x.detail}>
                  <Button size="lg" variant={i === 0 ? "default" : "outline"} className="w-36" asChild>
                    <a href={href} onClick={href.startsWith("#") ? () => go(href.slice(1)) : undefined}>{x.label}</a>
                  </Button>
                </Row>
              )
            })}
          </Rows>
        </Panel>
      )}

      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          <DealsPanel />
          <CampaignsPanel />
        </div>
        {b.voice && <VoicePanel v={b.voice} />}
      </div>

      <ChannelsPanel />
    </DeskProvider>
  )
}

export function DealsPage() {
  const state = useLoad(loadDesk)
  return (
    <Shell active="Customers" tab="/growth" title="Deals & campaigns">
      <LoadGate state={state}>{(desk) => <DeskView desk={desk} reload={state.reload} />}</LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/growth": () => <DealsPage /> } }
