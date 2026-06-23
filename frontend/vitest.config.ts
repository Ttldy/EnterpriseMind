import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(
        new URL("./src", import.meta.url),
      ),
    },
  },
  test: {
    include: ["src/**/*.spec.ts"],
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
