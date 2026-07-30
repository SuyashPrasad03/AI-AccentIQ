import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Allows "@/..." imports throughout the app
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/health": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/api": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/recordings": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/auth": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/consent": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/quota": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/assistant": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/progress": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: process.env.VITE_API_BASE_URL ?? "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
