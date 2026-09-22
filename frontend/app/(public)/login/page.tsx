import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  const params = await searchParams;
  const registered = params.registered === "1";
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <p className="text-sm text-[var(--muted)]">
        Access tokens stay in memory. The refresh session uses an httpOnly cookie.
      </p>
      {registered ? (
        <p className="border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm">
          Account created. You can sign in now.
        </p>
      ) : null}
      <LoginForm />
      <p className="text-sm text-[var(--muted)]">
        No account?{" "}
        <Link href="/register" className="underline-offset-2 hover:underline">
          Register
        </Link>
      </p>
    </div>
  );
}
