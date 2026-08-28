import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "@/components/auth/auth-provider";
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";
import { RoleGuard } from "@/components/auth/role-guard";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("authentication UI", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/auth/refresh")) {
          return jsonResponse({ title: "Unauthenticated", status: 401, detail: "Invalid" }, 401);
        }
        return jsonResponse({ title: "Not found", status: 404 }, 404);
      }),
    );
  });

  it("renders the login form", async () => {
    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders the register form", async () => {
    render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>,
    );
    expect(await screen.findByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Account type")).toBeInTheDocument();
  });

  it("redirects unauthenticated users away from protected routes", async () => {
    render(
      <AuthProvider>
        <RoleGuard allow="candidate">
          <p>secret</p>
        </RoleGuard>
      </AuthProvider>,
    );
    expect(await screen.findByText("Redirecting…")).toBeInTheDocument();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});

function LogoutProbe() {
  const { status, user, login, logout, accessToken } = useAuth();
  return (
    <div>
      <p>status:{status}</p>
      <p>token:{accessToken ?? "none"}</p>
      <p>user:{user?.email ?? "none"}</p>
      <button type="button" onClick={() => void login("ada@example.com", "correct-horse-battery")}>
        do-login
      </button>
      <button type="button" onClick={() => void logout()}>
        do-logout
      </button>
    </div>
  );
}

describe("auth state", () => {
  it("keeps the access token in memory and clears it on logout", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/refresh") && (!init || init.method === "POST")) {
        if ((init?.headers as Headers | undefined)?.get?.("Authorization")) {
          return jsonResponse({ message: "ok" });
        }
        return jsonResponse({ title: "Unauthenticated", status: 401 }, 401);
      }
      if (url.endsWith("/api/v1/auth/login")) {
        return jsonResponse({
          access_token: "access-in-memory",
          token_type: "bearer",
          expires_in: 900,
          csrf_token: "csrf",
          user: { id: "1", email: "ada@example.com", role: "candidate", status: "active" },
        });
      }
      if (url.endsWith("/api/v1/auth/logout")) {
        return jsonResponse({ message: "Signed out." });
      }
      return jsonResponse({ title: "Not found", status: 404 }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText("status:anonymous")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "do-login" }));
    expect(await screen.findByText("token:access-in-memory")).toBeInTheDocument();
    expect(screen.getByText("user:ada@example.com")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "do-logout" }));
    expect(await screen.findByText("token:none")).toBeInTheDocument();
    expect(screen.getByText("status:anonymous")).toBeInTheDocument();
  });

  it("sends a recruiter away from candidate routes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/auth/refresh")) {
          return jsonResponse({
            access_token: "r-token",
            token_type: "bearer",
            expires_in: 900,
            csrf_token: "csrf",
            user: { id: "2", email: "rec@example.com", role: "recruiter", status: "active" },
          });
        }
        return jsonResponse({ title: "Not found", status: 404 }, 404);
      }),
    );

    render(
      <AuthProvider>
        <RoleGuard allow="candidate">
          <p>candidate-only</p>
        </RoleGuard>
      </AuthProvider>,
    );

    expect(await screen.findByText("Redirecting…")).toBeInTheDocument();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/forbidden"));
  });
});
