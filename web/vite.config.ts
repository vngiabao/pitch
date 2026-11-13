import { resolve } from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  // Served by the Founder OS Python server at /next (same origin, so its script-src 'self' policy holds)
  base: "/next/",
  build: { outDir: resolve(import.meta.dirname, "../founder_os/ui/next"), emptyOutDir: true, assetsInlineLimit: 0 },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "./src"),
    },
  },
})
