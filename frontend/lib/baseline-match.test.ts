import { describe, expect, it } from "vitest";
import { BASELINE_MATCH_LABEL, formatBaselineMatch, formatCoverage } from "@/lib/baseline-match";

describe("baseline match display", () => {
  it("formats the 0–1 score and never calls it an AI score", () => {
    expect(formatBaselineMatch(0.67)).toBe("0.67");
    expect(formatBaselineMatch(null)).toBe("Unavailable");
    expect(formatCoverage(0.5)).toBe("0.50");
    expect(BASELINE_MATCH_LABEL).toBe("Baseline Match");
    expect(BASELINE_MATCH_LABEL.toLowerCase()).not.toContain("ai score");
  });
});
