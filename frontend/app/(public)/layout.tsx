import type { ReactNode } from "react";
import { SiteHeader } from "@/components/site-header";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
    </>
  );
}
