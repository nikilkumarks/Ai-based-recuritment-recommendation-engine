"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";

export function RegisterForm() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
        organizationName: role === "recruiter" ? organizationName : undefined,
      });
      router.replace("/login?registered=1");
    } catch (err) {
      setError(describeAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="space-y-3 border border-[var(--border)] bg-[var(--card)] p-5">
      <label className="block text-sm">
        Email
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Password
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Account type
        <select
          value={role}
          onChange={(event) => setRole(event.target.value as "candidate" | "recruiter")}
          className="mt-1 w-full px-3 py-2"
        >
          <option value="candidate">Candidate</option>
          <option value="recruiter">Recruiter</option>
        </select>
      </label>
      {role === "recruiter" ? (
        <label className="block text-sm">
          Organization name
          <input
            required
            value={organizationName}
            onChange={(event) => setOrganizationName(event.target.value)}
            className="mt-1 w-full px-3 py-2"
          />
        </label>
      ) : null}
      {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  );
}
