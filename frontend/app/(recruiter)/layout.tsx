import type { ReactNode } from "react";
import { RoleGuard } from "@/components/auth/role-guard";
import { AppShell } from "@/components/layout/app-shell";

export default function RecruiterLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard allow="recruiter">
      <AppShell role="recruiter">{children}</AppShell>
    </RoleGuard>
  );
}
