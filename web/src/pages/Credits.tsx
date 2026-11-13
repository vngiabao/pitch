import { useState, type FormEvent, type ReactNode } from "react"
import { ChevronDown, ExternalLink, Plus } from "lucide-react"

import { useFeedback } from "@/components/app/feedback"
import { Disclosure, Empty, Fact, Field, LoadGate, PageHead, Panel, Tag, useHashScroll, useLoad } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { day, plural } from "@/lib/format"
import { CREDIT_STATE_WORDS, LINK, cost, coverChoices, creditDue, creditTone, loadCredits, type Credit, type Stack, type StackItem } from "@/lib/money"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { ProgramMark, Shell } from "@/shell"

// The old forms sent every field as a string (Object.fromEntries(new FormData)); the server expects that.
const formBody = (f: HTMLFormElement) => Object.fromEntries(new FormData(f)) as Record<string, string>
const message = (e: unknown) => (e instanceof Error ? e.message : "Unable to complete this action.")

// ---------- The credits: one row each, the detail behind the row ----------
function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="max-w-[60ch] text-base">{children}</dd>
    </div>
  )
}

function CreditRows({ c, open, onToggle, onEdit }: { c: Credit; open: boolean; onToggle: () => void; onEdit: (c: Credit) => void }) {
  const due = creditDue(c)
  const dated = c.ends_on && !["DONE", "ACTIVATE", "NEEDS_DATES"].includes(c.level)
  return (
    <>
      <TableRow id={c.id} className={cn(open && "border-b-0")}>
        <TableCell className="py-1">
          <button type="button" aria-expanded={open} aria-controls={`${c.id}-detail`} onClick={onToggle}
            className="flex min-h-11 items-center gap-2 rounded-md text-left text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
            <ChevronDown className={cn("size-4 shrink-0 transition-transform duration-150 motion-reduce:transition-none", open && "rotate-180")} aria-hidden="true" />
            <ProgramMark name={c.provider} />{c.provider}
          </button>
        </TableCell>
        <TableCell className="py-2"><span className="line-clamp-2 text-base">{c.allowance || <span className="text-muted-foreground">Amount not published</span>}</span></TableCell>
        <TableCell className="py-1 whitespace-nowrap">
          {dated
            ? <span className={cn("text-base", due && "font-semibold text-deadline")}>{day(c.ends_on)}{due ? ` · ${plural(c.days_left ?? 0, "day")} left` : ""}</span>
            : <Tag tone={creditTone(c)}>{c.label}</Tag>}
        </TableCell>
        <TableCell className="py-2">
          {c.balance_note
            ? <span className="flex flex-col"><span className="line-clamp-2 text-base">{c.balance_note}</span><span className="text-sm text-muted-foreground">Checked {day(c.balance_checked_on)}{c.balance_stale ? ", check again" : ""}</span></span>
            : <span className="text-sm text-muted-foreground">Not checked yet</span>}
        </TableCell>
        <TableCell className="py-1 text-right">
          <Button size="lg" variant="outline" onClick={() => onEdit(c)} aria-label={`Update ${c.provider} dates and balance`}>Update</Button>
        </TableCell>
      </TableRow>
      {open && (
        <TableRow id={`${c.id}-detail`} className="hover:bg-transparent">
          <TableCell colSpan={5} className="pt-0 pb-5 pl-11">
            <div className="flex flex-col gap-3">
              <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2 xl:grid-cols-3">
                <Detail label="What you get">{c.allowance || "Amount not published"}</Detail>
                <Detail label="Covers">{c.covers || "Not published"}</Detail>
                <Detail label="After it ends">{c.after_expiry || "Not published"}</Detail>
                <Detail label="Started">{c.started_on ? day(c.started_on) : "Not set yet"}</Detail>
                <Detail label="Ends">{c.ends_on ? day(c.ends_on) : c.term_months ? `${c.term_months} months after the start date` : "Not set yet"}</Detail>
                {c.notes && <Detail label="Notes">{c.notes}</Detail>}
              </dl>
              {c.program_url && (
                <a href={c.program_url} target="_blank" rel="noopener noreferrer" className={cn(LINK, "gap-1.5 self-start")}>
                  Program page<ExternalLink className="size-4" aria-hidden="true" />
                </a>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

function CreditTable({ credits, onEdit }: { credits: Credit[]; onEdit: (c: Credit) => void }) {
  const [open, setOpen] = useState<string[]>([])
  const toggle = (id: string) => setOpen((o) => (o.includes(id) ? o.filter((x) => x !== id) : [...o, id]))
  return (
    <Table className="min-w-[60rem] table-fixed">
      <colgroup><col className="w-60" /><col /><col className="w-56" /><col className="w-60" /><col className="w-32" /></colgroup>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Provider</TableHead><TableHead>What you get</TableHead><TableHead>Ends</TableHead><TableHead>Balance</TableHead>
          <TableHead><span className="sr-only">Update</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>{credits.map((c) => <CreditRows key={c.id} c={c} open={open.includes(c.id)} onToggle={() => toggle(c.id)} onEdit={onEdit} />)}</TableBody>
    </Table>
  )
}

// ---------- The two forms ----------
function CreditDialog({ credit, onClose, onSaved }: { credit: Credit | null; onClose: () => void; onSaved: () => Promise<unknown> }) {
  const { toast } = useFeedback()
  const [busy, setBusy] = useState(false)
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!credit) return
    setBusy(true)
    try {
      await api("/api/credit", { id: credit.id, ...formBody(e.currentTarget) })
      await onSaved()
      toast("Credit details saved.")
      onClose()
    } catch (err) { toast(message(err), true) } finally { setBusy(false) }
  }
  return (
    <Dialog open={!!credit} onOpenChange={(o) => { if (!o && !busy) onClose() }}>
      {credit && (
        <DialogContent className="max-h-[90svh] overflow-y-auto text-base sm:max-w-[40rem]">
          <form onSubmit={save} className="grid gap-4">
            <DialogHeader>
              <DialogTitle className="text-xl">{credit.provider} credits</DialogTitle>
              <DialogDescription className="text-base">The end date is worked out from the start date unless the award email states one.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Start date" htmlFor="credit-start"><Input id="credit-start" type="date" name="started_on" defaultValue={credit.started_on || ""} /></Field>
              <Field label="End date, if the email states one" htmlFor="credit-end"><Input id="credit-end" type="date" name="expires_on" defaultValue={credit.expires_on || ""} /></Field>
              <Field label="Balance left" htmlFor="credit-balance"><Input id="credit-balance" name="balance_note" maxLength={300} defaultValue={credit.balance_note || ""} placeholder="e.g. 6.2M of 8M units this month" /></Field>
              <Field label="Account email" htmlFor="credit-email"><Input id="credit-email" type="email" name="account_email" maxLength={200} defaultValue={credit.account_email || ""} /></Field>
              <Field label="Status" htmlFor="credit-state">
                <NativeSelect id="credit-state" name="state" defaultValue={credit.state} className="w-full">
                  {CREDIT_STATE_WORDS.map(([v, l]) => <NativeSelectOption key={v} value={v}>{l}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
            </div>
            <Field label="Notes" htmlFor="credit-notes"><Textarea id="credit-notes" name="notes" maxLength={2000} defaultValue={credit.notes || ""} className="text-base" /></Field>
            <DialogFooter className="gap-2">
              <Button type="button" size="lg" variant="outline" onClick={onClose} disabled={busy}>Cancel</Button>
              <Button type="submit" size="lg" disabled={busy}>{busy ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      )}
    </Dialog>
  )
}

type CostTarget = StackItem | "new" | null

function CostDialog({ target, providers, onClose, onSaved }: { target: CostTarget; providers: string[]; onClose: () => void; onSaved: () => Promise<unknown> }) {
  const { toast, confirm } = useFeedback()
  const [busy, setBusy] = useState<"" | "save" | "remove">("")
  const row = target && target !== "new" ? target : null
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy("save")
    try {
      await api("/api/stack-cost", { ...(row ? { id: row.id } : {}), ...formBody(e.currentTarget) })
      await onSaved()
      toast("Saved.")
      onClose()
    } catch (err) { toast(message(err), true) } finally { setBusy("") }
  }
  async function remove() {
    if (!row) return
    onClose()
    if (!(await confirm({ title: `Remove ${row.item}?`, body: "It comes off the list of what A Story pays for.", action: "Remove", danger: true }))) return
    try {
      await api("/api/stack-delete", { id: row.id })
      await onSaved()
      toast("Removed.")
    } catch (err) { toast(message(err), true) }
  }
  return (
    <Dialog open={!!target} onOpenChange={(o) => { if (!o && !busy) onClose() }}>
      {target && (
        <DialogContent className="max-h-[90svh] overflow-y-auto text-base sm:max-w-[36rem]">
          <form onSubmit={save} className="grid gap-4">
            <DialogHeader>
              <DialogTitle className="text-xl">{row ? row.item : "Add something you pay for"}</DialogTitle>
              <DialogDescription className="text-base">The monthly cost, and the credit that covers it.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="What you pay for" htmlFor="cost-item" className="sm:col-span-2"><Input id="cost-item" name="item" maxLength={120} required defaultValue={row?.item || ""} /></Field>
              <Field label="Provider" htmlFor="cost-provider"><Input id="cost-provider" name="provider" maxLength={80} defaultValue={row?.provider || ""} /></Field>
              <Field label="Monthly cost, in dollars" htmlFor="cost-usd"><Input id="cost-usd" name="monthly_usd" type="number" min={0} step={0.01} defaultValue={row?.monthly_usd ?? ""} /></Field>
              <Field label="Covered by" htmlFor="cost-cover" className="sm:col-span-2">
                <NativeSelect id="cost-cover" name="covered_by" defaultValue={row?.covered_by || ""} className="w-full">
                  <NativeSelectOption value="">Not covered</NativeSelectOption>
                  {coverChoices(providers, row?.covered_by).map((p) => <NativeSelectOption key={p} value={p}>{p} credits</NativeSelectOption>)}
                </NativeSelect>
              </Field>
            </div>
            <DialogFooter className="gap-2">
              {row && <Button type="button" size="lg" variant="destructive" className="sm:mr-auto" onClick={remove} disabled={!!busy}>Remove</Button>}
              <Button type="button" size="lg" variant="outline" onClick={onClose} disabled={!!busy}>Cancel</Button>
              <Button type="submit" size="lg" disabled={!!busy}>{busy === "save" ? "Saving…" : row ? "Save" : "Add"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      )}
    </Dialog>
  )
}

// ---------- What A Story pays for, and which credit covers it ----------
function StackPanel({ stack, onEdit }: { stack: Stack; onEdit: (t: CostTarget) => void }) {
  const u = stack.monthly_uncovered || 0, c = stack.monthly_covered || 0
  const share = u + c ? Math.round((c / (u + c)) * 100) : 0
  // An item with no cost and no cover says nothing yet: those wait behind one control, not as a row each.
  const filled = stack.items.filter((r) => r.monthly_usd != null || r.covered_by)
  const blank = stack.items.filter((r) => r.monthly_usd == null && !r.covered_by)
  const add = <Button size="lg" variant="outline" onClick={() => onEdit("new")}><Plus aria-hidden="true" />Add a cost</Button>
  return (
    <Panel id="stack" className="scroll-mt-4" title="What A Story pays for" aside="The research agents look for credits to cover what is not covered">
      {(u > 0 || c > 0) && (
        <div className="flex max-w-[40rem] flex-col gap-3">
          <div className="grid grid-cols-2 gap-6">
            <Fact label="Not covered, a month" tone="money">{cost(u)}</Fact>
            <Fact label="Covered by credits, a month" tone="money">{cost(c)}</Fact>
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="h-2 overflow-hidden rounded-full bg-track" role="img" aria-label={`${share}% of the monthly cost is covered by credits`}>
              <div className="h-full rounded-full bg-foreground/60" style={{ width: `${share}%` }} />
            </div>
            <span className="text-sm text-muted-foreground">{share}% of the monthly cost is covered by credits</span>
          </div>
        </div>
      )}
      {filled.length > 0 ? (
        <>
          <Table className="min-w-[48rem] table-fixed">
            <colgroup><col /><col className="w-56" /><col className="w-40" /><col className="w-64" /><col className="w-28" /></colgroup>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>What you pay for</TableHead><TableHead>Provider</TableHead><TableHead className="text-right">A month</TableHead><TableHead>Covered by</TableHead>
                <TableHead><span className="sr-only">Edit</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filled.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="py-1 text-base font-semibold">{r.item}</TableCell>
                  <TableCell className="py-1 text-base text-muted-foreground">{r.provider || ""}</TableCell>
                  <TableCell className={cn("py-1 text-right tabular-nums", r.monthly_usd != null ? "font-semibold text-money" : "text-sm text-muted-foreground")}>{r.monthly_usd != null ? cost(r.monthly_usd) : "Not set"}</TableCell>
                  <TableCell className="py-1">{r.covered_by ? <span className="text-base">{r.covered_by} credits</span> : <Tag>Not covered</Tag>}</TableCell>
                  <TableCell className="py-1 text-right"><Button size="lg" variant="outline" onClick={() => onEdit(r)} aria-label={`Edit ${r.item}`}>Edit</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex">{add}</div>
        </>
      ) : (
        <Empty action={add}>No monthly costs yet. Add what A Story pays each month to see what credits still need to cover.</Empty>
      )}
      {blank.length > 0 && (
        <Disclosure label={`${plural(blank.length, "item")} listed without a cost`}>
          <ul className="grid gap-x-8 sm:grid-cols-2 xl:grid-cols-3">
            {blank.map((r) => (
              <li key={r.id} className="flex min-h-14 items-center justify-between gap-3 border-t">
                <span className="flex min-w-0 flex-col">
                  <span className="text-base font-semibold">{r.item}</span>
                  {r.provider && <span className="text-sm text-muted-foreground">{r.provider}</span>}
                </span>
                <Button size="lg" variant="outline" onClick={() => onEdit(r)} aria-label={`Set the cost of ${r.item}`}>Set cost</Button>
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </Panel>
  )
}

// ---------- The page ----------
function headline(open: Credit[]) {
  const due = open.filter(creditDue).sort((a, b) => (a.days_left ?? 0) - (b.days_left ?? 0))[0]
  if (due) return <><span className="font-semibold text-deadline">{due.provider} credits end in {plural(due.days_left ?? 0, "day")}.</span> Use them, and decide before any paid plan starts.</>
  const dates = open.filter((c) => c.level === "NEEDS_DATES")
  if (dates.length) return `${plural(dates.length, "credit needs", "credits need")} a start date before the end date can be tracked.`
  return "Free service credits you have won. Use them before they lapse, and decide before any paid plan starts."
}

export function CreditsPage() {
  const state = useLoad(loadCredits)
  useHashScroll(!!state.data)
  const [editing, setEditing] = useState<Credit | null>(null)
  const [costTarget, setCostTarget] = useState<CostTarget>(null)
  return (
    <Shell active="Funding" tab="/credits" title="Credits">
      <LoadGate state={state}>
        {({ credits, stack }) => {
          const open = credits.filter((c) => c.level !== "DONE"), done = credits.filter((c) => c.level === "DONE")
          const first = open.find((c) => c.level === "NEEDS_DATES")
          return (
            <>
              <PageHead title="Credits" line={headline(open)}>
                {first && <Button size="lg" onClick={() => setEditing(first)}>Add the {first.provider} start date</Button>}
              </PageHead>
              <Panel title="Your credits" aside={open.length ? `${open.length} active` : undefined}>
                {open.length
                  ? <CreditTable credits={open} onEdit={setEditing} />
                  : <Empty>No active credit grants. Accepted credit programs appear here on their own.</Empty>}
                {done.length > 0 && (
                  <Disclosure label={`Used up or ended (${done.length})`} className="border-t pt-2">
                    <CreditTable credits={done} onEdit={setEditing} />
                  </Disclosure>
                )}
              </Panel>
              {stack && <StackPanel stack={stack} onEdit={setCostTarget} />}
              <CreditDialog key={editing?.id || "credit"} credit={editing} onClose={() => setEditing(null)} onSaved={state.reload} />
              <CostDialog key={costTarget === "new" ? "new" : costTarget?.id || "cost"} target={costTarget} providers={stack?.credit_providers || []}
                onClose={() => setCostTarget(null)} onSaved={state.reload} />
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/credits": () => <CreditsPage /> } }
