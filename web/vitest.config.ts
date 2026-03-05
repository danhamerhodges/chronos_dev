import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["../tests/design_system/**/*.spec.ts", "../tests/visual_regression/**/*.spec.ts"],
    environment: "node",
  },
});
