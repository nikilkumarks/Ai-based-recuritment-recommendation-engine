import { cn } from "@/lib/utils";

type Tone = "accent" | "success" | "warning" | "info" | "danger" | "neutral";

const fills: Record<Tone, string> = {
  accent: "bg-teal-600",
  success: "bg-emerald-600",
  warning: "bg-amber-500",
  info: "bg-sky-600",
  danger: "bg-rose-600",
  neutral: "bg-slate-400",
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
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
        <span>{label}</span>
        <span className="font-mono text-slate-900 font-bold">{pct === null ? "N/A" : `${pct}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100 border border-slate-200/60" aria-hidden="true">
        <div className={cn("h-full rounded-full transition-all duration-500", fills[tone])} style={{ width: `${pct ?? 0}%` }} />
      </div>
      {hint ? <p className="text-[11px] text-slate-500 leading-tight">{hint}</p> : null}
    </div>
  );
}

