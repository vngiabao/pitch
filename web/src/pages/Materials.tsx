import { useEffect, useState, type FormEvent } from "react"
import { Download, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Disclosure, CopyBox, Empty, Field, LoadGate, PageHead, Panel, Tag, useLoad, evenBottoms } from "@/components/app/page"
import { useFeedback } from "@/components/app/feedback"
import { api } from "@/lib/api"
import { fileSize, plural, prettyKey, stamp } from "@/lib/format"
import { fileName, folderWords, LINK, MATERIALS_LIST_KEY, plainLabel, remember, type Answer, type MaterialList } from "@/lib/pitches"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"

// Materials & answers (old app.js materials()): search the indexed files and read the saved answer versions.
// The site's search box lives here: /materials?q=<words>.

const COLLECTIONS: [string, string][] = [["", "Useful materials"], ["ARCHIVE", "Archived or generated"], ["all", "All materials"]]
const textState = (extraction: string) => (extraction === "reference_only" ? "Original only" : extraction === "EXTRACTION_FAILED" ? "Text unavailable" : "Text searchable")

type Query = { q: string; kind: string; category: string; offset: number }
function fromLocation(): Query {
  const p = new URLSearchParams(location.search)
  return { q: p.get("q") || "", kind: p.get("kind") || "", category: p.get("category") || "", offset: Math.max(0, Number(p.get("offset")) || 0) }
}

