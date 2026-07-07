import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Proxy API calls to backend so the frontend only talks to one origin in dev.
    // In production, VITE_API_BASE_URL points at the deployed Render backend.
    proxy: {
      "/health": {
        target: process.env.VITE_API_BASE_URL ?? "http://backend:8000",
        changeOrigin: true,
      },
      "/api": {
        target: process.env.VITE_API_BASE_URL ?? "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
