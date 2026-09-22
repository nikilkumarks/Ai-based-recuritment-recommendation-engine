"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { createDatasetSnapshot, listDatasetSnapshots, type DatasetSnapshotSummary } from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function AdminDatasetsPanel() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<DatasetSnapshotSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setItems(await listDatasetSnapshots(accessToken));
  }, [accessToken]);

  useEffect(() => {
    void load().catch((err) => setError(describeHttpError(err, describeAuthError(err))));
  }, [load]);

  async function createSnapshot() {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    try {
      await createDatasetSnapshot(accessToken);
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Point-in-time training rows. Creating a snapshot does not train a model."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <Button type="button" className="mb-4" disabled={busy} onClick={() => void createSnapshot()}>
        {busy ? "Creating…" : "Create snapshot"}
      </Button>
      {items.length === 0 ? (
        <EmptyState title="No dataset snapshots yet." description="Create a snapshot after recruiter decisions exist." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">Snapshot</th>
                <th className="py-2 pr-3 font-medium">Eligible</th>
                <th className="py-2 pr-3 font-medium">Positive</th>
                <th className="py-2 pr-3 font-medium">Negative</th>
                <th className="py-2 pr-3 font-medium">Excluded</th>
                <th className="py-2 pr-3 font-medium">Schema</th>
                <th className="py-2 font-medium">Ontology</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[var(--border)]">
                  <td className="py-3 pr-3 font-medium">{item.name}</td>
                  <td className="tabular py-3 pr-3">{item.row_count ?? 0}</td>
                  <td className="tabular py-3 pr-3">{item.positive_count}</td>
                  <td className="tabular py-3 pr-3">{item.negative_count}</td>
                  <td className="tabular py-3 pr-3">{item.excluded_count}</td>
                  <td className="py-3 pr-3 text-[var(--muted)]">
                    {item.feature_schema_versions.join(", ") || "none"}
                  </td>
                  <td className="py-3 text-[var(--muted)]">{item.ontology_versions.join(", ") || "none"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
