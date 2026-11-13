// Shared data code for the Pitch Studio pages and the Materials pages (old pitch.js and app.js materials()).
import { useEffect } from "react"

import { pitchLength } from "@/lib/format"

export type PitchItem = {
  id: string; pitch_id: string; title: string; audience: string; scenario: string; preview: string
  word_count: number; duration_seconds: number; estimated_seconds: number; status: string; format: string
  placeholders: string[]
}
export type PitchChoices = { items: PitchItem[]; audiences: string[]; scenarios: string[]; lengths: number[] }

export type Pitch = {
  id: string; pitch_id: string; title: string; audience: string; scenario: string; speaker: string
  format: string; status: string; duration_seconds: number; body: string; notes: string; created_at: string
  sources: string[]; claim_versions: string[]
  source_details: { original_path: string; captured_at: string; material_id?: string | null }[]
  claim_details: { id: string; label: string; body: string; canonical_version_id: string; status?: string | null }[]
  history: { id: string; created_at: string; change_note?: string | null; format: string }[]
}

export type MaterialItem = { id: string; relative_path: string; kind: string; extraction: string; size_bytes: number; duplicates: number }
export type MaterialList = {
  stats: { unique_files: number; searchable_text?: number; kinds: { kind: string; count: number }[] }
  total: number; limit: number; items: MaterialItem[]
}
export type Material = {
  relative_path: string; kind: string; size_bytes: number; source_path: string; source_version_id?: string | null
  sha256?: string | null; aliases: { source_path: string }[]; body?: string | null
}
export type Answer = { id?: string; prompt: string; status: string; body: string; limit_value?: number | null; limit_unit?: string | null; created_at: string }

// "30 sec", "3 min", "1 min 30 sec"; "Choose a length" when there is none (old pitchLength()).
export const lengthWords = (s: number) => (Number.isFinite(s) && s > 0 ? pitchLength(Math.round(s)) : "Choose a length")

export const stageWords = (s: string) => ({ draft: "Draft", rehearsal_ready: "Ready for rehearsal", archived: "Archived" } as Record<string, string>)[s] || s
export const STAGES = ["draft", "rehearsal_ready", "archived"]
export const FORMATS: [string, string][] = [["script", "Script"], ["outline", "Outline"]]

// The last part of a Windows or POSIX path: the file's own name.
export const fileName = (path: string) => String(path || "").split(/[\\/]/).at(-1) || ""

// A source's plain title for a list: the file's name without its extension, dashes and underscores as spaces
// (a date keeps its dashes), first letter capital. "pitch-editorial-2026-10-09.json" -> "Pitch editorial 2026-10-09".
// A source that is a note, not a file, reads as written.
export function sourceTitle(path: string) {
  const name = fileName(path).replace(/\.[A-Za-z][A-Za-z0-9]{1,4}$/, "").replace(/_+/g, " ")
    .replace(/(\D)-+|-+(?=\D)/g, (_m, before) => (before || "") + " ").replace(/\s+/g, " ").trim()
  return name ? name[0].toUpperCase() + name.slice(1) : "Source"
}

// Spoken words, counted the way the old editor did (Unicode letters and digits, joined by ' ’ -).
export const spokenWords = (text: string) => (text.match(/[\p{L}\p{N}_]+(?:['’-][\p{L}\p{N}_]+)*/gu) || []).length
// Seconds to say it at 130 words a minute.
export const spokenSeconds = (words: number) => Math.round((words / 130) * 60)
// The [open prompts] still in the text, each once.
export const openPrompts = (text: string) => [...new Set(text.match(/\[[^\]\n]{1,250}\]/g) || [])]

// "00:00" for the rehearsal stopwatch.
export const clock = (seconds: number) => String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0")

// Session storage that never throws (private windows, blocked storage).
export const remember = (key: string, value: string) => { try { sessionStorage.setItem(key, value) } catch { /* not kept */ } }
export const recall = (key: string) => { try { return sessionStorage.getItem(key) } catch { return null } }
export const forget = (key: string) => { try { sessionStorage.removeItem(key) } catch { /* nothing to remove */ } }

export const PITCH_LIBRARY_KEY = "astory-pitch-library"
export const MATERIALS_LIST_KEY = "astory-materials-list"
export const recoveryKey = (pitchId: string) => "astory-pitch-recovery:" + pitchId

// The classes for a plain text link that is still 44px tall.
export const LINK = "inline-flex min-h-11 items-center rounded-md font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid"

// The folder a file sits in, in plain words: "Powerpoint Design / Final final final".
export const folderWords = (path: string) => String(path || "").split(/[\\/]/).slice(0, -1).join(" / ")

// Labels made by the importers carry em dashes (a question, a dash, "2,500 characters"); the house style is " - ".
export const plainLabel = (text: string) => String(text || "").replace(/\s*[—–]\s*/g, " - ")

// "general" and "General" are one audience: show it with a capital, list it once.
export const capital = (text: string) => { const t = String(text || "").trim(); return t ? t[0].toUpperCase() + t.slice(1) : "" }
export function uniqueWords(values: string[]) {
  const seen = new Set<string>()
  return values.filter((v) => { const k = v.trim().toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true })
}

// The breadcrumb's parent link goes back to the list as Bao last had it (its search and page), when this tab
// remembers one. The shell draws the link; this points it at the remembered address (the old app did the same).
export function useListCrumb(key: string, path: string) {
  useEffect(() => {
    const last = recall(key)
    if (!last || !last.startsWith(path)) return
    const link = document.querySelector<HTMLAnchorElement>('nav[aria-label="Where you are"] a')
    if (link) link.href = last
  })
}
