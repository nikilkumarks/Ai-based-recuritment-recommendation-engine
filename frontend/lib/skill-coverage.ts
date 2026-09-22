import type { SkillMatchItem } from "@/lib/api";

type SkillLists = {
  matched_skills?: SkillMatchItem[];
  missing_skills?: SkillMatchItem[];
  partial_skills?: SkillMatchItem[];
  related_skills?: SkillMatchItem[];
};

function uniqueNames(items: SkillMatchItem[] | undefined): string[] {
  const seen = new Set<string>();
  const names: string[] = [];
  for (const item of items ?? []) {
    const name = item.skill?.trim();
    if (!name || seen.has(name.toLowerCase())) {
      continue;
    }
    seen.add(name.toLowerCase());
    names.push(name);
  }
  return names;
}

export function requiredSkillCounts(match: SkillLists) {
  const matched = uniqueNames(match.matched_skills);
  const missing = uniqueNames(match.missing_skills);
  const partial = uniqueNames(match.partial_skills);
  const related = uniqueNames(match.related_skills);
  const required = new Set(
    [...matched, ...missing, ...partial, ...related].map((n) => n.toLowerCase()),
  );
  const covered = matched.length + related.length + partial.length;
  return {
    covered,
    required: required.size,
    missingNames: missing,
    relatedNames: related,
  };
}

export function coverageFractionLabel(match: SkillLists): string | null {
  if (!match.matched_skills) {
    return null;
  }
  const { covered, required } = requiredSkillCounts(match);
  if (required === 0) {
    return null;
  }
  return `${Math.min(covered, required)} / ${required}`;
}
