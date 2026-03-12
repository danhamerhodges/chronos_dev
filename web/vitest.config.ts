import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      react: fileURLToPath(new URL("./node_modules/react", import.meta.url)),
      "react-dom": fileURLToPath(new URL("./node_modules/react-dom", import.meta.url)),
      "@testing-library/dom": fileURLToPath(new URL("./node_modules/@testing-library/dom", import.meta.url)),
      "@testing-library/react": fileURLToPath(new URL("./node_modules/@testing-library/react", import.meta.url)),
      "@testing-library/user-event": fileURLToPath(new URL("./node_modules/@testing-library/user-event", import.meta.url)),
      "@testing-library/jest-dom": fileURLToPath(new URL("./node_modules/@testing-library/jest-dom", import.meta.url)),
      "@testing-library/jest-dom/vitest": fileURLToPath(new URL("./node_modules/@testing-library/jest-dom/dist/vitest.mjs", import.meta.url)),
    },
  },
  test: {
    include: [
      "../tests/design_system/**/*.spec.ts",
      "../tests/visual_regression/**/*.spec.ts",
      "../tests/web/**/*.spec.ts",
      "../tests/ui/**/*.spec.ts",
      "../tests/accessibility/**/*.spec.ts",
    ],
    environment: "node",
    environmentMatchGlobs: [
      ["../tests/ui/**/*.spec.ts", "jsdom"],
      ["../tests/accessibility/**/*.spec.ts", "jsdom"],
    ],
    setupFiles: ["./vitest.setup.ts"],
  },
});
