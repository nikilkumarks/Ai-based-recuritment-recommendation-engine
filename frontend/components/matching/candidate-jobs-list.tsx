"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageSkeleton } from "@/components/ui/skeleton";
import { ScoringModeNotice } from "@/components/matching/scoring-mode-notice";
import {
  listCandidateJobs,
  type CandidateJobMatchSummary,
  type ScoringMode,
} from "@/lib/api";
import {
  CURRENT_MATCH_LABEL,
  MODEL_RELEVANCE_LABEL,
  POTENTIAL_LABEL,
  formatMatchPercent,
  formatPotential,
} from "@/lib/baseline-match";
import { describeHttpError } from "@/lib/http-error";
import { requiredSkillCounts } from "@/lib/skill-coverage";

export function CandidateJobsList() {
  const { accessToken, user } = useAuth();
  const [items, setItems] = useState<CandidateJobMatchSummary[]>([]);
  const [mode, setMode] = useState<ScoringMode>("baseline");
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const payload = await listCandidateJobs(user.candidate_id, accessToken);
    setItems(payload.items);
    setMode(payload.scoring_mode);
    setModelVersion(payload.items.find((item) => item.model_version)?.model_version ?? null);
  }, [accessToken, user?.candidate_id]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (!user?.candidate_id) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is linked to this account.</p>;
  }
  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-4">
      {error ? <Alert>{error}</Alert> : null}
      <ScoringModeNotice mode={mode} modelVersion={modelVersion} />
      {items.length === 0 ? (
        <EmptyState
          title="No matching jobs yet."
          description="Jobs appear here after a recruiter confirms requirements and your profile is confirmed."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => {
            const gaps = requiredSkillCounts(item).missingNames;
            const trained = item.scoring_mode === "trained" && Boolean(item.model_version);
            return (
              <li key={item.job_id}>
                <Link href={`/candidate/jobs/${item.job_id}`} className="block">
                  <Card className="hover:border-[var(--accent)]">
                    <CardBody className="space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <h2 className="text-base font-semibold">{item.job_title}</h2>
                      </div>
                      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                          <dt className="text-xs text-[var(--muted)]">{CURRENT_MATCH_LABEL}</dt>
                          <dd className="tabular text-lg font-semibold">
                            {formatMatchPercent(item.current_match)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-[var(--muted)]">{POTENTIAL_LABEL}</dt>
                          <dd className="tabular text-lg font-semibold">
                            {formatPotential(item.potential, item.potential_status)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-[var(--muted)]">Required coverage</dt>
                          <dd className="tabular text-lg font-semibold">
                            {formatMatchPercent(item.required_skill_coverage)}
                          </dd>
                        </div>
                        {trained ? (
                          <div>
                            <dt className="text-xs text-[var(--muted)]">{MODEL_RELEVANCE_LABEL}</dt>
                            <dd className="tabular text-lg font-semibold">
                              {formatMatchPercent(item.model_relevance_score)}
                            </dd>
                          </div>
                        ) : (
                          <div>
                            <dt className="text-xs text-[var(--muted)]">Skill gaps</dt>
                            <dd className="text-sm">{gaps.length ? gaps.slice(0, 3).join(", ") : "None"}</dd>
                          </div>
                        )}
                      </dl>
                      {trained ? (
                        <p className="text-sm text-[var(--muted)]">
                          Skill gaps: {gaps.length ? gaps.slice(0, 4).join(", ") : "None"}
                        </p>
                      ) : null}
                    </CardBody>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
