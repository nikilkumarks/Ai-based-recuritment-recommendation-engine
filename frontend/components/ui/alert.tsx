import { cn } from "@/lib/utils";
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from "lucide-react";

export function Alert({
  children,
  tone = "danger",
  className,
}: {
  children: React.ReactNode;
  tone?: "danger" | "warning" | "info" | "success";
  className?: string;
}) {
  const styles = {
    danger: "border-rose-200 bg-rose-50/90 text-rose-800",
    warning: "border-amber-200 bg-amber-50/90 text-amber-800",
    info: "border-sky-200 bg-sky-50/90 text-sky-800",
    success: "border-emerald-200 bg-emerald-50/90 text-emerald-800",
  };

  const Icon = tone === "danger" ? AlertCircle : tone === "warning" ? AlertTriangle : tone === "info" ? Info : CheckCircle2;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2.5 rounded-xl border p-3.5 text-xs font-semibold leading-relaxed shadow-2xs",
        styles[tone],
        className,
      )}
    >
      <Icon className="h-4 w-4 shrink-0 mt-0.5" />
      <div className="flex-1">{children}</div>
    </div>
  );
}

