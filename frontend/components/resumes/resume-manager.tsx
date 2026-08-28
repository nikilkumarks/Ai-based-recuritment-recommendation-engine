"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  deleteResume,
  listResumes,
  uploadResume,
  type ResumeSummary,
} from "@/lib/api";
import { formatBytes, isTerminalParseStatus, parseStatusLabel } from "@/lib/resume-status";

export function ResumeManager() {
  const { user, accessToken } = useAuth();
  const candidateId = user?.candidate_id ?? null;
  const [file, setFile] = useState<File | null>(null);
  const [items, setItems] = useState<ResumeSummary[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!candidateId || !accessToken) {
      return;
    }
    const payload = await listResumes(candidateId, accessToken);
    setItems(payload.items);
  }, [accessToken, candidateId]);

  useEffect(() => {
    void refresh().catch((err) => setError(describeAuthError(err)));
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
    setStatus("Uploading…");
    try {
      const result = await uploadResume(candidateId, file, accessToken, setProgress);
      setStatus(`Uploaded — ${parseStatusLabel(result.parse_status)}`);
      setFile(null);
      await refresh();
    } catch (err) {
      setError(describeAuthError(err instanceof ApiError ? err : err));
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
      setError(describeAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!candidateId) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is attached to this account.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
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
          className="rounded border border-dashed border-[var(--border)] p-4 text-sm text-[var(--muted)]"
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
        {progress !== null ? <p className="text-sm">Upload progress: {progress}%</p> : null}
        {status ? <p className="text-sm">{status}</p> : null}
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <Button type="button" disabled={!file || busy} onClick={() => void onUpload()}>
          {busy ? "Working…" : "Upload"}
        </Button>
      </div>

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Uploaded resumes</h2>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No resumes yet.</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm"
              >
                <div>
                  <p className="font-medium">{item.filename}</p>
                  <p className="text-[var(--muted)]">
                    {parseStatusLabel(item.parse_status)} · {formatBytes(item.file_size)}
                    {item.parser_version ? ` · ${item.parser_version}` : ""}
                  </p>
                </div>
                <Button type="button" variant="outline" disabled={busy} onClick={() => void onDelete(item.id)}>
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
