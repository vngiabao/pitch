import { createContext, useContext, useId, useState, type ComponentProps, type FormEvent, type ReactNode } from "react"
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react"

import { Field } from "@/components/app/page"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { formBody, type Growth } from "@/lib/growth"
import { cn } from "@/lib/utils"

// What every part of the desk shares: the data, the one way to run an action (call, reload, toast),
// which action is running, and the anchor Bao asked to see (#deal-<id>, #campaign-<key>, ...).
export type Target = { id: string; n: number }
export type DeskCtx = {
  b: Growth
  busy: string | null
  act: (key: string, run: () => Promise<unknown>, done: string) => Promise<boolean>
  target: Target
  go: (id: string) => void
}
const Ctx = createContext<DeskCtx | null>(null)
export const DeskProvider = Ctx.Provider
export function useDesk() {
  const c = useContext(Ctx)
  if (!c) throw new Error("useDesk needs <DeskProvider>")
  return c
}

// Runs `open` once each time Bao follows a link to this element (also when the page loads on its anchor), so the
// part can open itself. It compares during render, React's way to adjust state when something outside changes.
export function useAsked(id: string, open: () => void) {
  const { target } = useDesk()
  const [seen, setSeen] = useState(-1)
  if (target.id === id && seen !== target.n) { setSeen(target.n); open() }
}

// Long detail stays closed until asked for: one quiet control, the content under it on the same left edge.
export function More({ label, closeLabel, defaultOpen = false, open: forced, children, className }: { label: string; closeLabel?: string; defaultOpen?: boolean; open?: boolean; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(defaultOpen || !!forced)
  const [wasForced, setWasForced] = useState(!!forced)
  const id = useId()
  if (!!forced !== wasForced) { setWasForced(!!forced); if (forced) setOpen(true) }
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <Button type="button" variant="outline" size="lg" aria-expanded={open} aria-controls={id} className="self-start" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}{open ? closeLabel || label : label}
      </Button>
      {open && <div id={id} className="flex flex-col gap-4">{children}</div>}
    </div>
  )
}

// A link that leaves Founder OS: opens in a new tab and says so.
export function ExtLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="inline-flex min-h-11 items-center gap-1.5 rounded-md text-base font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">
      {children}<ExternalLink className="size-4 shrink-0" aria-hidden="true" /><span className="sr-only">(opens in a new tab)</span>
    </a>
  )
}

// A small heading inside a panel (panels are not nested; space and hairlines separate).
export const SubHead = ({ children }: { children: ReactNode }) => <h4 className="text-base font-semibold">{children}</h4>

// A short note inside a panel that says where something stands: a bold lead, then one or two sentences.
export function Note({ lead, children }: { lead: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg bg-secondary px-4 py-3 text-base">
      <p className="max-w-[70ch]"><span className="font-semibold">{lead}</span> {children}</p>
    </div>
  )
}

// The words families use, as quiet chips.
export function Words({ words }: { words: string[] }) {
  if (!words.length) return null
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-muted-foreground">Their words</span>
      <ul className="flex flex-wrap gap-2">
        {words.map((w) => <li key={w} className="inline-flex min-h-7 items-center rounded-md bg-secondary px-2 text-sm">{w}</li>)}
      </ul>
    </div>
  )
}

// A form's grid of short fields: one column on a phone, more as the panel widens.
export const FormGrid = ({ children }: { children: ReactNode }) => <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{children}</div>

// A labelled input, textarea or select for the desk's forms. Values go to the server as typed (strings).
export function In({ label, hint, className, ...props }: { label: string; hint?: string } & ComponentProps<"input">) {
  const id = useId()
  return <Field label={label} hint={hint} htmlFor={id} className={className}><Input id={id} {...props} /></Field>
}
export function Area({ label, hint, className, ...props }: { label: string; hint?: string } & ComponentProps<"textarea">) {
  const id = useId()
  return <Field label={label} hint={hint} htmlFor={id} className={className}><Textarea id={id} {...props} /></Field>
}
export function Pick({ label, options, className, ...props }: { label: string; options: [string, string][] } & Omit<ComponentProps<"select">, "size">) {
  const id = useId()
  return (
    <Field label={label} htmlFor={id} className={className}>
      <NativeSelect id={id} className="w-full" {...props}>
        {options.map(([value, text]) => <NativeSelectOption key={value} value={value}>{text}</NativeSelectOption>)}
      </NativeSelect>
    </Field>
  )
}

// A button that runs one of the desk's actions: off while any action runs, and it says what is happening.
export function Act({ k, children, busyLabel = "Saving…", disabled, ...props }: { k: string; busyLabel?: string } & ComponentProps<typeof Button>) {
  const { busy } = useDesk()
  return <Button type="button" variant="outline" size="lg" {...props} disabled={disabled || busy !== null}>{busy === k ? busyLabel : children}</Button>
}

// Submit a form the way the old page did: the form's fields plus the record's id or key, then reload and say so.
export function useSubmit() {
  const { act } = useDesk()
  return (k: string, path: string, extra: Record<string, string>, done: string) => async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    if (await act(k, () => api(path, { ...extra, ...formBody(form) }), done)) form.reset()
  }
}
