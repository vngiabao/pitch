import type { ReactNode } from "react"

import type { PageRoutes } from "@/lib/route-types"

// Path -> page. Every file in src/pages exports `routes` (see lib/route-types.ts) and is picked up here, so adding a
// page never means editing a shared file. The server serves this app for the paths in NEXT_EXACT / NEXT_PREFIX in
// founder_os/server.py; a page goes live when its path is added there.
const files = import.meta.glob<{ routes?: PageRoutes }>("./pages/*.tsx", { eager: true })

const exact: Record<string, () => ReactNode> = {}
const prefix: [string, (id: string) => ReactNode][] = []
for (const file of Object.values(files)) {
  Object.assign(exact, file.routes?.exact)
  for (const entry of Object.entries(file.routes?.prefix || {})) prefix.push(entry)
}
prefix.sort((a, b) => b[0].length - a[0].length)

export function match(path: string): ReactNode | null {
  if (exact[path]) return exact[path]()
  for (const [start, page] of prefix) if (path.startsWith(start) && path.length > start.length) {
    let id = path.slice(start.length)
    try { id = decodeURIComponent(id) } catch { /* keep the raw id; the page shows "not found" */ }
    return page(id)
  }
  return null
}
