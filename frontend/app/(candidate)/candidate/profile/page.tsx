import { ProfileManager } from "@/components/profiles/profile-manager";

export default function CandidateProfilePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Profile draft</h1>
      <p className="text-[var(--muted)]">
        Review extracted fields, edit them, and confirm. NLP extraction is not
        semantic skill normalization.
      </p>
      <ProfileManager />
    </div>
  );
}
