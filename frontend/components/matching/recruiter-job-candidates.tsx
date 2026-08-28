"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { listJobCandidates, type JobCandidateMatchSummary } from "@/lib/api";
import { BASELINE_MATCH_LABEL, formatBaselineMatch, formatCoverage } from "@/lib/baseline-match";

export function RecruiterJobCandidates({ jobId }: { jobId: string }) {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<JobCandidateMatchSummary[]>([]);
  const [sort, setSort] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const payload = await listJobCandidates(jobId, accessToken);
    setItems(payload.items);
    setSort(payload.sort);
  }, [accessToken, jobId]);

  useEffect(() => {
    void load().catch((err) => setError(describeAuthError(err)));
  }, [load]);

  return (
    <div className="space-y-4 text-sm">
      {error ? <p className="text-red-700">{error}</p> : null}
      <p className="text-[var(--muted)]">
        {sort || "Baseline sorting by current match. This is not a trained ranker."}
      </p>
      {items.length === 0 ? (
        <p className="text-[var(--muted)]">No visible candidates for this job yet.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.candidate_id} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
              <p className="font-medium">{item.identifier}</p>
              <p>
                {BASELINE_MATCH_LABEL}: {formatBaselineMatch(item.current_match)}
              </p>
              <p>Required skill coverage: {formatCoverage(item.required_skill_coverage)}</p>
              <p>Missing: {item.missing_skills.map((skill) => skill.skill).join(", ") || "none"}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
