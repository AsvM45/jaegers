import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run build` writes ../dist, which tower/ui/server.py serves at http://127.0.0.1:8080.
// `npm run dev` serves the source with hot reload on :5173 and forwards the API to the Python
// server, so start that too (python start.py --serve-only).
const api = "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: { outDir: "../dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": api, "/orb": api, "/runs": api },
  },
});
