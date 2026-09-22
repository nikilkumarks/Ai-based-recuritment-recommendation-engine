"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Briefcase,
  Database,
  FolderKanban,
  GitBranch,
  LayoutDashboard,
  Layers,
  LineChart,
  Menu,
  Route,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { AuthStatus } from "@/components/auth/auth-status";
import { cn } from "@/lib/utils";

type Item = { href: string; label: string; icon: typeof LayoutDashboard };

const NAV: Record<string, Item[]> = {
  candidate: [
    { href: "/candidate", label: "Dashboard", icon: LayoutDashboard },
    { href: "/candidate/profile", label: "Profile", icon: UserRound },
    { href: "/candidate/resumes", label: "Resumes", icon: FolderKanban },
    { href: "/candidate/jobs", label: "Recommended jobs", icon: Briefcase },
    { href: "/candidate/career", label: "Skill path", icon: Route },
  ],
  recruiter: [
    { href: "/recruiter", label: "Dashboard", icon: LayoutDashboard },
    { href: "/recruiter/jobs", label: "Jobs", icon: Briefcase },
    { href: "/recruiter/candidates", label: "Candidates", icon: Users },
    { href: "/recruiter/analytics", label: "Analytics", icon: LineChart },
  ],
  admin: [
    { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
    { href: "/admin/users", label: "Users / orgs", icon: Users },
    { href: "/admin/ontology", label: "Ontology", icon: GitBranch },
    { href: "/admin/datasets", label: "Datasets", icon: Database },
    { href: "/admin/models", label: "Models", icon: Layers },
    { href: "/admin/analytics", label: "Analytics", icon: LineChart },
  ],
};

function isActive(pathname: string, href: string): boolean {
  if (href === "/candidate" || href === "/recruiter" || href === "/admin") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({
  role,
  children,
}: {
  role: "candidate" | "recruiter" | "admin";
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const items = NAV[role];
  const title = role === "candidate" ? "Candidate" : role === "recruiter" ? "Recruiter" : "Admin";

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-[var(--sidebar)] text-[var(--sidebar-fg)] transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-4">
          <Link href={`/${role}`} className="text-sm font-semibold tracking-tight">
            SkillMatch
          </Link>
          <button
            type="button"
            className="lg:hidden"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="flex-1 space-y-0.5 p-3" aria-label={`${title} navigation`}>
          {items.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2 rounded-[var(--radius)] px-2.5 py-2 text-sm",
                  active
                    ? "bg-[var(--sidebar-active)] text-white"
                    : "text-[var(--sidebar-muted)] hover:bg-white/5 hover:text-white",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <p className="border-t border-white/10 px-4 py-3 text-[11px] leading-relaxed text-[var(--sidebar-muted)]">
          Recommendations explain skill evidence. They are not hiring outcomes.
        </p>
      </aside>
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--card)] px-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="lg:hidden"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <p className="text-sm font-medium">{title}</p>
          </div>
          <AuthStatus />
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
