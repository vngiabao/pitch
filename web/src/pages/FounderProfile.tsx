import { useRef, useState, type FormEvent, type RefObject } from "react"
import { Eye } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { useFeedback } from "@/components/app/feedback"
import { Field, LoadGate, PageHead, Panel, useLoad, evenBottoms } from "@/components/app/page"
import { twoColumns } from "@/lib/agents"
import { api } from "@/lib/api"
import { GROUP_BLURBS, loadProfile, profileExample, profileInputType, type ProfileField, type ProfileNeed } from "@/lib/company"
import { day, plural } from "@/lib/format"
import type { PageRoutes } from "@/lib/route-types"
import { Shell } from "@/shell"
import { Disclosure } from "@/pages/Decisions"

const errorText = (e: unknown) => (e instanceof Error ? e.message : "Unable to complete this action.")

type Acts = {
  busy: string | null
  saveForm: (form: HTMLFormElement, key: string) => void
  clear: (key: string) => void
  remove: (key: string) => void
  add: (label: string, value: string, sensitive: boolean) => void
}

// What was typed in a form: the boxes Bao changed that hold a value. `blank` says a changed box was left empty.
function typed(form: HTMLFormElement) {
  const facts: { key: string; value: string }[] = []
  let blank = false
  form.querySelectorAll<HTMLInputElement>("input[data-key]").forEach((el) => {
    if (el.dataset.dirty !== "1") return
    if (el.value.trim()) facts.push({ key: el.dataset.key!, value: el.value })
    else blank = true
  })
  return { facts, blank }
}

// The box for one fact. Its value lives in the box itself, never in the page's state, so a private value that was
// revealed or typed is gone as soon as the page is read again or left. A date of birth gets a date box like any
// other date; every other private fact is plain text. The placeholder is a short example of the format, or empty.
function FactBox({ f, id, box }: { f: ProfileField; id: string; box?: RefObject<HTMLInputElement | null> }) {
  const kind = profileInputType(f.key)
  const type = f.sensitive && kind !== "date" ? "text" : kind
  return (
    <Input ref={box} id={id} data-key={f.key} type={type} defaultValue={f.sensitive ? "" : f.value || ""} maxLength={2000}
      onInput={(e) => { e.currentTarget.dataset.dirty = "1" }} className="md:text-base"
      autoComplete={f.sensitive ? "off" : undefined} spellCheck={f.sensitive ? false : undefined}
      max={type === "date" ? "2100-12-31" : undefined}
      placeholder={f.sensitive && f.set ? "Hidden. Reveal to see it, or type a new value" : type === "url" ? "https://" : type === "date" ? undefined : profileExample(f.key)} />
  )
}

// One fact in its section: the name, the box, and for a saved fact its state and the ways to see or clear it.
function FactCell({ f, acts }: { f: ProfileField; acts: Acts }) {
  const { toast } = useFeedback()
  const [revealed, setRevealed] = useState(false)
  const [revealing, setRevealing] = useState(false)
  const box = useRef<HTMLInputElement>(null)
  const id = `fp-${f.key}`

  // The private value goes straight from the server into the box. It is not kept anywhere else.
  const reveal = async () => {
    setRevealing(true)
    try {
      const r = await api<{ value?: string }>("/api/founder-profile-reveal", { key: f.key })
      if (box.current) {
        // A date box can only show a year-month-day value; a date saved in other words is shown as text.
        if (box.current.type === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(r.value ?? "")) box.current.type = "text"
        box.current.value = r.value ?? ""
        box.current.focus()
      }
      setRevealed(true)
    } catch (e) { toast(errorText(e), true) } finally { setRevealing(false) }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <label htmlFor={id} className="text-sm font-medium">{f.label}</label>
        {f.set && (
          <span className="text-sm text-muted-foreground">
            {f.sensitive
              ? revealed ? "Shown until you leave this page" : <span aria-label="Saved, hidden">{f.masked}</span>
              : <span className="font-medium text-good">Saved</span>}
            {f.updated_at && <> · <time dateTime={f.updated_at}>{day(f.updated_at)}</time></>}
          </span>
        )}
      </div>
      <FactBox f={f} id={id} box={box} />
      {(f.set || f.custom) && (
        <div className="flex flex-wrap gap-2">
          {f.set && f.sensitive && !revealed && (
            <Button type="button" size="lg" variant="outline" disabled={revealing} onClick={reveal}><Eye aria-hidden="true" />{revealing ? "Opening…" : "Reveal"}</Button>
          )}
          {f.set && <Button type="button" size="lg" variant="outline" disabled={acts.busy === f.key} onClick={() => acts.clear(f.key)}>Clear</Button>}
          {f.custom && <Button type="button" size="lg" variant="outline" disabled={acts.busy === f.key} onClick={() => acts.remove(f.key)}>Remove</Button>}
        </div>
      )}
    </div>
  )
}

