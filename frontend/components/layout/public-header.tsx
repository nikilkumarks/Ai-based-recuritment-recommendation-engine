import Link from "next/link";
import { AuthStatus } from "@/components/auth/auth-status";

export function PublicHeader() {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--card)]">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          SkillMatch
        </Link>
        <AuthStatus />
      </div>
    </header>
  );
}
