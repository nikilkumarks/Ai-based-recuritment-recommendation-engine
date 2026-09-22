import { RecruiterJobCandidates } from "@/components/matching/recruiter-job-candidates";
import { PageHeader } from "@/components/ui/page-header";

export default async function RecruiterJobCandidatesPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return (
    <div>
      <PageHeader
        title="Candidate ranking"
        description="Scan Current Match, Potential, coverage, and gaps. Shortlist and reject are recruiter actions, not hiring outcomes."
      />
      <RecruiterJobCandidates jobId={jobId} />
    </div>
  );
}
