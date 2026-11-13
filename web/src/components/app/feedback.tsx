import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

// Messages, confirmations and questions for every page. They replace the old app's toast(), confirm() and prompt().
// - toast(text) / toast(text, true): one message at the foot of the screen; the next one replaces it.
// - confirm({...}): resolves true only when Bao presses the action button. Use it before anything that can't be undone,
//   sends something outside, or changes what the agents treat as true.
// - ask({...}): a short written answer (old prompt()); resolves null when cancelled.

type ConfirmOpts = { title: string; body?: ReactNode; action: string; danger?: boolean; cancel?: string }
type AskOpts = { title: string; body?: ReactNode; label: string; action: string; initial?: string; required?: boolean }
type Ctx = {
  toast: (text: string, error?: boolean) => void
  confirm: (o: ConfirmOpts) => Promise<boolean>
  ask: (o: AskOpts) => Promise<string | null>
}
const FeedbackContext = createContext<Ctx | null>(null)

export function useFeedback() {
  const c = useContext(FeedbackContext)
  if (!c) throw new Error("useFeedback needs <Feedback>")
  return c
}

export function Feedback({ children }: { children: ReactNode }) {
  const [note, setNote] = useState<{ text: string; error: boolean; id: number } | null>(null)
  const [conf, setConf] = useState<ConfirmOpts | null>(null)
  const [question, setQuestion] = useState<AskOpts | null>(null)
  const [answer, setAnswer] = useState("")
  const settle = useRef<((v: any) => void) | null>(null) // eslint-disable-line @typescript-eslint/no-explicit-any

  const toast = useCallback((text: string, error = false) => setNote({ text, error, id: Date.now() }), [])
  const confirm = useCallback((o: ConfirmOpts) => new Promise<boolean>((res) => { settle.current = res; setConf(o) }), [])
  const ask = useCallback((o: AskOpts) => new Promise<string | null>((res) => { settle.current = res; setAnswer(o.initial || ""); setQuestion(o) }), [])
  const close = (v: unknown) => { settle.current?.(v); settle.current = null; setConf(null); setQuestion(null) }

  return (
    <FeedbackContext.Provider value={{ toast, confirm, ask }}>
      {children}
      <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center p-4">
        {note && (
          <div key={note.id} className={cn("toast-in pointer-events-auto flex max-w-[44rem] items-center gap-4 rounded-lg border bg-card px-4 py-3 text-base shadow-lg",
            note.error ? "border-deadline/40 text-deadline" : "text-foreground")}>
            <span className={cn(note.error && "font-semibold")}>{note.text}</span>
            <button type="button" onClick={() => setNote(null)} className="-my-2 -mr-2 flex min-h-11 items-center rounded-md px-2 text-sm font-semibold text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">Dismiss</button>
          </div>
        )}
      </div>

      <Dialog open={!!conf} onOpenChange={(o) => { if (!o) close(false) }}>
        {conf && (
          <DialogContent className="sm:max-w-[32rem]">
            <DialogHeader>
              <DialogTitle className="text-xl">{conf.title}</DialogTitle>
              {conf.body && <DialogDescription asChild><div className="text-base text-muted-foreground">{conf.body}</div></DialogDescription>}
            </DialogHeader>
            <DialogFooter className="gap-2">
              <Button size="lg" variant="outline" onClick={() => close(false)}>{conf.cancel || "Cancel"}</Button>
              <Button size="lg" variant={conf.danger ? "destructive" : "default"} onClick={() => close(true)}>{conf.action}</Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>

      <Dialog open={!!question} onOpenChange={(o) => { if (!o) close(null) }}>
        {question && (
          <DialogContent className="sm:max-w-[36rem]">
            <form onSubmit={(e) => { e.preventDefault(); if (!question.required || answer.trim()) close(answer.trim()) }} className="grid gap-4">
              <DialogHeader>
                <DialogTitle className="text-xl">{question.title}</DialogTitle>
                {question.body && <DialogDescription asChild><div className="text-base text-muted-foreground">{question.body}</div></DialogDescription>}
              </DialogHeader>
              <div className="grid gap-2">
                <Label htmlFor="ask-answer">{question.label}</Label>
                <Textarea id="ask-answer" value={answer} onChange={(e) => setAnswer(e.target.value)} autoFocus />
              </div>
              <DialogFooter className="gap-2">
                <Button type="button" size="lg" variant="outline" onClick={() => close(null)}>Cancel</Button>
                <Button type="submit" size="lg" disabled={question.required && !answer.trim()}>{question.action}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        )}
      </Dialog>
    </FeedbackContext.Provider>
  )
}
