import type { DistributionBucket } from "@/lib/api";

export function CountBars({
  items,
  empty,
}: {
  items: { name: string; count: number }[];
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-[var(--muted)]">{empty}</p>;
  }
  const max = Math.max(...items.map((item) => item.count), 1);
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.name}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span>{item.name}</span>
            <span className="tabular text-[var(--muted)]">{item.count}</span>
          </div>
          <div className="h-1.5 bg-[var(--background)]" aria-hidden="true">
            <div
              className="h-full bg-[var(--accent)]"
              style={{ width: `${Math.round((item.count / max) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function DistributionBars({
  items,
  empty,
}: {
  items: DistributionBucket[];
  empty: string;
}) {
  return (
    <CountBars
      items={items.map((item) => ({ name: item.bucket, count: item.count }))}
      empty={empty}
    />
  );
}

export function FunnelBars({
  applications,
  reviewed,
  shortlisted,
  rejected,
}: {
  applications: number;
  reviewed: number;
  shortlisted: number;
  rejected: number;
}) {
  const steps = [
    { name: "Applications", count: applications },
    { name: "Reviewed", count: reviewed },
    { name: "Shortlisted", count: shortlisted },
    { name: "Rejected", count: rejected },
  ];
  if (steps.every((item) => item.count === 0)) {
    return <p className="text-sm text-[var(--muted)]">No candidate decisions have been recorded.</p>;
  }
  return <CountBars items={steps} empty="No candidate decisions have been recorded." />;
}
