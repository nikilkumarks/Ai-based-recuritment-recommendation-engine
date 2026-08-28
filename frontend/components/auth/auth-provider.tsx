"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  loginAccount,
  logoutAllSessions,
  logoutSession,
  refreshSession,
  registerAccount,
} from "@/lib/api";
import type { AuthUser, UserRole } from "@/lib/auth";
import { clearSessionHint, setSessionHint } from "@/lib/session-hint";

type AuthStatus = "loading" | "anonymous" | "authenticated";

type RegisterInput = {
  email: string;
  password: string;
  role: "candidate" | "recruiter";
  organizationName?: string;
};

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (input: RegisterInput) => Promise<AuthUser>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refresh: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);

  const applySession = useCallback((nextUser: AuthUser, token: string, csrf: string) => {
    setUser(nextUser);
    setAccessToken(token);
    setCsrfToken(csrf);
    setStatus("authenticated");
    setSessionHint(nextUser.role);
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setCsrfToken(null);
    setStatus("anonymous");
    clearSessionHint();
  }, []);

  const refresh = useCallback(async () => {
    try {
      const tokens = await refreshSession(csrfToken);
      applySession(tokens.user, tokens.access_token, tokens.csrf_token);
      return true;
    } catch {
      clearSession();
      return false;
    }
  }, [applySession, clearSession, csrfToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const tokens = await refreshSession(null);
        if (cancelled) {
          return;
        }
        applySession(tokens.user, tokens.access_token, tokens.csrf_token);
      } catch {
        if (!cancelled) {
          clearSession();
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applySession, clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await loginAccount({ email, password });
      applySession(tokens.user, tokens.access_token, tokens.csrf_token);
      return tokens.user;
    },
    [applySession],
  );

  const register = useCallback(async (input: RegisterInput) => {
    return registerAccount({
      email: input.email,
      password: input.password,
      role: input.role,
      organization_name: input.organizationName,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutSession(csrfToken);
    } finally {
      clearSession();
    }
  }, [clearSession, csrfToken]);

  const logoutAll = useCallback(async () => {
    try {
      await logoutAllSessions(accessToken);
    } finally {
      clearSession();
    }
  }, [accessToken, clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      accessToken,
      login,
      register,
      logout,
      logoutAll,
      refresh,
    }),
    [accessToken, login, logout, logoutAll, refresh, register, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}

export function useRequiredRole(role: UserRole): {
  allowed: boolean;
  loading: boolean;
  user: AuthUser | null;
} {
  const { status, user } = useAuth();
  if (status === "loading") {
    return { allowed: false, loading: true, user };
  }
  return { allowed: status === "authenticated" && user?.role === role, loading: false, user };
}

export function describeAuthError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.problem.detail ?? error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}
