"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { listCandidateJobs, type CandidateJobMatchSummary } from "@/lib/api";
import { BASELINE_MATCH_LABEL, formatBaselineMatch, formatCoverage } from "@/lib/baseline-match";

export function CandidateJobsList() {
  const { accessToken, user } = useAuth();
  const [items, setItems] = useState<CandidateJobMatchSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const payload = await listCandidateJobs(user.candidate_id, accessToken);
    setItems(payload.items);
  }, [accessToken, user?.candidate_id]);

  useEffect(() => {
    void load().catch((err) => setError(describeAuthError(err)));
  }, [load]);

  if (!user?.candidate_id) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is linked to this account.</p>;
  }

  return (
    <div className="space-y-4">
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <p className="text-sm text-[var(--muted)]">
        Scores are a deterministic baseline, not a trained model and not accuracy.
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No matchable jobs yet. Jobs need confirmed requirements.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.job_id} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 text-sm">
              <Link href={`/candidate/jobs/${item.job_id}`} className="font-medium underline">
                {item.job_title}
              </Link>
              <p>
                {BASELINE_MATCH_LABEL}: {formatBaselineMatch(item.current_match)}
              </p>
              <p>Required skill coverage: {formatCoverage(item.required_skill_coverage)}</p>
              <p>Missing: {item.missing_skills.map((skill) => skill.skill).join(", ") || "none"}</p>
              <p>
                Partial/related:{" "}
                {[...item.partial_skills, ...item.related_skills].map((skill) => `${skill.skill} (${skill.evidence_type})`).join(", ") ||
                  "none"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
