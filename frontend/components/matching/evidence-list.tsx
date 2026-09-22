"use client";

import { useState } from "react";
import type { MatchExplanation } from "@/lib/api";
import { evidenceLabel } from "@/lib/evidence";

function line(item: MatchExplanation): string {
  const skill =
    (typeof item.required_skill === "string" && item.required_skill) ||
    (typeof item.preferred_skill === "string" && item.preferred_skill) ||
    (typeof item.missing_skill === "string" && item.missing_skill) ||
    "";
  const from =
    (typeof item.candidate_skill === "string" && item.candidate_skill) ||
    (typeof item.candidate_skill_name === "string" && item.candidate_skill_name) ||
    (typeof item.candidate_evidence === "string" && item.candidate_evidence) ||
    "";
  if (skill && from) {
    return `${from} → ${skill}`;
  }
  if (skill) {
    return skill;
  }
  if (typeof item.cosine === "number") {
    return `Similarity ${item.cosine.toFixed(2)}`;
  }
  if (typeof item.note === "string") {
    return item.note;
  }
  return "";
}

export function EvidenceList({ explanations }: { explanations: MatchExplanation[] }) {
  const items = explanations.filter((item) => item.kind !== "ml_model" && item.type !== "ml_fallback");
  const [open, setOpen] = useState<number | null>(null);
  if (items.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No evidence traces are available for this comparison.</p>;
  }
  return (
    <ul className="divide-y divide-[var(--border)]">
      {items.map((item, index) => {
        const extra = Object.entries(item).filter(
          ([key, value]) =>
            !["type", "kind", "title", "note", "canonical_skill_id", "candidate_skill_id", "ontology_version"].includes(
              key,
            ) &&
            value != null &&
            typeof value !== "object",
        );
        return (
          <li key={`${item.type}-${index}`} className="py-2">
            <button
              type="button"
              className="flex w-full items-start justify-between gap-3 text-left"
              onClick={() => setOpen(open === index ? null : index)}
              aria-expanded={open === index}
            >
              <span>
                <span className="text-sm font-medium">{evidenceLabel(item.type)}</span>
                {line(item) ? <span className="mt-0.5 block text-sm text-[var(--muted)]">{line(item)}</span> : null}
              </span>
              <span className="text-xs text-[var(--muted)]">{open === index ? "Hide" : "Details"}</span>
            </button>
            {open === index && extra.length > 0 ? (
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
                {extra.map(([key, value]) => (
                  <span key={key} className="contents">
                    <dt className="capitalize">{key.replaceAll("_", " ")}</dt>
                    <dd>{String(value)}</dd>
                  </span>
                ))}
              </dl>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
