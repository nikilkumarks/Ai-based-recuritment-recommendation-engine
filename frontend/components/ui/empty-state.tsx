import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed border-slate-200/90 bg-slate-50/50 px-6 py-10 text-center space-y-2",
        className,
      )}
    >
      <p className="text-xs sm:text-sm font-bold text-slate-900">{title}</p>
      {description ? <p className="mx-auto max-w-md text-xs text-slate-500 font-medium leading-relaxed">{description}</p> : null}
      {action ? <div className="pt-2">{action}</div> : null}
    </div>
  );
}

