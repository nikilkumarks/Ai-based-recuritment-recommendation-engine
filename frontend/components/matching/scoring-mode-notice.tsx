import { ScoringModeBadge } from "@/components/ui/status-badge";

export function ScoringModeNotice({
  mode,
  modelVersion,
  fallbackReason,
}: {
  mode: "baseline" | "trained";
  modelVersion?: string | null;
  fallbackReason?: string | null;
}) {
  const trained = mode === "trained" && Boolean(modelVersion);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-[var(--muted)]">Scoring mode</span>
      <ScoringModeBadge mode={trained ? "trained" : "baseline"} modelVersion={modelVersion} />
      {trained ? null : (
        <span className="text-[var(--muted)]">
          {fallbackReason ||
            "No trained model is currently active. Recommendations are using the deterministic baseline."}
        </span>
      )}
    </div>
  );
}
