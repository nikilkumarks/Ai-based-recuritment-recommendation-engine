"use client";

import Link from "next/link";
import Image from "next/image";
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
  Sparkles,
} from "lucide-react";
import { AuthStatus } from "@/components/auth/auth-status";
import { cn } from "@/lib/utils";

type Item = { href: string; label: string; icon: typeof LayoutDashboard };

const NAV: Record<string, Item[]> = {
  candidate: [
    { href: "/candidate", label: "Dashboard", icon: LayoutDashboard },
    { href: "/candidate/profile", label: "Profile", icon: UserRound },
    { href: "/candidate/resumes", label: "Resumes", icon: FolderKanban },
    { href: "/candidate/applications", label: "Applications", icon: FolderKanban },
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
    { href: "/admin/users", label: "Users / Orgs", icon: Users },
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
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-slate-900 text-slate-100 shadow-xl transition-transform lg:translate-x-0 border-r border-slate-800",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
          <Link href={`/${role}`} className="flex items-center gap-3 group">
            <Image
              src="/Logo.jpeg"
              alt="SkillMatch Logo"
              width={34}
              height={34}
              className="h-8 w-8 rounded-lg object-cover border border-slate-700 shadow-2xs group-hover:scale-105 transition-transform"
            />
            <div>
              <span className="text-sm font-bold text-white tracking-tight block leading-none">
                SkillMatch
              </span>
              <span className="text-[10px] text-teal-400 font-semibold uppercase tracking-wider block mt-1">
                {title} Portal
              </span>
            </div>
          </Link>
          <button
            type="button"
            className="lg:hidden text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 space-y-1 p-3" aria-label={`${title} navigation`}>
          <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Menu
          </div>
          {items.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all",
                  active
                    ? "bg-teal-700 text-white shadow-xs"
                    : "text-slate-300 hover:bg-slate-800/80 hover:text-white",
                )}
              >
                <Icon className={cn("h-4 w-4 shrink-0", active ? "text-teal-200" : "text-slate-400")} aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer Note */}
        <div className="border-t border-slate-800/90 p-4">
          <div className="rounded-xl bg-slate-800/60 p-3 border border-slate-700/50 space-y-1">
            <div className="flex items-center gap-1.5 text-teal-400 font-bold text-[11px]">
              <Sparkles className="h-3 w-3 shrink-0" />
              <span>Evidence Engine</span>
            </div>
            <p className="text-[10px] leading-normal text-slate-400 font-medium">
              Recommendations reflect verified skill evidence.
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile Backdrop */}
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-slate-900/60 backdrop-blur-xs lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setOpen(false)}
        />
      ) : null}

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 sm:px-6 backdrop-blur-sm shadow-2xs">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="lg:hidden text-slate-600 hover:text-slate-900 p-1.5 rounded-lg border border-slate-200 bg-slate-50"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Workspace</span>
              <span className="text-slate-300">/</span>
              <span className="text-xs font-bold text-slate-900">{title}</span>
            </div>
          </div>
          <AuthStatus />
        </header>

        <main className="flex-1 mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
}

