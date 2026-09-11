import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const { PUBLIC_BASE_URL } = loadEnv(mode, "..", "PUBLIC_");
  const allowedHosts = PUBLIC_BASE_URL ? [new URL(PUBLIC_BASE_URL).hostname] : [];
  return {
    plugins: [react()],
    publicDir: "../images",
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port: 8080,
      strictPort: true,
      allowedHosts,
      proxy: {
        "/health": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./tests/setup.ts",
      css: true,
      restoreMocks: true,
    },
  };
});
