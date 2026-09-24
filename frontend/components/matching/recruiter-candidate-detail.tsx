"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { EvidenceList } from "@/components/matching/evidence-list";
import { MatchScorePanel } from "@/components/matching/match-score-panel";
import { ScoringModeNotice } from "@/components/matching/scoring-mode-notice";
import { SkillComparison } from "@/components/matching/skill-comparison";
import { SkillGapPanel } from "@/components/matching/skill-gap-panel";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { DecisionBadge } from "@/components/ui/status-badge";
import {
  createRecruiterDecision,
  getCandidateJobMatch,
  listJobCandidates,
  listRecruiterDecisions,
  type JobCandidateMatchSummary,
  type MatchResult,
  type RecruiterDecisionList,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";
import { formatDateTime, shortId } from "@/lib/format";

export function RecruiterCandidateDetail({
  jobId,
  candidateId,
}: {
  jobId: string;
  candidateId: string;
}) {
  const { accessToken } = useAuth();
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [row, setRow] = useState<JobCandidateMatchSummary | null>(null);
  const [history, setHistory] = useState<RecruiterDecisionList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<"shortlist" | "reject" | "review" | "hire" | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const [detail, listed, decisions] = await Promise.all([
      getCandidateJobMatch(candidateId, jobId, accessToken),
      listJobCandidates(jobId, accessToken),
      listRecruiterDecisions(jobId, candidateId, accessToken),
    ]);
    setMatch(detail);
    setRow(listed.items.find((item) => item.candidate_id === candidateId) ?? null);
    setHistory(decisions);
  }, [accessToken, candidateId, jobId]);

  useEffect(() => {
    void load().catch((err) => setError(describeHttpError(err, describeAuthError(err))));
  }, [load]);

  async function decide(action: "shortlist" | "reject" | "review" | "hire") {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createRecruiterDecision(jobId, candidateId, accessToken, { action });
      setPending(null);
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (error && !match) {
    return <Alert>{error}</Alert>;
  }
  if (!match) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={row?.identifier ?? "Candidate"}
        description={row?.headline ?? "Match comparison for this job. Notes stay on this recruiter view."}
        actions={
          <Link href={`/recruiter/jobs/${jobId}/candidates`} className="text-sm underline-offset-2 hover:underline">
            Back to ranking
          </Link>
        }
      />
      {error ? <Alert>{error}</Alert> : null}
      <ScoringModeNotice
        mode={match.scoring_mode}
        modelVersion={match.model_version}
        fallbackReason={match.fallback_reason}
      />
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-[var(--muted)]">Decision</span>
        <DecisionBadge action={history?.current_action ?? row?.current_decision} />
        {row?.is_applicant ? (
          <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
            Applicant ({row.application_status ?? "Applied"})
          </span>
        ) : (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800/60 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            Discovered Candidate
          </span>
        )}
        <Button type="button" size="sm" variant="success" onClick={() => setPending("shortlist")}>
          Shortlist
        </Button>
        <Button type="button" size="sm" variant="default" onClick={() => setPending("hire")}>
          Hire
        </Button>
        <Button type="button" size="sm" variant="danger" onClick={() => setPending("reject")}>
          Reject
        </Button>
      </div>
      <Card>
        <CardHeader title="Match summary" />
        <CardBody>
          <MatchScorePanel match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Skill alignment" />
        <CardBody>
          <SkillComparison match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Skill gaps" />
        <CardBody>
          <SkillGapPanel match={match} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Evidence traces" />
        <CardBody>
          <EvidenceList explanations={match.explanations} />
        </CardBody>
      </Card>
      {match.scoring_mode === "trained" && match.model_version ? (
        <Card>
          <CardHeader title="Model Relevance" />
          <CardBody className="text-sm text-[var(--muted)]">
            Model relevance is influenced by skill coverage, semantic similarity, and experience alignment.
            It is not a hiring probability.
          </CardBody>
        </Card>
      ) : null}
      <Card>
        <CardHeader
          title="Decision history"
          description={history?.label_note ?? "History is append-only. Earlier decisions are not deleted."}
        />
        <CardBody>
          {!history?.items.length ? (
            <p className="text-sm text-[var(--muted)]">No candidate decisions have been recorded.</p>
          ) : (
            <ol className="space-y-2 text-sm">
              {history.items.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-[var(--muted)]">{formatDateTime(item.created_at)}</span>
                  <span>Recruiter {shortId(item.recruiter_id)}</span>
                  <DecisionBadge action={item.action} />
                  {item.reason ? <span className="text-[var(--muted)]">{item.reason.replaceAll("_", " ")}</span> : null}
                  {item.note ? <span className="text-[var(--muted)]">Note: {item.note}</span> : null}
                </li>
              ))}
            </ol>
          )}
        </CardBody>
      </Card>
      <ConfirmDialog
        open={Boolean(pending)}
        title={pending === "reject" ? "Reject this candidate?" : "Shortlist this candidate?"}
        description="This records a recruiter decision. It is not a hiring outcome."
        confirmLabel={pending === "reject" ? "Reject" : "Shortlist"}
        danger={pending === "reject"}
        busy={busy}
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending) {
            void decide(pending);
          }
        }}
      />
    </div>
  );
}
