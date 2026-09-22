import { describe, expect, it } from "vitest";
import { coverageFractionLabel, requiredSkillCounts } from "@/lib/skill-coverage";

function skill(name: string, id: string) {
  return {
    skill_id: id,
    skill: name,
    evidence_type: "exact",
    candidate_skill_id: null,
    candidate_evidence: null,
    hops: null,
  };
}

describe("skill coverage display", () => {
  it("counts unique required skills from match lists", () => {
    const match = {
      matched_skills: [skill("Python", "1")],
      related_skills: [skill("Kubernetes", "2")],
      partial_skills: [],
      missing_skills: [skill("Deep Learning", "3")],
    };
    const counts = requiredSkillCounts(match);
    expect(counts.required).toBe(3);
    expect(counts.covered).toBe(2);
    expect(coverageFractionLabel(match)).toBe("2 / 3");
  });
});
