import type { SuggestedSkillPath } from "@/lib/api";
import { SUGGESTED_SKILL_PATH_LABEL } from "@/lib/baseline-match";
import { Route, Info, ArrowRight } from "lucide-react";

export function SkillPathList({
  items,
  disclaimer,
}: {
  items: SuggestedSkillPath[];
  disclaimer?: string;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2.5 rounded-xl border border-teal-200/80 bg-teal-50/60 p-3.5 text-xs text-teal-900 font-medium">
        <Info className="h-4 w-4 shrink-0 text-teal-700 mt-0.5" />
        <p className="leading-relaxed">
          {disclaimer || `${SUGGESTED_SKILL_PATH_LABEL} uses the canonical skill ontology graph to identify logical progression steps. It is not a guaranteed career path.`}
        </p>
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-slate-500">No bounded ontology path is available yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map((path) => {
            const steps = (path.steps ?? []).map((step) => step?.skill).filter(Boolean);
            return (
              <div
                key={path.target_skill_id}
                className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs space-y-3 hover:border-teal-200 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-teal-50 text-teal-700">
                      <Route className="h-4 w-4" />
                    </div>
                    <h4 className="text-sm font-bold text-slate-900">{path.target_skill}</h4>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                    Ontology Path
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs font-mono">
                  {steps.map((skillName, idx) => (
                    <div key={`${path.target_skill_id}-${idx}`} className="flex items-center gap-2">
                      <span className="rounded-lg bg-slate-100 text-slate-800 px-2.5 py-1 border border-slate-200/80 font-medium text-xs">
                        {skillName}
                      </span>
                      {idx < steps.length - 1 ? (
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

