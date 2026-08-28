import { JobManager } from "@/components/jobs/job-manager";

export default function RecruiterJobsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Jobs</h1>
      <p className="text-[var(--muted)]">
        Extract raw skill mentions from a job description. This is not matching
        and not ontology normalization.
      </p>
      <JobManager />
    </div>
  );
}
