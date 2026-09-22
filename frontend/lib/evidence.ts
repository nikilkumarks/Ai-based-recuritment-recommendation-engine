const LABELS: Record<string, string> = {
  alias_match: "Alias Match",
  exact_match: "Exact Match",
  hierarchy_child: "Hierarchy Evidence",
  hierarchy_parent: "Hierarchy Evidence",
  related_skill: "Related Skill",
  missing_skill: "Gap",
  preferred_skill: "Preferred Skill",
  semantic_similarity: "Semantic Evidence",
  experience_match: "Experience Evidence",
  experience_gap: "Experience Gap",
  experience_unknown: "Experience Unknown",
  education_match: "Education Evidence",
  project_evidence: "Project Evidence",
  potential_adjacent: "Potential Adjacent Skill",
  potential_gap: "Gap",
  potential_graph_path: "Potential Path",
  potential_semantic: "Semantic Evidence",
  potential_project: "Project Evidence",
  potential_certification: "Certification Evidence",
  ml_fallback: "Baseline Fallback",
};

const COMPONENT_LABELS: Record<string, string> = {
  required: "Skill Coverage",
  preferred: "Preferred Coverage",
  semantic: "Semantic Similarity",
  experience: "Experience",
  education_project: "Education & Projects",
};

export function evidenceLabel(type: string | undefined): string {
  if (!type) {
    return "Evidence";
  }
  return LABELS[type] ?? type.replaceAll("_", " ");
}

export function componentLabel(name: string): string {
  return COMPONENT_LABELS[name] ?? name.replaceAll("_", " ");
}

export function relationLabel(value: string | null | undefined): string {
  if (!value) {
    return "Related";
  }
  return value.replaceAll("_", " ");
}
