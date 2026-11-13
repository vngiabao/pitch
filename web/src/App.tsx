import { Home } from "@/Home"
import { match } from "@/routes"

// Founder OS opens on Home; Today sits one click in (Bao, Nov 11: the home screen is not the to-do dashboard).
// Every other page is listed in routes.tsx under the path the old app used, so links and bookmarks keep working.
export function App() {
  const path = location.pathname.replace(/\/+$/, "") || "/"
  if (path === "/" || path === "/next") return <Home />
  return match(path) ?? <Home />
}

export default App
