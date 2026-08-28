import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Not allowed</h1>
      <p className="text-[var(--muted)]">
        This page is for a different role. Frontend routing is only a convenience —
        the API still enforces authorization.
      </p>
      <Link href="/" className="text-sm underline">
        Back to home
      </Link>
    </div>
  );
}
