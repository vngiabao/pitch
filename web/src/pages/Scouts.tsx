import { Fragment, useState } from "react"

import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useFeedback } from "@/components/app/feedback"
import { LoadGate, PageHead, Panel, Tag, useLoad, Disclosure } from "@/components/app/page"
import { lastRunWords, missedSchedule, scheduleWords, schedulesPaused, type Scout, type Scouts } from "@/lib/agents"
import { api } from "@/lib/api"
import { plural, prettyKey, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

const linkClass = "font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"

// The scout's name opens what it hunts, its schedule and its searches. The schedule is said here and nowhere else.
function About({ name, hunts, schedule, searches, note }: { name: string; hunts: string; schedule: string; searches?: string; note?: string }) {
  return (
    <Disclosure label={<span className="font-semibold">{name}</span>}>
      <div className="flex max-w-[60ch] flex-col gap-1 pl-6 text-base whitespace-normal text-muted-foreground">
        <p>{hunts}</p>
        <p>Schedule: {schedule}</p>
        {searches && <p>Searches: {searches}</p>}
        {note && <p>{note}</p>}
      </div>
    </Disclosure>
  )
}

// When the next run is. The server sends the calendar's next slot even when scheduled runs are off, so the page
// only shows it for a scout that has kept its schedule; otherwise it says the run is paused.
function NextRun({ s, paused }: { s: Scout; paused: boolean }) {
  if (s.running) return <Tag tone="review">Running now</Tag>
  if (!s.next_run) return <span className="text-muted-foreground">On request</span>
  if (paused || missedSchedule(s.schedule, s.last_run)) return <Tag>Paused</Tag>
  return <time dateTime={s.next_run}>{stamp(s.next_run)}</time>
}

export function ScoutsPage() {
  const state = useLoad(() => api<Scouts>("/api/scouts"))
  const { toast } = useFeedback()
  const [busy, setBusy] = useState<string | null>(null)

  const run = async (s: Scout) => {
    setBusy(s.key)
    try {
      await api("/api/scout-run", { key: s.key })
      await state.reload()
      toast("Scout started. Results appear on its page in about 15 minutes.")
    } catch (e) { toast(e instanceof Error ? e.message : "Unable to complete this action.", true) } finally { setBusy(null) }
  }

  return (
    <Shell active="Agents" tab="/scouts" title="Scouts">
      <LoadGate state={state}>
        {(r) => {
          const groups = [...new Set(r.scouts.map((s) => s.group))]
          const running = r.scouts.filter((s) => s.running).length
          const paused = schedulesPaused(r.scouts)
          const b = r.broad_sweep
          return (
            <>
              <PageHead title="Scouts"
                line={`${plural(r.scouts.length, "scout")}, ${running ? `${running} running now` : "none running"}.${paused ? " Scheduled runs are paused." : ""}`} />
              <Panel title="All scouts">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Scout</TableHead>
                      <TableHead>Results land in</TableHead>
                      <TableHead>Last result</TableHead>
                      <TableHead>Next run</TableHead>
                      <TableHead><span className="sr-only">Run</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {groups.map((g) => (
                      <Fragment key={g}>
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={5} className="pt-5 pb-1 text-sm font-medium text-muted-foreground">{g}</TableCell>
                        </TableRow>
                        {r.scouts.filter((s) => s.group === g).map((s) => (
                          <TableRow key={s.key}>
                            <TableCell className="min-w-64 py-1 align-top">
                              <About name={s.name} hunts={s.hunts} schedule={scheduleWords(s.schedule)}
                                searches={s.families?.length ? s.families.map((f) => prettyKey(f)).join(", ") : undefined}
                                note={s.key === "win" ? "It runs from a program’s page: open a program and press Research how to win." : undefined} />
                            </TableCell>
                            <TableCell className="py-1 align-top"><a href={s.lands_url} className={`flex min-h-11 items-center ${linkClass}`}>{s.lands_label}</a></TableCell>
                            <TableCell className="py-1 align-top whitespace-nowrap"><span className="flex min-h-11 items-center">{lastRunWords(s.last_run)}</span></TableCell>
                            <TableCell className="py-1 align-top whitespace-nowrap"><span className="flex min-h-11 items-center"><NextRun s={s} paused={paused} /></span></TableCell>
                            <TableCell className="py-1 text-right align-top">
                              {s.key === "win"
                                ? <Button size="lg" variant="outline" asChild><a href="/opportunities">Pick a program</a></Button>
                                : (
                                  <Button size="lg" variant="outline" disabled={s.running || busy === s.key} onClick={() => run(s)} aria-label={`Run ${s.name} now`}>
                                    {s.running ? "Running…" : busy === s.key ? "Starting…" : "Run now"}
                                  </Button>
                                )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </Fragment>
                    ))}
                    {b && (
                      <>
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={5} className="pt-5 pb-1 text-sm font-medium text-muted-foreground">Safety net</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="min-w-64 py-1 align-top"><About name={b.name} hunts={b.hunts} schedule={scheduleWords(b.schedule)} /></TableCell>
                          <TableCell className="py-1 align-top"><a href="/activity" className={`flex min-h-11 items-center ${linkClass}`}>All research runs</a></TableCell>
                          <TableCell className="py-1 align-top whitespace-nowrap"><span className="flex min-h-11 items-center">{lastRunWords(b.last_run)}</span></TableCell>
                          <TableCell className="py-1 align-top whitespace-nowrap">
                            <span className="flex min-h-11 items-center">
                              {b.running ? <Tag tone="review">Running now</Tag> : paused || missedSchedule(b.schedule, b.last_run) ? <Tag>Paused</Tag> : <span className="text-muted-foreground">On schedule</span>}
                            </span>
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      </>
                    )}
                  </TableBody>
                </Table>
              </Panel>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/scouts": () => <ScoutsPage /> } }
