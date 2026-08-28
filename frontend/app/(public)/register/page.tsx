import Link from "next/link";
import { RegisterForm } from "@/components/auth/register-form";

export default function RegisterPage() {
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Register</h1>
      <p className="text-[var(--muted)]">
        Candidates and recruiters can self-register. Admin accounts are not created
        here.
      </p>
      <RegisterForm />
      <p className="text-sm text-[var(--muted)]">
        Already registered?{" "}
        <Link href="/login" className="text-[var(--foreground)] underline">
          Login
        </Link>
      </p>
    </div>
  );
}
