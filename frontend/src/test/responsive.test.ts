import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {describe, expect, it} from "vitest";

describe("responsive and motion safeguards", () => {
  const css = readFileSync(resolve(process.cwd(), "src/styles/global.css"), "utf8");
  it("has desktop, tablet and mobile adaptations", () => {
    expect(css).toContain("@media (max-width: 1180px)");
    expect(css).toContain("@media (max-width: 900px)");
    expect(css).toContain("@media (max-width: 640px)");
  });
  it("disables repeated movement for reduced-motion users", () => {
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain("animation-iteration-count: 1");
  });
  it("provides a non-blur fallback", () => {
    expect(css).toContain("@supports not (backdrop-filter: blur(1px))");
  });
});
