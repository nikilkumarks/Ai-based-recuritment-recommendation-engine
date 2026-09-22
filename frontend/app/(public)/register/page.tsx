import Link from "next/link";
import { RegisterForm } from "@/components/auth/register-form";

export default function RegisterPage() {
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-xl font-semibold">Create an account</h1>
      <p className="text-sm text-[var(--muted)]">
        Candidates and recruiters can self-register. Admin accounts are not created here.
      </p>
      <RegisterForm />
      <p className="text-sm text-[var(--muted)]">
        Already registered?{" "}
        <Link href="/login" className="underline-offset-2 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
