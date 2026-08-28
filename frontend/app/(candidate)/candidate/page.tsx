import Link from "next/link";

export default function CandidateDashboardPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Candidate dashboard</h1>
      <p className="text-[var(--muted)]">
        Resume upload, NLP drafts, skill normalization, embeddings, and baseline matching
        are available. Ranking and trained ML are not implemented.
      </p>
      <Link href="/candidate/resumes" className="inline-block text-sm underline">
        Upload a resume
      </Link>
      <Link href="/candidate/profile" className="ml-4 inline-block text-sm underline">
        Review profile draft
      </Link>
      <Link href="/candidate/jobs" className="ml-4 inline-block text-sm underline">
        Baseline job matches
      </Link>
    </div>
  );
}
