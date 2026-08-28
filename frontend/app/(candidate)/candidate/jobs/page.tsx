import { CandidateJobsList } from "@/components/matching/candidate-jobs-list";

export default function CandidateJobsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Jobs</h1>
      <p className="text-[var(--muted)]">
        Baseline Match for jobs you can see. This is not a trained AI score.
      </p>
      <CandidateJobsList />
    </div>
  );
}
