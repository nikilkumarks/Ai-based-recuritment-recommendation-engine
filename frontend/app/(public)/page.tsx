import { HealthStatus } from "@/components/health-status";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="space-y-10">
      <section className="max-w-2xl space-y-4">
        <p className="text-sm text-[var(--muted)]">Recruitment recommendation engine</p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">
          Match candidates and jobs by skill evidence, not keyword overlap.
        </h1>
        <p className="text-[var(--muted)]">
          SkillMatch explains Current Match, remaining skill gaps, and Potential — how closable those
          gaps are using related skills. It does not produce an “AI score” or a hiring probability.
        </p>
        <div className="flex gap-3">
          <Link
            href="/register"
            className="inline-flex h-9 items-center bg-[var(--accent)] px-3.5 text-sm font-medium text-white"
          >
            Register
          </Link>
          <Link
            href="/login"
            className="inline-flex h-9 items-center border border-[var(--border)] bg-[var(--card)] px-3.5 text-sm font-medium"
          >
            Sign in
          </Link>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-3">
        <Feature
          title="Alias and hierarchy"
          body="ML resolves to Machine Learning. Child and parent skills are treated as evidence, not as exact mastery."
        />
        <Feature
          title="Related skills and paths"
          body="Docker can support a Kubernetes gap. Suggested paths come from the ontology graph."
        />
        <Feature
          title="Baseline vs trained"
          body="Scoring mode is always visible. A trained model appears only when one is active and compatible."
        />
      </section>
      <section className="border border-[var(--border)] bg-[var(--card)] p-5">
        <h2 className="mb-2 text-sm font-semibold">API connectivity</h2>
        <HealthStatus />
      </section>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-[var(--border)] bg-[var(--card)] p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">{body}</p>
    </div>
  );
}
