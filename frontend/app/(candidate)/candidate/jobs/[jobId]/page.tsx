import { CandidateJobMatchDetail } from "@/components/matching/candidate-job-match-detail";

export default async function CandidateJobMatchPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return <CandidateJobMatchDetail jobId={jobId} />;
}
