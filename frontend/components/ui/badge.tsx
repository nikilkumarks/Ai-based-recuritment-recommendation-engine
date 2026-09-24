import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const tones: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 border-slate-200",
  success: "bg-emerald-50 text-emerald-800 border-emerald-200/80 font-semibold",
  warning: "bg-amber-50 text-amber-800 border-amber-200/80 font-semibold",
  danger: "bg-rose-50 text-rose-800 border-rose-200/80 font-semibold",
  info: "bg-sky-50 text-sky-800 border-sky-200/80 font-semibold",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

