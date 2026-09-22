import type { SuggestedSkillPath } from "@/lib/api";
import { SUGGESTED_SKILL_PATH_LABEL } from "@/lib/baseline-match";

export function SkillPathList({
  items,
  disclaimer,
}: {
  items: SuggestedSkillPath[];
  disclaimer?: string;
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--muted)]">
        {disclaimer || `${SUGGESTED_SKILL_PATH_LABEL} uses the skill ontology. It is not a guaranteed career path.`}
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No bounded ontology path is available yet.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((path) => (
            <li key={path.target_skill_id} className="border border-[var(--border)] px-3 py-2 text-sm">
              <p className="font-medium">{path.target_skill}</p>
              <p className="mt-1 text-[var(--muted)]">
                {(path.steps ?? []).map((step) => step?.skill).filter(Boolean).join(" → ")}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
