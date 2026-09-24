"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { ParseStatusBadge } from "@/components/ui/status-badge";
import {
  getCareerPaths,
  getProfile,
  listCandidateJobs,
  listResumes,
  type CandidateJobMatchSummary,
  type ProfileView,
  type ResumeSummary,
  type SuggestedSkillPath,
} from "@/lib/api";
import { CURRENT_MATCH_LABEL, POTENTIAL_LABEL, formatMatchPercent, formatPotential } from "@/lib/baseline-match";
import { formatDate } from "@/lib/format";
import { describeHttpError } from "@/lib/http-error";
import { requiredSkillCounts } from "@/lib/skill-coverage";
import { Briefcase, UserCheck, FileText, ArrowUpRight, Sparkles, AlertTriangle, ArrowRight, Route } from "lucide-react";

import { CandidateDashboardSkeleton } from "@/components/ui/skeleton";

export function CandidateDashboard() {
  const { user, accessToken } = useAuth();
  const [jobs, setJobs] = useState<CandidateJobMatchSummary[]>([]);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [profile, setProfile] = useState<ProfileView | null>(null);
  const [paths, setPaths] = useState<SuggestedSkillPath[]>([]);
  const [pathNote, setPathNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken || !user?.candidate_id) {
      return;
    }
    const cid = user.candidate_id;
    const [jobPayload, resumePayload, profilePayload, pathPayload] = await Promise.all([
      listCandidateJobs(cid, accessToken).catch(() => ({ items: [] as CandidateJobMatchSummary[] })),
      listResumes(cid, accessToken),
      getProfile(cid, accessToken),
      getCareerPaths(cid, accessToken).catch(() => null),
    ]);
    setJobs(jobPayload.items);
    setResumes(resumePayload.items);
    setProfile(profilePayload.confirmed ?? profilePayload.draft);
    setPaths(pathPayload?.items ?? []);
    setPathNote(pathPayload?.disclaimer ?? null);
  }, [accessToken, user?.candidate_id]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (loading) {
    return <CandidateDashboardSkeleton />;
  }


  const top = jobs.slice(0, 3);
  const topJob = jobs[0];
  const gaps = topJob ? requiredSkillCounts(topJob).missingNames : [];
  const latestResume = resumes[0];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Candidate Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            {user?.email
              ? `Signed in as ${user.email}. Review matches, gaps, and skill evidence.`
              : "Review your matches, skill gaps, and career fit."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/candidate/resumes"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs transition-colors shadow-2xs"
          >
            <FileText className="h-3.5 w-3.5" />
            <span>Upload Resume</span>
          </Link>
        </div>
      </div>

      {error ? <Alert className="mb-4">{error}</Alert> : null}

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Recommended Jobs</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <Briefcase className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900">{jobs.length}</p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Top Match Score</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-teal-700">
            {topJob ? formatMatchPercent(topJob.current_match) : "—"}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Profile Status</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <UserCheck className="h-4 w-4" />
            </div>
          </div>
          <p className="text-lg font-bold text-slate-900">
            {profile?.confirmation_status === "confirmed" ? (
              <span className="text-emerald-700 inline-flex items-center gap-1">Confirmed</span>
            ) : profile ? (
              <span className="text-amber-700 inline-flex items-center gap-1">Needs Review</span>
            ) : (
              <span className="text-slate-400">No Profile</span>
            )}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Resumes Uploaded</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900">{resumes.length}</p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recommended Jobs */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Recommended Jobs</h2>
              <p className="text-xs text-slate-500">Top role recommendations based on your verified skill graph.</p>
            </div>
            <Link href="/candidate/jobs" className="text-xs font-semibold text-teal-700 hover:text-teal-800 hover:underline flex items-center gap-1">
              <span>View all</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {top.length === 0 ? (
            <EmptyState
              title="No matching jobs yet."
              description="Upload a resume, confirm your profile, then return here when jobs are available."
              action={
                <Link href="/candidate/resumes" className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-700 text-white hover:bg-teal-800 transition-colors">
                  Upload resume
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {top.map((item) => (
                <div
                  key={item.job_id}
                  className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 transition-colors"
                >
                  <div className="space-y-1">
                    <Link
                      href={`/candidate/jobs/${item.job_id}`}
                      className="text-sm font-bold text-slate-900 hover:text-teal-700 transition-colors flex items-center gap-1.5"
                    >
                      <span>{item.job_title}</span>
                      <ArrowUpRight className="h-3.5 w-3.5 text-slate-400" />
                    </Link>
                    <p className="text-xs text-slate-500">Job ID: {item.job_id}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="inline-flex items-center gap-1 rounded-md bg-teal-50 px-2.5 py-1 font-bold text-teal-800 border border-teal-200/60">
                      {CURRENT_MATCH_LABEL}: {formatMatchPercent(item.current_match)}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 font-semibold text-slate-700 border border-slate-200">
                      {POTENTIAL_LABEL}: {formatPotential(item.potential, item.potential_status)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profile Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Profile</h2>
            <Link href="/candidate/profile" className="text-xs font-semibold text-teal-700 hover:underline">
              Edit profile
            </Link>
          </div>

          {profile ? (
            <div className="space-y-3 text-xs">
              <p className="text-slate-600 leading-relaxed line-clamp-3">
                {profile.summary || profile.draft?.summary || "No profile summary provided yet."}
              </p>
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-slate-500">
                <span>Verification Status:</span>
                <span className="font-bold text-slate-800 capitalize">{profile.confirmation_status ?? "Needs review"}</span>
              </div>
              <Link
                href="/candidate/profile"
                className="w-full inline-flex justify-center items-center gap-1.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
              >
                <span>Open Profile</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          ) : (
            <EmptyState
              title="No resume uploaded yet."
              description="Upload a PDF or DOCX to build your profile."
              action={
                <Link href="/candidate/resumes" className="text-xs font-semibold text-teal-700 hover:underline">
                  Upload resume
                </Link>
              }
            />
          )}
        </div>

        {/* Current Skill Gaps */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Skill Gaps</h2>
            <p className="text-xs text-slate-500">Requirements missing from your top match.</p>
          </div>

          {!jobs[0] ? (
            <p className="text-xs text-slate-400">Gaps appear once a job can be compared to your profile.</p>
          ) : gaps.length === 0 ? (
            <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800 font-medium">
              ✓ No remaining required gaps on top match.
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {gaps.slice(0, 6).map((name) => (
                  <span key={name} className="inline-flex items-center gap-1 rounded-lg bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-800 border border-rose-200">
                    <AlertTriangle className="h-3 w-3 shrink-0 text-rose-600" />
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <Link href="/candidate/career" className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:underline pt-1">
            <Route className="h-3.5 w-3.5" />
            <span>Explore Skill Path</span>
          </Link>
        </div>

        {/* Suggested Skill Paths */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Suggested Skill Paths</h2>
            <p className="text-xs text-slate-500">Ontology-backed progression paths.</p>
          </div>

          {paths.length === 0 ? (
            <p className="text-xs text-slate-500 leading-relaxed">
              {pathNote ?? "No suggested skill path is available until related skills exist in the ontology."}
            </p>
          ) : (
            <ul className="space-y-2 text-xs">
              {paths.slice(0, 4).map((path) => (
                <li key={path.target_skill_id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 text-slate-700 font-mono">
                  {(path.steps ?? []).map((step) => step.skill).join(" → ")}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Resume Activity */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">Resume Activity</h2>
            <p className="text-xs text-slate-500">Latest uploaded resume parsing state.</p>
          </div>

          {latestResume ? (
            <div className="space-y-2 text-xs">
              <p className="font-bold text-slate-900 truncate">{latestResume.filename}</p>
              <p className="text-slate-500">Uploaded {formatDate(latestResume.created_at)}</p>
              <div className="pt-1">
                <ParseStatusBadge status={latestResume.parse_status} />
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400">No resume uploaded yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

