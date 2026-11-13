import { Panel, Tag } from "@/components/app/page"
import { api } from "@/lib/api"
import { day } from "@/lib/format"
import { threadsWords, type Quote, type Voice } from "@/lib/growth"

import { Act, ExtLink, More, Note, SubHead, Words, useDesk } from "./parts"

const QuoteLink = ({ q }: { q?: Quote | null }) => (q?.url ? <ExtLink href={q.url}>{q.who || "thread"}</ExtLink> : null)

function Said({ q }: { q: Quote }) {
  return (
    <li className="flex flex-col">
      <span className="max-w-[70ch] text-base">“{q.text}”</span>
      <QuoteLink q={q} />
    </li>
  )
}

// What families say online: public threads read by the Customer Voice Scout. Themes are counted by thread and
// every quote keeps its link. Evidence about the market, never about A Story's own customers.
export function VoicePanel({ v }: { v: Voice }) {
  const { act } = useDesk()
  const r = v.report
  const m = v.movement || {}
  const research = (
    <Act k="voice:research" busyLabel="Starting…" disabled={v.researching} className="self-start"
      onClick={() => act("voice:research", () => api("/api/scout-run", { key: "customer_voice" }), "Scout started. Results appear on its page in about 15 minutes.")}>
      {v.researching ? "Researching…" : r ? "Research again" : "Research now"}
    </Act>
  )
  const read = v.run_on ? `Read ${day(v.run_on)}${(v.runs || 0) > 1 ? ` · ${v.runs} weeks kept` : ""}` : "Not read yet"
  const mark = (theme: string) => {
    const k = theme.toLowerCase()
    if ((m.new || []).some((x) => x.toLowerCase() === k)) return "new"
    const up = (m.up || []).find((x) => x.theme.toLowerCase() === k)
    if (up) return `up from ${up.from}`
    const down = (m.down || []).find((x) => x.theme.toLowerCase() === k)
    return down ? `down from ${down.from}` : ""
  }

  if (!r) return (
    <Panel id="families-say" title="What families say online" aside={read} className="scroll-mt-4">
      {v.researching
        ? <Note lead="Reading the threads now.">Themes, quotes and links land here in about 15 minutes.</Note>
        : <Note lead="Nothing read yet.">Press Research now, or wait for Thursday 8:15 AM Eastern.</Note>}
      {research}
    </Panel>
  )

  const reach = [r.threads_read ? `${r.threads_read} threads read` : "", r.places_read.length ? `across ${r.places_read.join(", ")}` : ""].filter(Boolean).join(" ")
  const since = v.previous_on ? `Since ${day(v.previous_on)}: ${v.movement_words || ""}` : v.movement_words || ""
  return (
    <Panel id="families-say" title="What families say online" aside={read} className="scroll-mt-4">
      <p className="max-w-[70ch] text-base text-muted-foreground">{[reach ? reach + "." : "", since].filter(Boolean).join(" ")}</p>
      <ol className="flex flex-col">
        {r.themes.map((t) => {
          const moved = mark(t.theme)
          return (
            <li key={t.theme} className="flex flex-col gap-2 border-t py-3 first:border-t-0">
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <span className="text-base font-semibold">{t.theme}</span>
                <span className="flex items-center gap-2 text-sm text-muted-foreground">{threadsWords(t.threads)}{moved && <Tag>{moved}</Tag>}</span>
              </div>
              {t.summary && <p className="max-w-[70ch] text-base text-muted-foreground">{t.summary}</p>}
              {t.quotes.length > 0 && <ul className="flex flex-col gap-1">{t.quotes.slice(0, 2).map((q, i) => <Said key={i} q={q} />)}</ul>}
            </li>
          )
        })}
      </ol>
      {(r.tried.length > 0 || r.objections.length > 0 || r.willing_to_pay.length > 0 || r.words.length > 0) && (
        <More label="What they tried, objections and their words" className="border-t pt-4">
          {r.tried.length > 0 && (
            <div className="flex flex-col gap-2">
              <SubHead>What they tried</SubHead>
              <ul className="flex flex-col gap-3">
                {r.tried.map((x) => (
                  <li key={x.what} className="flex flex-col gap-0.5">
                    <span className="text-base"><span className="font-semibold">{x.what}</span>{x.threads ? ` · ${threadsWords(x.threads)}` : ""}</span>
                    {x.said && <span className="max-w-[70ch] text-base text-muted-foreground">{x.said}{x.quote ? ` “${x.quote.text}”` : ""}</span>}
                    {x.said && <QuoteLink q={x.quote} />}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {r.objections.length > 0 && (
            <div className="flex flex-col gap-2">
              <SubHead>Objections</SubHead>
              <ul className="flex flex-col gap-3">
                {r.objections.map((o) => (
                  <li key={o.objection} className="flex flex-col gap-0.5">
                    <span className="text-base"><span className="font-semibold">{o.objection}</span>{o.threads ? ` · ${threadsWords(o.threads)}` : ""}</span>
                    {o.quote && <span className="max-w-[70ch] text-base text-muted-foreground">“{o.quote.text}”</span>}
                    <QuoteLink q={o.quote} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {r.willing_to_pay.length > 0 && (
            <div className="flex flex-col gap-2">
              <SubHead>What they say they would pay</SubHead>
              <ul className="flex flex-col gap-3">
                {r.willing_to_pay.map((x, i) => (
                  <li key={i} className="flex flex-col gap-0.5">
                    <span className="max-w-[70ch] text-base">“{x.said}”</span>
                    {x.url && <ExtLink href={x.url}>Source</ExtLink>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Words words={r.words} />
        </More>
      )}
      <More label={r.sources.length ? `Sources and how this is used (${r.sources.length})` : "How this is used"}>
        <p className="max-w-[70ch] text-base text-muted-foreground">
          Adult children and caregivers on Reddit, X, Quora and the genealogy and senior-care forums, read by the Customer Voice Scout every Thursday morning. Public threads only; nothing here is about A Story.
        </p>
        <p className="max-w-[70ch] text-base text-muted-foreground">
          The pitch agents read these themes as evidence about the market; the Campaign Planner and the field-day script get the objections and the words. A count from here stays out of your pitch unless it is quoted with its link.
        </p>
        {r.sources.length > 0 && (
          <ul className="flex flex-col">
            {r.sources.slice(0, 30).map((u) => <li key={u} className="min-w-0 break-all"><ExtLink href={u}>{u.replace(/^https?:\/\//, "").slice(0, 80)}</ExtLink></li>)}
          </ul>
        )}
      </More>
      {research}
    </Panel>
  )
}
