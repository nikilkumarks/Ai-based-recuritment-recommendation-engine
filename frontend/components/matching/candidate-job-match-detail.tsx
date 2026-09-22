"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { EvidenceList } from "@/components/matching/evidence-list";
import { MatchScorePanel } from "@/components/matching/match-score-panel";
import { ScoringModeNotice } from "@/components/matching/scoring-mode-notice";
import { SkillComparison } from "@/components/matching/skill-comparison";
import { SkillGapPanel } from "@/components/matching/skill-gap-panel";
import { SkillPathList } from "@/components/matching/skill-path-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import {
  getCandidateJobMatch,
  listCandidateJobs,
  simulateAddSkill,
  type CounterfactualResult,
  type MatchResult,
} from "@/lib/api";
import { formatMatchPercent } from "@/lib/baseline-match";
import { coverageFractionLabel } from "@/lib/skill-coverage";
import { describeHttpError } from "@/lib/http-error";

export function CandidateJobMatchDetail({ jobId }: { jobId: string }) {
  const { accessToken, user } = useAuth();
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [title, setTitle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [counterfactual, setCounterfactual] = useState<CounterfactualResult | null>(null);
  const [busySkill, setBusySkill] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const [detail, listed] = await Promise.all([
      getCandidateJobMatch(user.candidate_id, jobId, accessToken),
      listCandidateJobs(user.candidate_id, accessToken).catch(() => null),
    ]);
    setMatch(detail);
    setTitle(listed?.items.find((item) => item.job_id === jobId)?.job_title ?? null);
  }, [accessToken, jobId, user?.candidate_id]);

  useEffect(() => {
    void load().catch((err) => setError(describeHttpError(err, describeAuthError(err))));
  }, [load]);

  async function simulate(skillId: string) {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    setBusySkill(skillId);
    setError(null);
    try {
      setCounterfactual(await simulateAddSkill(user.candidate_id, jobId, skillId, accessToken));
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusySkill(null);
    }
  }

  if (error && !match) {
    return <Alert>{error}</Alert>;
  }
  if (!match) {
    return <PageSkeleton />;
  }

  const coverage = coverageFractionLabel(match);
  const ml = match.ml_explanations.filter((item) => (item.features ?? []).length > 0 || item.note);

  return (
    <div className="space-y-6">
      <PageHeader
        title={title ?? "Job match"}
        description="Current Match is what you already satisfy. Potential is how closable remaining gaps are — not a hiring probability."
      />
      {error ? <Alert>{error}</Alert> : null}
      <ScoringModeNotice
        mode={match.scoring_mode}
        modelVersion={match.model_version}
        fallbackReason={match.fallback_reason}
      />
      <Card>
        <CardHeader title="Match summary" description={coverage ? `Required skills ${coverage}` : undefined} />
        <CardBody>
          <MatchScorePanel match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Skill comparison" />
        <CardBody>
          <SkillComparison match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Why this match?" description="Evidence traces from the matching engine, not generated prose." />
        <CardBody>
          <EvidenceList explanations={match.explanations} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Skill gaps" />
        <CardBody>
          <SkillGapPanel match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Suggested Skill Path" />
        <CardBody>
          <SkillPathList items={match.suggested_skill_paths} />
        </CardBody>
      </Card>
      {match.missing_skills.length > 0 ? (
        <Card>
          <CardHeader
            title="What happens if I add a skill?"
            description="Simulation only. This does not change your profile."
          />
          <CardBody className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {match.missing_skills.map((skill) => (
                <Button
                  key={skill.skill_id}
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={busySkill === skill.skill_id}
                  onClick={() => void simulate(skill.skill_id)}
                >
                  {busySkill === skill.skill_id ? "Simulating…" : `If I add ${skill.skill}`}
                </Button>
              ))}
            </div>
            {counterfactual ? (
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-[var(--muted)]">Current Match now</dt>
                  <dd className="tabular font-semibold">
                    {formatMatchPercent(counterfactual.baseline_current_match)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--muted)]">If {counterfactual.skill_name} is added</dt>
                  <dd className="tabular font-semibold">
                    {formatMatchPercent(counterfactual.simulated_current_match)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--muted)]">Change</dt>
                  <dd className="tabular">
                    {counterfactual.delta >= 0 ? "+" : "−"}
                    {Math.round(Math.abs(counterfactual.delta) * 100)} percentage points
                  </dd>
                </div>
              </dl>
            ) : null}
          </CardBody>
        </Card>
      ) : null}
      {match.scoring_mode === "trained" && match.model_version ? (
        <Card>
          <CardHeader title="Model Relevance" />
          <CardBody className="space-y-2 text-sm">
            {ml.length === 0 ? (
              <p className="text-[var(--muted)]">
                Model relevance is influenced by skill coverage, semantic similarity, and experience alignment.
              </p>
            ) : (
              ml.map((item, index) => (
                <div key={`ml-${index}`}>
                  <p className="text-[var(--muted)]">
                    {item.note ??
                      "Model relevance is influenced by skill coverage, semantic similarity, and experience alignment."}
                  </p>
                  <ul className="mt-2 space-y-1">
                    {(item.features ?? []).map((feature) => (
                      <li key={feature.feature} className="flex justify-between gap-3">
                        <span>{feature.feature.replaceAll("_", " ")}</span>
                        <span className="tabular text-[var(--muted)]">
                          {feature.contribution != null ? feature.contribution.toFixed(3) : "n/a"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
