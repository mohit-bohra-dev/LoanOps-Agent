import { useCallback, useEffect, useMemo, useState } from "react";
import { EvalInsightsBar } from "../eval/EvalInsightsBar";
import { EvalSpreadsheet } from "../eval/EvalSpreadsheet";
import { DEMO_SCENARIOS } from "../eval/mockData";
import { TraceReviewDrawer } from "../eval/TraceReviewDrawer";
import {
  summarizeInsights,
  type EvalMatrixRow,
  type MatrixApiResponse,
  type OutcomeStatus,
} from "../eval/types";

const API = import.meta.env.VITE_AGENT_API_URL ?? "http://127.0.0.1:8000";

type Health = {
  layers: Record<string, { passed?: boolean | null; missing?: boolean }>;
  ops_separate: boolean;
  release_gate: { ready?: boolean; reasons?: string[] };
};

type View = "matrix" | "insights" | "candidates";

function normalizeApiRow(raw: Record<string, unknown>, idx: number): EvalMatrixRow {
  return {
    id: String(raw.trace_id ?? `live-${idx}`),
    trace_id: String(raw.trace_id ?? `live-${idx}`),
    user_query: String(raw.user_query ?? ""),
    final_answer: String(raw.final_answer ?? ""),
    citations: Array.isArray(raw.citations) ? (raw.citations as EvalMatrixRow["citations"]) : [],
    spans: Array.isArray(raw.spans) ? (raw.spans as EvalMatrixRow["spans"]) : [],
    latency_ms: Number(raw.latency_ms ?? 0),
    token_usage: (raw.token_usage as Record<string, number>) ?? {},
    model_critique: (raw.model_critique as string | null) ?? null,
    model_outcome: (raw.model_outcome as OutcomeStatus | null) ?? null,
    human_critique: (raw.human_critique as string | null) ?? null,
    human_outcome: (raw.human_outcome as OutcomeStatus | null) ?? null,
    alignment: (raw.alignment as number | null) ?? null,
    primary_category: (raw.primary_category as EvalMatrixRow["primary_category"]) ?? null,
    severity: (raw.severity as EvalMatrixRow["severity"]) ?? null,
    root_component: (raw.root_component as string | null) ?? null,
    department: (raw.department as EvalMatrixRow["department"]) ?? null,
    recommended_action: (raw.recommended_action as EvalMatrixRow["recommended_action"]) ?? null,
    suggested_answer: (raw.suggested_answer as string | null) ?? null,
    flags: Array.isArray(raw.flags) ? (raw.flags as string[]) : [],
    span_refs: Array.isArray(raw.span_refs) ? (raw.span_refs as string[]) : [],
    reviewer: (raw.reviewer as string | null) ?? null,
    promoted_draft: Boolean(raw.promoted_draft),
    agent_version: String(raw.agent_version ?? "agent v1.4"),
    mcp_version: String(raw.mcp_version ?? "mcp v1.2"),
    loan_id: (raw.loan_id as string | null) ?? null,
    demo: false,
  };
}

/**
 * Spreadsheet-style AI Agent Evaluation & Human Review workspace.
 */
