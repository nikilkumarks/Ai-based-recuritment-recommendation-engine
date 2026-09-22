import { cn } from "@/lib/utils";

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
    danger: "border-[var(--danger)] bg-[var(--danger-bg)] text-[var(--danger)]",
    warning: "border-[var(--warning)] bg-[var(--warning-bg)] text-[var(--warning)]",
    info: "border-[var(--info)] bg-[var(--info-bg)] text-[var(--info)]",
    success: "border-[var(--success)] bg-[var(--success-bg)] text-[var(--success)]",
  };
  return (
    <div role="alert" className={cn("rounded-[var(--radius)] border px-3 py-2 text-sm", styles[tone], className)}>
      {children}
    </div>
  );
}
