"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { confirmProfile, createProfileEmbedding, getProfile, getProfileEmbedding, updateProfile, type EmbeddingStatus, type ProfileView } from "@/lib/api";
import { embeddingStatusLabel } from "@/lib/embedding-status";

export function ProfileManager() {
  const { user, accessToken } = useAuth();
  const candidateId = user?.candidate_id ?? null;
  const [confirmed, setConfirmed] = useState<ProfileView | null>(null);
  const [draft, setDraft] = useState<ProfileView | null>(null);
  const [embedding, setEmbedding] = useState<EmbeddingStatus | null>(null);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!candidateId || !accessToken) {
      return;
    }
    const payload = await getProfile(candidateId, accessToken);
    setConfirmed(payload.confirmed);
    setDraft(payload.draft);
    setSummary(payload.draft?.summary || payload.draft?.draft?.summary || "");
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
    void refresh().catch((err) => setError(describeAuthError(err)));
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
      setError(describeAuthError(err));
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
      setError(describeAuthError(err));
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
      setError(describeAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!candidateId) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is attached.</p>;
  }

  const extraction = draft?.draft;
  const skills = extraction?.skills ?? [];

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {confirmed ? (
        <div className="space-y-2">
          <p className="text-sm">Confirmed version {confirmed.profile_version}. Re-parse cannot overwrite it.</p>
          <p className="text-sm">
            Embedding: {embeddingStatusLabel(embedding)}
            {embedding?.model_name ? ` · ${embedding.model_name}` : ""}
          </p>
          <Button type="button" disabled={busy} onClick={() => void embed()}>
            Generate embedding
          </Button>
        </div>
      ) : null}
      {draft ? (
        <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
          <p className="text-sm text-[var(--muted)]">
            Draft v{draft.profile_version} · {draft.nlp_pipeline_version ?? "no NLP version"} ·{" "}
            {draft.ontology_version ?? "no ontology"} · {draft.confirmation_status}
          </p>
          <label className="block text-sm">
            Summary
            <textarea
              className="mt-2 w-full rounded border border-[var(--border)] p-2 text-sm"
              rows={4}
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
            />
          </label>
          <div>
            <p className="text-sm font-medium">Extracted skill mentions (raw)</p>
            <ul className="mt-2 flex flex-wrap gap-2 text-sm">
              {skills.map((skill) => (
                <li key={`${skill.raw_text}-${skill.evidence}`} className="rounded border px-2 py-1">
                  {skill.raw_text}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-medium">Normalized skills (not a match score)</p>
            <ul className="mt-2 space-y-1 text-sm">
              {(draft.normalized_skills ?? []).map((item) => (
                <li key={`${item.raw_text}-${item.canonical_skill_id ?? "none"}`}>
                  {item.raw_text} → {item.canonical_skill_name ?? "Needs review"} ({item.resolution_type}
                  {item.needs_review ? ", needs review" : ""})
                </li>
              ))}
            </ul>
          </div>
          <ReviewList
            title="Experience"
            items={(extraction?.experience ?? []).map(
              (item) => `${item.job_title ?? "Untitled"} · ${item.employer ?? "unknown employer"}`,
            )}
          />
          <ReviewList
            title="Education"
            items={(extraction?.education ?? []).map(
              (item) => `${item.degree ?? "Degree"} · ${item.institution ?? "unknown institution"}`,
            )}
          />
          <ReviewList
            title="Projects"
            items={(extraction?.projects ?? []).map((item) => item.name ?? "Untitled project")}
          />
          <ReviewList
            title="Certifications"
            items={(extraction?.certifications ?? []).map((item) => item.name ?? "Certification")}
          />
          <div className="flex gap-2">
            <Button type="button" disabled={busy} onClick={() => void save()}>
              Save draft
            </Button>
            <Button type="button" disabled={busy} onClick={() => void confirm()}>
              Confirm profile
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-[var(--muted)]">Upload a resume to create an extraction draft.</p>
      )}
    </div>
  );
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div>
      <p className="text-sm font-medium">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
