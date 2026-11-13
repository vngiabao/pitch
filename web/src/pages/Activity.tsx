import { useState } from "react"
import { ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useFeedback } from "@/components/app/feedback"
import { Empty, LoadGate, PageHead, Panel, Tag, useLoad } from "@/components/app/page"
import { RUN_PAUSED, humanState, isFailed, isRunning, knownCause, runDay, runTone, type Run } from "@/lib/agents"
import { api } from "@/lib/api"
import type { Dashboard } from "@/lib/company"
import { plural, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"
import { useShowAll } from "@/pages/Decisions"

// The state of research in one short line, from the latest run. What stopped a failed run is on the run's own page.
function stateLine(run?: Run) {
  if (!run) return "No research has run yet."
  if (isFailed(run)) return `Research stopped ${runDay(run)}. ${knownCause(run) ? `${RUN_PAUSED}.` : "New programs aren’t coming in."}`
  if (isRunning(run)) return "Research is running now."
  const r = run.report || {}
  return `Last research ${runDay(run)}: ${plural(r.candidates_discovered || 0, "program")} checked, ${r.verified || 0} verified, ${r.new_programs || 0} new.`
}

function Runs({ runs }: { runs: Run[] }) {
  const { shown, more } = useShowAll(runs, 7)
  return (
    <Panel title="Research runs" aside={runs.length ? plural(runs.length, "run") : undefined}>
      {runs.length === 0
        ? <Empty>The first research run will appear here with its searches, sources and results.</Empty>
        : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Started</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead className="text-right">Programs checked</TableHead>
                  <TableHead className="text-right">Verified</TableHead>
                  <TableHead className="text-right">New</TableHead>
                  <TableHead>Issues</TableHead>
                  <TableHead><span className="sr-only">Open</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((r) => {
                  const report = r.report || {}
                  const issues = (report.errors || []).length
                  return (
                    <TableRow key={r.id}>
                      <TableCell className="font-semibold whitespace-nowrap"><time dateTime={r.started_at}>{stamp(r.started_at)}</time></TableCell>
                      <TableCell><Tag tone={runTone(r.state)}>{humanState(r.state)}</Tag></TableCell>
                      <TableCell className="text-right tabular-nums">{report.candidates_discovered || 0}</TableCell>
                      <TableCell className="text-right tabular-nums">{report.verified || 0}</TableCell>
                      <TableCell className="text-right tabular-nums">{report.new_programs || 0}</TableCell>
                      <TableCell className={issues ? "font-medium whitespace-nowrap" : "whitespace-nowrap text-muted-foreground"}>{issues ? plural(issues, "issue") : "No issues"}</TableCell>
                      <TableCell className="text-right">
                        <Button size="lg" variant="ghost" asChild>
                          <a href={`/run/${encodeURIComponent(r.id)}`} aria-label={`See the run of ${stamp(r.started_at)}`}>See the run<ChevronRight aria-hidden="true" /></a>
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      {more}
    </Panel>
  )
}

export function ActivityPage() {
  const state = useLoad(() => api<Dashboard>("/api/dashboard"))
  const { toast } = useFeedback()
  const [running, setRunning] = useState(false)

  // The old sidebar's "Run research now". It starts web research on the PC; nothing is sent anywhere.
  const runNow = async () => {
    setRunning(true)
    try {
      await api("/api/run-now", {})
      await state.reload()
      toast("Research request saved. The run appears here when it finishes.")
    } catch (e) { toast(e instanceof Error ? e.message : "Unable to complete this action.", true) } finally { setRunning(false) }
  }

  return (
    <Shell active="Agents" tab="/activity" title="Activity">
      <LoadGate state={state}>
        {(dash) => {
          const runs: Run[] = dash.agent_activity || []
          const last = runs[0]
          const paused = isFailed(last) && knownCause(last)
          return (
            <>
              <PageHead title="Activity" line={stateLine(last)}>
                {paused && <Button size="lg" asChild><a href={`/run/${encodeURIComponent(last.id)}`}>See what failed</a></Button>}
                <Button size="lg" variant={paused ? "outline" : "default"} disabled={paused || running} title={paused ? RUN_PAUSED : undefined} onClick={runNow}>
                  {running ? "Starting…" : isFailed(last) && !paused ? "Run it again" : "Run research now"}
                </Button>
              </PageHead>
              <Runs runs={runs} />
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/activity": () => <ActivityPage /> } }
