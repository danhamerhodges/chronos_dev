import "./node_modules/@testing-library/jest-dom/dist/vitest.mjs";

import { cleanup } from "./node_modules/@testing-library/react/dist/@testing-library/react.esm.js";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
