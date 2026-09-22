"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
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
    return <PageSkeleton />;
  }

  const top = jobs.slice(0, 3);
  const gaps = jobs[0] ? requiredSkillCounts(jobs[0]).missingNames : [];
  const latestResume = resumes[0];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={
          user?.email
            ? `Signed in as ${user.email}. Review matches, gaps, and the evidence behind each recommendation.`
            : undefined
        }
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Recommended jobs"
            action={
              <Link href="/candidate/jobs" className="text-sm underline-offset-2 hover:underline">
                View all
              </Link>
            }
          />
          <CardBody>
            {top.length === 0 ? (
              <EmptyState
                title="No matching jobs yet."
                description="Upload a resume, confirm your profile, then return here when jobs are available."
                action={
                  <Link href="/candidate/resumes" className="text-sm underline-offset-2 hover:underline">
                    Upload resume
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-[var(--border)]">
                {top.map((item) => (
                  <li key={item.job_id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                    <Link href={`/candidate/jobs/${item.job_id}`} className="font-medium underline-offset-2 hover:underline">
                      {item.job_title}
                    </Link>
                    <p className="tabular text-sm text-[var(--muted)]">
                      {CURRENT_MATCH_LABEL} {formatMatchPercent(item.current_match)} · {POTENTIAL_LABEL}{" "}
                      {formatPotential(item.potential, item.potential_status)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Profile" />
          <CardBody className="space-y-2 text-sm">
            {profile ? (
              <>
                <p>{profile.summary || profile.draft?.summary || "No summary yet."}</p>
                <p className="text-[var(--muted)]">
                  Status: {profile.confirmation_status === "confirmed" ? "Confirmed" : "Needs review"}
                </p>
                <Link href="/candidate/profile" className="inline-block underline-offset-2 hover:underline">
                  Open profile
                </Link>
              </>
            ) : (
              <EmptyState
                title="No resume uploaded yet."
                description="Upload a PDF or DOCX to build your profile."
                action={
                  <Link href="/candidate/resumes" className="text-sm underline-offset-2 hover:underline">
                    Upload resume
                  </Link>
                }
              />
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Current skill gaps" description="From the top recommended job, if one exists." />
          <CardBody>
            {!jobs[0] ? (
              <p className="text-sm text-[var(--muted)]">Gaps appear once a job can be compared to your profile.</p>
            ) : gaps.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No remaining required gaps on the top match.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {gaps.slice(0, 6).map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
            <Link href="/candidate/career" className="mt-3 inline-block text-sm underline-offset-2 hover:underline">
              Skill path
            </Link>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Suggested paths" />
          <CardBody>
            {paths.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                {pathNote ?? "No suggested skill path is available until related skills exist in the ontology."}
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {paths.slice(0, 4).map((path) => (
                  <li key={path.target_skill_id}>
                    {(path.steps ?? []).map((step) => step.skill).join(" → ")}
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Resume activity" />
          <CardBody className="text-sm">
            {latestResume ? (
              <div className="space-y-2">
                <p className="font-medium">{latestResume.filename}</p>
                <p className="text-[var(--muted)]">Uploaded {formatDate(latestResume.created_at)}</p>
                <ParseStatusBadge status={latestResume.parse_status} />
              </div>
            ) : (
              <p className="text-[var(--muted)]">No resume uploaded yet.</p>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
