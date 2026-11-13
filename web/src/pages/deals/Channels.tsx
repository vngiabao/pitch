import { useFeedback } from "@/components/app/feedback"
import { Fact, Panel } from "@/components/app/page"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api } from "@/lib/api"
import { day, plural, usd } from "@/lib/format"
import { channelLabel, type ChannelEntry } from "@/lib/growth"

import { Act, In, More, Pick, useDesk, useSubmit } from "./parts"

const DASH = "–"

function Tile({ label, value, sub, money }: { label: string; value: string | number | null | undefined; sub?: string; money?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <Fact label={label} tone={money && value != null ? "money" : undefined}><span className="text-xl tabular-nums">{value == null ? DASH : value}</span></Fact>
      {sub && <span className="text-sm text-muted-foreground">{sub}</span>}
    </div>
  )
}

// Channel math: what each channel did each week, measured from Bao's own entries so the numbers can go in a pitch.
export function ChannelsPanel() {
  const { b, act } = useDesk()
  const { confirm } = useFeedback()
  const submit = useSubmit()
  const m = b.math, t = m.totals, f = m.deck_formula

  const remove = async (e: ChannelEntry) => {
    const ok = await confirm({
      title: "Remove this week’s entry?",
      body: `${channelLabel(b.channel_words, e.channel)}, week of ${day(e.week_start)}. The measured numbers change with it.`,
      action: "Remove entry", danger: true,
    })
    if (ok) await act(`entry:${e.id}`, () => api("/api/channel-entry-delete", { id: e.id }), "Removed.")
  }

  return (
    <Panel id="channels" title="Channel math" className="scroll-mt-4"
      aside={t.weeks ? `${plural(t.weeks, "week")} recorded, ${t.from === t.to ? day(t.from) : `${day(t.from)} to ${day(t.to)}`}` : "Nothing recorded yet"}>
      <p className="max-w-[70ch] text-base text-muted-foreground">
        Record what each channel did each week. These numbers are measured from your entries, with their dates, so they can go in a pitch as measured numbers.
      </p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3 xl:grid-cols-5">
        <Tile label="Visits" value={t.visits} />
        <Tile label="Signups" value={t.signups} sub={t.signup_rate !== null ? `${t.signup_rate}% of visits` : ""} />
        <Tile label="Purchasing families" value={t.purchases} sub={t.conversion !== null ? `${t.conversion}% of visits` : ""} />
        <Tile label="Cost per purchasing family" money value={t.cost_per_family !== null ? usd(t.cost_per_family) : null} sub={t.spend_usd ? `${usd(t.spend_usd)} spent` : "No spend recorded"} />
        <Tile label="Revenue" money value={t.revenue_usd ? usd(t.revenue_usd) : null} sub={t.revenue_usd && t.revenue_per_dollar !== null ? `${usd(t.revenue_per_dollar)} per $1 spent` : ""} />
      </div>
      <div className="grid gap-x-8 gap-y-3 rounded-lg bg-secondary px-4 py-3 text-base md:grid-cols-2">
        <p className="flex flex-col gap-0.5">
          <span className="text-sm text-muted-foreground">The deck’s example</span>
          <span className="font-semibold">{f.visits.toLocaleString("en-US")} visits × {f.rate * 100}% = {f.families} families</span>
        </p>
        <p className="flex flex-col gap-0.5">
          <span className="text-sm text-muted-foreground">Measured so far</span>
          {t.visits ? (
            <>
              <span className="font-semibold">{t.visits.toLocaleString("en-US")} visits × {t.conversion ?? 0}% = {t.purchases} families</span>
              {f.visits_needed_for_30 ? <span>At that rate, 30 families need about <span className="font-semibold">{f.visits_needed_for_30.toLocaleString("en-US")} visits</span>.</span> : null}
            </>
          ) : <span>Record the first week to replace the example.</span>}
        </p>
      </div>
      {m.channels.length > 0 && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Channel</TableHead>
                <TableHead className="text-right">Visits</TableHead>
                <TableHead className="text-right">Signups</TableHead>
                <TableHead className="text-right">Families</TableHead>
                <TableHead className="text-right">Conversion</TableHead>
                <TableHead className="text-right">Spend</TableHead>
                <TableHead className="text-right">Cost per family</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {m.channels.map((c) => (
                <TableRow key={c.label}>
                  <TableCell>
                    <span className="flex flex-col">
                      <span className="font-medium">{c.label}</span>
                      <span className="text-sm text-muted-foreground">{plural(c.weeks, "week")}</span>
                    </span>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{c.visits}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.signups}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.purchases}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.conversion === null ? DASH : `${c.conversion}%`}</TableCell>
                  <TableCell className="text-right tabular-nums text-money">{c.spend_usd ? usd(c.spend_usd) : <span className="text-foreground">{DASH}</span>}</TableCell>
                  <TableCell className="text-right tabular-nums text-money">{c.cost_per_family === null ? <span className="text-foreground">{DASH}</span> : usd(c.cost_per_family)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <More label="Record a week" defaultOpen={!m.entries.length} className="border-t pt-4">
        <form className="flex flex-col gap-4" onSubmit={submit("entry:add", "/api/channel-entry", {}, "Week saved.")}>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Pick label="Channel" name="channel" options={Object.entries(b.channel_words)} />
            <In label="Week of" name="week_start" type="date" />
            <In label="Visits" name="visits" type="number" min={0} defaultValue={0} />
            <In label="Signups" name="signups" type="number" min={0} defaultValue={0} />
            <In label="Purchases" name="purchases" type="number" min={0} defaultValue={0} />
            <In label="Spend (USD)" name="spend_usd" type="number" min={0} step="0.01" defaultValue={0} />
            <In label="Revenue (USD)" name="revenue_usd" type="number" min={0} step="0.01" defaultValue={0} />
            <In label="Note" name="note" maxLength={300} placeholder="e.g. gift guide ran Tuesday" />
          </div>
          <Act k="entry:add" type="submit" className="self-start">Save week</Act>
        </form>
      </More>
      {m.entries.length > 0 && (
        <More label={`Entries (${m.entries.length})`}>
          <ul className="flex flex-col">
            {m.entries.slice(0, 20).map((e) => (
              <li key={e.id} className="flex min-h-16 flex-wrap items-center gap-x-4 gap-y-2 border-t py-3 first:border-t-0">
                <span className="flex min-w-0 flex-1 basis-64 flex-col gap-0.5">
                  <span className="text-base"><span className="font-semibold">{channelLabel(b.channel_words, e.channel)}</span> · week of {day(e.week_start)}</span>
                  <span className="max-w-[70ch] text-base text-muted-foreground">
                    {e.visits} visits · {e.signups} signups · {e.purchases} purchases · {usd(e.spend_usd)} spent
                    {e.revenue_usd ? ` · ${usd(e.revenue_usd)} revenue` : ""}{e.note ? ` · ${e.note}` : ""}
                  </span>
                </span>
                <Act k={`entry:${e.id}`} busyLabel="Removing…" onClick={() => remove(e)}>Remove</Act>
              </li>
            ))}
          </ul>
        </More>
      )}
    </Panel>
  )
}
