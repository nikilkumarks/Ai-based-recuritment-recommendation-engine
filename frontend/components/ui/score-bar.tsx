import { cn } from "@/lib/utils";

type Tone = "accent" | "success" | "warning" | "info" | "danger" | "neutral";

const fills: Record<Tone, string> = {
  accent: "bg-[var(--accent)]",
  success: "bg-[var(--success)]",
  warning: "bg-[var(--warning)]",
  info: "bg-[var(--info)]",
  danger: "bg-[var(--danger)]",
  neutral: "bg-[var(--muted)]",
};

export function ScoreBar({
  value,
  label,
  hint,
  tone = "accent",
}: {
  value: number | null | undefined;
  label: string;
  hint?: string;
  tone?: Tone;
}) {
  const pct = value == null || Number.isNaN(value) ? null : Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <span className="text-sm text-[var(--muted)]">{label}</span>
        <span className="tabular text-sm font-semibold">{pct === null ? "n/a" : `${pct}%`}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--background)]" aria-hidden="true">
        <div className={cn("h-full rounded-full", fills[tone])} style={{ width: `${pct ?? 0}%` }} />
      </div>
      {hint ? <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  );
}
