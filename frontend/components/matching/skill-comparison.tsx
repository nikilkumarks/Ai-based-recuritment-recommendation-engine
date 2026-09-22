import { Badge } from "@/components/ui/badge";
import type { MatchResult, SkillMatchItem } from "@/lib/api";

function Row({
  item,
  mark,
  tone,
  detail,
}: {
  item: SkillMatchItem;
  mark: string;
  tone: "success" | "warning" | "danger" | "info";
  detail: string;
}) {
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--border)] py-2 last:border-0">
      <div>
        <p className="text-sm font-medium">
          <span className="mr-2 text-[var(--muted)]" aria-hidden="true">
            {mark}
          </span>
          {item.skill}
        </p>
        <p className="pl-5 text-xs text-[var(--muted)]">{detail}</p>
      </div>
      <Badge tone={tone}>{item.evidence_type.replaceAll("_", " ")}</Badge>
    </li>
  );
}

export function SkillComparison({ match }: { match: MatchResult }) {
  const exact = match.matched_skills;
  const related = [...match.related_skills, ...match.partial_skills];
  const missing = match.missing_skills;
  if (exact.length + related.length + missing.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No required skills were available for comparison.</p>;
  }
  return (
    <ul>
      {exact.map((item) => (
        <Row
          key={`exact-${item.skill_id}`}
          item={item}
          mark="✓"
          tone="success"
          detail={item.candidate_evidence ? `Exact match via ${item.candidate_evidence}` : "Exact"}
        />
      ))}
      {related.map((item) => (
        <Row
          key={`rel-${item.skill_id}`}
          item={item}
          mark="○"
          tone="info"
          detail={
            item.candidate_evidence
              ? `Related through ${item.candidate_evidence}`
              : "Related or hierarchical evidence"
          }
        />
      ))}
      {missing.map((item) => {
        const path = match.suggested_skill_paths.find((entry) => entry.target_skill_id === item.skill_id);
        return (
          <Row
            key={`miss-${item.skill_id}`}
            item={item}
            mark="△"
            tone="danger"
            detail={path ? `Potential path: ${path.steps.map((step) => step.skill).join(" → ")}` : "Missing"}
          />
        );
      })}
    </ul>
  );
}
