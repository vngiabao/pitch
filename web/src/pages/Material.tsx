import { useState } from "react"
import { Download } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Disclosure, Empty, LoadGate, PageHead, Panel, useLoad } from "@/components/app/page"
import { api } from "@/lib/api"
import { fileSize, plural, prettyKey } from "@/lib/format"
import { fileName, folderWords, MATERIALS_LIST_KEY, useListCrumb, type Material } from "@/lib/pitches"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"

// One file from Materials (old app.js material(id)): its text, its details, and the way into Pitch Studio.

const FIRST = 6000 // characters shown before "Show all the text"

// The text of a deck arrives with the file's inner part names ("[ppt/notesSlides/notesSlide3.xml]").
// Show them as what they are: "Slide 3 notes", "Slide 3".
const readable = (body: string) => body
  .replace(/^\[ppt\/notesSlides\/notesSlide(\d+)\.xml\]$/gm, "Slide $1 notes")
  .replace(/^\[ppt\/slides\/slide(\d+)\.xml\]$/gm, "Slide $1")
  .replace(/^\[(?:[\w.-]+\/)*([\w.-]+)\.xml\]$/gm, "$1")

// The text as blocks: one per slide (its title, then its words) or one per paragraph. A deck's parts arrive in
// file-name order (1, 10, 11, 2…), so when every block is a numbered slide they are put in slide order.
type Block = { title: string; body: string; n: number | null }
function blocks(text: string): Block[] {
  const out: Block[] = []
  for (const part of text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean)) {
    const lines = part.split("\n")
    const m = /^Slide (\d+)(?: notes)?$/i.exec(lines[0].trim())
    const last = out[out.length - 1]
    if (m) {
      const rest = lines.slice(1)
      // A slide's text ends with its own page number on a line of its own; that line says nothing
      if (rest.length > 0 && /^\d+$/.test(rest[rest.length - 1].trim()) && Number(rest[rest.length - 1]) === Number(m[1])) rest.pop()
      // A slide with nothing but its number has no words to show
      if (rest.join("").trim()) out.push({ title: lines[0].trim(), body: rest.join("\n"), n: Number(m[1]) })
    } else if (last && last.n !== null) { if (part !== String(last.n)) last.body += "\n\n" + part }
    else out.push({ title: "", body: part, n: null })
  }
  return out.every((b) => b.n !== null) ? out.map((b, i) => ({ b, i })).sort((x, y) => (x.b.n! - y.b.n!) || x.i - y.i).map((x) => x.b) : out
}

function Text({ body, file }: { body?: string | null; file: string }) {
  const [all, setAll] = useState(false)
  if (!body) return (
    <Empty action={<Button size="lg" variant="outline" asChild><a href={file}><Download aria-hidden="true" />Download original</a></Button>}>
      This file is kept as an original. Download it to see its slides or images.
    </Empty>
  )
  const text = readable(body)
  const groups = blocks(text)
  // The preview shows whole blocks, in order, up to about FIRST characters
  const sizes = groups.map((g) => g.title.length + g.body.length)
  const preview = groups.filter((_, i) => i === 0 || sizes.slice(0, i).reduce((a, b) => a + b, 0) < FIRST)
  const long = preview.length < groups.length
  return (
    <>
      {/* One block per slide or paragraph, read left to right then down, so nothing sends the eye back up a column */}
      <div className="grid gap-x-12 gap-y-6 lg:grid-cols-2 2xl:grid-cols-3">
        {(all ? groups : preview).map((g, i) => (
          <div key={i} className="flex max-w-[70ch] flex-col gap-1 text-base leading-relaxed break-words whitespace-pre-wrap">
            {g.title && <span className="font-semibold">{g.title}</span>}
            <span>{g.body}</span>
          </div>
        ))}
      </div>
      {long && !all && <div><Button size="lg" variant="outline" onClick={() => setAll(true)}>Show all the text ({text.length.toLocaleString("en-US")} characters)</Button></div>}
    </>
  )
}

export function MaterialPage({ id }: { id: string }) {
  useListCrumb(MATERIALS_LIST_KEY, "/materials")
  const state = useLoad(() => api<Material>("/api/material/" + encodeURIComponent(id)), [id])
  const m = state.data
  const file = `/api/material/${encodeURIComponent(id)}/file`
  return (
    <Shell active="Pitch" tab="/materials" title="Material" crumb={m ? fileName(m.relative_path) : "Material"}>
      <LoadGate state={state}>
        {(m) => (
          <>
            <PageHead title={fileName(m.relative_path)} line={[prettyKey(m.kind), fileSize(m.size_bytes), folderWords(m.relative_path), m.aliases.length ? plural(m.aliases.length, "identical copy", "identical copies") : ""].filter(Boolean).join(" · ")}>
              <Button size="lg" asChild><a href={"/pitches?material=" + encodeURIComponent(id)}>Adapt in Pitch Studio</a></Button>
              <Button size="lg" variant="outline" asChild><a href={file}><Download aria-hidden="true" />Download original</a></Button>
            </PageHead>
            <Panel title="Text">
              <Text body={m.body} file={file} />
              <Disclosure label="Show location" className="border-t pt-2">
                <span className="text-base break-all">{m.source_path}</span>
                {m.aliases.length > 0 && (
                  <ul className="flex flex-col gap-1">
                    {m.aliases.map((a) => <li key={a.source_path} className="text-base break-all">{a.source_path}</li>)}
                  </ul>
                )}
              </Disclosure>
            </Panel>
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/material/": (id) => <MaterialPage id={id} /> } }
