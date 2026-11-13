import { Empty, Fact, LoadGate, PageHead, Panel, Row, Rows, Tag, useLoad } from "@/components/app/page"
import { errorCause, errorProgram, errorState, fixedCause, humanState, knownCause, plainKey, runTone, runUsage, type Run } from "@/lib/agents"
import { api } from "@/lib/api"
import { day, plural, stamp } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"
import { Disclosure } from "@/pages/Decisions"

// What the agent does next about an unfinished item (old errorView)
const errorHint = (state: string) =>
  state === "ELIGIBILITY_UNKNOWN" ? "Confirm company facts before relying on eligibility."
    : state === "SOURCE_UNAVAILABLE" ? "The agent retries this on a later run." : ""

function Issues({ run }: { run: Run }) {
  const errors = run.report?.errors || []
  return (
    <Panel title="Issues and unfinished research" aside={errors.length ? plural(errors.length, "issue") : undefined}>
      {errors.length === 0
        ? <Empty>No issues recorded.</Empty>
        : (
          <>
          {/* A known cause is not a dead end: say what happens next and that nothing here needs Bao */}
          {knownCause(run) && (
            <div className="rounded-lg bg-secondary px-4 py-3">
              <p className="max-w-[70ch] text-base"><strong className="font-semibold">What happens next.</strong> Running it again stops the same way, so research stays paused until the research agent's size limit is changed. Ask Claude to fix it; nothing on this page needs you.</p>
            </div>
          )}
          {fixedCause(run) && (
            <div className="rounded-lg bg-secondary px-4 py-3">
              <p className="max-w-[70ch] text-base"><strong className="font-semibold">Fixed Nov 12.</strong> A new run now stays within the limit.</p>
              <a href="/activity" className="inline-flex min-h-11 items-center rounded-md font-medium text-primary underline underline-offset-4 hover:no-underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">Run it again from Activity</a>
            </div>
          )}
          <Rows label="Issues and unfinished research">
            {errors.map((e, i) => {
              const st = errorState(e)
              const note = [errorProgram(e), errorHint(st)].filter(Boolean).join(" · ")
              return (
                <Row key={i} title={plainKey(st || "Research incomplete")}
                  line={<>{errorCause(e)}{note && <span className="block text-sm">{note}</span>}</>} />
              )
            })}
          </Rows>
          </>
        )}
    </Panel>
  )
}

function Details({ run }: { run: Run }) {
  const report = run.report || {}
  const queries = report.queries_used || []
  const sources = report.sources_checked || []
  const usage = runUsage(run)
  const tokens = usage.tokens || {}
  return (
    <Panel title="How it ran">
      <div className="flex flex-col">
        <Disclosure summary={`Searches used (${queries.length})`}>
          {queries.length
            ? <ul className="flex list-disc flex-col gap-1 pl-5 text-base">{queries.map((q, i) => <li key={i}>{typeof q === "string" ? q : q.query}</li>)}</ul>
            : <p className="text-base text-muted-foreground">No searches were recorded.</p>}
        </Disclosure>
        <Disclosure summary={`Sources checked (${sources.length})`}>
          {sources.length
            ? (
              <ul className="flex flex-col">
                {sources.map((u, i) => (
                  <li key={i}>
                    <a href={u} target="_blank" rel="noopener noreferrer" className="flex min-h-11 items-center rounded-md text-base break-all text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">{u}</a>
                  </li>
                ))}
              </ul>
            )
            : <p className="text-base text-muted-foreground">No sources were recorded.</p>}
        </Disclosure>
        <Disclosure summary="Usage">
          <div className="grid gap-4 sm:grid-cols-2">
            <Fact label="Ran on">{usage.runner === "codex_chatgpt" ? "Your existing ChatGPT sign-in" : usage.research_runner || usage.runner || "Not recorded"}</Fact>
            <Fact label="API key">{usage.api_key_used === false ? "Not used" : "Not recorded"}</Fact>
            <Fact label="Tokens">{tokens.input_tokens ?? "Unknown"} input · {tokens.output_tokens ?? "Unknown"} output</Fact>
            <Fact label="API cost">{usage.model_api_cost === null ? "Not reported; this run uses your ChatGPT plan allowance" : usage.model_api_cost ?? "Unknown"}</Fact>
          </div>
        </Disclosure>
        <Disclosure summary="Exact run data">
          <pre className="max-h-[32rem] max-w-full overflow-auto rounded-lg bg-secondary p-4 font-mono text-sm break-words whitespace-pre-wrap text-muted-foreground">{JSON.stringify(report, null, 2)}</pre>
        </Disclosure>
      </div>
    </Panel>
  )
}

export function RunPage({ id }: { id: string }) {
  const state = useLoad(() => api<Run>("/api/run/" + encodeURIComponent(id)), [id])
  const crumb = state.data ? day(state.data.started_at) : "Research run"
  return (
    <Shell active="Agents" tab="/activity" crumb={crumb} title="Research run">
      <LoadGate state={state}>
        {(r) => {
          const report = r.report || {}
          const found = [
            ["Programs checked", report.candidates_discovered || 0], ["Verified", report.verified || 0],
            ["New", report.records_created || 0], ["Duplicates merged", report.duplicates_removed || 0],
          ] as [string, number][]
          return (
            <>
              <PageHead title="Research run"
                line={<span className="flex flex-wrap items-center gap-3"><Tag tone={runTone(r.state)}>{humanState(r.state)}</Tag><time dateTime={r.started_at}>{stamp(r.started_at)}</time></span>} />
              <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="flex flex-col gap-5">
                  {/* A strip of four zeros says nothing; it shows only when the run found something. */}
                  {found.some(([, n]) => n > 0) && (
                    <Panel title="What it found">
                      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        {found.map(([label, n]) => <Fact key={label} label={label}><span className="tabular-nums">{n}</span></Fact>)}
                      </div>
                    </Panel>
                  )}
                  <Issues run={r} />
                </div>
                <Details run={r} />
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/run/": (id) => <RunPage id={id} /> } }