// The page opens here: the few facts worth typing first, with the one primary action.
function DoNext({ needs, fromApplications, acts }: { needs: ProfileNeed[]; fromApplications: boolean; acts: Acts }) {
  const saving = acts.busy === "next"
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); acts.saveForm(e.currentTarget, "next") }
  return (
    <Panel title="Do next" aside={fromApplications ? "Your open applications ask for these" : "Most forms ask for these"}>
      <form onSubmit={submit} className="flex flex-col gap-5">
        <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
          {needs.map(({ field: f, programs }) => (
            <div key={f.key} className="flex flex-col gap-2">
              <label htmlFor={`next-${f.key}`} className="text-base font-semibold">{f.label}</label>
              <FactBox f={f} id={`next-${f.key}`} />
              {programs.length > 0 && (
                <p className="text-sm text-muted-foreground">Asked by {programs[0]}{programs.length > 1 ? ` and ${programs.length - 1} more` : ""}</p>
              )}
            </div>
          ))}
        </div>
        <Button type="submit" size="lg" className="self-start" disabled={saving}>{saving ? "Saving…" : "Save these facts"}</Button>
      </form>
    </Panel>
  )
}

function AddFact({ acts }: { acts: Acts }) {
  const [label, setLabel] = useState("")
  const [value, setValue] = useState("")
  const [sensitive, setSensitive] = useState(false)
  const saving = acts.busy === "add"
  const submit = (e: FormEvent) => { e.preventDefault(); acts.add(label, value, sensitive) }
  return (
    <Disclosure summary="Add another fact">
      <form onSubmit={submit} className="flex flex-col gap-4 rounded-lg bg-secondary p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="What the form calls it" htmlFor="fp-add-label">
            <Input id="fp-add-label" value={label} onChange={(e) => setLabel(e.target.value)} required maxLength={120} placeholder="e.g. Deepgram project ID" className="md:text-base" />
          </Field>
          <Field label="Value" htmlFor="fp-add-value">
            <Input id="fp-add-value" value={value} onChange={(e) => setValue(e.target.value)} required maxLength={2000} autoComplete="off" className="md:text-base" />
          </Field>
        </div>
        <label className="flex min-h-11 items-center gap-3 text-base">
          <Checkbox checked={sensitive} onCheckedChange={(v) => setSensitive(v === true)} />
          Private: mask it on this page and keep it out of AI drafts
        </label>
        <p className="max-w-[70ch] text-sm text-muted-foreground">Never bank account, routing or card numbers. Enter those on the official form yourself.</p>
        <Button type="submit" size="lg" variant="outline" className="self-start" disabled={saving}>{saving ? "Saving…" : "Save fact"}</Button>
      </form>
    </Disclosure>
  )
}

// One section of the profile: one line on what it is for, its facts two across, and one Save for all of them.
function Group({ name, fields, acts }: { name: string; fields: ProfileField[]; acts: Acts }) {
  const saving = acts.busy === `group:${name}`
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); acts.saveForm(e.currentTarget, `group:${name}`) }
  return (
    <Panel title={name} aside={fields.length ? `${fields.filter((f) => f.set).length} of ${fields.length} filled` : undefined}>
      {GROUP_BLURBS[name] && <p className="max-w-[70ch] text-base text-muted-foreground">{GROUP_BLURBS[name]}</p>}
      {fields.length > 0 && (
        <form onSubmit={submit} className="flex flex-col gap-5">
          <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2">{fields.map((f) => <FactCell key={f.key} f={f} acts={acts} />)}</div>
          <Button type="submit" size="lg" variant="outline" className="self-start" disabled={saving} aria-label={`Save ${name}`}>{saving ? "Saving…" : "Save this section"}</Button>
        </form>
      )}
      {name === "Other" && <AddFact acts={acts} />}
    </Panel>
  )
}

