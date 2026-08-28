"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import type { UserRole } from "@/lib/auth";

export function RoleGuard({
  allow,
  children,
}: {
  allow: UserRole;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { status, user } = useAuth();

  useEffect(() => {
    if (status === "loading") {
      return;
    }
    if (status !== "authenticated") {
      router.replace("/login");
      return;
    }
    if (user?.role !== allow) {
      router.replace("/forbidden");
    }
  }, [allow, router, status, user?.role]);

  if (status === "loading") {
    return <p className="text-sm text-[var(--muted)]">Checking session…</p>;
  }
  if (status !== "authenticated" || user?.role !== allow) {
    return <p className="text-sm text-[var(--muted)]">Redirecting…</p>;
  }
  return <>{children}</>;
}
