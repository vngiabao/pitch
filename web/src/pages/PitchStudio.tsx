import { useEffect, useRef, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { Empty, Field, LoadGate, PageHead, Panel, Tag, useLoad } from "@/components/app/page"
import { useFeedback } from "@/components/app/feedback"
import { api } from "@/lib/api"
import { cleanName, plural } from "@/lib/format"
import { capital, fileName, lengthWords, LINK, PITCH_LIBRARY_KEY, remember, stageWords, uniqueWords, type Material, type PitchChoices } from "@/lib/pitches"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"

// Pitch Studio library (old pitch.js pitchLibrary()): the saved pitches, the filters, and the form that starts a new one.

const LENGTHS = ["", "30", "60", "180", "300", "420", "600", "900", "1200"]

type Loaded = { choices: PitchChoices; source: Material | null }

export function Choices({ choices }: { choices: PitchChoices }) {
  return (
    <>
      <datalist id="pitch-audiences">{uniqueWords(choices.audiences).map((a) => <option key={a} value={a} />)}</datalist>
      <datalist id="pitch-scenarios">{uniqueWords(choices.scenarios).map((a) => <option key={a} value={a} />)}</datalist>
    </>
  )
}

function NewPitch({ source, onClose }: { source: Material | null; onClose: () => void }) {
  const { toast, confirm } = useFeedback()
  // Typing in the form makes it unsaved; leaving the page then asks first.
  const dirty = useRef(false)
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (dirty.current) { e.preventDefault(); e.returnValue = "" } }
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [])
  const [busy, setBusy] = useState(false)
  const first = useRef<HTMLInputElement>(null)
  useEffect(() => { if (!source) first.current?.focus() }, [source])
  const long = (source?.body?.length || 0) > 40000

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const p: Record<string, unknown> = Object.fromEntries(f)
    p.duration_seconds = Math.round(Number(f.get("duration_minutes")) * 60)
    p.sources = source?.source_version_id ? [source.source_version_id] : []
    p.claim_versions = []
    setBusy(true)
    try {
      const r = await api<{ pitch_id: string }>("/api/pitches", p)
      dirty.current = false
      location.href = "/pitch/" + r.pitch_id
    } catch (err) {
      toast(err instanceof Error ? err.message : "Unable to create this pitch.", true)
      setBusy(false)
    }
  }
  async function cancel() {
    if (dirty.current && !(await confirm({ title: "Discard the new pitch?", body: "What you typed here has not been saved and will be lost.", action: "Discard it", cancel: "Keep writing", danger: true }))) return
    dirty.current = false
    onClose()
  }

  return (
    <Panel id="pitch-new" title="Start a pitch">
      <p className="max-w-[60ch] text-base text-muted-foreground">
        {source ? "Adapt this source as a working draft. Its original stays untouched." : "Write a new script here. To adapt a saved pitch, open it and make a variant."}
      </p>
      <form id="pitch-new-form" onSubmit={create} onInput={() => { dirty.current = true }} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,1.2fr)]">
          <Field label="Title" htmlFor="new-title">
            <Input ref={first} id="new-title" name="title" required maxLength={160} placeholder="e.g. A Story - investor introduction"
              defaultValue={source ? "Adaptation of " + fileName(source.relative_path) : ""} />
          </Field>
          <Field label="Length (minutes)" htmlFor="new-minutes">
            <Input id="new-minutes" name="duration_minutes" type="number" min={0.17} max={120} step="any" defaultValue={1} required className="tabular-nums" />
          </Field>
          <Field label="Audience" htmlFor="new-audience">
            <Input id="new-audience" name="audience" list="pitch-audiences" defaultValue="General" required maxLength={100} />
          </Field>
          <Field label="Scenario" htmlFor="new-scenario">
            <Input id="new-scenario" name="scenario" list="pitch-scenarios" defaultValue="Quick introduction" required maxLength={100} />
          </Field>
        </div>
        <Field label="Pitch text" htmlFor="new-body"
          hint={source ? (
            <span className="break-words">
              Source: {fileName(source.source_path)}
              {long && ". Only the first 40,000 characters are here; the full source stays in Materials."}
              {!source.body && ". Its text could not be read; use the original as a reference."}
            </span>
          ) : undefined}>
          <Textarea id="new-body" name="body" required maxLength={40000} rows={10} className="max-h-[60svh] min-h-60 overflow-y-auto leading-relaxed md:text-base"
            placeholder="Start with the problem, explain A Story, and end with the next step." defaultValue={source?.body?.slice(0, 40000) || ""} />
        </Field>
        <div className="flex flex-wrap gap-3">
          <Button type="submit" size="lg" disabled={busy}>{busy ? "Creating…" : "Create draft"}</Button>
          <Button type="button" size="lg" variant="outline" onClick={cancel} disabled={busy}>Cancel</Button>
        </div>
      </form>
    </Panel>
  )
}