export function EvalPortal({ onClose }: { onClose: () => void }) {
  const [view, setView] = useState<View>("matrix");
  const [includeDemo, setIncludeDemo] = useState(true);
  const [liveRows, setLiveRows] = useState<EvalMatrixRow[]>([]);
  const [demoRows, setDemoRows] = useState<EvalMatrixRow[]>(DEMO_SCENARIOS);
  const [health, setHealth] = useState<Health | null>(null);
  const [inspect, setInspect] = useState<EvalMatrixRow | null>(null);
  const [agentVersionFilter, setAgentVersionFilter] = useState("all");
  const [loadNote, setLoadNote] = useState("");

  const load = useCallback(async () => {
    try {
      const [matrixRes, healthRes] = await Promise.all([
        fetch(`${API}/eval/matrix`),
        fetch(`${API}/eval/health`),
      ]);
      if (matrixRes.ok) {
        const body = (await matrixRes.json()) as MatrixApiResponse;
        setLiveRows(
          (body.rows as unknown as Record<string, unknown>[]).map((r, i) => normalizeApiRow(r, i)),
        );
        setLoadNote(`Live matrix: ${body.rows.length} traces`);
      } else {
        setLoadNote(`Matrix HTTP ${matrixRes.status} — demo rows only`);
      }
      if (healthRes.ok) setHealth((await healthRes.json()) as Health);
    } catch {
      setLoadNote("Agent API unreachable — showing demo scenarios");
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const rows = useMemo(() => {
    const merged = includeDemo ? [...demoRows, ...liveRows] : [...liveRows];
    if (agentVersionFilter === "all") return merged;
    return merged.filter((r) => r.agent_version === agentVersionFilter);
  }, [includeDemo, demoRows, liveRows, agentVersionFilter]);

  const insights = useMemo(() => summarizeInsights(rows), [rows]);

  function onRowsChange(next: EvalMatrixRow[]) {
    const demoIds = new Set(demoRows.map((r) => r.id));
    setDemoRows(next.filter((r) => demoIds.has(r.id)));
    setLiveRows(next.filter((r) => !demoIds.has(r.id)));
  }

  function onSaved(updated: EvalMatrixRow) {
    onRowsChange(rows.map((r) => (r.id === updated.id ? updated : r)));
    setInspect(updated);
  }

  const candidates = rows.filter((r) => r.promoted_draft);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-surface-0 text-text-primary">
      <header className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-surface-3 bg-surface-1 shrink-0">
        <div className="min-w-0 flex-1">
          <h1 className="text-base font-semibold truncate">
            AI Agent Evaluation & Human Review Matrix
          </h1>
          <p className="text-[11px] text-text-muted">{loadNote}</p>
        </div>
        <nav className="flex gap-1 text-xs">
          {(
            [
              ["matrix", "Spreadsheet Matrix"],
              ["insights", "Insights & Layers"],
              ["candidates", "Golden Candidates"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`px-3 py-1.5 rounded border ${
                view === id
                  ? "border-brand-500 text-brand-300 bg-brand-500/10"
                  : "border-surface-3 text-text-secondary"
              }`}
              onClick={() => setView(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <label className="flex items-center gap-1.5 text-xs text-text-secondary">
          <input
            type="checkbox"
            checked={includeDemo}
            onChange={(e) => setIncludeDemo(e.target.checked)}
          />
          Include Demo Rows
        </label>
        <button
          type="button"
          className="text-xs text-text-secondary underline"
          onClick={() => void load()}
        >
          Refresh
        </button>
        <button type="button" className="text-sm text-text-secondary underline" onClick={onClose}>
          Close
        </button>
      </header>

      <div className="flex-1 min-h-0 flex flex-col gap-3 p-3 overflow-hidden">
        {(view === "matrix" || view === "insights") && (
          <EvalInsightsBar
            insights={insights}
            layers={health?.layers ?? null}
            agentVersionFilter={agentVersionFilter}
            onAgentVersionFilter={setAgentVersionFilter}
          />
        )}

        {view === "matrix" && (
          <div className="flex-1 min-h-0">
            <EvalSpreadsheet
              rows={rows}
              agreementRate={insights.agreementRate}
              onRowsChange={onRowsChange}
              onInspect={setInspect}
            />
          </div>
        )}

        {view === "insights" && (
          <div className="flex-1 overflow-auto space-y-3 text-sm">
            <p className="text-text-secondary">
              Offline layer health stays separate from ops scores. Release gate:{" "}
              {health ? String(health.release_gate?.ready) : "n/a"}
            </p>
            {health?.release_gate?.reasons?.length ? (
              <ul className="text-xs text-text-muted list-disc pl-5">
                {health.release_gate.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
            <div className="rounded border border-surface-3 p-3 bg-surface-1">
              <h3 className="text-xs uppercase tracking-wider text-text-muted mb-2">
                Department agreement
              </h3>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-text-muted">
                    <th className="py-1">Department</th>
                    <th>Reviewed</th>
                    <th>Agreement</th>
                  </tr>
                </thead>
                <tbody>
                  {insights.byDepartment.map((d) => (
                    <tr key={d.department} className="border-t border-surface-3">
                      <td className="py-1.5">{d.department}</td>
                      <td>{d.reviewed}</td>
                      <td className="font-mono">{(d.agreement * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {view === "candidates" && (
          <div className="flex-1 overflow-auto space-y-2">
            <p className="text-xs text-text-secondary">
              Draft golden candidates only — never auto-approved. Promote from the Inspect drawer.
            </p>
            {candidates.length === 0 && (
              <p className="text-sm text-text-muted">No draft candidates yet.</p>
            )}
            {candidates.map((c) => (
              <button
                key={c.id}
                type="button"
                className="w-full text-left border border-surface-3 rounded-lg px-3 py-2 hover:bg-surface-2"
                onClick={() => setInspect(c)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium truncate">{c.user_query}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40 shrink-0">
                    draft
                  </span>
                </div>
                <p className="text-[11px] text-text-muted font-mono mt-0.5">{c.trace_id}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {inspect && (
        <TraceReviewDrawer
          row={inspect}
          onClose={() => setInspect(null)}
          onSaved={onSaved}
        />
      )}
    </div>
  );
}
