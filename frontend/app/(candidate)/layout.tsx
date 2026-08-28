import type { ReactNode } from "react";
import { RoleGuard } from "@/components/auth/role-guard";
import { SiteHeader } from "@/components/site-header";

export default function CandidateLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard allow="candidate">
      <SiteHeader role="Candidate" />
      <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
    </RoleGuard>
  );
}
