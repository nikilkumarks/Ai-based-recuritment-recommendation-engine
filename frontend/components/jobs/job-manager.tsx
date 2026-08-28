"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { confirmJobRequirements, createJob, createJobEmbedding, getJob, getJobEmbedding, listJobs, type EmbeddingStatus, type JobDetail, type JobSummary } from "@/lib/api";
import { embeddingStatusLabel } from "@/lib/embedding-status";

export function JobManager() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<JobSummary[]>([]);
  const [selected, setSelected] = useState<JobDetail | null>(null);
  const [embedding, setEmbedding] = useState<EmbeddingStatus | null>(null);
  const [title, setTitle] = useState("Backend Engineer");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const payload = await listJobs(accessToken);
    setItems(payload.items);
  }, [accessToken]);

  useEffect(() => {
    void refresh().catch((err) => setError(describeAuthError(err)));
  }, [refresh]);

  async function onCreate() {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const job = await createJob(accessToken, { title, description_raw: description });
      setSelected(job);
      setEmbedding(null);
      await refresh();
    } catch (err) {
      setError(describeAuthError(err));
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
    await loadJob(id, accessToken);
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
      setError(describeAuthError(err));
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
      setError(describeAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  const required = selected?.requirements?.draft?.required_skills ?? [];
  const normalized = selected?.requirements?.normalized_required_skills ?? [];

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <label className="block text-sm">
          Title
          <input
            className="mt-2 w-full rounded border border-[var(--border)] p-2 text-sm"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="block text-sm">
          Job description
          <textarea
            className="mt-2 w-full rounded border border-[var(--border)] p-2 text-sm"
            rows={8}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <Button type="button" disabled={busy || description.length < 20} onClick={() => void onCreate()}>
          Extract requirements
        </Button>
      </div>
      <ul className="space-y-2 text-sm">
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" className="underline" onClick={() => void onOpen(item.id)}>
              {item.title}
            </button>
          </li>
        ))}
      </ul>
      {selected ? (
        <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6 text-sm">
          <p>
            {selected.title} · {selected.requirements?.confirmation_status ?? "no draft"}
          </p>
          <p>Required mentions: {required.map((item) => item.raw_text).join(", ") || "none"}</p>
          <p>
            Normalized required:{" "}
            {normalized
              .map((item) =>
                item.canonical_skill_name
                  ? `${item.raw_text} → ${item.canonical_skill_name}`
                  : `${item.raw_text} → Needs review`,
              )
              .join(", ") || "none"}
          </p>
          <p>
            Semantic representation: {embeddingStatusLabel(embedding)}
          </p>
          <Button type="button" disabled={busy || !selected.requirements} onClick={() => void onConfirm()}>
            Confirm requirements
          </Button>
          <Button
            type="button"
            disabled={busy || selected.requirements?.confirmation_status !== "confirmed"}
            onClick={() => void onEmbed()}
          >
            Generate embedding
          </Button>
          {selected.requirements?.confirmation_status === "confirmed" ? (
            <Link href={`/recruiter/jobs/${selected.id}/candidates`} className="ml-3 inline-block text-sm underline">
              Baseline match candidates
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
