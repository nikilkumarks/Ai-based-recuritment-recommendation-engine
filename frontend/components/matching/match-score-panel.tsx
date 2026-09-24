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
import { Sparkles, TrendingUp, Cpu } from "lucide-react";

export function MatchScorePanel({ match }: { match: MatchResult }) {
  const trained = match.scoring_mode === "trained" && Boolean(match.model_version);
  const potentialAvailable = match.potential_status === "available" && match.potential != null;
  const components = match.components ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-12 items-start">
      {/* Metrics Column */}
      <div className="lg:col-span-6 space-y-4">
        {/* Current Match Card */}
        <div className="rounded-2xl border border-teal-200/80 bg-teal-50/40 p-5 space-y-2 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-900 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-teal-700" />
              {CURRENT_MATCH_LABEL}
            </span>
            <span className="text-[10px] font-bold text-teal-800 bg-teal-100 px-2 py-0.5 rounded-full">
              Baseline Engine
            </span>
          </div>
          <p className="text-3xl font-extrabold text-teal-950 font-mono tracking-tight">
            {formatMatchPercent(match.current_match)}
          </p>
          <p className="text-xs text-slate-600 leading-relaxed font-medium pt-1 border-t border-teal-200/60">
            {CURRENT_MATCH_HINT}
          </p>
        </div>

        {/* Potential Card */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 space-y-2 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <TrendingUp className="h-4 w-4 text-teal-600" />
              {POTENTIAL_LABEL}
            </span>
            <span className="text-[10px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
              {match.potential_status ?? "Status"}
            </span>
          </div>
          <p className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {formatPotential(match.potential, match.potential_status)}
          </p>
          <p className="text-xs text-slate-500 leading-relaxed pt-1 border-t border-slate-100">
            {potentialAvailable
              ? POTENTIAL_HINT
              : "Potential is not applicable when there is no remaining required skill gap."}
          </p>
        </div>

        {/* Trained Model Relevance */}
        {trained ? (
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 space-y-2 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Cpu className="h-4 w-4 text-sky-600" />
                {MODEL_RELEVANCE_LABEL}
              </span>
              <span className="text-[10px] font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded-full border border-sky-200">
                v{match.model_version}
              </span>
            </div>
            <p className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {formatMatchPercent(match.model_relevance_score)}
            </p>
            <p className="text-xs text-slate-500 leading-relaxed pt-1 border-t border-slate-100">
              Model relevance is influenced by skill coverage, semantic similarity, and experience alignment.
            </p>
          </div>
        ) : null}
      </div>

      {/* Components Decomposition Column */}
      <div className="lg:col-span-6 rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900">Current Match Breakdown</h3>
          <p className="text-xs text-slate-500">Decomposition of evidence factors contributing to match score.</p>
        </div>

        {components.length === 0 ? (
          <div className="space-y-4">
            <ScoreBar value={match.required_skill_coverage} label="Skill Coverage" tone="accent" />
            <ScoreBar
              value={match.semantic_similarity_available ? match.semantic_similarity : null}
              label="Semantic Similarity"
              tone="info"
            />
            <ScoreBar value={match.preferred_skill_coverage} label="Preferred Coverage" tone="neutral" />
          </div>
        ) : (
          <div className="space-y-4">
            {components.map((item) => (
              <ScoreBar
                key={item.name}
                value={item.available ? item.value : null}
                label={componentLabel(item.name)}
                tone={item.name === "required" ? "accent" : "neutral"}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

