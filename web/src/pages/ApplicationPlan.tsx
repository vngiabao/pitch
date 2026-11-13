import { ExternalLink } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Empty, LoadGate, PageHead, Panel, Row, Rows, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { cycleLabel, external, plain, useLimit, type PlanReview } from "@/lib/applications"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

function Attention({ blockers }: { blockers: string[] }) {
  const { shown, hidden, showAll } = useLimit(blockers, 7)
  return (
    <Panel title="What needs attention" aside={blockers.length || undefined}>
      {blockers.length ? (
        <>
          <Rows label="What needs attention">
            {shown.map((b, i) => <Row key={i} title={<span className="font-medium">{plain(b)}</span>} />)}
          </Rows>
          {hidden > 0 && <Button size="lg" variant="outline" className="self-start" onClick={showAll}>Show all {blockers.length}</Button>}
        </>
      ) : <Empty>Preparation checks passed.</Empty>}
    </Panel>
  )
}

// A planned application whose form has not been read yet. Once the form is read, this address goes to its answers.
export function ApplicationPlanPage({ id }: { id: string }) {
  const state = useLoad<PlanReview>(async () => {
    const r = await api<PlanReview>("/api/application-review/" + encodeURIComponent(id))
    if (r.application_id) location.replace("/application/" + r.application_id)
    return r
  }, [id])
  const program = state.data ? plain(state.data.program) : undefined
  return (
    <Shell active="Funding" tab="/applications" crumb={program} title={program || "Application plan"}>
      <LoadGate state={state}>
        {(r) => r.application_id ? null : (
          <>
            <PageHead title={plain(r.program)}
              line={["Application plan", plain(cycleLabel(r.cycle))].filter(Boolean).join(" · ") + ". The agent has not read this form yet."}>
              {r.url
                ? <Button size="lg" asChild><a href={r.url} {...external}>Open the official form<ExternalLink aria-hidden="true" /></a></Button>
                : <span className="text-base text-muted-foreground">Application link not found yet.</span>}
            </PageHead>
            <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <Attention blockers={r.blockers || []} />
              <Panel title="What happens next">
                <Rows label="What happens next">
                  <Row title="The agent reads the form" line="Its questions appear under Applications once it does." />
                  <Row title="You copy the answers in" line="The agent prepares them from your approved facts. You submit the form yourself." />
                </Rows>
              </Panel>
            </div>
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/application-review/": (id) => <ApplicationPlanPage id={id} /> } }
