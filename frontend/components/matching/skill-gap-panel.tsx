import type { MatchResult } from "@/lib/api";
import { POTENTIAL_HINT } from "@/lib/baseline-match";
import { relationLabel } from "@/lib/evidence";

export function SkillGapPanel({ match }: { match: MatchResult }) {
  const gaps = match.missing_skills;
  if (gaps.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No remaining required skill gaps. Potential is not applicable.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--muted)]">{POTENTIAL_HINT}</p>
      <ul className="space-y-3">
        {gaps.map((gap) => {
          const adjacent = match.explanations.find(
            (item) => item.type === "potential_adjacent" && item.missing_skill === gap.skill,
          );
          const path = match.suggested_skill_paths.find((item) => item.target_skill_id === gap.skill_id);
          const related = gap.candidate_evidence || (typeof adjacent?.candidate_skill === "string"
            ? adjacent.candidate_skill
            : null);
          const relation =
            (typeof adjacent?.relation === "string" && adjacent.relation) || path?.relation || gap.evidence_type;
          return (
            <li key={gap.skill_id} className="border border-[var(--border)] px-3 py-3">
              <p className="text-sm font-semibold">{gap.skill}</p>
              <dl className="mt-2 grid gap-1 text-sm sm:grid-cols-[8rem_1fr]">
                <dt className="text-[var(--muted)]">Candidate has</dt>
                <dd>{related ?? "No related skill on the confirmed profile"}</dd>
                <dt className="text-[var(--muted)]">Relationship</dt>
                <dd>{relationLabel(relation)}</dd>
                {path ? (
                  <>
                    <dt className="text-[var(--muted)]">Suggested path</dt>
                    <dd>{path.steps.map((step) => step.skill).join(" → ")}</dd>
                    <dt className="text-[var(--muted)]">Distance</dt>
                    <dd>{path.distance} hop{path.distance === 1 ? "" : "s"}</dd>
                  </>
                ) : null}
              </dl>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
