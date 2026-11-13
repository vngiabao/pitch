import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { Check, ChevronDown, Copy } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { copyText, countLabel } from "@/lib/format"
import { cn } from "@/lib/utils"

// The parts every rebuilt page is made of. Type scale: 14 labels, 16 rows and body, 20 panel titles, 24 the page's
// one next step. Colour: navy accent, brass = money only, red = deadlines and failures only, green = done only.

// Load a page's data: { data, error, loading, reload }. After an action, call reload() (the old app's boot()).
export function useLoad<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  // The loader is re-made only when the caller's deps change (the caller passes them, as with useEffect)
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/use-memo
  const run = useCallback(load, deps)
  // Only the newest request may set the page's data: a slower, older response is dropped
  const latest = useRef(0)
  const reload = useCallback(async () => {
    const mine = ++latest.current
    try {
      const v = await run()
      if (mine === latest.current) { setData(v); setError(null) }
      return v
    } catch (e) {
      if (mine === latest.current) setError(e instanceof Error ? e.message : "Unable to open this page.")
      return null
    } finally { if (mine === latest.current) setLoading(false) }
  }, [run])
  // Fetching on mount and when the deps change is what this hook is for
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setLoading(true); void reload() }, [reload])
  return { data, error, loading, reload }
}

// Shows the skeleton while loading, a plain error with a retry when it fails, the page when it has data.
export function LoadGate<T>({ state, children }: { state: { data: T | null; error: string | null; loading: boolean; reload: () => unknown }; children: (data: T) => ReactNode }) {
  if (state.data) return (
    <>
      {state.error && (
        <Alert>
          <AlertTitle>This page could not refresh</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 text-base">
            What you see may be out of date. {state.error}
            <Button variant="outline" size="lg" onClick={() => state.reload()}>Load it again</Button>
          </AlertDescription>
        </Alert>
      )}
      {children(state.data)}
    </>
  )
  if (state.error) return (
    <Alert>
      <AlertTitle>This page didn’t load</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 text-base">
        {state.error}
        <Button variant="outline" size="lg" onClick={() => state.reload()}>Load it again</Button>
      </AlertDescription>
    </Alert>
  )
  return <div className="flex flex-col gap-5" aria-busy="true"><Skeleton className="h-28" /><Skeleton className="h-80" /></div>
}

// The dates and counts in a state line are what the page turns on, so they are set heavier than the words
// around them (the same way Home's line reads: "5 accepted, 7 waiting on results"). Only three things count:
// a date the page turns on (not a "last search / last verified / written" stamp, which is context), a sum of
// money, and a count that opens a clause ("11 things…", "12 of 21 answers"). A number inside a phrase
// ("round 1", "within 14 days", a cycle year) stays plain.
const VITAL = /((?<!(?:[Ll]ast \w+|written|Read|ran) )(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:–\d{1,2})?(?:, \d{4})?|\$\d[\d,]*(?:\.\d+)?|(?<=^|[.,;] | · )\d{1,3}(?:,\d{3})*(?:\.\d+)?%?(?: of \d+)?(?![\d:–-]))/g
function vitals(line: string): ReactNode {
  return line.split(VITAL).map((part, i) => i % 2 ? <strong key={i} className="font-semibold tabular-nums">{part}</strong> : part)
}

// The top of a page: what this page is, in one line, and at most one or two actions. The line is set in ink,
// never grey: it often carries the page's key fact. `plain` keeps numbers that aren't vitals (a file size) unbolded.
export function PageHead({ title, line, children, plain = false }: { title: string; line?: ReactNode; children?: ReactNode; plain?: boolean }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="flex min-w-0 flex-col gap-1">
        <h2 className="text-2xl leading-tight font-semibold tracking-tight">{title}</h2>
        {line && <p className="max-w-[70ch] text-base text-foreground">{typeof line === "string" && !plain ? vitals(line) : line}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-3">{children}</div>}
    </div>
  )
}

