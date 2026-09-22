"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { ConfirmationBadge, ParseStatusBadge } from "@/components/ui/status-badge";
import {
  ApiError,
  deleteResume,
  getProfile,
  listResumes,
  uploadResume,
  type ResumeSummary,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import { describeHttpError } from "@/lib/http-error";
import { formatBytes, isTerminalParseStatus } from "@/lib/resume-status";

function processingCopy(status: string): string | null {
  if (status === "queued") {
    return "Queued";
  }
  if (status === "processing") {
    return "Processing document";
  }
  return null;
}

export function ResumeManager() {
  const { user, accessToken } = useAuth();
  const candidateId = user?.candidate_id ?? null;
  const [file, setFile] = useState<File | null>(null);
  const [items, setItems] = useState<ResumeSummary[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!candidateId || !accessToken) {
      return;
    }
    const payload = await listResumes(candidateId, accessToken);
    setItems(payload.items);
    try {
      const profile = await getProfile(candidateId, accessToken);
      setConfirmation(profile.confirmed?.confirmation_status ?? profile.draft?.confirmation_status ?? null);
    } catch {
      setConfirmation(null);
    }
  }, [accessToken, candidateId]);

  useEffect(() => {
    void refresh()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    const pending = items.some((item) => !isTerminalParseStatus(item.parse_status));
    if (!pending) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [items, refresh]);

  async function onUpload() {
    if (!file || !candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    setProgress(0);
    setStatus("Uploading");
    try {
      const result = await uploadResume(candidateId, file, accessToken, setProgress);
      setStatus(processingCopy(result.parse_status) ?? "Uploaded");
      setFile(null);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err instanceof ApiError ? err : err));
      setStatus(null);
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  async function onDelete(resumeId: string) {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteResume(candidateId, resumeId, accessToken);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (!candidateId) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is attached to this account.</p>;
  }
  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div>
      <PageHeader
        title="Resumes"
        description="Upload a PDF or DOCX. Processing status is reported by the document pipeline; extraction percentages are not estimated."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <Card className="mb-4">
        <CardHeader title="Upload" />
        <CardBody className="space-y-3">
          <label className="block text-sm">
            Resume file (PDF or DOCX)
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="mt-2 block w-full text-sm"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div
            className="border border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--muted)]"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const dropped = event.dataTransfer.files[0];
              if (dropped) {
                setFile(dropped);
              }
            }}
          >
            Drop a PDF or DOCX here, or use the file picker.
          </div>
          {file ? (
            <p className="text-sm text-[var(--muted)]">
              {file.name} · {formatBytes(file.size)}
            </p>
          ) : null}
          {progress !== null ? <p className="text-sm">Uploading {progress}%</p> : null}
          {status ? <p className="text-sm">{status}</p> : null}
          <Button type="button" disabled={!file || busy} onClick={() => void onUpload()}>
            {busy ? "Working…" : "Upload"}
          </Button>
        </CardBody>
      </Card>
      {items.length === 0 ? (
        <EmptyState
          title="No resume uploaded yet."
          description="Upload a PDF or DOCX to build your profile."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <Card>
                <CardBody className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-medium">{item.filename}</p>
                    <p className="text-sm text-[var(--muted)]">
                      Uploaded {formatDate(item.created_at)} · {formatBytes(item.file_size)}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <ParseStatusBadge status={item.parse_status} />
                      {processingCopy(item.parse_status) ? (
                        <span className="text-xs text-[var(--muted)]">{processingCopy(item.parse_status)}</span>
                      ) : null}
                      {item.parse_status === "ready" ? <ConfirmationBadge status={confirmation} /> : null}
                    </div>
                  </div>
                  <Button type="button" variant="outline" disabled={busy} onClick={() => void onDelete(item.id)}>
                    Delete
                  </Button>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
