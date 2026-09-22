"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { ScoringModeNotice } from "@/components/matching/scoring-mode-notice";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { PageSkeleton } from "@/components/ui/skeleton";
import { DecisionBadge } from "@/components/ui/status-badge";
import {
  createRecruiterDecision,
  listJobCandidates,
  type JobCandidateMatchSummary,
  type ScoringMode,
} from "@/lib/api";
import {
  CURRENT_MATCH_LABEL,
  POTENTIAL_LABEL,
  formatMatchPercent,
  formatPotential,
} from "@/lib/baseline-match";
import { describeHttpError } from "@/lib/http-error";

const REASONS = [
  { value: "", label: "No reason" },
  { value: "skill_gap", label: "Skill gap" },
  { value: "experience_gap", label: "Experience gap" },
  { value: "education_mismatch", label: "Education mismatch" },
  { value: "strong_skill_match", label: "Strong skill match" },
  { value: "strong_project_evidence", label: "Strong project evidence" },
  { value: "insufficient_evidence", label: "Insufficient evidence" },
  { value: "other", label: "Other" },
];

export function RecruiterJobCandidates({ jobId }: { jobId: string }) {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<JobCandidateMatchSummary[]>([]);
  const [sort, setSort] = useState("");
  const [mode, setMode] = useState<ScoringMode>("baseline");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<{ id: string; action: "shortlist" | "reject" } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const payload = await listJobCandidates(jobId, accessToken);
    setItems(payload.items);
    setSort(payload.sort);
    setMode(payload.scoring_mode);
  }, [accessToken, jobId]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  async function decide(candidateId: string, action: "shortlist" | "reject") {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createRecruiterDecision(jobId, candidateId, accessToken, {
        action,
        reason: reason || undefined,
        note: note || undefined,
      });
      setPending(null);
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <PageSkeleton />;
  }

  const modelVersion = items.find((item) => item.model_version)?.model_version ?? null;

  return (
    <div className="space-y-4">
      {error ? <Alert>{error}</Alert> : null}
      <ScoringModeNotice mode={mode} modelVersion={modelVersion} />
      <p className="text-sm text-[var(--muted)]">
        {sort || "Sorted by Current Match. This is baseline sorting, not a trained ranker."} Shortlist and
        reject are recruiter actions, not hiring outcomes.
      </p>
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          Reason
          <select
            className="ml-2 px-2 py-1.5 text-sm"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          >
            {REASONS.map((item) => (
              <option key={item.value || "none"} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-[12rem] flex-1 text-sm">
          Note
          <input
            className="ml-2 w-[calc(100%-3rem)] px-2 py-1.5 text-sm"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={2000}
          />
        </label>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="No visible candidates for this job yet."
          description="Candidates appear after they confirm a profile and are visible to your organization."
        />
      ) : (
        <>
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[860px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">Candidate</th>
                  <th className="py-2 pr-3 font-medium">{CURRENT_MATCH_LABEL}</th>
                  <th className="py-2 pr-3 font-medium">{POTENTIAL_LABEL}</th>
                  <th className="py-2 pr-3 font-medium">Coverage</th>
                  <th className="py-2 pr-3 font-medium">Key gaps</th>
                  <th className="py-2 pr-3 font-medium">Decision</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.candidate_id} className="border-b border-[var(--border)]">
                    <td className="py-3 pr-3">
                      <Link
                        href={`/recruiter/jobs/${jobId}/candidates/${item.candidate_id}`}
                        className="font-medium underline-offset-2 hover:underline"
                      >
                        {item.identifier}
                      </Link>
                      {item.headline ? (
                        <p className="text-xs text-[var(--muted)]">{item.headline}</p>
                      ) : null}
                    </td>
                    <td className="tabular py-3 pr-3 font-semibold">
                      {formatMatchPercent(item.current_match)}
                    </td>
                    <td className="tabular py-3 pr-3">
                      {formatPotential(item.potential, item.potential_status)}
                    </td>
                    <td className="tabular py-3 pr-3">
                      {formatMatchPercent(item.required_skill_coverage)}
                    </td>
                    <td className="py-3 pr-3 text-[var(--muted)]">
                      {item.missing_skills.length
                        ? item.missing_skills
                            .slice(0, 3)
                            .map((skill) => skill.skill)
                            .join(", ")
                        : "None"}
                    </td>
                    <td className="py-3 pr-3">
                      <DecisionBadge action={item.current_decision} />
                    </td>
                    <td className="py-3">
                      <div className="flex gap-1.5">
                        <Button
                          type="button"
                          size="sm"
                          variant="success"
                          onClick={() => setPending({ id: item.candidate_id, action: "shortlist" })}
                        >
                          Shortlist
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="danger"
                          onClick={() => setPending({ id: item.candidate_id, action: "reject" })}
                        >
                          Reject
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="space-y-3 lg:hidden">
            {items.map((item) => (
              <li key={item.candidate_id}>
                <Card>
                  <CardBody className="space-y-3">
                    <Link
                      href={`/recruiter/jobs/${jobId}/candidates/${item.candidate_id}`}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {item.identifier}
                    </Link>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <dt className="text-xs text-[var(--muted)]">{CURRENT_MATCH_LABEL}</dt>
                        <dd className="tabular font-semibold">{formatMatchPercent(item.current_match)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-[var(--muted)]">{POTENTIAL_LABEL}</dt>
                        <dd className="tabular font-semibold">
                          {formatPotential(item.potential, item.potential_status)}
                        </dd>
                      </div>
                    </dl>
                    <DecisionBadge action={item.current_decision} />
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="success"
                        onClick={() => setPending({ id: item.candidate_id, action: "shortlist" })}
                      >
                        Shortlist
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="danger"
                        onClick={() => setPending({ id: item.candidate_id, action: "reject" })}
                      >
                        Reject
                      </Button>
                    </div>
                  </CardBody>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}
      <ConfirmDialog
        open={Boolean(pending)}
        title={pending?.action === "reject" ? "Reject this candidate?" : "Shortlist this candidate?"}
        description="This records a recruiter decision. It is not a hiring outcome and does not delete previous decisions."
        confirmLabel={pending?.action === "reject" ? "Reject" : "Shortlist"}
        danger={pending?.action === "reject"}
        busy={busy}
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending) {
            void decide(pending.id, pending.action);
          }
        }}
      />
    </div>
  );
}
