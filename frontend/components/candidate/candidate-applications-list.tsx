"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { listCandidateApplications, type ApplicationView } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { describeHttpError } from "@/lib/http-error";

export function CandidateApplicationsList() {
  const { user, accessToken } = useAuth();
  const [items, setItems] = useState<ApplicationView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const payload = await listCandidateApplications(user.candidate_id, accessToken);
    setItems(payload.items);
  }, [accessToken, user?.candidate_id]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (!user?.candidate_id) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile linked.</p>;
  }
  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Application History"
        description="Track your submitted job applications and current review status."
      />
      {error ? <Alert>{error}</Alert> : null}
      {items.length === 0 ? (
        <EmptyState
          title="No applications submitted yet."
          description="Browse recommended jobs and submit your application directly."
        />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardBody className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-semibold text-base">
                    <Link
                      href={`/candidate/jobs/${item.job_id}`}
                      className="hover:underline text-[var(--foreground)]"
                    >
                      {item.job_title ?? "Job Opportunity"}
                    </Link>
                  </h3>
                  {item.organization_name ? (
                    <p className="text-xs text-[var(--muted)]">{item.organization_name}</p>
                  ) : null}
                  <p className="text-xs text-[var(--muted)] mt-1">
                    Applied on {formatDate(item.applied_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={item.status === "selected" ? "success" : item.status === "rejected" ? "danger" : "info"}>
                    {item.status.toUpperCase()}
                  </Badge>
                  <Link
                    href={`/candidate/jobs/${item.job_id}`}
                    className="text-xs font-semibold text-[var(--accent)] hover:underline"
                  >
                    View Match
                  </Link>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
