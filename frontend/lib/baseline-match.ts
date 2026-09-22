/** Display helpers for match scores. Values are 0–1; UI may show percents. Not accuracy. */

export function formatBaselineMatch(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "Unavailable";
  }
  return score.toFixed(2);
}

export function formatMatchPercent(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "Unavailable";
  }
  return `${Math.round(score * 100)}%`;
}

export function formatCoverage(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(2);
}

export function formatPotential(
  score: number | null | undefined,
  status: "available" | "not_applicable" | string | undefined,
): string {
  if (status === "not_applicable" || score === null || score === undefined) {
    return "Not applicable";
  }
  if (Number.isNaN(score)) {
    return "Not applicable";
  }
  return formatMatchPercent(score);
}

export const CURRENT_MATCH_LABEL = "Current Match";
export const BASELINE_MATCH_LABEL = "Baseline Match";
export const MODEL_RELEVANCE_LABEL = "Model Relevance";
export const POTENTIAL_LABEL = "Potential";
export const SUGGESTED_SKILL_PATH_LABEL = "Suggested Skill Path";
export const CURRENT_MATCH_HINT =
  "How closely the candidate currently satisfies the stated requirements.";
export const POTENTIAL_HINT =
  "How closable remaining skill gaps are using related skills and evidence. Not a hiring probability.";
