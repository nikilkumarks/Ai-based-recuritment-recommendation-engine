"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { dashboardPath } from "@/lib/auth";

export function AuthStatus() {
  const { status, user, logout } = useAuth();

  if (status === "loading") {
    return <span className="text-xs text-[var(--muted)]">…</span>;
  }

  if (status !== "authenticated" || !user) {
    return (
      <span className="flex gap-3 text-sm">
        <Link href="/login" className="hover:text-[var(--foreground)]">
          Login
        </Link>
        <Link href="/register" className="hover:text-[var(--foreground)]">
          Register
        </Link>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-3 text-sm">
      <Link href={dashboardPath(user.role)} className="hover:text-[var(--foreground)]">
        {user.email}
      </Link>
      <button type="button" className="hover:text-[var(--foreground)]" onClick={() => void logout()}>
        Logout
      </button>
    </span>
  );
}
