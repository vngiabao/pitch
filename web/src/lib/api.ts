// The one way every page talks to the Founder OS server. It mirrors the old app's helper (app.js api()):
// GET when there is no body, POST with the owner's CSRF token when there is one, a 20 second timeout,
// and the same plain-word errors. The server refuses an empty POST body, so actions with no fields send {}.
/* eslint-disable @typescript-eslint/no-explicit-any */

const csrf = () => document.querySelector<HTMLMetaElement>('meta[name="founder-csrf"]')?.content || ""

export class ApiError extends Error {
  status: number
  constructor(message: string, status = 0) { super(message); this.status = status }
}

export async function api<T = any>(path: string, body?: unknown): Promise<T> {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), 20000)
  let r: Response
  try {
    r = await fetch(path, body === undefined
      ? { credentials: "same-origin", headers: { Accept: "application/json" }, signal: ctl.signal }
      : { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Founder-CSRF": csrf() }, body: JSON.stringify(body ?? {}), signal: ctl.signal })
  } catch (e: any) {
    throw new ApiError(e?.name === "AbortError"
      ? "The workspace took too long to respond. Try again."
      : "The workspace is offline. Check that your PC is awake and online, then reload.")
  } finally { clearTimeout(timer) }
  let v: any
  try { v = await r.json() } catch {
    throw new ApiError("Your sign-in expired or the server returned an unexpected page. Reload to sign in again.", r.status)
  }
  if (!r.ok) throw new ApiError(v?.error || "Unable to complete this action.", r.status)
  return v as T
}

// GETs that several parts of one page share are fetched once per page load (old apiOnce()).
const once = new Map<string, Promise<any>>()
export function apiOnce<T = any>(path: string): Promise<T> {
  if (!once.has(path)) once.set(path, api<T>(path).catch((e) => { once.delete(path); throw e }))
  return once.get(path)!
}
export const clearOnce = () => once.clear()