// For a two-column row of panels (`ref={evenBottoms}` on the grid): when the two columns end within NEAR pixels
// of each other, the shorter one's last panel grows so both end on one line. Columns that differ by more are left
// alone, since a short panel stretched to match a long list would be mostly empty.
const NEAR = 80
export function evenBottoms(el: HTMLDivElement | null) {
  if (!el) return
  const even = () => {
    const cols = [...el.children].filter((c): c is HTMLElement => c instanceof HTMLElement)
    // A column that arrives after the first render (a side panel shown once data loads) is watched too
    for (const c of cols) watch.observe(c)
    const ends = cols.map((c) => c.dataset.slot === "card" || !(c.lastElementChild instanceof HTMLElement) ? c : c.lastElementChild)
    for (const t of ends) t.style.minHeight = ""
    if (cols.length !== 2 || cols[0].offsetTop !== cols[1].offsetTop) return
    const gap = cols[0].offsetHeight - cols[1].offsetHeight
    if (gap === 0 || Math.abs(gap) > NEAR) return
    const t = ends[gap < 0 ? 0 : 1]
    t.style.minHeight = t.offsetHeight + Math.abs(gap) + "px"
  }
  const watch = new ResizeObserver(() => even())
  const arrivals = new MutationObserver(() => even())
  watch.observe(el)
  arrivals.observe(el, { childList: true })
  even()
  return () => { watch.disconnect(); arrivals.disconnect() }
}

// A region of the page on its own ground. `title` is a 20px panel title; `aside` sits at the right of the title row.
export function Panel({ title, aside, children, className, id }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <Card id={id} className={cn("gap-4 py-5", className)}>
      {(title || aside) && (
        <CardHeader className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          {title && <CardTitle className="text-xl font-semibold tracking-tight"><h3>{title}</h3></CardTitle>}
          {aside && <div className="text-sm text-muted-foreground">{aside}</div>}
        </CardHeader>
      )}
      <CardContent className="flex flex-col gap-4">{children}</CardContent>
    </Card>
  )
}

