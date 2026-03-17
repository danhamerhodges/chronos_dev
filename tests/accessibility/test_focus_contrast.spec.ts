/**
 * Maps to:
 * - DS-004
 * - DS-005
 */

import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const tokensCss = fs.readFileSync(
  path.resolve(process.cwd(), "src/styles/tokens.css"),
  "utf8",
);

describe("Packet 4G focus contrast styles", () => {
  it("defines explicit focus-ring tokens and focus-visible rules for shared controls", () => {
    expect(tokensCss).toContain("--color-focus-ring: #0a5bd8;");
    expect(tokensCss).toContain("--color-focus-ring-offset: #f7f9fc;");
    expect(tokensCss).toContain(".chronos-button:focus-visible");
    expect(tokensCss).toContain(".chronos-input:focus-visible");
    expect(tokensCss).toContain(".chronos-select:focus-visible");
    expect(tokensCss).toContain("outline: 2px solid var(--color-focus-ring);");
  });
});
