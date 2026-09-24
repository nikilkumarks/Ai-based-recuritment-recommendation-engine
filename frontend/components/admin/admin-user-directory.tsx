"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { listAdminUsers, type AdminUserView } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { describeHttpError } from "@/lib/http-error";

export function AdminUserDirectory() {
  const { accessToken } = useAuth();
  const [users, setUsers] = useState<AdminUserView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!accessToken) return;
    const payload = await listAdminUsers(accessToken);
    setUsers(payload.items);
  }, [accessToken]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (loading) {
    return <PageSkeleton />;
  }

  const filtered = users.filter(
    (u) =>
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.role.toLowerCase().includes(search.toLowerCase()) ||
      (u.organization_name && u.organization_name.toLowerCase().includes(search.toLowerCase())),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="User & Organization Directory"
        description="System-wide accounts, organization memberships, and role assignments."
      />
      {error ? <Alert>{error}</Alert> : null}

      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Filter by email, role, or organization..."
          className="w-full max-w-md px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)]"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span className="text-xs text-[var(--muted)]">{filtered.length} users</span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No matching users found." description="Try adjusting your filter search term." />
      ) : (
        <Card>
          <CardBody className="p-0 overflow-x-auto">
            <table className="w-full min-w-[700px] border-collapse text-sm text-left">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--surface-subtle)] text-xs uppercase tracking-wider text-[var(--muted)]">
                  <th className="py-3 px-4 font-semibold">User Email</th>
                  <th className="py-3 px-4 font-semibold">System Role</th>
                  <th className="py-3 px-4 font-semibold">Organization</th>
                  <th className="py-3 px-4 font-semibold">Org Role</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Created Date</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.id} className="border-b border-[var(--border)] hover:bg-[var(--surface-subtle)]">
                    <td className="py-3 px-4 font-medium">{u.email}</td>
                    <td className="py-3 px-4">
                      <Badge
                        tone={
                          u.role === "admin"
                            ? "info"
                            : u.role === "recruiter"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {u.role.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-[var(--muted)]">
                      {u.organization_name ?? "—"}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-[var(--muted)]">
                      {u.membership_role ?? "—"}
                    </td>
                    <td className="py-3 px-4">
                      <Badge tone={u.status === "active" ? "success" : "warning"}>
                        {u.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-xs text-[var(--muted)] tabular">
                      {formatDate(u.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