function Filters({ q, choices }: { q: URLSearchParams; choices: PitchChoices }) {
  // Old behaviour: the form's own fields make the next URL (so `material` is dropped); selects search on change.
  function search(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    location.href = "/pitches?" + new URLSearchParams(new FormData(e.currentTarget) as unknown as Record<string, string>)
  }
  const onPick = (e: { currentTarget: HTMLSelectElement }) => e.currentTarget.form?.requestSubmit()
  const lengthHref = (s: string) => {
    const p = new URLSearchParams(q)
    if (s) p.set("duration", s); else p.delete("duration")
    p.delete("material")
    return "/pitches" + (p.size ? "?" + p : "")
  }
  const duration = q.get("duration") || ""
  return (
    <div className="flex flex-col gap-4">
      <form id="pitch-filters" onSubmit={search} className="grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
        <Field label="Search pitches" htmlFor="pitch-q">
          <Input id="pitch-q" name="q" type="search" defaultValue={q.get("q") || ""} placeholder="Title or wording" />
        </Field>
        {duration && <input type="hidden" name="duration" value={duration} />}
        <Field label="Audience" htmlFor="pitch-audience">
          <NativeSelect id="pitch-audience" name="audience" defaultValue={q.get("audience") || ""} onChange={onPick} className="w-full">
            <NativeSelectOption value="">Any audience</NativeSelectOption>
            {uniqueWords(choices.audiences).map((a) => <NativeSelectOption key={a} value={a}>{cleanName(capital(a))}</NativeSelectOption>)}
          </NativeSelect>
        </Field>
        <Field label="Scenario" htmlFor="pitch-scenario">
          <NativeSelect id="pitch-scenario" name="scenario" defaultValue={q.get("scenario") || ""} onChange={onPick} className="w-full">
            <NativeSelectOption value="">Any scenario</NativeSelectOption>
            {uniqueWords(choices.scenarios).map((a) => <NativeSelectOption key={a} value={a}>{capital(a)}</NativeSelectOption>)}
          </NativeSelect>
        </Field>
        <Field label="Collection" htmlFor="pitch-archived">
          <NativeSelect id="pitch-archived" name="archived" defaultValue={q.get("archived") === "yes" ? "yes" : ""} onChange={onPick} className="w-full">
            <NativeSelectOption value="">Active drafts</NativeSelectOption>
            <NativeSelectOption value="yes">Include archived</NativeSelectOption>
          </NativeSelect>
        </Field>
        <div className="flex gap-3">
          <Button type="submit" size="lg" variant="outline">Search</Button>
          <Button size="lg" variant="ghost" asChild><a href="/pitches">Clear</a></Button>
        </div>
      </form>
      <nav aria-label="Pitch length" className="flex flex-wrap gap-2">
        {LENGTHS.map((s) => (
          <a key={s || "all"} href={lengthHref(s)} aria-current={duration === s ? "true" : undefined}
            className={cn("flex h-11 items-center rounded-lg border px-4 text-base font-medium transition-colors hover:bg-secondary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid",
              duration === s ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground")}>
            {s ? lengthWords(Number(s)) : "All lengths"}
          </a>
        ))}
      </nav>
    </div>
  )
}

function Library({ choices }: { choices: PitchChoices }) {
  const items = choices.items
  if (!items.length) return (
    <Empty action={<Button size="lg" variant="outline" asChild><a href="/pitches">Clear the filters</a></Button>}>
      No pitches match these choices. Clear the filters or write a new pitch.
    </Empty>
  )
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Pitch</TableHead>
          <TableHead>Audience</TableHead>
          <TableHead className="text-right">Target</TableHead>
          <TableHead className="text-right">Words</TableHead>
          <TableHead className="text-right">Spoken</TableHead>
          <TableHead>Stage</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((p) => (
          <TableRow key={p.pitch_id}>
            <TableCell className="min-w-72 whitespace-normal">
              <a href={"/pitch/" + p.pitch_id} className={cn(LINK, "font-semibold text-foreground")}>{cleanName(p.title)}</a>
              <p className="line-clamp-2 max-w-[58ch] text-base text-muted-foreground">{p.preview}{p.word_count > 40 ? "…" : ""}</p>
            </TableCell>
            <TableCell className="min-w-44 whitespace-normal">
              {cleanName(capital(p.audience))}
              <span className="block text-sm text-muted-foreground">{capital(p.scenario)}</span>
            </TableCell>
            <TableCell className="text-right font-semibold whitespace-nowrap tabular-nums">{lengthWords(p.duration_seconds)}</TableCell>
            <TableCell className="text-right whitespace-nowrap tabular-nums">{p.word_count}</TableCell>
            <TableCell className="text-right whitespace-nowrap tabular-nums">{lengthWords(p.estimated_seconds)}</TableCell>
            <TableCell>
              <span className="flex flex-wrap items-center gap-2">
                <Tag tone={p.status === "rehearsal_ready" ? "good" : "quiet"}>{stageWords(p.status)}</Tag>
                {p.format === "outline" && <span className="text-sm whitespace-nowrap text-muted-foreground">Session plan</span>}
                {p.placeholders.length > 0 && <Tag tone="review">{plural(p.placeholders.length, "open prompt")}</Tag>}
              </span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function PitchStudioPage() {
  const q = new URLSearchParams(location.search)
  const materialId = q.get("material")
  const state = useLoad<Loaded>(async () => {
    remember(PITCH_LIBRARY_KEY, location.pathname + location.search)
    const choices = await api<PitchChoices>("/api/pitches?" + q)
    // "general" and "General" are listed once, so a search for one also asks for the other spelling.
    for (const [name, all] of [["audience", choices.audiences], ["scenario", choices.scenarios]] as const) {
      const chosen = q.get(name)
      if (!chosen) continue
      for (const other of all.filter((a) => a !== chosen && a.trim().toLowerCase() === chosen.trim().toLowerCase())) {
        const again = new URLSearchParams(q)
        again.set(name, other)
        const more = await api<PitchChoices>("/api/pitches?" + again)
        const have = new Set(choices.items.map((i) => i.pitch_id))
        choices.items.push(...more.items.filter((i) => !have.has(i.pitch_id)))
      }
    }
    choices.items.sort((a, b) => a.duration_seconds - b.duration_seconds || a.title.localeCompare(b.title))
    const source = materialId ? await api<Material>("/api/material/" + encodeURIComponent(materialId)) : null
    return { choices, source }
  })
  const [open, setOpen] = useState(!!materialId)

  return (
    <Shell active="Pitch" tab="/pitches" title="Pitch Studio">
      <LoadGate state={state}>
        {({ choices, source }) => (
          <>
            <PageHead title="Pitch Studio" line="Choose who you’re talking to and how much time you have.">
              {!open && <Button size="lg" onClick={() => setOpen(true)}>Write a new pitch</Button>}
            </PageHead>
            {open && <NewPitch source={source} onClose={() => setOpen(false)} />}
            <Panel title="Your pitch library"
              aside={<span className="flex flex-wrap items-center gap-x-4">{plural(choices.items.length, "pitch", "pitches")}, timed at 130 words a minute<a href="/materials" className={LINK}>Find source materials</a></span>}>
              <Filters q={q} choices={choices} />
              <Library choices={choices} />
            </Panel>
            <Choices choices={choices} />
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/pitches": () => <PitchStudioPage /> } }
