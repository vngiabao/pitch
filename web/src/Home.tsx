import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { loadHome, type HomeFacts } from "@/lib/today"
import outbox from "@/assets/home/outbox.webp"

// Founder OS home (Bao's pick, Nov 11: "2 · Outbox wall"). The picture is the company's applications as a paper
// model; the live numbers stay in type. One arrival, once: the picture settles, the words rise, the line fades in.
// The button is there from the first frame and holds the focus.

const greeting = () => {
  const h = Number(new Intl.DateTimeFormat("en-US", { hour: "numeric", hourCycle: "h23", timeZone: "America/New_York" }).format(new Date()))
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"
}

export function Home() {
  const [facts, setFacts] = useState<HomeFacts | null>(null)
  const [failed, setFailed] = useState(false)
  const [seen, setSeen] = useState(false)
  const load = () => { setFailed(false); loadHome().then(setFacts).catch(() => setFailed(true)) }
  // Fetch the line of facts once, when Home opens
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(load, [])
  // Enter goes straight in, without putting a focus ring on the button before the keyboard is used
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Enter" && document.activeElement === document.body) location.assign("/today") }
    addEventListener("keydown", onKey)
    return () => removeEventListener("keydown", onKey)
  }, [])
  const next = facts?.next
  const soon = !!next && next.days <= 14
  return (
    <div className="relative min-h-svh overflow-hidden bg-home-paper">
      <img src={outbox} width={2752} height={1536} fetchPriority="high" decoding="async" onLoad={() => setSeen(true)}
        alt="A paper model of a wall of mail slots: sealed letters waiting, opened letters with a brass seal, and one navy envelope being filled"
        className={cn("home-scene absolute inset-0 size-full", seen ? "home-arrive" : "opacity-0")} />
      <main className="home-frame relative flex min-h-svh w-full flex-col justify-between">
        <p className="text-[clamp(1.125rem,1.15vw,1.5rem)] font-semibold">Founder OS</p>
        <div>
          <div className="home-rise">
            <h1 className="text-[clamp(2.75rem,4.2vw,5.5rem)] leading-none font-semibold tracking-[-0.04em]">{greeting()}, Bao</h1>
            <p className="mt-3 min-h-[2.7em] text-[clamp(1.25rem,1.5vw,1.75rem)] leading-[1.35] md:min-h-[1.35em]">
              {facts && (
                <span className="home-line">
                  <span className="font-semibold">{facts.accepted}</span> accepted, <span className="font-semibold">{facts.waiting}</span> waiting on results.
                  {next && (
                    <>
                      {" "}<span className="font-semibold">{next.name}</span> closes{" "}
                      <span className={cn("font-semibold whitespace-nowrap", soon && "text-deadline")}>
                        {next.days === 0 ? "today" : `in ${next.days} ${next.days === 1 ? "day" : "days"}`}
                      </span>.
                    </>
                  )}
                </span>
              )}
              {failed && (
                <span className="home-line">
                  Your numbers didn’t load.{" "}
                  <button type="button" onClick={load} className="inline-flex min-h-11 items-center rounded-sm font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary focus-visible:outline-solid">Load them again</button>
                </span>
              )}
            </p>
          </div>
          <Button size="lg" className="mt-4 h-[clamp(3.25rem,3.4vw,4rem)] w-full px-7 text-[clamp(1.125rem,1.15vw,1.375rem)] focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-primary focus-visible:outline-solid sm:w-auto" asChild>
            <a href="/today">Open today</a>
          </Button>
        </div>
      </main>
    </div>
  )
}
