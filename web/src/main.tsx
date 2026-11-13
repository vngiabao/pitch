import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import { Boundary } from "@/components/app/boundary"
import { Feedback } from "@/components/app/feedback"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Boundary><Feedback><App /></Feedback></Boundary>
  </StrictMode>
)
