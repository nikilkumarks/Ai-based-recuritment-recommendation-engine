import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-xl font-semibold">Not allowed</h1>
      <p className="text-sm text-[var(--muted)]">
        This page is for a different role. The API still enforces authorization even if a route is
        opened directly.
      </p>
      <Link href="/" className="text-sm underline-offset-2 hover:underline">
        Back to home
      </Link>
    </div>
  );
}
