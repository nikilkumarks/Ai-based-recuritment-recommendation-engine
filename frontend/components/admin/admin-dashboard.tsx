"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { AdminDashboardSkeleton } from "@/components/ui/skeleton";
import {
  listDatasetSnapshots,
  listMlModels,
  listOntologySkills,
  listOntologyVersions,
  type DatasetSnapshotSummary,
  type MlModelSummary,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";
import { GitBranch, Database, Layers, ShieldCheck } from "lucide-react";

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
    return <AdminDashboardSkeleton />;
  }


  const activeModel = models.find((item) => item.status === "active");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200/80 pb-5">
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Admin Console</h1>
        <p className="text-xs text-slate-500 mt-1 font-medium">
          Ontology version control, dataset snapshots, and ML model registry.
        </p>
      </div>

      {error ? <Alert className="mb-4">{error}</Alert> : null}

      <div className="grid gap-4 sm:grid-cols-3">
        {/* Ontology Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Ontology Version</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <GitBranch className="h-4 w-4" />
            </div>
          </div>
          <p className="text-xl font-extrabold text-slate-900">{ontologyVersion ?? "None active"}</p>
          <p className="text-xs text-slate-500 font-medium pt-1 border-t border-slate-100">
            {skillCount ?? 0} canonical skills mapped
          </p>
        </div>

        {/* Datasets Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Dataset Snapshots</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <Database className="h-4 w-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900 font-mono">{datasets.length}</p>
          <p className="text-xs text-slate-500 font-medium pt-1 border-t border-slate-100">
            Recorded evaluation datasets
          </p>
        </div>

        {/* Active Model Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Active ML Model</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <Layers className="h-4 w-4" />
            </div>
          </div>
          <p className="text-xl font-extrabold text-slate-900">{activeModel?.version ?? "Baseline Engine"}</p>
          <p className="text-xs text-slate-500 leading-relaxed pt-1 border-t border-slate-100">
            {!activeModel
              ? "No trained model active. Recommendations use baseline deterministic matching."
              : `Active model version ${activeModel.version}`}
          </p>
        </div>
      </div>

      {/* System Note */}
      <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-5 space-y-2">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
          <ShieldCheck className="h-4 w-4 text-teal-700" />
          <span>System Governance & Determinism</span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed font-normal">
          Model training and ontology creation occur offline or via controlled scripts. All candidate scoring maintains explicit auditability and baseline fallback compatibility.
        </p>
      </div>
    </div>
  );
}