function Files({ lib, query, busy, go }: { lib: MaterialList; query: Query; busy: boolean; go: (q: Query, top?: boolean) => void }) {
  function search(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    go({ q: String(f.get("q") || ""), kind: String(f.get("kind") || ""), category: String(f.get("category") || ""), offset: 0 })
  }
  const from = lib.total ? query.offset + 1 : 0, to = Math.min(query.offset + lib.limit, lib.total)
  return (
    <Panel title="Find a file"
      aside={`${lib.stats.unique_files.toLocaleString("en-US")} files, ${(lib.stats.searchable_text || 0).toLocaleString("en-US")} with searchable text`}>
      <form id="material-filters" role="search" onSubmit={search} className="grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(11rem,1fr)_auto]">
        <Field label="Search materials" htmlFor="material-q">
          <Input id="material-q" name="q" type="search" defaultValue={query.q} placeholder="Deck, grant, traction…" />
        </Field>
        <Field label="Type" htmlFor="material-kind">
          <NativeSelect id="material-kind" name="kind" defaultValue={query.kind} className="w-full">
            <NativeSelectOption value="">All types</NativeSelectOption>
            {lib.stats.kinds.map((k) => <NativeSelectOption key={k.kind} value={k.kind}>{prettyKey(k.kind)} ({k.count})</NativeSelectOption>)}
          </NativeSelect>
        </Field>
        <Field label="Collection" htmlFor="material-category">
          <NativeSelect id="material-category" name="category" defaultValue={query.category} className="w-full">
            {COLLECTIONS.map(([v, l]) => <NativeSelectOption key={v} value={v}>{l}</NativeSelectOption>)}
          </NativeSelect>
        </Field>
        <Button type="submit" size="lg" variant="outline" disabled={busy}><Search aria-hidden="true" />{busy ? "Searching…" : "Search"}</Button>
      </form>

      {lib.items.length ? (
        <div className={cn(busy && "opacity-60")} aria-busy={busy}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Size</TableHead>
                <TableHead><span className="sr-only">Download</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lib.items.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="min-w-72 whitespace-normal">
                    <a href={"/material/" + encodeURIComponent(m.id)} className={cn(LINK, "font-semibold break-words text-foreground")}>{fileName(m.relative_path)}</a>
                    {folderWords(m.relative_path) && <p className="text-sm break-words text-muted-foreground">{folderWords(m.relative_path)}</p>}
                    <p className="text-sm text-muted-foreground">{textState(m.extraction)}{m.duplicates ? " · " + plural(m.duplicates, "copy", "copies") : ""}</p>
                  </TableCell>
                  <TableCell><Tag>{prettyKey(m.kind)}</Tag></TableCell>
                  <TableCell className="text-right whitespace-nowrap tabular-nums">{fileSize(m.size_bytes)}</TableCell>
                  <TableCell className="text-right">
                    <a href={`/api/material/${encodeURIComponent(m.id)}/file`} className={cn(LINK, "gap-2 whitespace-nowrap")}><Download className="size-4" aria-hidden="true" />Download</a>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <Empty action={query.category !== "all" || query.q || query.kind
          ? <Button size="lg" variant="outline" onClick={() => go({ q: "", kind: "", category: "all", offset: 0 })}>Show all materials</Button> : undefined}>
          No materials match. Try a broader search or choose All materials.
        </Empty>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button size="lg" variant="outline" disabled={busy || query.offset === 0} onClick={() => go({ ...query, offset: Math.max(0, query.offset - lib.limit) }, true)}>Previous</Button>
        <Button size="lg" variant="outline" disabled={busy || query.offset + lib.limit >= lib.total} onClick={() => go({ ...query, offset: query.offset + lib.limit }, true)}>Next</Button>
        <span className="text-sm text-muted-foreground tabular-nums">{from} to {to} of {lib.total.toLocaleString("en-US")} matching files</span>
        <a href="/api/materials-manifest" className={cn(LINK, "ml-auto gap-2")}><Download className="size-4" aria-hidden="true" />Download the list of sources</a>
      </div>
    </Panel>
  )
}

// One row per question. The saved wordings of that question sit under it, newest first, each said once.
type Question = { prompt: string; versions: Answer[] }
function byQuestion(answers: Answer[]): Question[] {
  const groups = new Map<string, Answer[]>()
  for (const a of answers) {
    const list = groups.get(a.prompt) || []
    if (!list.some((v) => v.body === a.body)) list.push(a)
    else if (a.status === "approved") list[list.findIndex((v) => v.body === a.body)] = a
    groups.set(a.prompt, list)
  }
  return [...groups].map(([prompt, versions]) => ({ prompt, versions: versions.sort((x, y) => String(y.created_at).localeCompare(String(x.created_at))) }))
}

function Answers() {
  const state = useLoad(() => api<Answer[]>("/api/answers"))
  const [find, setFind] = useState("")
  const [all, setAll] = useState(false)
  return (
    <Panel title="Saved answers" aside={state.data ? plural(byQuestion(state.data).length, "question") : undefined}>
      <LoadGate state={state}>
        {(answers) => {
          const questions = byQuestion(answers)
          const words = find.trim().toLowerCase()
          const match = words ? questions.filter((q) => (q.prompt + "\n" + q.versions.map((v) => v.body).join("\n")).toLowerCase().includes(words)) : questions
          const shown = all || words ? match : match.slice(0, 6)
          return (
            <>
              <Field label="Find an answer" htmlFor="answer-find">
                <Input id="answer-find" type="search" value={find} onChange={(e) => setFind(e.currentTarget.value)} placeholder="A question or a phrase" />
              </Field>
              {match.length ? (
                <ul aria-label="Saved answers" className="flex flex-col">
                  {shown.map((q) => (
                    <li key={q.prompt} className="border-t py-1 first:border-t-0">
                      <Disclosure block label={
                          <span className="flex min-w-0 flex-col items-start gap-1.5 text-left">
                            <span className="font-semibold break-words underline-offset-4 group-hover:underline">{plainLabel(q.prompt)}</span>
                            {q.versions.some((v) => v.status === "approved")
                              ? <Tag tone="good">Approved</Tag>
                              : <Tag>{q.versions.length > 1 ? plural(q.versions.length, "draft") : "Draft"}</Tag>}
                          </span>
                      }>
                          {q.versions.map((v, i) => (
                            <div key={v.id || i} className="flex flex-col gap-2 pb-2">
                              <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                                <span className="tabular-nums">{stamp(v.created_at)}</span>
                                {q.versions.length > 1 && <Tag tone={v.status === "approved" ? "good" : "quiet"}>{prettyKey(v.status)}</Tag>}
                              </span>
                              <CopyBox text={v.body} limit={v.limit_value} unit={v.limit_unit === "characters" ? "characters" : "words"} />
                            </div>
                          ))}
                        </Disclosure>
                    </li>
                  ))}
                </ul>
              ) : <Empty>{answers.length ? "No saved answer has those words." : "No answers are saved yet."}</Empty>}
              {shown.length < match.length && <div><Button size="lg" variant="outline" onClick={() => setAll(true)}>Show all {match.length} questions</Button></div>}
            </>
          )
        }}
      </LoadGate>
    </Panel>
  )
}

export function MaterialsPage() {
  const [query, setQuery] = useState<Query>(fromLocation)
  const state = useLoad(async () => {
    const params = new URLSearchParams({ q: query.q, kind: query.kind, category: query.category, offset: String(query.offset) })
    const lib = await api<MaterialList>("/api/materials?" + params)
    history.replaceState(null, "", "/materials?" + params)
    remember(MATERIALS_LIST_KEY, location.pathname + location.search)
    return lib
  }, [query.q, query.kind, query.category, query.offset])
  const go = (q: Query, top = false) => { setQuery(q); if (top) window.scrollTo(0, 0) }
  // A search or page turn that fails says so; the last good list stays on screen
  const { toast } = useFeedback()
  const failed = state.data ? state.error : null
  useEffect(() => { if (failed) toast(failed, true) }, [failed, toast])
  return (
    <Shell active="Pitch" tab="/materials" title="Materials & answers">
      <PageHead title="Materials & answers" line="Search your decks, essays, scripts and research." />
      <div ref={evenBottoms} className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <LoadGate state={state}>
          {(lib) => <Files key={`${query.q}|${query.kind}|${query.category}`} lib={lib} query={query} busy={state.loading} go={go} />}
        </LoadGate>
        <Answers />
      </div>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/materials": () => <MaterialsPage /> } }
