import Link from "next/link";

export default function RecruiterDashboardPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Recruiter dashboard</h1>
      <p className="text-[var(--muted)]">
        Job description extraction and baseline matching are available. Ranking and
        trained ML are not implemented.
      </p>
      <Link href="/recruiter/jobs" className="inline-block text-sm underline">
        Manage jobs
      </Link>
    </div>
  );
}
