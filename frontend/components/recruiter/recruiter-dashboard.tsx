"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { DecisionBadge } from "@/components/ui/status-badge";
import {
  getRecruiterFunnel,
  getRecruiterOverview,
  listJobCandidates,
  listJobs,
  type FunnelAnalytics,
  type JobCandidateMatchSummary,
  type JobSummary,
  type RecruiterOverview,
} from "@/lib/api";
import { CURRENT_MATCH_LABEL, formatMatchPercent } from "@/lib/baseline-match";
import { describeHttpError } from "@/lib/http-error";

export function RecruiterDashboard() {
  const { accessToken, user } = useAuth();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [overview, setOverview] = useState<RecruiterOverview | null>(null);
  const [funnel, setFunnel] = useState<FunnelAnalytics | null>(null);
  const [top, setTop] = useState<{ job: JobSummary; rows: JobCandidateMatchSummary[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const [jobPayload, nextOverview, nextFunnel] = await Promise.all([
      listJobs(accessToken),
      getRecruiterOverview(accessToken),
      getRecruiterFunnel(accessToken),
    ]);
    setJobs(jobPayload.items);
    setOverview(nextOverview);
    setFunnel(nextFunnel);
    const first = jobPayload.items[0];
    if (first) {
      try {
        const ranked = await listJobCandidates(first.id, accessToken);
        setTop({ job: first, rows: ranked.items.slice(0, 5) });
      } catch {
        setTop({ job: first, rows: [] });
      }
    } else {
      setTop(null);
    }
  }, [accessToken]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (loading) {
    return <PageSkeleton />;
  }

  const openJobs = jobs.filter((job) => job.status !== "closed" && job.status !== "archived");

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={user?.email ? `Workspace for ${user.email}. Counts below come from recorded activity only.` : undefined}
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Open jobs" value={openJobs.length} />
        <Stat label="Applications" value={overview?.applications ?? 0} />
        <Stat label="Shortlisted" value={overview?.shortlist_count ?? 0} />
        <Stat label="Rejected" value={overview?.reject_count ?? 0} />
      </div>
      {overview?.disclaimer ? <p className="mt-3 text-sm text-[var(--muted)]">{overview.disclaimer}</p> : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Jobs"
            action={
              <Link href="/recruiter/jobs" className="text-sm underline-offset-2 hover:underline">
                Manage
              </Link>
            }
          />
          <CardBody>
            {jobs.length === 0 ? (
              <EmptyState title="No jobs yet." description="Create a job and confirm extracted requirements to rank candidates." />
            ) : (
              <ul className="divide-y divide-[var(--border)] text-sm">
                {jobs.slice(0, 6).map((job) => (
                  <li key={job.id} className="flex justify-between gap-3 py-2 first:pt-0 last:pb-0">
                    <Link href={`/recruiter/jobs/${job.id}/candidates`} className="underline-offset-2 hover:underline">
                      {job.title}
                    </Link>
                    <span className="text-[var(--muted)]">{job.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Pipeline" />
          <CardBody className="space-y-2 text-sm">
            {funnel && funnel.applications + funnel.shortlisted + funnel.rejected === 0 ? (
              <p className="text-[var(--muted)]">No candidate decisions have been recorded.</p>
            ) : (
              <>
                <p>Applications {funnel?.applications ?? 0}</p>
                <p>Reviewed {funnel?.reviewed ?? 0}</p>
                <p>Shortlisted {funnel?.shortlisted ?? 0}</p>
                <p>Rejected {funnel?.rejected ?? 0}</p>
              </>
            )}
          </CardBody>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader
            title={top ? `Top matches · ${top.job.title}` : "Top matches"}
            action={
              top ? (
                <Link
                  href={`/recruiter/jobs/${top.job.id}/candidates`}
                  className="text-sm underline-offset-2 hover:underline"
                >
                  Ranking
                </Link>
              ) : null
            }
          />
          <CardBody>
            {!top ? (
              <EmptyState title="No candidate pipeline yet." description="Confirm a job to rank candidates." />
            ) : top.rows.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No visible candidates for this job yet.</p>
            ) : (
              <ul className="divide-y divide-[var(--border)] text-sm">
                {top.rows.map((row) => (
                  <li key={row.candidate_id} className="flex flex-wrap items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
                    <Link
                      href={`/recruiter/jobs/${top.job.id}/candidates/${row.candidate_id}`}
                      className="underline-offset-2 hover:underline"
                    >
                      {row.identifier}
                    </Link>
                    <span className="tabular text-[var(--muted)]">
                      {CURRENT_MATCH_LABEL} {formatMatchPercent(row.current_match)}
                    </span>
                    <DecisionBadge action={row.current_decision} />
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
        <p className="tabular mt-1 text-2xl font-semibold">{value}</p>
      </CardBody>
    </Card>
  );
}