export function FounderProfilePage() {
  const state = useLoad(loadProfile)
  const { toast, confirm } = useFeedback()
  const [busy, setBusy] = useState<string | null>(null)
  // Every successful action reads the page again and redraws every box from it, so a revealed value never outlives it.
  const [stamp, setStamp] = useState(0)

  const act = async (key: string, run: () => Promise<string>) => {
    setBusy(key)
    try { const done = await run(); await state.reload(); setStamp((n) => n + 1); toast(done) }
    catch (e) { toast(errorText(e), true) }
    finally { setBusy(null) }
  }
  const answersWords = (n: number) => (n ? ` ${plural(n, "application answer")} filled from your profile.` : "")

  const acts: Acts = {
    busy,
    // Saves each changed fact with the old page's call, one after the other, then reads the page again.
    saveForm: async (form, key) => {
      const { facts, blank } = typed(form)
      if (!facts.length) { toast(blank ? "Type a value first, or use Clear to empty this field." : "Type a value first, then save.", true); return }
      setBusy(key)
      let saved = 0, filled = 0
      try {
        for (const x of facts) { const r = await api<{ filled?: number }>("/api/founder-profile", { key: x.key, value: x.value }); saved++; filled += r.filled || 0 }
        await state.reload()
        setStamp((n) => n + 1)
        toast(`Saved${saved > 1 ? ` ${saved} facts` : ""}.${answersWords(filled)}`)
      } catch (e) {
        if (saved) await state.reload()
        toast(errorText(e), true)
      } finally { setBusy(null) }
    },
    clear: async (key) => {
      const ok = await confirm({
        title: "Clear this saved value?", action: "Clear it", danger: true,
        body: "Questions it answered keep their current answers until you change them.",
      })
      if (ok) void act(key, async () => { await api("/api/founder-profile", { key, value: "" }); return "Cleared." })
    },
    remove: async (key) => {
      const ok = await confirm({ title: "Remove this fact from your profile?", action: "Remove it", danger: true, body: "The fact and its saved value are deleted." })
      if (ok) void act(key, async () => { await api("/api/founder-profile-delete", { key }); return "Removed." })
    },
    add: (label, value, sensitive) => {
      void act("add", async () => { const r = await api<{ filled?: number }>("/api/founder-profile", { label, value, sensitive }); return `Saved.${answersWords(r.filled || 0)}` })
    },
  }

  return (
    <Shell active="Company" tab="/founder-profile" title="Founder profile">
      <LoadGate state={state}>
        {({ profile: b, needs, fromApplications }) => {
          const groups = b.groups.map((g) => ({ name: g, fields: b.fields.filter((f) => f.group === g) }))
          const [left, right] = twoColumns(groups, (g) => Math.ceil(g.fields.length / 2) + 2)
          return (
            <>
              <PageHead title="Founder profile"
                line={`${b.filled} of ${b.total} filled.${fromApplications ? ` Your open applications still ask for ${plural(needs.length, "fact")}.` : ""}`} />
              <div key={stamp} className="flex flex-col gap-5">
                {needs.length > 0 && <DoNext needs={needs} fromApplications={fromApplications} acts={acts} />}
                <div ref={evenBottoms} className="grid items-start gap-5 xl:grid-cols-2">
                  <div className="flex flex-col gap-5">{left.map((g) => <Group key={g.name} name={g.name} fields={g.fields} acts={acts} />)}</div>
                  <div className="flex flex-col gap-5">{right.map((g) => <Group key={g.name} name={g.name} fields={g.fields} acts={acts} />)}</div>
                </div>
              </div>
            </>
          )
        }}
      </LoadGate>
    </Shell>
  )
}

export const routes: PageRoutes = { exact: { "/founder-profile": () => <FounderProfilePage /> } }
