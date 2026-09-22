import type { ReactNode } from "react";
import { RoleGuard } from "@/components/auth/role-guard";
import { AppShell } from "@/components/layout/app-shell";

export default function CandidateLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard allow="candidate">
      <AppShell role="candidate">{children}</AppShell>
    </RoleGuard>
  );
}
