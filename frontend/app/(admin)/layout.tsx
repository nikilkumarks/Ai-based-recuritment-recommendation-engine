import type { ReactNode } from "react";
import { RoleGuard } from "@/components/auth/role-guard";
import { AppShell } from "@/components/layout/app-shell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard allow="admin">
      <AppShell role="admin">{children}</AppShell>
    </RoleGuard>
  );
}
