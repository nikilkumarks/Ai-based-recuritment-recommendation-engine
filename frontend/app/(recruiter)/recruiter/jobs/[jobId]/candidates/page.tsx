import { RecruiterJobCandidates } from "@/components/matching/recruiter-job-candidates";

export default async function RecruiterJobCandidatesPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Candidates</h1>
      <p className="text-[var(--muted)]">
        Sorted by Baseline Match descending. This is baseline sorting, not a trained ranker.
      </p>
      <RecruiterJobCandidates jobId={jobId} />
    </div>
  );
}
