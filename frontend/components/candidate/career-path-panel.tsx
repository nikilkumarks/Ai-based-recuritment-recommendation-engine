"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { SkillPathList } from "@/components/matching/skill-path-list";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { getCareerPaths, listCandidateJobs, type SuggestedSkillPath } from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function CareerPathPanel() {
  const { accessToken, user } = useAuth();
  const [items, setItems] = useState<SuggestedSkillPath[]>([]);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const jobs = await listCandidateJobs(user.candidate_id, accessToken).catch(() => ({ items: [] }));
    const jobId = jobs.items[0]?.job_id;
    const payload = await getCareerPaths(user.candidate_id, accessToken, jobId);
    setItems(payload.items);
    setDisclaimer(payload.disclaimer);
  }, [accessToken, user?.candidate_id]);

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
        title="Skill path"
        description="Suggested paths come from the skill ontology. They are not guaranteed career outcomes."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      {items.length === 0 ? (
        <EmptyState
          title="No suggested skill path yet."
          description={disclaimer ?? "Confirm your profile and wait for a job comparison with related skills."}
        />
      ) : (
        <SkillPathList items={items} disclaimer={disclaimer ?? undefined} />
      )}
    </div>
  );
}
