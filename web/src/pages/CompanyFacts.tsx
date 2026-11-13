import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Empty, LoadGate, PageHead, Panel, useLoad, evenBottoms } from "@/components/app/page"
import { api } from "@/lib/api"
import { groupFacts, noDash, type Claim, type Dashboard, type FactGroup } from "@/lib/company"
import { day, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"
import { Disclosure } from "@/pages/Decisions"

// A stored record is often a JSON object; show it indented so it can be read.
function recordText(body: string) {
  try { const v = JSON.parse(body); return typeof v === "object" && v ? JSON.stringify(v, null, 2) : body } catch { return body }
}

// One group of facts. The panel says once when its facts were verified; a fact says so only when its day differs.
// Name parts already shown in the panel wait behind "Show all".
function Group({ g }: { g: FactGroup }) {
  const [all, setAll] = useState(false)
  const hidden = g.facts.filter((f) => f.minor).length
  const shown = all ? g.facts : g.facts.filter((f) => !f.minor)
  return (
    <Panel title={g.title} aside={g.verified ? `Verified ${g.verified}` : undefined}>
      <dl className="flex flex-col">
        {shown.map((f) => (
          <div key={f.key} className="grid gap-x-4 gap-y-0.5 border-t py-3 first:border-t-0 first:pt-0 last:pb-0 sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)]">
            <dt className="text-sm text-muted-foreground sm:pt-0.5">{f.label}</dt>
            <dd className="text-base font-medium break-words">
              {f.value}
              {f.verified && <span className="block text-sm font-normal text-muted-foreground">Verified {f.verified}</span>}
            </dd>
          </div>
        ))}
      </dl>
      {hidden > 0 && !all && <Button size="lg" variant="outline" className="self-start" onClick={() => setAll(true)}>Show all {g.facts.length}</Button>}
    </Panel>
  )
}

function Records({ claims }: { claims: Claim[] }) {
  if (!claims.length) return null
  return (
    <Panel title="Original approved records" aside={plural(claims.length, "record")}>
      <Disclosure summary={`Show the ${plural(claims.length, "record")} as they were approved`}>
        <ul className="flex flex-col">
          {claims.map((c, i) => (
            <li key={i} className="flex flex-col gap-2 border-t py-4 first:border-t-0 first:pt-0">
              <span className="text-base font-semibold">{noDash(c.label)}</span>
              <pre className="max-w-full overflow-x-auto rounded-lg bg-secondary p-4 font-sans text-sm break-words whitespace-pre-wrap text-muted-foreground">{recordText(c.body)}</pre>
            </li>
          ))}
        </ul>
      </Disclosure>
    </Panel>
  )
}

export function CompanyFactsPage() {
  const state = useLoad(() => api<Dashboard>("/api/dashboard"))
  return (
    <Shell active="Company" tab="/memory" title="Company facts">
      <LoadGate state={state}>
        {(dash) => {
          const groups = groupFacts(dash.company_memory.attributes || {})
          const claims = dash.company_memory.canonical_claims || []
          const count = groups.reduce((n, g) => n + g.facts.length, 0)
          // Two columns: Company and Funding on the left, Founders and Product on the right, anything else under the shorter.
          const left = groups.filter((g) => g.title === "Company" || g.title === "Funding")
          const right = groups.filter((g) => g.title === "Founders" || g.title === "Product and market")
          const size = (col: FactGroup[]) => col.reduce((n, g) => n + g.facts.length, 0)
          for (const g of groups) if (!left.includes(g) && !right.includes(g)) (size(left) <= size(right) ? left : right).push(g)
          const checked = Object.values(dash.company_memory.attributes || {}).map((f) => f.last_verified || "").sort().pop()
          return (
            <>
              <PageHead title="Company facts"
                line={count ? `${plural(count, "fact")}${checked ? `, last verified ${day(checked)}` : ""}.` : "No facts are approved yet."}>
                <Button size="lg" variant="outline" asChild><a href="/decisions">Change a fact in Decisions</a></Button>
              </PageHead>
              {claims.length === 0 && (
                <Panel title="Company eligibility needs confirmation">
                  <p className="max-w-[70ch] text-base text-muted-foreground">
                    No company facts have been approved yet. Programs can still be verified, but whether A Story fits them stays open until you confirm the facts.
                  </p>
                </Panel>
              )}
              {groups.length === 0
                ? <Panel title="Approved profile"><Empty>No structured eligibility facts are approved yet.</Empty></Panel>
                : (
                  <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-2">
                    {[left, right].map((col, i) => col.length > 0 && (
                      <div key={i} className="flex min-w-0 flex-col gap-5">{col.map((g) => <Group key={g.title} g={g} />)}</div>
                    ))}
                  </div>
                )}
              <Records claims={claims} />
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/memory": () => <CompanyFactsPage /> } }
