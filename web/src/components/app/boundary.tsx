import { Component, type ReactNode } from "react"

import { Button } from "@/components/ui/button"

// If a page fails while drawing, say so in plain words with two ways out, instead of leaving a blank screen.
export class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="ground-dots flex min-h-svh flex-col items-start justify-center gap-4 p-7">
        <h1 className="text-2xl font-semibold tracking-tight">This page didn’t open</h1>
        <p className="max-w-[60ch] text-base text-muted-foreground">Something on it failed to draw. Your saved work is not affected.</p>
        <div className="flex flex-wrap gap-3">
          <Button size="lg" onClick={() => location.reload()}>Load it again</Button>
          <Button size="lg" variant="outline" asChild><a href="/today">Open today</a></Button>
        </div>
      </div>
    )
  }
}
