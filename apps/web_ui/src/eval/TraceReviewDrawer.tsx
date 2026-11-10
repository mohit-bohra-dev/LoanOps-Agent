import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { AgentSteps } from "../components/AgentSteps";
import type { ToolCallItem } from "../types";
import { OutcomePill } from "./OutcomePill";
import {
  ACTION_LABELS,
  FAILURE_CATEGORY_LABELS,
  type Department,
  type EvalMatrixRow,
  type FailureCategory,
  type HighlightKind,
  type RecommendedAction,
  type Severity,
  computeAlignment,
  outcomeFromHumanLabel,
} from "./types";

const API = import.meta.env.VITE_AGENT_API_URL ?? "http://127.0.0.1:8000";

const DEPT_RUBRICS: Record<Department, string[]> = {
  Operations: ["Facts match loan data", "Tone suitable for borrower-facing ops", "Next step clear"],
  Compliance: ["No unauthorized write", "Policy cited when required", "No prohibited advice"],
  QA: ["Citations present for facts", "No hallucinated numbers/dates", "Tool errors handled"],
  Product: ["Capability gap identified", "Recommendation actionable", "User intent resolved"],
  Engineering: ["Correct tool selected", "Args valid", "No redundant MCP calls"],
};

function spansToToolCalls(row: EvalMatrixRow): ToolCallItem[] {
  return row.spans
    .filter((s) => s.tool && (s.kind === "tool" || s.name === "mcp.tool.call" || !s.kind))
    .map((s) => ({
      name: s.tool as string,
      args: s.args ?? {},
      result_summary: s.result_summary ?? s.result ?? "",
      latency_ms: s.latency_ms,
      is_error: s.is_error,
    }));
}

function kindColor(kind?: string, isError?: boolean): string {
  if (isError) return "bg-rose-500/70";
  switch (kind) {
    case "llm":
      return "bg-violet-500/70";
    case "tool":
      return "bg-brand-400/70";
    case "subtool":
      return "bg-sky-500/60";
    case "safety":
      return "bg-amber-500/70";
    case "validator":
      return "bg-emerald-500/70";
    case "turn":
      return "bg-surface-3";
    default:
      return "bg-surface-3";
  }
}

