import { useEffect, type ReactNode } from "react"
import { ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { logoFor } from "@/lib/today"

// The six departments and the pages under each. Every page of Founder OS shares this shell: the name in type
// (no logo mark, at Bao's word, Nov 11), the departments, today's date, the department's pages, then the page.
export type Dept = "Today" | "Funding" | "Pitch" | "Customers" | "Company" | "Agents"

export const DEPTS: [Dept, string][] = [
  ["Today", "/today"], ["Funding", "/funding"], ["Pitch", "/pitch-lab"],
  ["Customers", "/growth"], ["Company", "/decisions"], ["Agents", "/activity"],
]

export const PAGES: Record<Dept, [string, string][]> = {
  Today: [],
  Funding: [["/funding", "Needs you"], ["/opportunities", "Pipeline"], ["/applications", "Applications"], ["/credits", "Credits"], ["/money", "Money map"]],
  Pitch: [["/pitch-lab", "Pitch Lab"], ["/pitches", "Pitch Studio"], ["/assumptions", "Assumptions"], ["/materials", "Materials & answers"]],
  Customers: [["/growth", "Deals & campaigns"], ["/families", "Beta families"], ["/drive", "Reservation drive"], ["/press", "Press & gift guides"], ["/people", "People"]],
  Company: [["/decisions", "Decisions"], ["/memory", "Company facts"], ["/founder-profile", "Founder profile"]],
  Agents: [["/activity", "Activity"], ["/scouts", "Scouts"], ["/plans", "Plans"]],
}

const today = () => new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "America/New_York" })

function Header({ active }: { active: Dept }) {
  return (
    <header className="shrink-0 border-b bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-[105rem] flex-wrap items-center gap-1 px-4 py-2 md:h-14 md:flex-nowrap md:px-7 md:py-0">
        <a href="/" className="flex min-h-11 shrink-0 items-center pr-3 font-semibold md:mr-5 md:pr-0">Founder OS</a>
        <nav aria-label="Departments" className="flex min-w-0 flex-wrap gap-0.5 sm:gap-1">
          {DEPTS.map(([name, href]) => (
            <a key={name} href={href} aria-current={name === active ? "true" : undefined}
              className={cn("flex h-11 shrink-0 items-center rounded-lg border border-transparent px-2.5 font-medium sm:px-3 transition-colors hover:bg-card focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none",
                name === active && "border-border bg-card")}>
              {name}
            </a>
          ))}
        </nav>
        <span className="text-sm ml-auto hidden shrink-0 text-muted-foreground lg:block">{today()}</span>
      </div>
    </header>
  )
}

// The department's own pages, as one quiet row under the header. `tab` is the path of the page that is open;
// on a detail page it is the path of the list the detail belongs to, and `crumb` names the detail.
function DeptNav({ active, tab, crumb, crumbHref }: { active: Dept; tab?: string; crumb?: string; crumbHref?: string }) {
  const pages = PAGES[active]
  if (!pages.length) return null
  const parent = pages.find(([href]) => href === tab)
  return (
    <div className="flex flex-col gap-2">
      <nav aria-label={`${active} pages`} className="flex flex-wrap gap-x-1 gap-y-1 border-b">
        {pages.map(([href, name]) => (
          <a key={href} href={href} aria-current={href === tab && !crumb ? "page" : undefined}
            className={cn("-mb-px flex h-11 items-center border-b-2 border-transparent px-3 text-base font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid",
              href === tab && "border-primary text-foreground")}>
            {name}
          </a>
        ))}
      </nav>
      {crumb && parent && (
        <nav aria-label="Where you are" className="flex min-h-11 flex-wrap items-center gap-1 text-sm text-muted-foreground">
          <a href={crumbHref || parent[0]} className="flex min-h-11 items-center rounded-md font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-solid">{parent[1]}</a>
          <ChevronRight className="size-4" aria-hidden="true" />
          <span aria-current="page">{crumb}</span>
        </nav>
      )}
    </div>
  )
}

// The frame every page shares: the dot-grid paper ground, the header, the department's pages, and the page on one grid.
// `crumbHref` lets a detail page send its breadcrumb back to the exact list the visitor came from (filters and all).
export function Shell({ active, tab, crumb, crumbHref, title, children }: { active: Dept; tab?: string; crumb?: string; crumbHref?: string; title: string; children: ReactNode }) {
  useEffect(() => { document.title = active === "Today" ? "Today · Founder OS" : `${crumb || title} · ${active} · Founder OS` }, [active, crumb, title])
  return (
    <div className="ground-dots flex min-h-svh flex-col">
      <a href="#page" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2">Skip to the page</a>
      <Header active={active} />
      <main id="page" className="mx-auto flex w-full max-w-[105rem] flex-1 flex-col gap-5 p-4 md:p-7">
        <h1 className="sr-only">{title}</h1>
        <DeptNav active={active} tab={tab} crumb={crumb} crumbHref={crumbHref} />
        {children}
      </main>
    </div>
  )
}

// A program's own mark (its favicon, served by the app), or its first letter when none is saved.
export function ProgramMark({ name, className }: { name: string; className?: string }) {
  const src = logoFor(name)
  return src
    ? <img src={src} alt="" width={20} height={20} className={cn("size-5 shrink-0 rounded-[0.3rem] ring-1 ring-border", className)} />
    : <span aria-hidden="true" className={cn("flex size-5 shrink-0 items-center justify-center rounded-[0.3rem] text-sm font-semibold text-muted-foreground ring-1 ring-border", className)}>{name.trim()[0]}</span>
}
