/** Display helpers for the interpretable baseline match. Not an accuracy metric. */

export function formatBaselineMatch(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "Unavailable";
  }
  return score.toFixed(2);
}

export function formatCoverage(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(2);
}

export const BASELINE_MATCH_LABEL = "Baseline Match";
