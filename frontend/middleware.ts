import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED: { prefix: string; role: string }[] = [
  { prefix: "/candidate", role: "candidate" },
  { prefix: "/recruiter", role: "recruiter" },
  { prefix: "/admin", role: "admin" },
];

function matches(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hint = request.cookies.get("session_hint")?.value;
  for (const rule of PROTECTED) {
    if (!matches(pathname, rule.prefix)) {
      continue;
    }
    if (!hint) {
      const login = request.nextUrl.clone();
      login.pathname = "/login";
      login.searchParams.set("next", pathname);
      return NextResponse.redirect(login);
    }
    if (hint !== rule.role) {
      const forbidden = request.nextUrl.clone();
      forbidden.pathname = "/forbidden";
      forbidden.search = "";
      return NextResponse.redirect(forbidden);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/candidate/:path*", "/recruiter/:path*", "/admin/:path*"],
};
