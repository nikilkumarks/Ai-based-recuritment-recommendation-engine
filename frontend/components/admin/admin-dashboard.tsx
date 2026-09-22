"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import {
  listDatasetSnapshots,
  listMlModels,
  listOntologySkills,
  listOntologyVersions,
  type DatasetSnapshotSummary,
  type MlModelSummary,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function AdminDashboard() {
  const { accessToken } = useAuth();
  const [datasets, setDatasets] = useState<DatasetSnapshotSummary[]>([]);
  const [models, setModels] = useState<MlModelSummary[]>([]);
  const [ontologyVersion, setOntologyVersion] = useState<string | null>(null);
  const [skillCount, setSkillCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const [nextDatasets, nextModels, versions, skills] = await Promise.all([
      listDatasetSnapshots(accessToken),
      listMlModels(accessToken),
      listOntologyVersions(accessToken).catch(() => []),
      listOntologySkills(accessToken).catch(() => ({ ontology_version: null, items: [] })),
    ]);
    setDatasets(nextDatasets);
    setModels(nextModels);
    const active = versions.find((item) => item.status === "active");
    setOntologyVersion(active?.version ?? skills.ontology_version);
    setSkillCount(skills.items.length);
  }, [accessToken]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  if (loading) {
    return <PageSkeleton />;
  }

  const activeModel = models.find((item) => item.status === "active");

  return (
    <div>
      <PageHeader
        title="Admin"
        description="Ontology, datasets, and model registry. Training is offline and is never started from this page."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardBody>
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Ontology</p>
            <p className="mt-1 font-semibold">{ontologyVersion ?? "None active"}</p>
            <p className="text-sm text-[var(--muted)]">{skillCount ?? 0} skills</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Dataset snapshots</p>
            <p className="tabular mt-1 text-2xl font-semibold">{datasets.length}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Active model</p>
            <p className="mt-1 font-semibold">{activeModel?.version ?? "None"}</p>
            {!activeModel ? (
              <p className="mt-1 text-sm text-[var(--muted)]">
                No trained model is currently active. Recommendations use the deterministic baseline.
              </p>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
