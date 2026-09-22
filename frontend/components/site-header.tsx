import Link from "next/link";
import { AuthStatus } from "@/components/auth/auth-status";

const links = [
  { href: "/", label: "Home" },
  { href: "/login", label: "Login" },
  { href: "/register", label: "Register" },
];

export function SiteHeader({ role }: { role?: string }) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--card)]">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          PRJ_385
        </Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm text-[var(--muted)]">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-[var(--foreground)]">
              {link.label}
            </Link>
          ))}
          {role === "Candidate" ? (
            <>
              <Link href="/candidate/resumes" className="hover:text-[var(--foreground)]">
                Resumes
              </Link>
              <Link href="/candidate/profile" className="hover:text-[var(--foreground)]">
                Profile
              </Link>
              <Link href="/candidate/jobs" className="hover:text-[var(--foreground)]">
                Jobs
              </Link>
            </>
          ) : null}
          {role === "Recruiter" ? (
            <>
              <Link href="/recruiter/jobs" className="hover:text-[var(--foreground)]">
                Jobs
              </Link>
              <Link href="/recruiter/analytics" className="hover:text-[var(--foreground)]">
                Analytics
              </Link>
            </>
          ) : null}
          {role === "Admin" ? (
            <>
              <Link href="/admin/datasets" className="hover:text-[var(--foreground)]">
                Datasets
              </Link>
              <Link href="/admin/models" className="hover:text-[var(--foreground)]">
                Models
              </Link>
            </>
          ) : null}
          <AuthStatus />
        </nav>
      </div>
      {role ? (
        <div className="border-t border-[var(--border)] px-6 py-2 text-center text-xs uppercase tracking-wide text-[var(--muted)]">
          {role} area — Phase 10 trains only from real labeled snapshots; no fake accuracy
        </div>
      ) : null}
    </header>
  );
}
