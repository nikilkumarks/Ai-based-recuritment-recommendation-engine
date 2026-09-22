"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { listJobs, type JobSummary } from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function RecruiterCandidatesIndex() {
  const { accessToken } = useAuth();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setJobs((await listJobs(accessToken)).items);
  }, [accessToken]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div>
      <PageHeader
        title="Candidates"
        description="Open a job to review ranked candidates. There is no global candidate directory in this product."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      {jobs.length === 0 ? (
        <EmptyState title="No jobs yet." description="Create a job first, then rank candidates against confirmed requirements." />
      ) : (
        <ul className="divide-y divide-[var(--border)] border border-[var(--border)] bg-[var(--card)]">
          {jobs.map((job) => (
            <li key={job.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <span className="font-medium">{job.title}</span>
              <Link
                href={`/recruiter/jobs/${job.id}/candidates`}
                className="underline-offset-2 hover:underline"
              >
                View ranking
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