function formatMs(ms?: number): string {
  if (ms == null || ms <= 0) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function spanDepth(spans: EvalMatrixRow["spans"], spanId: string, memo = new Map<string, number>()): number {
  if (memo.has(spanId)) return memo.get(spanId)!;
  const span = spans.find((s) => s.span_id === spanId);
  if (!span || !span.parent_span_id) {
    memo.set(spanId, 0);
    return 0;
  }
  const d = 1 + spanDepth(spans, span.parent_span_id, memo);
  memo.set(spanId, d);
  return d;
}

export function TraceReviewDrawer({
  row,
  defaultReviewer,
  onClose,
  onSaved,
}: {
  row: EvalMatrixRow;
  defaultReviewer?: string;
  onClose: () => void;
  onSaved: (next: EvalMatrixRow) => void;
}) {
  const [tab, setTab] = useState<"business" | "trace">("business");
  const [draft, setDraft] = useState<EvalMatrixRow>(() => ({
    ...row,
    reviewer: row.reviewer ?? (defaultReviewer?.trim() || null),
  }));
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [selectionHint, setSelectionHint] = useState("");

  const toolCalls = useMemo(() => spansToToolCalls(draft), [draft]);

  function patch(p: Partial<EvalMatrixRow>) {
    setDraft((d) => {
      const next = { ...d, ...p };
      next.alignment = computeAlignment(next.model_outcome, next.human_outcome);
      return next;
    });
  }

  function tagSelection(kind: HighlightKind) {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.anchorNode) {
      setSelectionHint("Select text in the agent response first.");
      return;
    }
    const answerEl = document.getElementById("eval-answer-text");
    if (!answerEl || !answerEl.contains(sel.anchorNode)) {
      setSelectionHint("Selection must be inside the agent response.");
      return;
    }
    const full = draft.final_answer;
    const selected = sel.toString();
    const start = full.indexOf(selected);
    if (start < 0) {
      setSelectionHint("Could not map selection to answer text.");
      return;
    }
    const end = start + selected.length;
    const ref = `answer:${start}:${end}:${kind}`;
    const span_refs = [...draft.span_refs.filter((r) => !r.startsWith(`answer:${start}:${end}:`)), ref];
    const flags = kind === "hallucinated" && !draft.flags.includes("hallucination")
      ? [...draft.flags, "hallucination"]
      : draft.flags;
    patch({ span_refs, flags });
    setSelectionHint(`Tagged “${selected.slice(0, 40)}…” as ${kind}`);
    sel.removeAllRanges();
  }

  async function saveReview() {
    if (draft.demo) {
      onSaved(draft);
      setStatus("Saved locally (demo row)");
      return;
    }
    if (!draft.human_outcome) {
      setStatus("Set Human Outcome before saving.");
      return;
    }
    setSaving(true);
    setStatus("saving…");
    try {
      const res = await fetch(`${API}/eval/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trace_id: draft.trace_id,
          label: outcomeFromHumanLabel(draft.human_outcome),
          primary_category: draft.primary_category,
          severity: draft.severity,
          root_component: draft.root_component,
          comment: draft.human_critique,
          span_refs: draft.span_refs,
          department: draft.department,
          reviewer: draft.reviewer?.trim() || defaultReviewer?.trim() || "web_ui",
          model_critique: draft.model_critique,
          model_outcome: draft.model_outcome,
          suggested_answer: draft.suggested_answer,
          recommended_action: draft.recommended_action,
          flags: draft.flags,
        }),
      });
      if (!res.ok) {
        setStatus(`error ${res.status}`);
      } else {
        onSaved(draft);
        setStatus("Review saved");
      }
    } catch {
      setStatus("Network error — saved locally only");
      onSaved(draft);
    } finally {
      setSaving(false);
    }
  }

  async function promote() {
    if (draft.demo) {
      patch({ promoted_draft: true });
      onSaved({ ...draft, promoted_draft: true });
      setStatus("Demo: marked as draft candidate (local)");
      return;
    }
    setSaving(true);
    setStatus("promoting…");
    try {
      const res = await fetch(`${API}/eval/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: draft.trace_id, reviewer: draft.reviewer ?? "web_ui" }),
      });
      if (res.ok) {
        patch({ promoted_draft: true });
        onSaved({ ...draft, promoted_draft: true });
        setStatus("Draft candidate written — human PR approval still required");
      } else {
        setStatus(`promote error ${res.status}`);
      }
    } catch {
      setStatus("Promote failed (API unreachable)");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-black/50" onClick={onClose}>
      <aside
        className="w-full max-w-xl h-full bg-surface-1 border-l border-surface-3 shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 px-4 py-3 border-b border-surface-3 bg-surface-2">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-text-primary truncate">{draft.user_query}</h2>
            <p className="text-[11px] text-text-muted font-mono mt-0.5">
              {draft.trace_id}
              {draft.loan_id ? ` · loan ${draft.loan_id}` : ""}
              {draft.promoted_draft ? " · draft candidate" : ""}
            </p>
          </div>
          <button type="button" className="p-1 text-text-muted hover:text-text-primary" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>

        <nav className="flex gap-1 px-4 pt-2 border-b border-surface-3 text-xs">
          {(
            [
              ["business", "Business review"],
              ["trace", "Trace & evidence"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`px-3 py-2 border-b-2 ${
                tab === id
                  ? "border-brand-400 text-brand-300"
                  : "border-transparent text-text-secondary"
              }`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-auto p-4 space-y-4 text-sm">
          {tab === "business" && (
            <>
              <div className="grid grid-cols-1 gap-3">
                <section className="rounded border border-surface-3 p-3 bg-surface-0/40">
                  <h3 className="text-[10px] uppercase tracking-wider text-text-muted mb-1">User query</h3>
                  <p className="text-text-primary">{draft.user_query}</p>
                </section>
                <section className="rounded border border-surface-3 p-3 bg-surface-0/40">
                  <h3 className="text-[10px] uppercase tracking-wider text-text-muted mb-1">
                    Agent response — select text to tag
                  </h3>
                  <p id="eval-answer-text" className="text-text-primary whitespace-pre-wrap select-text">
                    {draft.final_answer}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(["hallucinated", "incorrect", "incomplete", "irrelevant"] as HighlightKind[]).map(
                      (k) => (
                        <button
                          key={k}
                          type="button"
                          className="px-2 py-0.5 rounded border border-surface-3 text-[10px] uppercase hover:bg-surface-3"
                          onClick={() => tagSelection(k)}
                        >
                          {k}
                        </button>
                      ),
                    )}
                  </div>
                  {selectionHint && <p className="mt-1 text-[11px] text-amber-300">{selectionHint}</p>}
                  {draft.span_refs.length > 0 && (
                    <p className="mt-1 text-[10px] text-text-muted font-mono">
                      {draft.span_refs.join(" · ")}
                    </p>
                  )}
                </section>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <label className="block text-xs space-y-1">
                  <span className="text-text-muted">Department</span>
                  <select
                    className="w-full bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                    value={draft.department ?? ""}
                    onChange={(e) =>
                      patch({ department: (e.target.value || null) as Department | null })
                    }
                  >
                    <option value="">—</option>
                    {(["Operations", "Compliance", "QA", "Product", "Engineering"] as Department[]).map(
                      (d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <label className="block text-xs space-y-1">
                  <span className="text-text-muted">Human outcome</span>
                  <OutcomePill
                    value={draft.human_outcome}
                    onChange={(v) => patch({ human_outcome: v })}
                  />
                </label>
              </div>

              {draft.department && (
                <ul className="text-xs text-text-secondary space-y-1 border border-surface-3 rounded p-2 bg-surface-2/40">
                  {DEPT_RUBRICS[draft.department].map((item) => (
                    <li key={item} className="flex gap-2">
                      <input type="checkbox" className="mt-0.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="grid grid-cols-2 gap-3">
                <label className="block text-xs space-y-1">
                  <span className="text-text-muted">Failure category</span>
                  <select
                    className="w-full bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                    value={draft.primary_category ?? ""}
                    onChange={(e) =>
                      patch({
                        primary_category: (e.target.value || null) as FailureCategory | null,
                      })
                    }
                  >
                    <option value="">—</option>
                    {(Object.keys(FAILURE_CATEGORY_LABELS) as FailureCategory[]).map((c) => (
                      <option key={c} value={c}>
                        {FAILURE_CATEGORY_LABELS[c]}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs space-y-1">
                  <span className="text-text-muted">Severity</span>
                  <select
                    className="w-full bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                    value={draft.severity ?? ""}
                    onChange={(e) =>
                      patch({ severity: (e.target.value || null) as Severity | null })
                    }
                  >
                    <option value="">—</option>
                    <option value="blocker">blocker</option>
                    <option value="major">major</option>
                    <option value="minor">minor</option>
                  </select>
                </label>
              </div>

              <label className="block text-xs space-y-1">
                <span className="text-text-muted">Root component</span>
                <input
                  className="w-full bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                  value={draft.root_component ?? ""}
                  onChange={(e) => patch({ root_component: e.target.value || null })}
                  placeholder="generation | mcp | sop_retrieval | …"
                />
              </label>

              <fieldset className="text-xs space-y-1">
                <legend className="text-text-muted mb-1">Flags</legend>
                <div className="flex flex-wrap gap-2">
                  {["security", "compliance", "policy", "hallucination", "missing_info"].map((f) => {
                    const on = draft.flags.includes(f);
                    return (
                      <label key={f} className="inline-flex items-center gap-1 px-2 py-1 rounded border border-surface-3">
                        <input
                          type="checkbox"
                          checked={on}
                          onChange={() =>
                            patch({
                              flags: on
                                ? draft.flags.filter((x) => x !== f)
                                : [...draft.flags, f],
                            })
                          }
                        />
                        {f}
                      </label>
                    );
                  })}
                </div>
              </fieldset>

              <label className="block text-xs space-y-1">
                <span className="text-text-muted">Human critique</span>
                <textarea
                  className="w-full min-h-[80px] bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                  value={draft.human_critique ?? ""}
                  onChange={(e) => patch({ human_critique: e.target.value })}
                />
              </label>

              <label className="block text-xs space-y-1">
                <span className="text-text-muted">Suggested answer</span>
                <textarea
                  className="w-full min-h-[60px] bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                  value={draft.suggested_answer ?? ""}
                  onChange={(e) => patch({ suggested_answer: e.target.value || null })}
                />
              </label>

              <label className="block text-xs space-y-1">
                <span className="text-text-muted">Improvement recommendation</span>
                <select
                  className="w-full bg-surface-2 border border-surface-3 rounded px-2 py-1.5"
                  value={draft.recommended_action ?? ""}
                  onChange={(e) =>
                    patch({
                      recommended_action: (e.target.value || null) as RecommendedAction | null,
                    })
                  }
                >
                  <option value="">—</option>
                  {(Object.keys(ACTION_LABELS) as RecommendedAction[]).map((a) => (
                    <option key={a} value={a}>
                      {ACTION_LABELS[a]}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}

          {tab === "trace" && (
            <div className="space-y-3">
              {(() => {
                const llmMs = draft.spans
                  .filter((s) => s.kind === "llm")
                  .reduce((sum, s) => sum + (s.latency_ms ?? 0), 0);
                const toolMs = draft.spans
                  .filter((s) => s.kind === "tool" || s.name === "mcp.tool.call")
                  .reduce((sum, s) => sum + (s.latency_ms ?? 0), 0);
                const totalWindow = Math.max(
                  draft.latency_ms,
                  ...draft.spans.map((s) => (s.start_offset_ms ?? 0) + (s.latency_ms ?? 0)),
                  1,
                );
                const prompt = draft.token_usage.prompt ?? draft.token_usage.prompt_tokens ?? 0;
                const completion =
                  draft.token_usage.completion ?? draft.token_usage.completion_tokens ?? 0;
                return (
                  <div className="flex flex-wrap gap-2 text-[11px] text-text-secondary">
                    <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40">
                      {draft.spans.length} spans · {formatMs(draft.latency_ms)}
                    </span>
                    <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40">
                      LLM {formatMs(llmMs)} · tools {formatMs(toolMs)}
                    </span>
                    <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40">
                      tokens {prompt}/{completion}
                    </span>
                    {draft.model ? (
                      <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40 font-mono">
                        {draft.model}
                      </span>
                    ) : null}
                    {(draft.rounds_used ?? 0) > 0 ? (
                      <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40">
                        rounds {draft.rounds_used}
                        {(draft.validation_retries ?? 0) > 0
                          ? ` · val retries ${draft.validation_retries}`
                          : ""}
                      </span>
                    ) : null}
                    {draft.status ? (
                      <span className="px-2 py-1 rounded border border-surface-3 bg-surface-0/40">
                        {draft.status}
                      </span>
                    ) : null}
                    {/* keep totalWindow in closure for waterfall below via data attr */}
                    <span className="hidden" data-total-window={totalWindow} />
                  </div>
                );
              })()}
              {toolCalls.length > 0 ? (
                <AgentSteps toolCalls={toolCalls} />
              ) : (
                <p className="text-text-muted text-xs">No MCP tool spans on this trace.</p>
              )}
              <div className="space-y-1.5">
                <h3 className="text-[10px] uppercase tracking-wider text-text-muted">Waterfall</h3>
                {(() => {
                  const totalWindow = Math.max(
                    draft.latency_ms,
                    ...draft.spans.map((s) => (s.start_offset_ms ?? 0) + (s.latency_ms ?? 0)),
                    1,
                  );
                  const ordered = [...draft.spans].sort(
                    (a, b) => (a.start_offset_ms ?? 0) - (b.start_offset_ms ?? 0),
                  );
                  return ordered.map((s) => {
                    const depth = spanDepth(draft.spans, s.span_id);
                    const left = Math.min(100, ((s.start_offset_ms ?? 0) / totalWindow) * 100);
                    const width = Math.max(
                      0.5,
                      Math.min(100 - left, ((s.latency_ms ?? 0) / totalWindow) * 100),
                    );
                    return (
                      <details
                        key={s.span_id}
                        className="border border-surface-3 rounded p-2 bg-surface-0/30 text-xs"
                        style={{ marginLeft: depth * 12 }}
                      >
                        <summary className="cursor-pointer font-mono text-text-secondary list-none">
                          <div className="flex items-center gap-2">
                            <span className="truncate min-w-0 flex-1">
                              {s.name}
                              {s.tool ? ` · ${s.tool}` : ""}
                              {s.kind ? ` · ${s.kind}` : ""}
                              {s.is_error ? " · ERROR" : ""}
                            </span>
                            <span className="text-text-muted shrink-0">{formatMs(s.latency_ms)}</span>
                          </div>
                          <div className="mt-1.5 h-1.5 w-full rounded bg-surface-2 relative overflow-hidden">
                            <div
                              className={`absolute top-0 h-full rounded ${kindColor(s.kind, s.is_error)}`}
                              style={{ left: `${left}%`, width: `${width}%` }}
                            />
                          </div>
                        </summary>
                        {s.args && Object.keys(s.args).length > 0 && (
                          <pre className="mt-2 overflow-auto text-[10px] text-text-muted">
                            {JSON.stringify(s.args, null, 2)}
                          </pre>
                        )}
                        {s.attributes && Object.keys(s.attributes).length > 0 && (
                          <pre className="mt-2 overflow-auto text-[10px] text-sky-200/70">
                            {JSON.stringify(s.attributes, null, 2)}
                          </pre>
                        )}
                        {(s.result_summary || s.result) && (
                          <pre className="mt-2 overflow-auto text-[10px] text-emerald-200/80 whitespace-pre-wrap">
                            {s.result_summary ?? s.result}
                          </pre>
                        )}
                      </details>
                    );
                  });
                })()}
              </div>
              {draft.pipeline_hits &&
                (draft.pipeline_hits.docs.length > 0 ||
                  draft.pipeline_hits.api_index.length > 0 ||
                  draft.pipeline_hits.eakg.length > 0 ||
                  draft.pipeline_hits.code.length > 0) && (
                  <div className="space-y-2">
                    <h3 className="text-[10px] uppercase tracking-wider text-text-muted">
                      Pipeline hits
                    </h3>
                    {(
                      [
                        ["docs", draft.pipeline_hits.docs],
                        ["api_index", draft.pipeline_hits.api_index],
                        ["eakg", draft.pipeline_hits.eakg],
                        ["code", draft.pipeline_hits.code],
                      ] as const
                    ).map(([label, rows]) =>
                      rows.length === 0 ? null : (
                        <div key={label} className="border border-surface-3 rounded p-2 text-xs">
                          <div className="text-text-muted mb-1">{label}</div>
                          <pre className="overflow-auto text-[10px] text-text-secondary">
                            {JSON.stringify(rows, null, 2)}
                          </pre>
                        </div>
                      ),
                    )}
                  </div>
                )}
              {draft.citations.length > 0 && (
                <ul className="text-xs space-y-1">
                  {draft.citations.map((c) => (
                    <li key={c.id} className="border border-surface-3 rounded px-2 py-1">
                      <span className="text-brand-300">[{c.id}] {c.source}</span>
                      <p className="text-text-muted mt-0.5">{c.snippet}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <footer className="border-t border-surface-3 px-4 py-3 flex flex-wrap items-center gap-2 bg-surface-2">
          <button
            type="button"
            disabled={saving}
            className="px-3 py-1.5 rounded bg-brand-500/20 border border-brand-500/40 text-sm text-brand-200 disabled:opacity-50"
            onClick={() => void saveReview()}
          >
            Save Review
          </button>
          <button
            type="button"
            disabled={saving}
            className="px-3 py-1.5 rounded border border-surface-3 text-sm disabled:opacity-50"
            onClick={() => void promote()}
          >
            Promote to Golden Candidate
          </button>
          {draft.promoted_draft && (
            <span className="text-[10px] px-2 py-1 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40">
              Draft — human PR approval required
            </span>
          )}
          {status && <span className="text-[11px] text-text-muted ml-auto">{status}</span>}
        </footer>
      </aside>
    </div>
  );
}
