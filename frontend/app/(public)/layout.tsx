import type { ReactNode } from "react";
import { PublicHeader } from "@/components/layout/public-header";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50/50 flex flex-col font-sans">
      <PublicHeader />
      <main className="flex-1 w-full">{children}</main>
    </div>
  );
}
