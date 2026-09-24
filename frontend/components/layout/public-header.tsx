"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { AuthStatus } from "@/components/auth/auth-status";

export function PublicHeader() {
  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur-sm shadow-xs">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-2.5 sm:px-6">
        <Link href="/" className="flex items-center gap-3 group">
          <Image
            src="/Logo.jpeg"
            alt="AI-Based Recruitment Recommendation Engine"
            width={34}
            height={34}
            className="h-8 w-8 rounded-lg object-cover border border-slate-200 shadow-2xs group-hover:scale-105 transition-transform"
          />
          <div>
            <span className="text-base font-bold text-slate-900 tracking-tight block leading-none">
              SkillMatch
            </span>
            <span className="text-[10px] text-slate-500 font-medium block mt-0.5 tracking-wide">
              AI-Based Recruitment Recommendation Engine
            </span>
          </div>
        </Link>
        <div className="flex items-center gap-6">
          {isLandingPage ? (
            <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-600">
              <a href="#product" className="hover:text-teal-700 transition-colors">Product</a>
              <a href="#how-it-works" className="hover:text-teal-700 transition-colors">How It Works</a>
              <a href="#evidence" className="hover:text-teal-700 transition-colors">Evidence</a>
              <a href="#for-recruiters" className="hover:text-teal-700 transition-colors">For Recruiters</a>
            </nav>
          ) : null}
          <AuthStatus />
        </div>
      </div>
    </header>
  );
}
