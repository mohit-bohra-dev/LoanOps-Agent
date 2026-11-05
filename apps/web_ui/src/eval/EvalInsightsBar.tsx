import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { FAILURE_CATEGORY_LABELS, type EvalInsightsSummary, type FailureCategory } from "./types";

type LayerHealth = Record<string, { passed?: boolean | null; missing?: boolean }>;

export function EvalInsightsBar({
  insights,
  layers,
  agentVersionFilter,
  onAgentVersionFilter,
}: {
  insights: EvalInsightsSummary;
  layers: LayerHealth | null;
  agentVersionFilter: string;
  onAgentVersionFilter: (v: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const totalOutcomes = insights.goodCount + insights.badCount + insights.needsReviewCount || 1;

  return (
    <div className="border border-surface-3 rounded-lg bg-surface-2/60 overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider text-text-secondary hover:bg-surface-3/40"
        onClick={() => setOpen((v) => !v)}
      >
        <span>Evaluation insights</span>
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {open && (
        <div className="px-3 pb-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 text-xs">
          <div className="rounded border border-surface-3 bg-surface-0/40 p-3">
            <p className="text-text-muted uppercase tracking-wide text-[10px]">AI vs Human agreement</p>
            <p className="text-2xl font-bold tabular-nums text-text-primary mt-1">
              {(insights.agreementRate * 100).toFixed(2)}%
            </p>
            <p className="text-text-muted mt-0.5">{insights.totalReviewed} compared · {insights.disagreeCount} disagree</p>
          </div>

          <div className="rounded border border-surface-3 bg-surface-0/40 p-3">
            <p className="text-text-muted uppercase tracking-wide text-[10px]">Outcome mix</p>
            <div className="mt-2 h-2 flex rounded overflow-hidden bg-surface-3">
              <div
                className="bg-emerald-500"
                style={{ width: `${(insights.goodCount / totalOutcomes) * 100}%` }}
                title={`Good ${insights.goodCount}`}
              />
              <div
                className="bg-rose-500"
                style={{ width: `${(insights.badCount / totalOutcomes) * 100}%` }}
                title={`Bad ${insights.badCount}`}
              />
              <div
                className="bg-amber-400"
                style={{ width: `${(insights.needsReviewCount / totalOutcomes) * 100}%` }}
                title={`Needs review ${insights.needsReviewCount}`}
              />
            </div>
            <p className="mt-2 text-text-secondary">
              <span className="text-emerald-400">{insights.goodCount} good</span>
              {" · "}
              <span className="text-rose-400">{insights.badCount} bad</span>
              {" · "}
              <span className="text-amber-300">{insights.needsReviewCount} review</span>
            </p>
          </div>

          <div className="rounded border border-surface-3 bg-surface-0/40 p-3">
            <p className="text-text-muted uppercase tracking-wide text-[10px]">Top failure categories</p>
            <ul className="mt-2 space-y-1">
              {insights.topCategories.length === 0 && (
                <li className="text-text-muted">None tagged yet</li>
              )}
              {insights.topCategories.map((c) => (
                <li key={c.category} className="flex justify-between gap-2">
                  <span className="truncate">
                    {FAILURE_CATEGORY_LABELS[c.category as FailureCategory] ?? c.category}
                  </span>
                  <span className="font-mono text-text-muted">{c.count}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded border border-surface-3 bg-surface-0/40 p-3 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-text-muted uppercase tracking-wide text-[10px]">Version / layers</p>
              <select
                className="bg-surface-2 border border-surface-3 rounded px-1.5 py-0.5 text-[11px]"
                value={agentVersionFilter}
                onChange={(e) => onAgentVersionFilter(e.target.value)}
              >
                <option value="all">All versions</option>
                <option value="agent v1.4">agent v1.4</option>
                <option value="agent v1.3">agent v1.3</option>
              </select>
            </div>
            {insights.byDepartment.length > 0 && (
              <ul className="space-y-0.5 text-text-secondary">
                {insights.byDepartment.map((d) => (
                  <li key={d.department} className="flex justify-between">
                    <span>{d.department}</span>
                    <span className="font-mono">
                      {(d.agreement * 100).toFixed(0)}% · {d.reviewed}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-1 pt-1">
              {layers
                ? Object.entries(layers).map(([k, v]) => {
                    const label =
                      v.missing ? "—" : v.passed === true ? "✓" : v.passed === false ? "✗" : "?";
                    const color =
                      v.missing
                        ? "border-surface-3 text-text-muted"
                        : v.passed === true
                          ? "border-emerald-700 text-emerald-300"
                          : v.passed === false
                            ? "border-rose-700 text-rose-300"
                            : "border-surface-3 text-text-muted";
                    return (
                      <span
                        key={k}
                        className={`px-1.5 py-0.5 rounded border font-mono text-[10px] ${color}`}
                        title={`Layer ${k}`}
                      >
                        L{k}:{label}
                      </span>
                    );
                  })
                : (
                  <span className="text-text-muted">Layer health offline</span>
                )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
