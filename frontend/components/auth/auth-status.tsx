"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { dashboardPath } from "@/lib/auth";
import { User, LogOut, Loader2 } from "lucide-react";

export function AuthStatus() {
  const { status, user, logout } = useAuth();

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-600" />
        <span>Loading...</span>
      </div>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <div className="flex items-center gap-2.5 text-xs font-semibold">
        <Link
          href="/login"
          className="px-3 py-1.5 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors"
        >
          Sign in
        </Link>
        <Link
          href="/register"
          className="px-3 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white shadow-2xs transition-colors"
        >
          Create account
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link
        href={dashboardPath(user.role)}
        className="flex items-center gap-2.5 rounded-xl border border-slate-200/80 bg-slate-50/80 px-3 py-1.5 hover:bg-slate-100/80 transition-colors group"
      >
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-teal-100 text-teal-700 font-bold text-xs">
          <User className="h-3.5 w-3.5" />
        </div>
        <div className="flex flex-col text-left">
          <span className="text-xs font-semibold text-slate-900 leading-none group-hover:text-teal-700 transition-colors">
            {user.email}
          </span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mt-0.5">
            {user.role}
          </span>
        </div>
      </Link>
      <button
        type="button"
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-rose-600 px-2 py-1.5 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
        onClick={() => void logout()}
        title="Sign out"
      >
        <LogOut className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Logout</span>
      </button>
    </div>
  );
}

