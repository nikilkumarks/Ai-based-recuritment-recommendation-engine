import { RecruiterCandidateDetail } from "@/components/matching/recruiter-candidate-detail";

export default async function RecruiterCandidateDetailPage({
  params,
}: {
  params: Promise<{ jobId: string; candidateId: string }>;
}) {
  const { jobId, candidateId } = await params;
  return <RecruiterCandidateDetail jobId={jobId} candidateId={candidateId} />;
}
