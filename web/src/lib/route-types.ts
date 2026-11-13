import type { ReactNode } from "react"

// Each page file under src/pages exports `routes`: the paths it answers. `exact` paths have no trailing slash;
// `prefix` paths end with a slash and receive the rest of the path (decoded) as the id.
export type PageRoutes = {
  exact?: Record<string, () => ReactNode>
  prefix?: Record<string, (id: string) => ReactNode>
}
