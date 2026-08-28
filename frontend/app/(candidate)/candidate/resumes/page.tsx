import { ResumeManager } from "@/components/resumes/resume-manager";

export default function CandidateResumesPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Resumes</h1>
      <p className="text-[var(--muted)]">
        Upload a PDF or DOCX. This page tracks processing status only. Skill
        extraction and matching are not implemented yet.
      </p>
      <ResumeManager />
    </div>
  );
}
