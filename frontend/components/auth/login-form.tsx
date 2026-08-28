"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardPath } from "@/lib/auth";

export function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const user = await login(email, password);
      router.replace(dashboardPath(user.role));
    } catch (err) {
      setError(describeAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
      <label className="block text-sm">
        Email
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full rounded border border-[var(--border)] bg-transparent px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Password
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded border border-[var(--border)] bg-transparent px-3 py-2"
        />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
