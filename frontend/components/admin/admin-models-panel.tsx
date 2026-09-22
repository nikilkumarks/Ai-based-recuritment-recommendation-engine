"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import {
  activateMlModel,
  listMlModels,
  rejectMlModel,
  type MlModelSummary,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";
import { formatDateTime } from "@/lib/format";

function metricLine(evaluation: Record<string, unknown> | null, method: string, name: string): string {
  const block = evaluation?.[method];
  if (!block || typeof block !== "object") {
    return "unavailable";
  }
  const metric = (block as Record<string, { value?: number | null; reason?: string | null }>)[name];
  if (!metric || metric.value === null || metric.value === undefined) {
    return metric?.reason === "insufficient_data" ? "unavailable (insufficient data)" : "unavailable";
  }
  return metric.value.toFixed(3);
}

export function AdminModelsPanel() {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<MlModelSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setItems(await listMlModels(accessToken));
  }, [accessToken]);

  useEffect(() => {
    void load().catch((err) => setError(describeHttpError(err, describeAuthError(err))));
  }, [load]);

  async function activate(id: string) {
    if (!accessToken) {
      return;
    }
    await activateMlModel(id, accessToken);
    await load();
  }

  async function reject(id: string) {
    if (!accessToken) {
      return;
    }
    await rejectMlModel(id, accessToken);
    await load();
  }

  return (
    <div>
      <PageHeader
        title="Models"
        description="Training is offline (python -m ml.train). Activation is never automatic. Recruiter decisions are behavioral labels, not hiring outcomes."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      {items.length === 0 ? (
        <EmptyState
          title="No candidate models yet."
          description="No trained project model is produced until sufficient real labeled data exists."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => {
            const eligible = Boolean((item.activation as { eligible?: boolean }).eligible);
            const canActivate = item.status === "candidate" && eligible;
            const canReject = item.status === "candidate" || item.status === "retired";
            return (
              <li key={item.id}>
                <Card>
                  <CardBody className="space-y-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold">{item.version}</p>
                      <Badge>{item.status}</Badge>
                      {item.test_fixture_only ? <Badge tone="danger">Test fixture only</Badge> : null}
                    </div>
                    <p>
                      Algorithm {item.algorithm} · Dataset {item.dataset_snapshot_id ?? "n/a"} · Schema{" "}
                      {item.feature_schema_version}
                    </p>
                    <p className="text-[var(--muted)]">Created {formatDateTime(item.created_at)}</p>
                    <p>
                      NDCG@5 {metricLine(item.evaluation, "xgboost", "ndcg_at_5")} / baseline{" "}
                      {metricLine(item.evaluation, "baseline", "ndcg_at_5")}
                    </p>
                    <p>
                      ROC-AUC {metricLine(item.evaluation, "xgboost", "roc_auc")} / baseline{" "}
                      {metricLine(item.evaluation, "baseline", "roc_auc")}
                    </p>
                    {item.test_fixture_only ? (
                      <Alert tone="warning">{item.warning ?? "TEST FIXTURE ONLY. Not project performance."}</Alert>
                    ) : null}
                    <p className="text-[var(--muted)]">{item.target_note}</p>
                    <div className="flex gap-2">
                      {canActivate ? (
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => void activate(item.id).catch((err) => setError(describeHttpError(err)))}
                        >
                          Activate
                        </Button>
                      ) : null}
                      {canReject ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => void reject(item.id).catch((err) => setError(describeHttpError(err)))}
                        >
                          Reject
                        </Button>
                      ) : null}
                    </div>
                  </CardBody>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
