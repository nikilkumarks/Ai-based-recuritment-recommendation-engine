import { CandidateJobsList } from "@/components/matching/candidate-jobs-list";
import { PageHeader } from "@/components/ui/page-header";

export default function CandidateJobsPage() {
  return (
    <div>
      <PageHeader
        title="Recommended jobs"
        description="Current Match is how closely you satisfy the requirements today. Potential is gap closability, not a hiring probability."
      />
      <CandidateJobsList />
    </div>
  );
}
