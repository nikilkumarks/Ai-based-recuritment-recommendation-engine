import { HealthStatus } from "@/components/health-status";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="space-y-8">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
        Phase 2 · Authentication
      </p>
      <h1 className="max-w-3xl text-4xl font-semibold tracking-tight">
        AI-Based Recruitment Recommendation Engine
      </h1>
      <p className="max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
        This project matches people and jobs by skill meaning, aliases, and
        hierarchy — not by exact keyword overlap. Authentication is implemented.
        Recommendation, NLP, and ML are not implemented yet.
      </p>
      <div className="flex gap-3">
        <Link
          href="/register"
          className="rounded bg-stone-900 px-4 py-2 text-sm text-white"
        >
          Register
        </Link>
        <Link
          href="/login"
          className="rounded border border-[var(--border)] px-4 py-2 text-sm"
        >
          Login
        </Link>
      </div>
      <section className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
        <h2 className="mb-2 text-sm font-semibold">Backend connectivity</h2>
        <HealthStatus />
      </section>
    </div>
  );
}
