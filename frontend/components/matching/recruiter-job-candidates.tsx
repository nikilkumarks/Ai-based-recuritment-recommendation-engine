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
  const [sourceFilter, setSourceFilter] = useState<"all" | "applicant" | "discovered">("all");
  const [pending, setPending] = useState<{ id: string; action: "shortlist" | "reject" | "review" | "hire" } | null>(null);
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

  async function decide(candidateId: string, action: "shortlist" | "reject" | "review" | "hire") {
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

  const filteredItems = items.filter((item) => {
    if (sourceFilter === "applicant") return item.is_applicant;
    if (sourceFilter === "discovered") return !item.is_applicant;
    return true;
  });

  const modelVersion = items.find((item) => item.model_version)?.model_version ?? null;

  return (
    <div className="space-y-4">
      {error ? <Alert>{error}</Alert> : null}
      <ScoringModeNotice mode={mode} modelVersion={modelVersion} />
      <p className="text-sm text-[var(--muted)]">
        {sort || "Sorted by Current Match. This is baseline sorting, not a trained ranker."} Shortlist,
        reject, review, and hire are recruiter actions.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm">
          Source Filter
          <select
            className="ml-2 px-2 py-1.5 text-sm rounded border border-[var(--border)] bg-[var(--surface)]"
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value as "all" | "applicant" | "discovered")}
          >
            <option value="all">All Candidates ({items.length})</option>
            <option value="applicant">
              Applicants Only ({items.filter((i) => i.is_applicant).length})
            </option>
            <option value="discovered">
              Discovered / Sourced ({items.filter((i) => !i.is_applicant).length})
            </option>
          </select>
        </label>
        <label className="text-sm">
          Reason
          <select
            className="ml-2 px-2 py-1.5 text-sm rounded border border-[var(--border)] bg-[var(--surface)]"
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
            className="ml-2 w-[calc(100%-3rem)] px-2 py-1.5 text-sm rounded border border-[var(--border)] bg-[var(--surface)]"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={2000}
          />
        </label>
      </div>
      {filteredItems.length === 0 ? (
        <EmptyState
          title="No candidates match the selected view."
          description="Try changing the candidate source filter or wait for candidates to apply/confirm profiles."
        />
      ) : (
        <>
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[860px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">Candidate</th>
                  <th className="py-2 pr-3 font-medium">Source</th>
                  <th className="py-2 pr-3 font-medium">{CURRENT_MATCH_LABEL}</th>
                  <th className="py-2 pr-3 font-medium">{POTENTIAL_LABEL}</th>
                  <th className="py-2 pr-3 font-medium">Coverage</th>
                  <th className="py-2 pr-3 font-medium">Key gaps</th>
                  <th className="py-2 pr-3 font-medium">Decision</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
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
                    <td className="py-3 pr-3">
                      {item.is_applicant ? (
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                          Applicant
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800/60 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                          Discovered
                        </span>
                      )}
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
                      <div className="flex gap-1.5 flex-wrap">
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
                          variant="default"
                          onClick={() => setPending({ id: item.candidate_id, action: "hire" })}
                        >
                          Hire
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
            {filteredItems.map((item) => (
              <li key={item.candidate_id}>
                <Card>
                  <CardBody className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Link
                        href={`/recruiter/jobs/${jobId}/candidates/${item.candidate_id}`}
                        className="font-medium underline-offset-2 hover:underline"
                      >
                        {item.identifier}
                      </Link>
                      {item.is_applicant ? (
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                          Applicant
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800/60 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                          Discovered
                        </span>
                      )}
                    </div>
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
                    <div className="flex gap-2 flex-wrap">
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
                        variant="default"
                        onClick={() => setPending({ id: item.candidate_id, action: "hire" })}
                      >
                        Hire
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
        title={
          pending?.action === "hire"
            ? "Hire this candidate?"
            : pending?.action === "reject"
            ? "Reject this candidate?"
            : "Shortlist this candidate?"
        }
        description="This records a recruiter decision. It is saved in decision history."
        confirmLabel={
          pending?.action === "hire" ? "Hire" : pending?.action === "reject" ? "Reject" : "Shortlist"
        }
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
