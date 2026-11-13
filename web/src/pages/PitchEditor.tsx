import { useEffect, useRef, useState, type FormEvent } from "react"
import { Copy, Download, Pause, Play, RotateCcw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { Disclosure, Field, LoadGate, PageHead, Panel, Tag, useLoad } from "@/components/app/page"
import { useFeedback } from "@/components/app/feedback"
import { api, ApiError } from "@/lib/api"
import { cleanName, plural, stamp } from "@/lib/format"
import {
  capital, clock, forget, FORMATS, lengthWords, LINK, openPrompts, PITCH_LIBRARY_KEY, recall, recoveryKey, remember,
  sourceTitle, spokenSeconds, spokenWords, STAGES, stageWords, useListCrumb, type Pitch, type PitchChoices,
} from "@/lib/pitches"
import type { PageRoutes } from "@/lib/route-types"
import { cn } from "@/lib/utils"
import { Shell } from "@/shell"
import { Choices } from "@/pages/PitchStudio"

// The pitch editor (old pitch.js pitchEditor()): write and version one pitch, check its length, rehearse against a timer.

type Fields = {
  title: string; duration_seconds: string; custom_seconds: string; audience: string; scenario: string; speaker: string
  format: string; status: string; body: string; notes: string; change_note: string
}
type Draft = { version: string; fields: Record<string, unknown> }

const fromPitch = (p: Pitch, lengths: number[]): Fields => ({
  title: p.title, duration_seconds: lengths.includes(p.duration_seconds) ? String(p.duration_seconds) : "custom",
  custom_seconds: String(p.duration_seconds), audience: p.audience, scenario: p.scenario, speaker: p.speaker || "",
  format: p.format, status: p.status, body: p.body, notes: p.notes || "", change_note: "",
})
const target = (f: Fields) => (f.duration_seconds === "custom" ? Number(f.custom_seconds) : Number(f.duration_seconds))
// What the server gets (old pitchValues()): every field, the length as a number, the sources, and the version we edited.
const payload = (f: Fields, p: Pitch) => ({ ...f, duration_seconds: target(f), sources: p.sources || [], claim_versions: p.claim_versions || [], expected_version_id: p.id })

function readDraft(pitchId: string): Draft | null {
  try { return JSON.parse(recall(recoveryKey(pitchId)) || "null") } catch { return null }
}

// Rehearsal: a reading mode. The text, the timer, and the way out. It covers the whole screen.
function Rehearsal({ text, targetSeconds, onExit }: { text: string; targetSeconds: number; onExit: () => void }) {
  const [elapsed, setElapsed] = useState(0) // seconds banked before the current run
  const [started, setStarted] = useState<number | null>(null)
  const [now, setNow] = useState(0) // the clock, read only by the ticking interval and the buttons
  useEffect(() => {
    if (started === null) return
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [started])
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onExit() }
    document.addEventListener("keydown", key)
    return () => document.removeEventListener("keydown", key)
  }, [onExit])
  const seconds = elapsed + (started !== null ? Math.max(0, Math.floor((now - started) / 1000)) : 0)
  const over = seconds > targetSeconds
  const toggle = () => {
    const t = Date.now()
    if (started !== null) { setElapsed(elapsed + Math.floor((t - started) / 1000)); setStarted(null) } else { setStarted(t); setNow(t) }
  }
  const reset = () => { setStarted(null); setElapsed(0) }
  return (
    <section id="pitch-rehearsal" aria-label="Rehearsal" className="fixed inset-0 z-40 flex flex-col overflow-y-auto bg-background">
      <div className="sticky top-0 z-10 border-b bg-background">
        <div className="mx-auto flex w-full max-w-[72rem] flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 md:px-7">
          <strong id="pitch-timer" role="timer" className="text-2xl font-semibold tabular-nums">{clock(seconds)}</strong>
          <span id="pitch-timer-target" className={cn("text-base", over ? "font-semibold text-deadline" : "text-muted-foreground")}>
            Target {lengthWords(targetSeconds)}{over ? ", over target" : ""}
          </span>
          <div className="ml-auto flex flex-wrap gap-3">
            <Button type="button" size="lg" onClick={toggle} autoFocus>
              {started !== null ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
              {started !== null ? "Pause timer" : seconds ? "Resume timer" : "Start timer"}
            </Button>
            <Button type="button" size="lg" variant="outline" onClick={reset}><RotateCcw aria-hidden="true" />Reset</Button>
            <Button type="button" size="lg" variant="outline" onClick={onExit}>Back to editing</Button>
          </div>
        </div>
      </div>
      <div id="pitch-practice-text" className="mx-auto w-full max-w-[72rem] flex-1 px-4 py-8 md:px-7 md:py-12">
        <p className="max-w-[52ch] text-2xl leading-[1.6] whitespace-pre-wrap">{text}</p>
      </div>
    </section>
  )
}

