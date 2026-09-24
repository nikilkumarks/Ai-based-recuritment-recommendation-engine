"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { CountBars, DistributionBars, FunnelBars } from "@/components/ui/count-bars";
import { EmptyState } from "@/components/ui/empty-state";
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
import { Info } from "lucide-react";

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
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">System Analytics</h1>
        <p className="text-xs text-slate-500 mt-1 font-medium">
          Descriptive activity counts and skill demand/supply distribution.
        </p>
      </div>

      <div className="flex items-start gap-2.5 rounded-xl border border-slate-200/80 bg-slate-100/60 p-3.5 text-xs text-slate-700 font-medium">
        <Info className="h-4 w-4 shrink-0 text-slate-500 mt-0.5" />
        <p className="leading-relaxed">{overview.disclaimer}</p>
      </div>

      {noActivity ? (
        <EmptyState
          className="mb-4"
          title="No candidate decisions have been recorded."
          description="Charts appear when jobs, applications, or decisions exist."
        />
      ) : null}

      {/* KPI Metrics */}
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Metric label="Jobs" value={overview.jobs} />
        <Metric label="Candidates" value={overview.candidates} />
        <Metric label="Applications" value={overview.applications} />
        <Metric label="Reviewed" value={overview.review_count} />
        <Metric label="Shortlisted" value={overview.shortlist_count} />
        <Metric label="Rejected" value={overview.reject_count} />
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {funnel ? (
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">Decision Funnel</h3>
            </div>
            <FunnelBars
              applications={funnel.applications}
              reviewed={funnel.reviewed}
              shortlisted={funnel.shortlisted}
              rejected={funnel.rejected}
            />
          </div>
        ) : null}

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">Skill Demand</h3>
            <p className="text-xs text-slate-500">Most requested required skills across job requisitions.</p>
          </div>
          <CountBars items={skills.required_demand} empty="No confirmed required skills yet." />
        </div>

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">Skill Supply</h3>
            <p className="text-xs text-slate-500">Candidate skill availability across confirmed profiles.</p>
          </div>
          <CountBars items={skills.candidate_supply} empty="No confirmed candidate skills yet." />
        </div>

        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">Common Skill Gaps</h3>
            <p className="text-xs text-slate-500">Most frequent missing requirements across matches.</p>
          </div>
          <CountBars items={skills.top_missing_skills} empty="No gap traces yet." />
        </div>

        {matching ? (
          <>
            <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900">Current Match Distribution</h3>
              </div>
              <DistributionBars items={matching.current_match} empty="No match runs yet." />
            </div>

            <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900">Potential Distribution</h3>
              </div>
              <DistributionBars items={matching.potential} empty="No potential scores yet." />
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3.5 shadow-2xs space-y-1">
      <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">{label}</p>
      <p className="font-mono text-2xl font-extrabold text-slate-900">{value}</p>
    </div>
  );
}

