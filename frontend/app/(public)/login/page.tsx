import Image from "next/image";
import { LoginForm } from "@/components/auth/login-form";
import { CheckCircle2, ShieldCheck } from "lucide-react";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  const params = await searchParams;
  const registered = params.registered === "1";

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
              Recruitment decisions backed by evidence.
            </h1>

            <p className="text-sm text-slate-600 leading-relaxed font-normal">
              Understand candidate skills, evaluate job fit, and review explainable evidence before making recruitment decisions.
            </p>
          </div>

          <div className="space-y-3 pt-2 text-xs font-medium text-slate-700 border-t border-slate-200/80">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
              <span>Evidence-based matching</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
              <span>Canonical skill ontology</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
              <span>Explainable candidate fit</span>
            </div>
          </div>
        </div>

        {/* Right Side: Centered Login Card */}
        <div className="lg:col-span-6">
          <LoginForm registered={registered} />
        </div>
      </div>
    </div>
  );
}
