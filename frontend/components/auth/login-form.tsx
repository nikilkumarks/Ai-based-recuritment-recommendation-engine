"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardPath, type UserRole } from "@/lib/auth";
import { Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

export function LoginForm({ registered }: { registered?: boolean }) {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [targetRole, setTargetRole] = useState<UserRole | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const user = await login(email, password);
      setTargetRole(user.role);
      setIsNavigating(true);
      router.replace(dashboardPath(user.role));
    } catch (err) {
      setError(describeAuthError(err));
      setPending(false);
      setIsNavigating(false);
    }
  }

  return (
    <>
      {/* Full-Page Premium Transition Screen */}
      {isNavigating ? (
        <div
          role="status"
          aria-busy="true"
          aria-live="polite"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-50/95 backdrop-blur-md p-4 transition-all duration-300"
        >
          <div className="flex flex-col items-center justify-center text-center space-y-4 max-w-sm w-full bg-white p-8 rounded-2xl border border-slate-200/90 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="relative">
              <Image
                src="/Logo.jpeg"
                alt="SkillMatch Logo"
                width={52}
                height={52}
                className="h-13 w-13 rounded-2xl object-cover border border-slate-200 shadow-xs"
              />
              <div className="absolute -bottom-1 -right-1 p-1 bg-teal-700 text-white rounded-full shadow-2xs">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
                Signing you in...
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                {targetRole ? `Loading your ${targetRole} workspace` : "Loading your workspace"}
              </p>
            </div>

            <div className="w-48 h-1.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/80">
              <div className="h-full bg-teal-600 rounded-full animate-pulse w-full" />
            </div>
          </div>
        </div>
      ) : null}

      {/* Login Card */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-xl shadow-slate-200/50 space-y-6">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">Welcome back</h2>
          <p className="mt-1 text-xs text-slate-500 font-medium">
            Sign in to continue to your SkillMatch workspace.
          </p>
        </div>

        {registered ? (
          <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 text-xs font-medium text-emerald-900">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>Account created successfully. You can sign in now.</span>
          </div>
        ) : null}

        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4">
          {error ? (
            <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50/90 p-3.5 text-xs text-rose-800 font-medium">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-bold block text-rose-900">Unable to sign in</span>
                <span className="text-[11px] leading-tight block">{error}</span>
              </div>
            </div>
          ) : null}

          <div className="space-y-1.5">
            <label htmlFor="login-email" className="block text-xs font-semibold text-slate-700">
              Email
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <Mail className="h-4 w-4" />
              </div>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                disabled={pending || isNavigating}
                placeholder="name@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 transition-all disabled:opacity-60"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="login-password" className="block text-xs font-semibold text-slate-700">
              Password
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <Lock className="h-4 w-4" />
              </div>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                disabled={pending || isNavigating}
                placeholder="••••••••"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 transition-all disabled:opacity-60"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-11 bg-teal-700 hover:bg-teal-800 text-white font-semibold text-sm rounded-xl shadow-xs transition-all disabled:opacity-70 cursor-pointer"
            disabled={pending || isNavigating}
          >
            {pending || isNavigating ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                <span>Signing in...</span>
              </div>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>

        <div className="pt-2 text-center text-xs text-slate-500 border-t border-slate-100">
          No account yet?{" "}
          <Link href="/register" className="font-semibold text-teal-700 hover:text-teal-800 hover:underline transition-colors">
            Create one
          </Link>
        </div>
      </div>
    </>
  );
}

