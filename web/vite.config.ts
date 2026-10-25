import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// La API corre aparte: `uvicorn an.web.app:crear_app --factory` (AN_ORIGEN=http://localhost:5173 en desarrollo).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
