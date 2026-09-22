"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CountBars, DistributionBars, FunnelBars } from "@/components/ui/count-bars";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import {
  getAdminOverview,
  getAdminSkills,
  getRecruiterFunnel,
  getRecruiterMatching,
  getRecruiterOverview,
  getRecruiterSkills,
  type FunnelAnalytics,
  type RecruiterMatchingAnalytics,
  type RecruiterOverview,
  type RecruiterSkillsAnalytics,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function RecruiterAnalyticsPanel({ scope = "recruiter" }: { scope?: "recruiter" | "admin" }) {
  const { accessToken } = useAuth();
  const [overview, setOverview] = useState<RecruiterOverview | null>(null);
  const [skills, setSkills] = useState<RecruiterSkillsAnalytics | null>(null);
  const [matching, setMatching] = useState<RecruiterMatchingAnalytics | null>(null);
  const [funnel, setFunnel] = useState<FunnelAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    if (scope === "admin") {
      const [nextOverview, nextSkills] = await Promise.all([
        getAdminOverview(accessToken),
        getAdminSkills(accessToken),
      ]);
      setOverview(nextOverview);
      setSkills(nextSkills);
      setMatching(null);
      setFunnel(null);
      return;
    }
    const [nextOverview, nextSkills, nextMatching, nextFunnel] = await Promise.all([
      getRecruiterOverview(accessToken),
      getRecruiterSkills(accessToken),
      getRecruiterMatching(accessToken),
      getRecruiterFunnel(accessToken),
    ]);
    setOverview(nextOverview);
    setSkills(nextSkills);
    setMatching(nextMatching);
    setFunnel(nextFunnel);
  }, [accessToken, scope]);

  useEffect(() => {
    void load().catch((err) => setError(describeHttpError(err, describeAuthError(err))));
  }, [load]);

  if (error) {
    return <Alert>{error}</Alert>;
  }
  if (!overview || !skills) {
    return <PageSkeleton />;
  }

  const noActivity = overview.applications === 0 && overview.shortlist_count === 0 && overview.reject_count === 0;

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Descriptive counts from this workspace. Shortlist is not a hire. No model accuracy is shown."
      />
      <p className="mb-4 text-sm text-[var(--muted)]">{overview.disclaimer}</p>
      {noActivity ? (
        <EmptyState
          className="mb-4"
          title="No candidate decisions have been recorded."
          description="Charts appear when jobs, applications, or decisions exist."
        />
      ) : null}
      <div className="mb-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Metric label="Jobs" value={overview.jobs} />
        <Metric label="Candidates" value={overview.candidates} />
        <Metric label="Applications" value={overview.applications} />
        <Metric label="Reviewed" value={overview.review_count} />
        <Metric label="Shortlisted" value={overview.shortlist_count} />
        <Metric label="Rejected" value={overview.reject_count} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {funnel ? (
          <Card>
            <CardHeader title="Decision funnel" />
            <CardBody>
              <FunnelBars
                applications={funnel.applications}
                reviewed={funnel.reviewed}
                shortlisted={funnel.shortlisted}
                rejected={funnel.rejected}
              />
            </CardBody>
          </Card>
        ) : null}
        <Card>
          <CardHeader title="Skill demand" description="Most requested required skills." />
          <CardBody>
            <CountBars items={skills.required_demand} empty="No confirmed required skills yet." />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Skill supply" description="Candidate skill availability." />
          <CardBody>
            <CountBars items={skills.candidate_supply} empty="No confirmed candidate skills yet." />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Common skill gaps" />
          <CardBody>
            <CountBars items={skills.top_missing_skills} empty="No gap traces yet." />
          </CardBody>
        </Card>
        {matching ? (
          <>
            <Card>
              <CardHeader title="Current Match distribution" />
              <CardBody>
                <DistributionBars items={matching.current_match} empty="No match runs yet." />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Potential distribution" />
              <CardBody>
                <DistributionBars items={matching.potential} empty="No potential scores yet." />
              </CardBody>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-[var(--border)] bg-[var(--card)] px-3 py-3">
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="tabular mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}
