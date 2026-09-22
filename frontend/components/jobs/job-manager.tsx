"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { ConfirmationBadge } from "@/components/ui/status-badge";
import {
  confirmJobRequirements,
  createJob,
  createJobEmbedding,
  getJob,
  getJobEmbedding,
  listJobs,
  type EmbeddingStatus,
  type JobDetail,
  type JobSummary,
} from "@/lib/api";
import { embeddingStatusLabel } from "@/lib/embedding-status";
import { describeHttpError } from "@/lib/http-error";

export function JobManager() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<JobSummary[]>([]);
  const [selected, setSelected] = useState<JobDetail | null>(null);
  const [embedding, setEmbedding] = useState<EmbeddingStatus | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const payload = await listJobs(accessToken);
    setItems(payload.items);
  }, [accessToken]);

  useEffect(() => {
    void refresh()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [refresh]);

  async function onCreate() {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const job = await createJob(accessToken, {
        title,
        description_raw: description,
        location: location || undefined,
        employment_type: employmentType || undefined,
      });
      setSelected(job);
      setEmbedding(null);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function loadJob(id: string, token: string) {
    const job = await getJob(id, token);
    setSelected(job);
    if (job.requirements?.confirmation_status === "confirmed") {
      try {
        setEmbedding(await getJobEmbedding(id, token));
      } catch {
        setEmbedding(null);
      }
    } else {
      setEmbedding(null);
    }
  }

  async function onOpen(id: string) {
    if (!accessToken) {
      return;
    }
    setError(null);
    try {
      await loadJob(id, accessToken);
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    }
  }

  async function onConfirm() {
    if (!accessToken || !selected) {
      return;
    }
    setBusy(true);
    try {
      await confirmJobRequirements(selected.id, accessToken);
      await loadJob(selected.id, accessToken);
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function onEmbed() {
    if (!accessToken || !selected) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setEmbedding(await createJobEmbedding(selected.id, accessToken));
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <PageSkeleton />;
  }

  const required = selected?.requirements?.normalized_required_skills ?? [];
  const preferred = selected?.requirements?.normalized_preferred_skills ?? [];
  const draftRequired = selected?.requirements?.draft?.required_skills ?? [];
  const draftPreferred = selected?.requirements?.draft?.preferred_skills ?? [];

  return (
    <div>
      <PageHeader
        title="Jobs"
        description="Extract required and preferred skills from a job description, then confirm before ranking candidates."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader title="Create job" />
            <CardBody className="space-y-3">
              <label className="block text-sm">
                Title
                <input className="mt-1 w-full px-3 py-2 text-sm" value={title} onChange={(event) => setTitle(event.target.value)} />
              </label>
              <label className="block text-sm">
                Location
                <input
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Employment type
                <select
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={employmentType}
                  onChange={(event) => setEmploymentType(event.target.value)}
                >
                  <option value="">Not specified</option>
                  <option value="full_time">Full-time</option>
                  <option value="part_time">Part-time</option>
                  <option value="contract">Contract</option>
                  <option value="internship">Internship</option>
                </select>
              </label>
              <label className="block text-sm">
                Description
                <textarea
                  className="mt-1 w-full px-3 py-2 text-sm"
                  rows={8}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
              <Button type="button" disabled={busy || title.length < 3 || description.length < 20} onClick={() => void onCreate()}>
                Extract requirements
              </Button>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Open jobs" />
            <CardBody>
              {items.length === 0 ? (
                <EmptyState title="No jobs yet." description="Create a job to extract requirements." />
              ) : (
                <ul className="divide-y divide-[var(--border)] text-sm">
                  {items.map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
                      <button type="button" className="text-left underline-offset-2 hover:underline" onClick={() => void onOpen(item.id)}>
                        {item.title}
                      </button>
                      <span className="text-[var(--muted)]">{item.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
        {selected ? (
          <Card>
            <CardHeader
              title={selected.title}
              description={[selected.location, selected.employment_type?.replaceAll("_", " ")].filter(Boolean).join(" · ") || undefined}
              action={<ConfirmationBadge status={selected.requirements?.confirmation_status} />}
            />
            <CardBody className="space-y-4 text-sm">
              <p className="whitespace-pre-wrap text-[var(--muted)]">{selected.description_raw}</p>
              <div>
                <p className="font-medium">Required skills</p>
                <SkillList normalized={required} draft={draftRequired.map((item) => item.raw_text)} />
              </div>
              <div>
                <p className="font-medium">Preferred skills</p>
                <SkillList normalized={preferred} draft={draftPreferred.map((item) => item.raw_text)} />
              </div>
              {selected.requirements?.draft?.education_level ? (
                <p>Education: {selected.requirements.draft.education_level}</p>
              ) : null}
              {selected.requirements?.draft?.min_years_experience != null ? (
                <p>Experience: {selected.requirements.draft.min_years_experience} years</p>
              ) : null}
              <p className="text-[var(--muted)]">Semantic representation: {embeddingStatusLabel(embedding)}</p>
              <div className="flex flex-wrap gap-2">
                <Button type="button" disabled={busy || !selected.requirements} onClick={() => void onConfirm()}>
                  Confirm requirements
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy || selected.requirements?.confirmation_status !== "confirmed"}
                  onClick={() => void onEmbed()}
                >
                  Generate embedding
                </Button>
                {selected.requirements?.confirmation_status === "confirmed" ? (
                  <Link
                    href={`/recruiter/jobs/${selected.id}/candidates`}
                    className="inline-flex h-9 items-center px-3 text-sm underline-offset-2 hover:underline"
                  >
                    Rank candidates
                  </Link>
                ) : null}
              </div>
            </CardBody>
          </Card>
        ) : (
          <EmptyState title="Select a job" description="Open a job from the list to review extracted requirements." />
        )}
      </div>
    </div>
  );
}

function SkillList({
  normalized,
  draft,
}: {
  normalized: { raw_text: string; canonical_skill_name: string | null; needs_review: boolean }[];
  draft: string[];
}) {
  if (normalized.length === 0 && draft.length === 0) {
    return <p className="mt-1 text-[var(--muted)]">None extracted.</p>;
  }
  return (
    <ul className="mt-1 space-y-1">
      {normalized.length
        ? normalized.map((item) => (
            <li key={`${item.raw_text}-${item.canonical_skill_name ?? "none"}`}>
              {item.canonical_skill_name ?? item.raw_text}
              {item.canonical_skill_name && item.raw_text.toLowerCase() !== item.canonical_skill_name.toLowerCase()
                ? ` (from “${item.raw_text}”)`
                : ""}
              {item.needs_review ? " — needs review" : ""}
            </li>
          ))
        : draft.map((name) => <li key={name}>{name}</li>)}
    </ul>
  );
}
