import { CandidateJobMatchDetail } from "@/components/matching/candidate-job-match-detail";

export default async function CandidateJobMatchPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Baseline match detail</h1>
      <CandidateJobMatchDetail jobId={jobId} />
    </div>
  );
}
