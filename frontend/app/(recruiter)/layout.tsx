import type { ReactNode } from "react";
import { RoleGuard } from "@/components/auth/role-guard";
import { SiteHeader } from "@/components/site-header";

export default function RecruiterLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard allow="recruiter">
      <SiteHeader role="Recruiter" />
      <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
    </RoleGuard>
  );
}
