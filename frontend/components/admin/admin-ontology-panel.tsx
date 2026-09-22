"use client";

import { useCallback, useEffect, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import {
  createOntologyAlias,
  createOntologyRelation,
  createOntologySkill,
  getOntologyValidation,
  listOntologySkills,
  listOntologyVersions,
  seedOntology,
  type OntologySkill,
} from "@/lib/api";
import { describeHttpError } from "@/lib/http-error";

export function AdminOntologyPanel() {
  const { accessToken } = useAuth();
  const [skills, setSkills] = useState<OntologySkill[]>([]);
  const [version, setVersion] = useState<string | null>(null);
  const [versions, setVersions] = useState<{ version: string; checksum: string; status: string }[]>([]);
  const [validation, setValidation] = useState<{ ok: boolean; errors: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newSkill, setNewSkill] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [aliasSkill, setAliasSkill] = useState("");
  const [aliasText, setAliasText] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [relation, setRelation] = useState<"parent_of" | "related_to" | "similar_to">("related_to");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    const [skillPayload, versionPayload, report] = await Promise.all([
      listOntologySkills(accessToken),
      listOntologyVersions(accessToken),
      getOntologyValidation(accessToken),
    ]);
    setSkills(skillPayload.items);
    setVersion(skillPayload.ontology_version);
    setVersions(versionPayload);
    setValidation(report);
  }, [accessToken]);

  useEffect(() => {
    void load()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [load]);

  async function seed() {
    if (!accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await seedOntology(accessToken);
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function addSkill() {
    if (!accessToken || !newSkill.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createOntologySkill(accessToken, {
        canonical_name: newSkill.trim(),
        category: newCategory.trim() || undefined,
      });
      setNewSkill("");
      setNewCategory("");
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function addAlias() {
    if (!accessToken || !aliasSkill || !aliasText) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createOntologyAlias(accessToken, { skill_id: aliasSkill, alias: aliasText });
      setAliasText("");
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function addRelation() {
    if (!accessToken || !sourceId || !targetId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createOntologyRelation(accessToken, {
        source_skill_id: sourceId,
        target_skill_id: targetId,
        relation,
      });
      await load();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div>
      <PageHeader
        title="Ontology"
        description="Canonical skills, aliases, and relations used for matching. Candidate screens never show internal identifiers."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className="text-sm text-[var(--muted)]">Active version {version ?? "none"}</span>
        {validation ? (
          <Badge tone={validation.ok ? "success" : "danger"}>{validation.ok ? "Valid" : "Has errors"}</Badge>
        ) : null}
        <Button type="button" size="sm" disabled={busy} onClick={() => void seed()}>
          Seed catalog
        </Button>
      </div>
      {validation && !validation.ok ? (
        <Alert className="mb-4" tone="warning">
          {validation.errors.join(" ")}
        </Alert>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Skills" />
          <CardBody>
            {skills.length === 0 ? (
              <EmptyState title="No skills in the active ontology." description="Seed the catalog to load the default skill graph." />
            ) : (
              <div className="max-h-[28rem] overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                      <th className="py-1 font-medium">Canonical name</th>
                      <th className="py-1 font-medium">Category</th>
                      <th className="py-1 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {skills.map((skill) => (
                      <tr key={skill.id} className="border-t border-[var(--border)]">
                        <td className="py-1.5">{skill.canonical_name}</td>
                        <td className="py-1.5 text-[var(--muted)]">{skill.category ?? "—"}</td>
                        <td className="py-1.5">{skill.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>
        <div className="space-y-4">
          <Card>
            <CardHeader title="Versions" />
            <CardBody>
              {versions.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No versions recorded.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {versions.map((item) => (
                    <li key={item.version}>
                      {item.version} · {item.status}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Add skill" />
            <CardBody className="space-y-2">
              <label className="block text-sm">
                Canonical name
                <input
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={newSkill}
                  onChange={(event) => setNewSkill(event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Category
                <input
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={newCategory}
                  onChange={(event) => setNewCategory(event.target.value)}
                />
              </label>
              <Button type="button" size="sm" disabled={busy} onClick={() => void addSkill()}>
                Add skill
              </Button>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Add alias" description="Example: ML → Machine Learning." />
            <CardBody className="space-y-2">
              <label className="block text-sm">
                Skill
                <select
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={aliasSkill}
                  onChange={(event) => setAliasSkill(event.target.value)}
                >
                  <option value="">Select skill</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.canonical_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Alias
                <input
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={aliasText}
                  onChange={(event) => setAliasText(event.target.value)}
                />
              </label>
              <Button type="button" size="sm" disabled={busy} onClick={() => void addAlias()}>
                Add alias
              </Button>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Add relation" description="Example: Docker related_to Kubernetes." />
            <CardBody className="space-y-2">
              <label className="block text-sm">
                Source
                <select className="mt-1 w-full px-3 py-2 text-sm" value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
                  <option value="">Select skill</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.canonical_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Target
                <select className="mt-1 w-full px-3 py-2 text-sm" value={targetId} onChange={(event) => setTargetId(event.target.value)}>
                  <option value="">Select skill</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.canonical_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Relation
                <select
                  className="mt-1 w-full px-3 py-2 text-sm"
                  value={relation}
                  onChange={(event) => setRelation(event.target.value as typeof relation)}
                >
                  <option value="related_to">Related to</option>
                  <option value="parent_of">Parent of</option>
                  <option value="similar_to">Similar to</option>
                </select>
              </label>
              <Button type="button" size="sm" disabled={busy} onClick={() => void addRelation()}>
                Add relation
              </Button>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
