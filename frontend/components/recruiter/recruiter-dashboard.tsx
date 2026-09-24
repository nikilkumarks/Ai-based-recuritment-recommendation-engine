"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
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
import { Briefcase, Users, CheckCircle2, XCircle, Plus, ArrowUpRight, Filter } from "lucide-react";

import { RecruiterDashboardSkeleton } from "@/components/ui/skeleton";

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
    return <RecruiterDashboardSkeleton />;
  }


  const openJobs = jobs.filter((job) => job.status !== "closed" && job.status !== "archived");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Recruiter Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            {user?.email
              ? `Workspace for ${user.email}. Recorded recruitment activity and pipeline overview.`
              : "Overview of your job requisitions, candidate pipeline, and decisions."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/recruiter/jobs/new"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs transition-colors shadow-2xs"
          >
            <Plus className="h-4 w-4" />
            <span>Create Job</span>
          </Link>
        </div>
      </div>

      {error ? <Alert className="mb-4">{error}</Alert> : null}

      {/* KPI Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Open Requisitions" value={openJobs.length} icon={Briefcase} tone="teal" />
        <StatCard label="Applications" value={overview?.applications ?? 0} icon={Users} tone="slate" />
        <StatCard label="Shortlisted" value={overview?.shortlist_count ?? 0} icon={CheckCircle2} tone="emerald" />
        <StatCard label="Rejected" value={overview?.reject_count ?? 0} icon={XCircle} tone="rose" />
      </div>

      {overview?.disclaimer ? (
        <p className="text-xs text-slate-500 italic bg-slate-100/60 p-2.5 rounded-xl border border-slate-200/60">
          {overview.disclaimer}
        </p>
      ) : null}

      {/* Dashboard Main Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Requisitions List */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Job Requisitions</h2>
              <p className="text-xs text-slate-500">Active and draft recruitment positions.</p>
            </div>
            <Link href="/recruiter/jobs" className="text-xs font-semibold text-teal-700 hover:underline flex items-center gap-1">
              <span>Manage</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {jobs.length === 0 ? (
            <EmptyState
              title="No jobs yet."
              description="Create a job and confirm extracted requirements to rank candidates."
              action={
                <Link href="/recruiter/jobs/new" className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-700 text-white hover:bg-teal-800 transition-colors">
                  Create Job
                </Link>
              }
            />
          ) : (
            <div className="space-y-2 text-xs">
              {jobs.slice(0, 6).map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50/70 border border-slate-200/70 hover:bg-slate-50 transition-colors"
                >
                  <Link
                    href={`/recruiter/jobs/${job.id}/candidates`}
                    className="font-bold text-slate-900 hover:text-teal-700 transition-colors truncate max-w-[70%]"
                  >
                    {job.title}
                  </Link>
                  <span className="capitalize px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200/70 text-slate-700 border border-slate-300/60">
                    {job.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline Summary */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Candidate Pipeline</h2>
            <p className="text-xs text-slate-500">Funnel stage activity breakdown.</p>
          </div>

          {funnel && funnel.applications + funnel.shortlisted + funnel.rejected === 0 ? (
            <p className="text-xs text-slate-400">No candidate decisions have been recorded yet.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Applications</span>
                <span className="text-xl font-bold text-slate-900">{funnel?.applications ?? 0}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Reviewed</span>
                <span className="text-xl font-bold text-slate-900">{funnel?.reviewed ?? 0}</span>
              </div>
              <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200/80">
                <span className="text-emerald-800 font-semibold block uppercase text-[10px]">Shortlisted</span>
                <span className="text-xl font-bold text-emerald-900">{funnel?.shortlisted ?? 0}</span>
              </div>
              <div className="p-3 rounded-xl bg-rose-50/60 border border-rose-200/80">
                <span className="text-rose-800 font-semibold block uppercase text-[10px]">Rejected</span>
                <span className="text-xl font-bold text-rose-900">{funnel?.rejected ?? 0}</span>
              </div>
            </div>
          )}
        </div>

        {/* Top Matches Section */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {top ? `Top Candidate Matches · ${top.job.title}` : "Top Candidate Matches"}
              </h2>
              <p className="text-xs text-slate-500">Highest ranked candidates based on evidence matching.</p>
            </div>
            {top ? (
              <Link
                href={`/recruiter/jobs/${top.job.id}/candidates`}
                className="text-xs font-semibold text-teal-700 hover:underline flex items-center gap-1"
              >
                <Filter className="h-3.5 w-3.5" />
                <span>Full Candidate Ranking</span>
              </Link>
            ) : null}
          </div>

          {!top ? (
            <EmptyState title="No candidate pipeline yet." description="Confirm a job requirement spec to rank candidates." />
          ) : top.rows.length === 0 ? (
            <p className="text-xs text-slate-400">No visible candidates for this job yet.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {top.rows.map((row) => (
                <div
                  key={row.candidate_id}
                  className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/70 hover:bg-slate-50 transition-colors"
                >
                  <Link
                    href={`/recruiter/jobs/${top.job.id}/candidates/${row.candidate_id}`}
                    className="font-bold text-slate-900 hover:text-teal-700 transition-colors"
                  >
                    {row.identifier}
                  </Link>

                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-teal-800 bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200/60 text-xs">
                      {CURRENT_MATCH_LABEL}: {formatMatchPercent(row.current_match)}
                    </span>
                    <DecisionBadge action={row.current_decision} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  tone: "teal" | "emerald" | "rose" | "slate";
}) {
  const tones = {
    teal: "bg-teal-50 text-teal-700",
    emerald: "bg-emerald-50 text-emerald-700",
    rose: "bg-rose-50 text-rose-700",
    slate: "bg-slate-100 text-slate-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-2xs space-y-1">
      <div className="flex items-center justify-between text-slate-500">
        <span className="text-xs font-semibold">{label}</span>
        <div className={`p-2 rounded-xl ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="text-2xl font-extrabold text-slate-900">{value}</p>
    </div>
  );
}

