import { describe, expect, it } from "vitest";
import { dashboardPath, isUserRole } from "@/lib/auth";
import { clearSessionHint, readSessionHint, setSessionHint } from "@/lib/session-hint";

describe("dashboardPath", () => {
  it("routes each role to its placeholder area", () => {
    expect(dashboardPath("candidate")).toBe("/candidate");
    expect(dashboardPath("recruiter")).toBe("/recruiter");
    expect(dashboardPath("admin")).toBe("/admin");
  });
});

describe("isUserRole", () => {
  it("accepts only known roles", () => {
    expect(isUserRole("candidate")).toBe(true);
    expect(isUserRole("admin")).toBe(true);
    expect(isUserRole("superuser")).toBe(false);
  });
});

describe("session hint cookie", () => {
  it("stores and clears the UX-only role hint", () => {
    setSessionHint("candidate");
    expect(readSessionHint()).toBe("candidate");
    clearSessionHint();
    expect(readSessionHint()).toBeNull();
  });
});
