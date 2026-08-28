"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { getCandidateJobMatch, type MatchResult } from "@/lib/api";
import { BASELINE_MATCH_LABEL, formatBaselineMatch, formatCoverage } from "@/lib/baseline-match";

export function CandidateJobMatchDetail({ jobId }: { jobId: string }) {
  const { accessToken, user } = useAuth();
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    setMatch(await getCandidateJobMatch(user.candidate_id, jobId, accessToken));
  }, [accessToken, jobId, user?.candidate_id]);

  useEffect(() => {
    void load().catch((err) => setError(describeAuthError(err)));
  }, [load]);

  if (error) {
    return <p className="text-sm text-red-700">{error}</p>;
  }
  if (!match) {
    return <p className="text-sm text-[var(--muted)]">Loading baseline match…</p>;
  }

  return (
    <div className="space-y-4 text-sm">
      <p>
        {BASELINE_MATCH_LABEL}: {formatBaselineMatch(match.current_match)} (0.0–1.0, not accuracy)
      </p>
      <p>Required coverage: {formatCoverage(match.required_skill_coverage)}</p>
      <p>Preferred coverage: {formatCoverage(match.preferred_skill_coverage)}</p>
      <p>
        Semantic similarity:{" "}
        {match.semantic_similarity_available ? formatBaselineMatch(match.semantic_similarity) : "unavailable"}
      </p>
      <p>Matched: {match.matched_skills.map((item) => item.skill).join(", ") || "none"}</p>
      <p>
        Partial:{" "}
        {match.partial_skills.map((item) => `${item.skill} (${item.evidence_type})`).join(", ") || "none"}
      </p>
      <p>Related: {match.related_skills.map((item) => item.skill).join(", ") || "none"}</p>
      <p>Missing: {match.missing_skills.map((item) => item.skill).join(", ") || "none"}</p>
      <div>
        <p className="font-medium">Explanation traces</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {match.explanations.map((item, index) => (
            <li key={`${item.type}-${index}`}>
              {item.type}
              {item.required_skill ? `: ${item.required_skill}` : ""}
              {item.candidate_evidence ? ` ← ${item.candidate_evidence}` : ""}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
