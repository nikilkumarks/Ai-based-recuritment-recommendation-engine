"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { describeAuthError, useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSkeleton } from "@/components/ui/skeleton";
import { ConfirmationBadge } from "@/components/ui/status-badge";
import {
  addCandidateSkill,
  confirmProfile,
  createProfileEmbedding,
  getProfile,
  getProfileEmbedding,
  removeCandidateSkill,
  searchOntologySkills,
  updateProfile,
  type EmbeddingStatus,
  type OntologySkill,
  type ProfileView,
  type SkillNormalizationResult,
} from "@/lib/api";
import { embeddingStatusLabel } from "@/lib/embedding-status";
import { describeHttpError } from "@/lib/http-error";

function resolutionNote(item: SkillNormalizationResult): string {
  if (item.resolution_type === "alias" && item.canonical_skill_name) {
    return `${item.raw_text} → ${item.canonical_skill_name} (alias)`;
  }
  if (item.canonical_skill_name) {
    return item.canonical_skill_name;
  }
  return `${item.raw_text} — needs review`;
}

export function ProfileManager() {
  const { user, accessToken } = useAuth();
  const candidateId = user?.candidate_id ?? null;
  const [confirmed, setConfirmed] = useState<ProfileView | null>(null);
  const [draft, setDraft] = useState<ProfileView | null>(null);
  const [embedding, setEmbedding] = useState<EmbeddingStatus | null>(null);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  // Skill management state
  const [skillQuery, setSkillQuery] = useState("");
  const [searchResults, setSearchResults] = useState<OntologySkill[]>([]);
  const [searching, setSearching] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const refresh = useCallback(async () => {
    if (!candidateId || !accessToken) {
      return;
    }
    const payload = await getProfile(candidateId, accessToken);
    setConfirmed(payload.confirmed);
    setDraft(payload.draft);
    setSummary(payload.draft?.summary || payload.draft?.draft?.summary || payload.confirmed?.summary || "");
    if (payload.confirmed) {
      try {
        setEmbedding(await getProfileEmbedding(candidateId, accessToken));
      } catch {
        setEmbedding(null);
      }
    } else {
      setEmbedding(null);
    }
  }, [accessToken, candidateId]);

  useEffect(() => {
    void refresh()
      .catch((err) => setError(describeHttpError(err, describeAuthError(err))))
      .finally(() => setLoading(false));
  }, [refresh]);

  const handleSearchSkills = async (q: string) => {
    setSkillQuery(q);
    if (!q.trim() || !accessToken) {
      setSearchResults([]);
      setDropdownOpen(false);
      return;
    }
    setSearching(true);
    setDropdownOpen(true);
    try {
      const res = await searchOntologySkills(q, accessToken);
      setSearchResults(Array.isArray(res) ? res : (res as { items?: OntologySkill[] })?.items ?? []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleAddSkill = async (skillName: string) => {
    if (!candidateId || !accessToken) return;
    setBusy(true);
    setError(null);
    try {
      await addCandidateSkill(candidateId, skillName, accessToken);
      setSkillQuery("");
      setSearchResults([]);
      setDropdownOpen(false);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveSkill = async (skillName: string) => {
    if (!candidateId || !accessToken) return;
    setBusy(true);
    setError(null);
    try {
      await removeCandidateSkill(candidateId, skillName, accessToken);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  };

  async function save() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateProfile(candidateId, accessToken, { summary });
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await confirmProfile(candidateId, accessToken);
      await refresh();
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  async function embed() {
    if (!candidateId || !accessToken) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setEmbedding(await createProfileEmbedding(candidateId, accessToken));
    } catch (err) {
      setError(describeHttpError(err, describeAuthError(err)));
    } finally {
      setBusy(false);
    }
  }

  if (!candidateId) {
    return <p className="text-sm text-[var(--muted)]">No candidate profile is attached.</p>;
  }
  if (loading) {
    return <PageSkeleton />;
  }

  const view = draft ?? confirmed;
  const extraction = view?.draft;
  const rawSkills = view?.normalized_skills ?? [];

  // Deduplicate skills by canonical_skill_id, canonical_skill_name, or raw_text
  const skills: SkillNormalizationResult[] = [];
  const seenSkillKeys = new Set<string>();
  for (const item of rawSkills) {
    const key = (
      item.canonical_skill_id ||
      item.canonical_skill_name ||
      item.raw_text
    ).toLowerCase().trim();
    if (!seenSkillKeys.has(key)) {
      seenSkillKeys.add(key);
      skills.push(item);
    }
  }

  // Deduplicate search results by canonical_name / id
  const uniqueSearchResults: OntologySkill[] = [];
  const seenSearchKeys = new Set<string>();
  for (const item of searchResults) {
    const key = (item.id || item.canonical_name).toLowerCase().trim();
    if (!seenSearchKeys.has(key)) {
      seenSearchKeys.add(key);
      uniqueSearchResults.push(item);
    }
  }

  return (
    <div>
      <PageHeader
        title="Profile"
        description="Confirmed information is used for matching. Extracted fields stay in review until you confirm."
      />
      {error ? <Alert className="mb-4">{error}</Alert> : null}
      {!view ? (
        <EmptyState
          title="No resume uploaded yet."
          description="Upload a PDF or DOCX to extract skills, experience, and education."
        />
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader
              title="Profile summary"
              action={<ConfirmationBadge status={view.confirmation_status} />}
            />
            <CardBody className="space-y-3">
              {confirmed ? (
                <p className="text-sm text-[var(--muted)]">
                  Confirmed version {confirmed.profile_version} is used for matching. Re-parse cannot overwrite it.
                </p>
              ) : (
                <p className="text-sm text-[var(--muted)]">Extracted draft — review before confirming.</p>
              )}
              <label className="block text-sm">
                Summary
                <textarea
                  className="mt-1 w-full px-3 py-2 text-sm rounded border border-[var(--border)] bg-[var(--surface)]"
                  rows={4}
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button type="button" disabled={busy || !draft} onClick={() => void save()}>
                  Save summary
                </Button>
                <Button type="button" variant="outline" disabled={busy || !draft} onClick={() => void confirm()}>
                  Confirm profile
                </Button>
                {confirmed ? (
                  <Button type="button" variant="outline" disabled={busy} onClick={() => void embed()}>
                    Generate embedding ({embeddingStatusLabel(embedding)})
                  </Button>
                ) : null}
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardHeader
              title="Skills Management"
              description="Canonical skills from the ontology system. Add or remove verified skills."
            />
            <CardBody className="space-y-4">
              <div ref={searchContainerRef} className="relative z-20">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Search canonical ontology skills (e.g. HTML, Python, Docker)..."
                    className="flex-1 px-3 py-2 text-sm rounded border border-[var(--border)] bg-[var(--surface)] focus:outline-none focus:ring-1 focus:ring-[var(--border)]"
                    value={skillQuery}
                    onFocus={() => {
                      if (skillQuery.trim() && searchResults.length > 0) setDropdownOpen(true);
                    }}
                    onChange={(e) => void handleSearchSkills(e.target.value)}
                  />
                  {skillQuery.trim() ? (
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      disabled={busy}
                      onClick={() => void handleAddSkill(skillQuery.trim())}
                    >
                      Add &quot;{skillQuery}&quot;
                    </Button>
                  ) : null}
                </div>
                {dropdownOpen && skillQuery.trim() ? (
                  <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-56 overflow-auto rounded-md border border-[var(--border)] bg-[var(--surface)] p-1 shadow-xl">
                    {searching ? (
                      <p className="px-3 py-2 text-xs text-[var(--muted)]">Searching ontology...</p>
                    ) : uniqueSearchResults.length > 0 ? (
                      <ul className="divide-y divide-[var(--border)]">
                        {uniqueSearchResults.map((item, index) => {
                          const isAlreadyAdded = skills.some(
                            (s) =>
                              (s.canonical_skill_name || s.raw_text).toLowerCase().trim() ===
                              item.canonical_name.toLowerCase().trim(),
                          );
                          return (
                            <li key={item.id || `search-${item.canonical_name}-${index}`}>
                              <button
                                type="button"
                                disabled={busy || isAlreadyAdded}
                                className="w-full px-3 py-2 text-left text-sm hover:bg-[var(--accent-subtle)] flex items-center justify-between transition-colors disabled:opacity-50"
                                onClick={() => void handleAddSkill(item.canonical_name)}
                              >
                                <div>
                                  <span className="font-medium text-[var(--foreground)]">{item.canonical_name}</span>
                                  <span className="ml-2 text-xs text-[var(--muted)]">
                                    {item.category ?? "Canonical Skill"}
                                  </span>
                                </div>
                                {isAlreadyAdded ? (
                                  <span className="text-xs text-[var(--muted)] italic">Added</span>
                                ) : (
                                  <span className="text-xs font-semibold text-blue-500 hover:underline">+ Add</span>
                                )}
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="px-3 py-2 text-xs text-[var(--muted)]">
                        No canonical match for &quot;{skillQuery}&quot;. Click Add to save as unmapped skill.
                      </p>
                    )}
                  </div>
                ) : null}
              </div>

              {skills.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No skills added yet.</p>
              ) : (
                <ul className="flex flex-wrap gap-2">
                  {skills.map((item, index) => {
                    const skillName = item.canonical_skill_name || item.raw_text;
                    const reactKey = item.canonical_skill_id
                      ? `skill-id-${item.canonical_skill_id}`
                      : `skill-name-${(skillName || "skill").toLowerCase().replace(/[^\w]/g, "_")}-${index}`;
                    return (
                      <li key={reactKey}>
                        <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] px-2.5 py-1 text-sm bg-[var(--surface)]">
                          <span>{resolutionNote(item)}</span>
                          {item.needs_review ? (
                            <Badge tone="warning">Review</Badge>
                          ) : (
                            <Badge tone="success">Mapped</Badge>
                          )}
                          <button
                            type="button"
                            className="ml-1 text-[var(--muted)] hover:text-red-500 font-bold text-xs"
                            title="Remove skill"
                            disabled={busy}
                            onClick={() => void handleRemoveSkill(skillName)}
                          >
                            ×
                          </button>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardBody>
          </Card>
          <ExperienceSection items={extraction?.experience ?? []} />
          <EducationSection items={extraction?.education ?? []} />
          <ProjectsSection items={extraction?.projects ?? []} />
          <CertificationsSection items={extraction?.certifications ?? []} />
        </div>
      )}
    </div>
  );
}

function ExperienceSection({ items }: { items: NonNullable<ProfileView["draft"]>["experience"] }) {
  return (
    <Card>
      <CardHeader title="Experience" />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">None extracted.</p>
        ) : (
          <div className="space-y-4">
            {items.map((item, index) => {
              const dates = [item.start_date, item.is_current ? "Present" : item.end_date].filter(Boolean).join(" – ");
              return (
                <div key={`exp-${index}`} className="border-b border-[var(--border)] pb-3 last:border-b-0 last:pb-0">
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="font-semibold text-sm">
                      {[item.job_title, item.employer].filter(Boolean).join(" · ") || "Untitled role"}
                    </span>
                    {dates ? <span className="text-xs text-[var(--muted)]">{dates}</span> : null}
                  </div>
                  {item.description ? (
                    <p className="mt-1 text-xs text-[var(--muted)] whitespace-pre-line">{item.description}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function EducationSection({ items }: { items: NonNullable<ProfileView["draft"]>["education"] }) {
  return (
    <Card>
      <CardHeader title="Education" />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">None extracted.</p>
        ) : (
          <div className="space-y-4">
            {items.map((item, index) => {
              const dates = [item.start_date, item.end_date].filter(Boolean).join(" – ");
              const cgpaEvidence = item.evidence?.find((e) => e.evidence?.includes("CGPA") || e.evidence?.includes("GPA"))?.evidence;
              return (
                <div key={`edu-${index}`} className="border-b border-[var(--border)] pb-3 last:border-b-0 last:pb-0">
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="font-semibold text-sm">
                      {[item.degree, item.institution].filter(Boolean).join(" · ") || "Education"}
                    </span>
                    {dates ? <span className="text-xs text-[var(--muted)]">{dates}</span> : null}
                  </div>
                  {item.field_of_study ? (
                    <p className="mt-0.5 text-xs font-medium text-[var(--foreground)]">Field: {item.field_of_study}</p>
                  ) : null}
                  {cgpaEvidence ? (
                    <p className="mt-0.5 text-xs text-[var(--muted)]">{cgpaEvidence}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function ProjectsSection({ items }: { items: NonNullable<ProfileView["draft"]>["projects"] }) {
  return (
    <Card>
      <CardHeader title="Projects" />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">None extracted.</p>
        ) : (
          <div className="space-y-4">
            {items.map((item, index) => (
              <div key={`proj-${index}`} className="border-b border-[var(--border)] pb-3 last:border-b-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <span className="font-semibold text-sm">{item.name || "Untitled project"}</span>
                  {item.url ? (
                    <a href={item.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 underline">
                      {item.url}
                    </a>
                  ) : null}
                </div>
                {item.technologies && item.technologies.length > 0 ? (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <span className="text-xs text-[var(--muted)] font-medium self-center mr-1">Technologies:</span>
                    {item.technologies.map((t, idx) => (
                      <Badge key={`tech-${idx}`} tone="neutral" className="text-xs py-0.5 px-1.5">
                        {t.raw_text}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {item.description ? (
                  <p className="mt-1 text-xs text-[var(--muted)] whitespace-pre-line">{item.description}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function CertificationsSection({ items }: { items: NonNullable<ProfileView["draft"]>["certifications"] }) {
  return (
    <Card>
      <CardHeader title="Certifications" />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">None extracted.</p>
        ) : (
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={`cert-${index}`} className="text-sm">
                <span className="font-medium">{item.name || "Certification"}</span>
                {item.issuing_organization ? (
                  <span className="text-xs text-[var(--muted)]"> — {item.issuing_organization}</span>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
