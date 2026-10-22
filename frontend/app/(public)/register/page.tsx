import Image from "next/image";
import { RegisterForm } from "@/components/auth/register-form";
import { UserRound, BriefcaseBusiness, ShieldCheck } from "lucide-react";

export default function RegisterPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
        {/* Left Side: Branded Product-Information Panel */}
        <div className="lg:col-span-6 space-y-6 text-left">
          <div className="flex items-center gap-3">
            <Image
              src="/Logo.jpeg"
              alt="SkillMatch Logo"
              width={40}
              height={40}
              className="h-10 w-10 rounded-xl object-cover border border-slate-200 shadow-2xs"
            />
            <div>
              <span className="text-base font-bold text-slate-900 tracking-tight block leading-none">
                SkillMatch
              </span>
              <span className="text-[11px] text-slate-500 font-medium block mt-0.5">
                AI-Based Recruitment Recommendation Engine
              </span>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800 border border-teal-200/70">
              <ShieldCheck className="h-3.5 w-3.5 text-teal-700" />
              <span>Enterprise Recruitment Intelligence</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-snug">
              Build your path with SkillMatch.
            </h1>

            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              Create your account to discover opportunities or make evidence-based recruitment decisions.
            </p>
          </div>

          {/* Informational Cards */}
          <div className="space-y-3 pt-2">
            <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-4 flex items-start gap-3.5 shadow-2xs">
              <div className="p-2.5 rounded-xl bg-teal-50 text-teal-700 shrink-0">
                <UserRound className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-sm font-bold text-slate-900">Candidate</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Find opportunities and understand your career fit.
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-4 flex items-start gap-3.5 shadow-2xs">
              <div className="p-2.5 rounded-xl bg-teal-50 text-teal-700 shrink-0">
                <BriefcaseBusiness className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-sm font-bold text-slate-900">Recruiter's</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Find candidates and make evidence-based decisions.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Centered Register Card */}
        <div className="lg:col-span-6">
          <RegisterForm />
        </div>
      </div>
    </div>
  );
}