function Editor({ pitch, choices, onSaved }: { pitch: Pitch; choices: PitchChoices; onSaved: (message: string) => Promise<void> }) {
  const { toast, confirm } = useFeedback()
  const [fields, setFields] = useState<Fields>(() => fromPitch(pitch, choices.lengths))
  const [saveState, setSaveState] = useState(`Saved · ${stamp(pitch.created_at)}`)
  const [busy, setBusy] = useState<"" | "save" | "variant" | "restore">("")
  const [draft, setDraft] = useState<Draft | null>(() => readDraft(pitch.pitch_id))
  const [conflict, setConflict] = useState("")
  const [rehearsing, setRehearsing] = useState(false)
  const [allSources, setAllSources] = useState(false)
  const [allVersions, setAllVersions] = useState(false)
  const dirty = useRef(false)
  const form = useRef<HTMLFormElement>(null)
  const bodyField = useRef<HTMLTextAreaElement>(null)
  const key = recoveryKey(pitch.pitch_id)
  const busyRef = useRef(false)
  useEffect(() => { busyRef.current = busy !== "" }, [busy])

  // Leaving with unsaved edits asks first; Ctrl/Cmd+S saves.
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (dirty.current) { e.preventDefault(); e.returnValue = "" } }
    const keys = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (!busyRef.current) form.current?.requestSubmit() }
    }
    window.addEventListener("beforeunload", warn)
    document.addEventListener("keydown", keys)
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("keydown", keys) }
  }, [])
  // Every edit marks the pitch unsaved and keeps a recovery copy in this tab.
  function keep(next: Fields) { remember(key, JSON.stringify({ version: pitch.id, fields: payload(next, pitch) })) }
  function edit(patch: Partial<Fields>) {
    const next = { ...fields, ...patch }
    setFields(next); dirty.current = true; setSaveState("Unsaved edits"); keep(next)
  }
  // One change handler for every field: the control's name is the field's name.
  const onField = (e: { currentTarget: { name: string; value: string } }) => edit({ [e.currentTarget.name]: e.currentTarget.value })

  function recover() {
    const d = readDraft(pitch.pitch_id)
    if (!d) return
    const next = { ...fields }
    for (const [k, v] of Object.entries(d.fields)) if (k in next && k !== "duration_seconds" && typeof v === "string") next[k as keyof Fields] = v
    const duration = String(d.fields.duration_seconds)
    if (choices.lengths.map(String).includes(duration)) next.duration_seconds = duration
    else { next.duration_seconds = "custom"; next.custom_seconds = duration }
    setFields(next); dirty.current = true; setSaveState("Recovered unsaved wording"); setDraft(null); keep(next)
  }
  function discardRecovery() { forget(key); setDraft(null) }

  async function save(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy("save")
    try {
      await api("/api/pitch/" + encodeURIComponent(pitch.pitch_id), payload(fields, pitch))
      forget(key); dirty.current = false
      setSaveState("Saved")
      await onSaved("Saved as a new version. Your earlier wording is preserved.")
      setBusy("")
    } catch (err) {
      // 409: the pitch was saved somewhere else first. The edits stay here and in the recovery copy.
      if (err instanceof ApiError && err.status === 409) setConflict(err.message)
      toast(err instanceof Error ? err.message : "Unable to save this pitch.", true)
      setBusy("")
    }
  }
  async function variant() {
    setBusy("variant")
    try {
      const p = { ...payload(fields, pitch), title: (fields.title + " - variant").slice(0, 160), status: "draft", change_note: "Adapted from " + pitch.id }
      const r = await api<{ pitch_id: string }>("/api/pitches", p)
      dirty.current = false
      location.href = "/pitch/" + r.pitch_id
    } catch (err) {
      toast(err instanceof Error ? err.message : "Unable to make a variant.", true)
      setBusy("")
    }
  }
  async function restore(versionId: string) {
    if (dirty.current && !(await confirm({ title: "Restore this saved version?", body: "Your unsaved edits will be replaced. The restored wording is saved as a new version, and every earlier version is kept.", action: "Restore it", cancel: "Keep my edits" }))) return
    setBusy("restore")
    try {
      await api("/api/pitch/" + pitch.pitch_id + "/restore", { version_id: versionId, expected_version_id: pitch.id })
      dirty.current = false
      await onSaved("Restored as a new version. All previous versions are retained.")
      setBusy("")
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setConflict(err.message)
      toast(err instanceof Error ? err.message : "Unable to restore this version.", true)
      setBusy("")
    }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(fields.body); toast("Current pitch text copied.") }
    catch { bodyField.current?.focus(); bodyField.current?.select(); toast("Text selected. Press Ctrl + C to copy.") }
  }
  // The newer version is on the server; this tab's wording is in the recovery copy and comes back after the reload.
  function loadLatest() { dirty.current = false; location.reload() }

  const words = spokenWords(fields.body), seconds = spokenSeconds(words), goal = target(fields)
  const long = seconds > goal
  const prompts = openPrompts(fields.body)
  const sources = allSources ? pitch.source_details : pitch.source_details.slice(0, 5)
  const versions = allVersions ? pitch.history : pitch.history.slice(0, 5)

  return (
    <>
      {rehearsing && <Rehearsal text={fields.body} targetSeconds={goal} onExit={() => setRehearsing(false)} />}
      <form id="pitch-editor-form" ref={form} onSubmit={save} hidden={rehearsing} className={cn("flex flex-col gap-5", rehearsing && "hidden")}>
        <PageHead title={cleanName(pitch.title)} line={`${capital(pitch.audience)} · ${capital(pitch.scenario)}`}>
          <Button type="submit" size="lg" disabled={busy !== ""}>{busy === "save" ? "Saving…" : "Save pitch"}</Button>
          <Button type="button" size="lg" variant="outline" onClick={() => setRehearsing(true)}>Practice aloud</Button>
        </PageHead>

        {conflict && (
          <Panel title="A newer version was saved somewhere else">
            <p className="max-w-[60ch] text-base text-muted-foreground">{conflict}</p>
            <p className="max-w-[60ch] text-base text-muted-foreground">Your wording is kept in this tab. Load the latest version, then restore your wording to compare before saving.</p>
            <div className="flex flex-wrap gap-3">
              <Button type="button" size="lg" variant="outline" onClick={loadLatest}>Load the latest version</Button>
              <Button type="button" size="lg" variant="outline" onClick={copy}><Copy aria-hidden="true" />Copy my text first</Button>
            </div>
          </Panel>
        )}

        {draft && (
          <Panel id="pitch-recovery" title="Unsaved wording is available in this tab">
            <p className="max-w-[60ch] text-base text-muted-foreground">
              {draft.version === pitch.id ? "Restore it to the editor or keep the saved version." : "This pitch has a newer saved version. Restore your wording to compare before saving."}
            </p>
            <div className="flex flex-wrap gap-3">
              <Button type="button" size="lg" variant="outline" onClick={recover}>Restore unsaved wording</Button>
              <Button type="button" size="lg" variant="outline" onClick={discardRecovery}>Keep saved version</Button>
            </div>
          </Panel>
        )}

        <div id="pitch-edit-layout" className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
          <Panel title={pitch.format === "outline" ? "Session text & demo plan" : "Spoken draft"}
            aside={<span id="pitch-save-state" role="status" aria-live="polite" className={cn(!saveState.startsWith("Saved") && "font-semibold text-foreground")}>{saveState}</span>}>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.2fr)]">
              <Field label="Title" htmlFor="pitch-title">
                <Input id="pitch-title" name="title" required maxLength={160} value={fields.title} onChange={onField} />
              </Field>
              <Field label="Length" htmlFor="pitch-duration">
                <NativeSelect id="pitch-duration" name="duration_seconds" value={fields.duration_seconds} onChange={onField} className="w-full">
                  {choices.lengths.map((s) => <NativeSelectOption key={s} value={String(s)}>{lengthWords(s)}</NativeSelectOption>)}
                  <NativeSelectOption value="custom">Custom length</NativeSelectOption>
                </NativeSelect>
              </Field>
              <Field label="Audience" htmlFor="pitch-audience">
                <Input id="pitch-audience" name="audience" list="pitch-audiences" required maxLength={100} value={fields.audience} onChange={onField} />
              </Field>
              {fields.duration_seconds === "custom" && (
                <Field label="Custom length (seconds)" htmlFor="pitch-custom">
                  <Input id="pitch-custom" name="custom_seconds" type="number" min={10} max={7200} required value={fields.custom_seconds} onChange={onField} className="tabular-nums" />
                </Field>
              )}
            </div>
            <Field label="Pitch text" htmlFor="pitch-body"
              hint={<span id="pitch-count" aria-live="polite" className={cn(long && "font-semibold text-deadline")}>
                {words} words · about {lengthWords(seconds)} at 130 words a minute · target {lengthWords(goal)}
                {long ? " - shorten or allow more time." : fields.format === "outline" ? " - includes outline cues; allow time for demos and pauses." : " - rehearse to confirm."}
              </span>}>
              <Textarea ref={bodyField} id="pitch-body" name="body" required maxLength={40000} rows={13} value={fields.body} onChange={onField}
                className="max-h-[70svh] min-h-80 overflow-y-auto leading-relaxed md:text-base" />
            </Field>
            <p className="text-sm text-muted-foreground">Saving keeps the previous version. Ctrl or Cmd + S saves.</p>
            <Disclosure label="Delivery notes & settings" className="border-t pt-2">
              <div className="flex flex-col gap-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Scenario" htmlFor="pitch-scenario">
                    <Input id="pitch-scenario" name="scenario" list="pitch-scenarios" required maxLength={100} value={fields.scenario} onChange={onField} />
                  </Field>
                  <Field label="Speaker" htmlFor="pitch-speaker">
                    <Input id="pitch-speaker" name="speaker" maxLength={100} placeholder="Bao, Daniel, or a team handoff" value={fields.speaker} onChange={onField} />
                  </Field>
                  <Field label="Format" htmlFor="pitch-format">
                    <NativeSelect id="pitch-format" name="format" value={fields.format} onChange={onField} className="w-full">
                      {FORMATS.map(([v, l]) => <NativeSelectOption key={v} value={v}>{l}</NativeSelectOption>)}
                    </NativeSelect>
                  </Field>
                  <Field label="Stage" htmlFor="pitch-status">
                    <NativeSelect id="pitch-status" name="status" value={fields.status} onChange={onField} className="w-full">
                      {STAGES.map((v) => <NativeSelectOption key={v} value={v}>{stageWords(v)}</NativeSelectOption>)}
                    </NativeSelect>
                  </Field>
                </div>
                <Field label="Speaker notes" htmlFor="pitch-notes">
                  <Textarea id="pitch-notes" name="notes" maxLength={10000} rows={5} placeholder="Delivery cues, demonstrations, or claims to check" value={fields.notes} onChange={onField} className="max-h-[50svh] overflow-y-auto md:text-base" />
                </Field>
                <Field label="What changed? (optional)" htmlFor="pitch-change">
                  <Input id="pitch-change" name="change_note" maxLength={300} placeholder="e.g. Clearer investor ask" value={fields.change_note} onChange={onField} />
                </Field>
              </div>
            </Disclosure>
            <Disclosure label="More with this pitch" className="border-t pt-2">
              <div className="flex flex-col items-start gap-2">
                <Button type="button" size="lg" variant="outline" onClick={copy}><Copy aria-hidden="true" />Copy text</Button>
                <Button size="lg" variant="outline" asChild><a href={`/api/pitch/${encodeURIComponent(pitch.pitch_id)}/export`}><Download aria-hidden="true" />Download as text file</a></Button>
                <Button type="button" size="lg" variant="outline" onClick={variant} disabled={busy !== ""}>{busy === "variant" ? "Making a variant…" : "Make a variant"}</Button>
              </div>
            </Disclosure>
          </Panel>

          <div className="flex flex-col gap-5">
            <Panel title="For this audience">
              <p className="max-w-[60ch] text-base whitespace-pre-wrap">{pitch.notes || "Use Delivery notes to record the decision this audience should make and the proof they need."}</p>
              <div id="pitch-open-prompts" className="flex flex-col gap-1">
                {prompts.length ? (
                  <>
                    <span className="text-sm text-muted-foreground">{plural(prompts.length, "open prompt")} still in the text</span>
                    <ul className="flex flex-col">
                      {prompts.map((p) => <li key={p} className="border-t py-2 text-base font-semibold break-words first:border-t-0">{p}</li>)}
                    </ul>
                  </>
                ) : <p className="text-base text-muted-foreground">Read it aloud. Does it sound like something you would actually say?</p>}
              </div>
              <div><Button size="lg" variant="outline" asChild><a href={`/pitch-lab?coach=${encodeURIComponent(pitch.pitch_id)}`}>Get coached</a></Button></div>
            </Panel>

            <Panel title="Version history" aside={`${plural(pitch.history.length, "saved version")}. Restoring makes a new one.`}>
              <ul aria-label="Saved versions" className="flex flex-col">
                {versions.map((v) => (
                  <li key={v.id} className="flex flex-col gap-1 border-t py-3 first:border-t-0 first:pt-0">
                    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="text-base font-semibold tabular-nums">{stamp(v.created_at)}</span>
                      {v.id === pitch.history[0].id && <Tag tone="good">Current</Tag>}
                    </span>
                    <span className="max-w-[60ch] text-base text-muted-foreground">{v.change_note || "Saved edits"} · {capital(v.format)}</span>
                    <span className="flex flex-wrap items-center gap-x-5 gap-y-1">
                      {v.id !== pitch.history[0].id && <Button type="button" size="lg" variant="outline" disabled={busy !== ""} onClick={() => restore(v.id)}>Restore as new version</Button>}
                      <a href={`/api/pitch/${encodeURIComponent(pitch.pitch_id)}/export?version=${encodeURIComponent(v.id)}`} className={LINK}>Read as text</a>
                    </span>
                  </li>
                ))}
              </ul>
              {pitch.history.length > 5 && !allVersions && <div><Button type="button" size="lg" variant="outline" onClick={() => setAllVersions(true)}>Show all {pitch.history.length} versions</Button></div>}
            </Panel>

            <Panel title="Source material" aside={pitch.source_details.length ? plural(pitch.source_details.length, "source") : undefined}>
              {pitch.source_details.length ? (
                <ul aria-label="Sources" className="flex flex-col">
                  {sources.map((src, i) => (
                    <li key={src.original_path + i} className="flex flex-col border-t py-3 first:border-t-0 first:pt-0">
                      <span className="text-base font-semibold break-words">{sourceTitle(src.original_path)}</span>
                      <span className="text-sm text-muted-foreground">Captured {stamp(src.captured_at)}</span>
                      {src.material_id && <span><a href={"/material/" + encodeURIComponent(src.material_id)} className={LINK}>Read source</a></span>}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-base text-muted-foreground">No source attached. This is your own working draft.</p>}
              {pitch.source_details.length > 5 && !allSources && <div><Button type="button" size="lg" variant="outline" onClick={() => setAllSources(true)}>Show all {pitch.source_details.length} sources</Button></div>}
              {pitch.claim_details.length > 0 && (
                <Disclosure label="Linked company claims" className="border-t pt-2">
                  <ul className="flex flex-col">
                    {pitch.claim_details.map((c) => (
                      <li key={c.id} className="flex flex-col gap-0.5 border-t py-3 first:border-t-0">
                        <span className="text-base font-semibold">{c.label}</span>
                        <span className="text-base">{c.body}</span>
                        <span className="text-sm text-muted-foreground">{c.id === c.canonical_version_id ? "Canonical version" : "Historical version"} · {c.status || "Unreviewed"}</span>
                      </li>
                    ))}
                  </ul>
                </Disclosure>
              )}
            </Panel>
          </div>
        </div>
      </form>
    </>
  )
}

export function PitchEditorPage({ id }: { id: string }) {
  const { toast } = useFeedback()
  useListCrumb(PITCH_LIBRARY_KEY, "/pitches")
  const state = useLoad(async () => {
    const [choices, pitch] = await Promise.all([api<PitchChoices>("/api/pitches"), api<Pitch>("/api/pitch/" + encodeURIComponent(id))])
    return { choices, pitch }
  }, [id])
  return (
    <Shell active="Pitch" tab="/pitches" title="Pitch editor" crumb={cleanName(state.data?.pitch.title) || "Pitch"}>
      <LoadGate state={state}>
        {({ choices, pitch }) => (
          <>
            {/* A new version id remounts the editor: fresh fields, clean state (the old app re-rendered it). */}
            <Editor key={pitch.id} pitch={pitch} choices={choices}
              onSaved={async (message) => {
                if (await state.reload()) toast(message)
                else toast("That was saved, but the page did not refresh. Reload before editing again.", true)
              }} />
            <Choices choices={choices} />
          </>
        )}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { prefix: { "/pitch/": (id) => <PitchEditorPage id={id} /> } }
