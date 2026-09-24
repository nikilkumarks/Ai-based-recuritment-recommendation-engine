import { Badge } from "@/components/ui/badge";
import { parseStatusLabel } from "@/lib/resume-status";

export function ParseStatusBadge({ status }: { status: string }) {
  const tone =
    status === "ready"
      ? "success"
      : status === "failed"
        ? "danger"
        : status === "needs_ocr"
          ? "warning"
          : status === "processing" || status === "queued"
            ? "info"
            : "neutral";
  return <Badge tone={tone}>{parseStatusLabel(status)}</Badge>;
}

export function ConfirmationBadge({ status }: { status: string | null | undefined }) {
  if (status === "confirmed") {
    return <Badge tone="success">Confirmed</Badge>;
  }
  if (status === "draft") {
    return <Badge tone="warning">Needs review</Badge>;
  }
  return <Badge>Unconfirmed</Badge>;
}

export function DecisionBadge({ action }: { action: string | null | undefined }) {
  if (action === "hire" || action === "hired") {
    return <Badge tone="success">Hired</Badge>;
  }
  if (action === "shortlist" || action === "shortlisted") {
    return <Badge tone="success">Shortlisted</Badge>;
  }
  if (action === "reject" || action === "rejected") {
    return <Badge tone="danger">Rejected</Badge>;
  }
  if (action === "review") {
    return <Badge tone="warning">Review</Badge>;
  }
  return <Badge>No decision</Badge>;
}

export function ScoringModeBadge({
  mode,
  modelVersion,
}: {
  mode: "baseline" | "trained";
  modelVersion?: string | null;
}) {
  if (mode === "trained" && modelVersion) {
    return (
      <span className="inline-flex flex-wrap items-center gap-1.5">
        <Badge tone="info">Trained</Badge>
        <span className="font-mono text-xs text-[var(--muted)]">{modelVersion}</span>
      </span>
    );
  }
  return <Badge>Baseline</Badge>;
}
