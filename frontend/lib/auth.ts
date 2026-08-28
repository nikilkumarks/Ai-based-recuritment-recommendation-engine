export type UserRole = "candidate" | "recruiter" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  role: UserRole;
  status: string;
  candidate_id?: string | null;
  organization_id?: string | null;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  csrf_token: string;
  user: AuthUser;
};

export type ProblemDetails = {
  type?: string;
  title?: string;
  status: number;
  detail?: string;
  code?: string;
  errors?: { field: string; message: string }[];
};

export function dashboardPath(role: UserRole): string {
  if (role === "recruiter") {
    return "/recruiter";
  }
  if (role === "admin") {
    return "/admin";
  }
  return "/candidate";
}

export function isUserRole(value: string): value is UserRole {
  return value === "candidate" || value === "recruiter" || value === "admin";
}
