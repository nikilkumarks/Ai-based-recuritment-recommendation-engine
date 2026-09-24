"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import {
  Mail,
  Lock,
  Building2,
  Eye,
  EyeOff,
  UserRound,
  BriefcaseBusiness,
  Loader2,
  AlertCircle,
} from "lucide-react";

export function RegisterForm() {
  const router = useRouter();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState<"candidate" | "recruiter">("candidate");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      await register({
        email,
        password,
        role,
        organizationName:
          role === "recruiter" ? organizationName : undefined,
      });

      router.replace("/login?registered=1");
    } catch (err) {
      setError(describeAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xl shadow-slate-200/50 space-y-6">
      <div>
        <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
          Create your account
        </h2>
        <p className="mt-1 text-xs text-slate-500 font-medium">
          Choose your role and get started with SkillMatch.
        </p>
      </div>

      <form onSubmit={(event) => void onSubmit(event)} className="space-y-4">
        {error ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50/90 p-3.5 text-xs text-rose-800 font-medium">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-bold block text-rose-900">Registration failed</span>
              <span className="text-[11px] leading-tight block">{error}</span>
            </div>
          </div>
        ) : null}

        {/* Account Type Selection */}
        <div className="space-y-2">
          <label htmlFor="account-type-select" className="block text-xs font-semibold text-slate-700">
            Account type
          </label>
          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Account type">
            <button
              type="button"
              role="radio"
              aria-checked={role === "candidate"}
              onClick={() => setRole("candidate")}
              className={`flex flex-col items-center justify-center p-3.5 rounded-xl border transition-all text-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 ${
                role === "candidate"
                  ? "border-teal-600 bg-teal-50/60 text-teal-900 ring-2 ring-teal-600/20 shadow-2xs font-semibold"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50/80"
              }`}
            >
              <UserRound className={`h-5 w-5 mb-1.5 ${role === "candidate" ? "text-teal-700" : "text-slate-400"}`} />
              <span className="text-xs font-bold">Candidate</span>
            </button>

            <button
              type="button"
              role="radio"
              aria-checked={role === "recruiter"}
              onClick={() => setRole("recruiter")}
              className={`flex flex-col items-center justify-center p-3.5 rounded-xl border transition-all text-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 ${
                role === "recruiter"
                  ? "border-teal-600 bg-teal-50/60 text-teal-900 ring-2 ring-teal-600/20 shadow-2xs font-semibold"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50/80"
              }`}
            >
              <BriefcaseBusiness className={`h-5 w-5 mb-1.5 ${role === "recruiter" ? "text-teal-700" : "text-slate-400"}`} />
              <span className="text-xs font-bold">Recruiter</span>
            </button>
          </div>

          {/* Accessible Select element for screen readers and unit tests */}
          <select
            id="account-type-select"
            aria-label="Account type"
            value={role}
            onChange={(event) =>
              setRole(event.target.value as "candidate" | "recruiter")
            }
            className="sr-only"
            tabIndex={-1}
          >
            <option value="candidate">Candidate</option>
            <option value="recruiter">Recruiter</option>
          </select>
        </div>

        {/* Email Field */}
        <div className="space-y-1.5">
          <label htmlFor="register-email" className="block text-xs font-semibold text-slate-700">
            Email address
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
              <Mail className="h-4 w-4" />
            </div>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 transition-all"
            />
          </div>
        </div>

        {/* Password Field */}
        <div className="space-y-1.5">
          <label htmlFor="register-password" className="block text-xs font-semibold text-slate-700">
            Password
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
              <Lock className="h-4 w-4" />
            </div>
            <input
              id="register-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              minLength={8}
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {/* Recruiter Organization Field */}
        {role === "recruiter" ? (
          <div className="space-y-1.5">
            <label htmlFor="register-organization" className="block text-xs font-semibold text-slate-700">
              Organization name
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <Building2 className="h-4 w-4" />
              </div>
              <input
                id="register-organization"
                type="text"
                required
                placeholder="Acme Corp"
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
                className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 transition-all"
              />
            </div>
          </div>
        ) : null}

        {/* Submit Button */}
        <Button
          type="submit"
          className="w-full h-11 bg-teal-700 hover:bg-teal-800 text-white font-semibold text-sm rounded-xl shadow-xs transition-all disabled:opacity-70 cursor-pointer"
          disabled={pending}
        >
          {pending ? (
            <div className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>Creating account…</span>
            </div>
          ) : (
            "Create account"
          )}
        </Button>
      </form>

      {/* Login Link */}
      <div className="pt-2 text-center text-xs text-slate-500 border-t border-slate-100">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-semibold text-teal-700 hover:text-teal-800 hover:underline transition-colors"
        >
          Sign in
        </Link>
      </div>
    </div>
  );
}