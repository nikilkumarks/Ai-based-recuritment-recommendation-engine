"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { ConfirmationBadge } from "@/components/ui/status-badge";
import {
  confirmProfile,
  createProfileEmbedding,
  getProfile,
  getProfileEmbedding,
  updateProfile,
  type EmbeddingStatus,
  type ProfileView,
  type SkillNormalizationResult,
} from "@/lib/api";
import { embeddingStatusLabel } from "@/lib/embedding-status";
import { describeHttpError } from "@/lib/http-error";

function resolutionNote(item: SkillNormalizationResult): string {
  if (item.resolution_type === "alias" && item.canonical_skill_name) {
    return `${item.raw_text} → ${item.canonical_skill_name} (alias)`;
  }
  if (item.canonical_skill_name) {
    return item.canonical_skill_name;
  }
  return `${item.raw_text} — needs review`;
}

export function ProfileManager() {
  const { user, accessToken } = useAuth();
  const candidateId = user?.candidate_id ?? null;
  const [confirmed, setConfirmed] = useState<ProfileView | null>(null);
  const [draft, setDraft] = useState<ProfileView | null>(null);
  const [embedding, setEmbedding] = useState<EmbeddingStatus | null>(null);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!candidateId || !accessToken) {
      return;
    }
    const payload = await getProfile(candidateId, accessToken);
    setConfirmed(payload.confirmed);
    setDraft(payload.draft);
    setSummary(payload.draft?.summary || payload.draft?.draft?.summary || payload.confirmed?.summary || "");
    if (payload.confirmed) {
      try {
        setEmbedding(await getProfileEmbedding(candidateId, accessToken));
      } catch {
        setEmbedding(null);
      }
    } else {
      setEmbedding(null);
    }
  }, [accessToken, candidateId]);

  useEffect(() => {
    void refresh()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [refresh]);

  async function save() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateProfile(candidateId, accessToken, { summary });
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await confirmProfile(candidateId, accessToken);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function embed() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setEmbedding(await createProfileEmbedding(candidateId, accessToken));
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (!candidateId) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is attached.</p>;
  }
  if (loading) {
    return <PageSkeleton />;
  }

  const view = draft ?? confirmed;
  const extraction = view?.draft;
  const skills = view?.normalized_skills ?? [];

  return (
    <div>
      <PageHeader
        title="Profile"
        description="Confirmed information is used for matching. Extracted fields stay in review until you confirm."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      {!view ? (
        <EmptyState
          title="No resume uploaded yet."
          description="Upload a PDF or DOCX to extract skills, experience, and education."
        />
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader
              title="Profile summary"
              action={<ConfirmationBadge status={view.confirmation_status} />}
            />
            <CardBody className="space-y-3">
              {confirmed ? (
                <p className="text-sm text-[var(--muted)]">
                  Confirmed version {confirmed.profile_version} is used for matching. Re-parse cannot overwrite it.
                </p>
              ) : (
                <p className="text-sm text-[var(--muted)]">Extracted draft — review before confirming.</p>
              )}
              <label className="block text-sm">
                Summary
                <textarea
                  className="mt-1 w-full px-3 py-2 text-sm"
                  rows={4}
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button type="button" disabled={busy || !draft} onClick={() => void save()}>
                  Save summary
                </Button>
                <Button type="button" variant="outline" disabled={busy || !draft} onClick={() => void confirm()}>
                  Confirm profile
                </Button>
                {confirmed ? (
                  <Button type="button" variant="outline" disabled={busy} onClick={() => void embed()}>
                    Generate embedding ({embeddingStatusLabel(embedding)})
                  </Button>
                ) : null}
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Skills" description="Canonical names from the ontology. Internal IDs are not shown." />
            <CardBody>
              {skills.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No skills extracted yet.</p>
              ) : (
                <ul className="flex flex-wrap gap-2">
                  {skills.map((item) => (
                    <li key={`${item.raw_text}-${item.canonical_skill_name ?? "none"}`}>
                      <span className="inline-flex items-center gap-1.5 border border-[var(--border)] px-2 py-1 text-sm">
                        {resolutionNote(item)}
                        {item.needs_review ? <Badge tone="warning">Review</Badge> : <Badge tone="success">Mapped</Badge>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
          <Section title="Experience" items={(extraction?.experience ?? []).map((item) =>
            [item.job_title, item.employer].filter(Boolean).join(" · ") || "Untitled role",
          )} />
          <Section title="Education" items={(extraction?.education ?? []).map((item) =>
            [item.degree, item.institution].filter(Boolean).join(" · ") || "Education",
          )} />
          <Section title="Projects" items={(extraction?.projects ?? []).map((item) => item.name ?? "Untitled project")} />
          <Section
            title="Certifications"
            items={(extraction?.certifications ?? []).map((item) => item.name ?? "Certification")}
          />
        </div>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">None extracted.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {items.map((item, index) => (
              <li key={`${title}-${index}`}>{item}</li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