// Nothing here yet: one sentence, and one action when there is something to do about it.
export function Empty({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg bg-secondary px-4 py-4 text-base text-muted-foreground">{children}{action}</div>
}

// A status word. Colour means something: urgent = a deadline or failure, good = done, review = needs Bao, quiet = the rest.
export function Tag({ tone = "quiet", children }: { tone?: "urgent" | "good" | "review" | "quiet"; children: ReactNode }) {
  return (
    <span className={cn("inline-flex h-7 shrink-0 items-center gap-1.5 rounded-md px-2 text-sm font-medium whitespace-nowrap",
      tone === "urgent" && "bg-deadline/10 text-deadline", tone === "good" && "bg-good/10 text-good",
      tone === "review" && "bg-primary/10 text-primary", tone === "quiet" && "bg-secondary text-muted-foreground")}>
      <i aria-hidden="true" className={cn("size-1.5 rounded-full", tone === "urgent" && "bg-deadline", tone === "good" && "bg-good", tone === "review" && "bg-primary", tone === "quiet" && "bg-muted-foreground")} />
      {children}
    </span>
  )
}

// A row in a list of things: a name, one line, and what to do, all on one left edge. Rows are separated by space
// and a hairline; the whole row is a link when `href` is given.
export function Row({ title, line, meta, href, children, tone }: { title: ReactNode; line?: ReactNode; meta?: ReactNode; href?: string; children?: ReactNode; tone?: "urgent" }) {
  const body = (
    <>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className={cn("text-base font-semibold", tone === "urgent" && "text-deadline")}>{title}</span>
        {line && <span className="text-base text-muted-foreground">{line}</span>}
      </span>
      {meta && <span className="shrink-0 text-sm text-muted-foreground">{meta}</span>}
    </>
  )
  return (
    <li className="flex min-h-16 flex-wrap items-center gap-x-4 gap-y-2 border-t py-3 first:border-t-0">
      {href ? <a href={href} className="flex min-h-11 min-w-0 flex-1 items-center gap-4 rounded-lg hover:bg-secondary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">{body}</a> : body}
      {children && <span className="flex shrink-0 flex-wrap items-center gap-2">{children}</span>}
    </li>
  )
}
export const Rows = ({ children, label }: { children: ReactNode; label?: string }) => <ul aria-label={label} className="flex flex-col">{children}</ul>

// A label over a form control, with an optional hint under it.
export function Field({ label, hint, htmlFor, children, className }: { label: string; hint?: ReactNode; htmlFor?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-2", className)}>
      <Label htmlFor={htmlFor} className="text-sm font-medium">{label}</Label>
      {children}
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  )
}

// Text Bao copies into a form somewhere else (old answerBox()): the text, its count against the limit, a Copy button.
export function CopyBox({ text, limit, unit = "words", label = "Copy" }: { text: string; limit?: number | null; unit?: "words" | "characters"; label?: string }) {
  const [done, setDone] = useState(false)
  const over = !!limit && (unit === "words" ? (text.trim().match(/\S+/g) || []).length : text.length) > limit
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-secondary p-4">
      <p className="text-base whitespace-pre-wrap">{text}</p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className={cn("text-sm", over ? "font-semibold text-deadline" : "text-muted-foreground")}>{countLabel(text, limit, unit)}</span>
        <Button variant="outline" size="lg" onClick={async () => { if (await copyText(text)) { setDone(true); setTimeout(() => setDone(false), 1600) } }}>
          {done ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{done ? "Copied" : label}
        </Button>
      </div>
    </div>
  )
}

// A fact with its label (prize, deadline, a count): label 14, value 20 semibold, the same as Today everywhere.
// Hide a strip of facts when every value is zero; an empty strip says nothing.
export function Fact({ label, children, tone }: { label: string; children: ReactNode; tone?: "money" | "deadline" | "good" }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn("text-xl font-semibold", tone === "money" && "text-money", tone === "deadline" && "text-deadline", tone === "good" && "text-good")}>{children}</span>
    </div>
  )
}

// The one disclosure used on every page: a quiet text control with a chevron that opens more detail under it.
// Use it for anything long that isn't needed to decide what to do next (how a number was figured, a full draft,
// history, a file's location). `open` starts it open, e.g. when the address has a matching #anchor.
export function Disclosure({ label, children, open = false, id, className, block = false }: { label: ReactNode; children: ReactNode; open?: boolean; id?: string; className?: string; block?: boolean }) {
  // `block`: a long label (a question with a tag under it) that may wrap; the chevron stays at the first line.
  return (
    <details id={id} open={open} className={cn("group", className)}>
      <summary className={cn("flex min-h-11 cursor-pointer list-none gap-1.5 rounded-md text-base text-foreground underline-offset-4 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid [&::-webkit-details-marker]:hidden",
        block ? "items-start py-2 text-left" : "w-fit items-center font-medium hover:underline")}>
        <ChevronDown className={cn("size-4 shrink-0 transition-transform duration-150 group-open:rotate-180 motion-reduce:transition-none", block && "mt-1")} aria-hidden="true" />
        {label}
      </summary>
      <div className="flex flex-col gap-3 pt-2 pb-1">{children}</div>
    </details>
  )
}

// Scroll to the element named by the address's #anchor once the page has its data (old pages' anchors keep working).
export function useHashScroll(ready: boolean) {
  useEffect(() => {
    if (!ready || !location.hash) return
    let id: string
    try { id = decodeURIComponent(location.hash.slice(1)) } catch { return }
    const el = document.getElementById(id)
    if (el instanceof HTMLDetailsElement) el.open = true
    el?.scrollIntoView({ block: "start" })
  }, [ready])
}
