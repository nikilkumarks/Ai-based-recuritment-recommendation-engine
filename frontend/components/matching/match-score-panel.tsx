import { ScoreBar } from "@/components/ui/score-bar";
import type { MatchResult } from "@/lib/api";
import {
  CURRENT_MATCH_HINT,
  CURRENT_MATCH_LABEL,
  MODEL_RELEVANCE_LABEL,
  POTENTIAL_HINT,
  POTENTIAL_LABEL,
  formatMatchPercent,
  formatPotential,
} from "@/lib/baseline-match";
import { componentLabel } from "@/lib/evidence";

export function MatchScorePanel({ match }: { match: MatchResult }) {
  const trained = match.scoring_mode === "trained" && Boolean(match.model_version);
  const potentialAvailable = match.potential_status === "available" && match.potential != null;
  const components = match.components ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {CURRENT_MATCH_LABEL}
          </p>
          <p className="tabular mt-1 text-3xl font-semibold leading-none">
            {formatMatchPercent(match.current_match)}
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">{CURRENT_MATCH_HINT}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {POTENTIAL_LABEL}
          </p>
          <p className="tabular mt-1 text-3xl font-semibold leading-none">
            {formatPotential(match.potential, match.potential_status)}
          </p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {potentialAvailable
              ? POTENTIAL_HINT
              : "Potential is not applicable when there is no remaining required skill gap."}
          </p>
        </div>
        {trained ? (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              {MODEL_RELEVANCE_LABEL}
            </p>
            <p className="tabular mt-1 text-3xl font-semibold leading-none">
              {formatMatchPercent(match.model_relevance_score)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Model relevance is influenced by skill coverage, semantic similarity, and experience
              alignment. It is not a hiring probability.
            </p>
          </div>
        ) : null}
      </div>
      <div className="space-y-3">
        <p className="text-sm font-medium">Current Match components</p>
        {components.length === 0 ? (
          <div className="space-y-3">
            <ScoreBar value={match.required_skill_coverage} label="Skill Coverage" />
            <ScoreBar
              value={match.semantic_similarity_available ? match.semantic_similarity : null}
              label="Semantic Similarity"
            />
            <ScoreBar value={match.preferred_skill_coverage} label="Preferred Coverage" tone="info" />
          </div>
        ) : (
          components.map((item) => (
            <ScoreBar
              key={item.name}
              value={item.available ? item.value : null}
              label={componentLabel(item.name)}
              tone={item.name === "required" ? "accent" : "neutral"}
            />
          ))
        )}
      </div>
    </div>
  );
}
