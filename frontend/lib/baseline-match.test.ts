import { describe, expect, it } from "vitest";
import {
  BASELINE_MATCH_LABEL,
  CURRENT_MATCH_LABEL,
  MODEL_RELEVANCE_LABEL,
  formatBaselineMatch,
  formatCoverage,
  formatMatchPercent,
  formatPotential,
  POTENTIAL_LABEL,
  SUGGESTED_SKILL_PATH_LABEL,
} from "@/lib/baseline-match";

describe("baseline match display", () => {
  it("formats the 0–1 score and never calls it an AI score", () => {
    expect(formatBaselineMatch(0.67)).toBe("0.67");
    expect(formatBaselineMatch(null)).toBe("Unavailable");
    expect(formatMatchPercent(0.82)).toBe("82%");
    expect(formatMatchPercent(null)).toBe("Unavailable");
    expect(formatCoverage(0.5)).toBe("0.50");
    expect(BASELINE_MATCH_LABEL).toBe("Baseline Match");
    expect(CURRENT_MATCH_LABEL).toBe("Current Match");
    expect(BASELINE_MATCH_LABEL.toLowerCase()).not.toContain("ai score");
    expect(CURRENT_MATCH_LABEL.toLowerCase()).not.toContain("ai score");
    expect(MODEL_RELEVANCE_LABEL).toBe("Model Relevance");
    expect(MODEL_RELEVANCE_LABEL.toLowerCase()).not.toContain("hire");
  });

  it("distinguishes potential from current match and does not claim mastery", () => {
    expect(formatPotential(null, "not_applicable")).toBe("Not applicable");
    expect(formatPotential(0.68, "available")).toBe("68%");
    expect(POTENTIAL_LABEL).toBe("Potential");
    expect(SUGGESTED_SKILL_PATH_LABEL).toBe("Suggested Skill Path");
    expect(SUGGESTED_SKILL_PATH_LABEL.toLowerCase()).not.toContain("guaranteed");
    expect(formatPotential(1, "not_applicable")).toBe("Not applicable");
  });
});
