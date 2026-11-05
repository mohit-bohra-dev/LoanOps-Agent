import { useMemo, useState } from "react";
import { ChevronRight, Search } from "lucide-react";
import { OutcomePill } from "./OutcomePill";
import {
  FAILURE_CATEGORY_LABELS,
  type Department,
  type EvalMatrixRow,
  type FailureCategory,
  type OutcomeStatus,
  computeAlignment,
} from "./types";

export type ColKey = "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I";

const COLS: { key: ColKey; label: string; width: string }[] = [
  { key: "A", label: "Input / Scenario", width: "260px" },
  { key: "B", label: "Model Response", width: "320px" },
  { key: "C", label: "Model Critique", width: "280px" },
  { key: "D", label: "Model Outcome", width: "140px" },
  { key: "E", label: "Human Critique", width: "320px" },
  { key: "F", label: "Human Outcome", width: "140px" },
  { key: "G", label: "Alignment", width: "100px" },
  { key: "H", label: "Trace / Evidence", width: "150px" },
  { key: "I", label: "Agreement", width: "120px" },
];

type FilterOutcome = "all" | "disagree" | "bad" | "needs_review";

function cellText(row: EvalMatrixRow, col: ColKey): string {
  switch (col) {
    case "A":
      return row.user_query;
    case "B":
      return row.final_answer;
    case "C":
      return row.model_critique ?? "";
    case "D":
      return row.model_outcome ?? "";
    case "E":
      return row.human_critique ?? "";
    case "F":
      return row.human_outcome ?? "";
    case "G":
      return row.alignment == null ? "—" : String(row.alignment);
    case "H":
      return `${row.spans.length} steps · ${Math.round(row.latency_ms)}ms`;
    case "I":
      return "";
    default:
      return "";
  }
}

function HighlightedAnswer({ text, spanRefs }: { text: string; spanRefs: string[] }) {
  // span_refs like "answer:36:48:incorrect"
  const ranges = spanRefs
    .map((ref) => {
      const m = /^answer:(\d+):(\d+):(\w+)$/.exec(ref);
      if (!m) return null;
      return { start: Number(m[1]), end: Number(m[2]), kind: m[3] };
    })
    .filter(Boolean) as { start: number; end: number; kind: string }[];

  if (!ranges.length) {
    return <span className="whitespace-pre-wrap">{text}</span>;
  }

  const sorted = [...ranges].sort((a, b) => a.start - b.start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  sorted.forEach((r, i) => {
    if (r.start > cursor) {
      parts.push(<span key={`t-${i}`}>{text.slice(cursor, r.start)}</span>);
    }
    const cls =
      r.kind === "hallucinated" || r.kind === "incorrect"
        ? "bg-rose-500/30 text-rose-100 underline decoration-rose-400"
        : "bg-amber-500/30 text-amber-100 underline decoration-amber-400";
    parts.push(
      <mark key={`m-${i}`} className={`${cls} rounded px-0.5`}>
        {text.slice(r.start, r.end)}
      </mark>,
    );
    cursor = r.end;
  });
  if (cursor < text.length) parts.push(<span key="tail">{text.slice(cursor)}</span>);
  return <span className="whitespace-pre-wrap">{parts}</span>;
}

export function EvalSpreadsheet({
  rows,
  agreementRate,
  onRowsChange,
  onInspect,
}: {
  rows: EvalMatrixRow[];
  agreementRate: number;
  onRowsChange: (rows: EvalMatrixRow[]) => void;
  onInspect: (row: EvalMatrixRow) => void;
}) {
  const [active, setActive] = useState<{ row: number; col: ColKey } | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [filterOutcome, setFilterOutcome] = useState<FilterOutcome>("all");
  const [filterDept, setFilterDept] = useState<Department | "all">("all");
  const [filterCat, setFilterCat] = useState<FailureCategory | "all">("all");
  const [sortBy, setSortBy] = useState<"none" | "alignment" | "severity" | "latency">("none");

  const filtered = useMemo(() => {
    let list = [...rows];
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (r) =>
          r.user_query.toLowerCase().includes(q) ||
          r.final_answer.toLowerCase().includes(q) ||
          (r.loan_id ?? "").includes(q) ||
          r.trace_id.toLowerCase().includes(q),
      );
    }
    if (filterOutcome === "disagree") list = list.filter((r) => r.alignment === 0);
    if (filterOutcome === "bad") list = list.filter((r) => r.human_outcome === "bad" || r.model_outcome === "bad");
    if (filterOutcome === "needs_review") {
      list = list.filter(
        (r) => r.human_outcome === "needs_review" || r.model_outcome === "needs_review" || !r.human_outcome,
      );
    }
    if (filterDept !== "all") list = list.filter((r) => r.department === filterDept);
    if (filterCat !== "all") list = list.filter((r) => r.primary_category === filterCat);

    if (sortBy === "alignment") {
      list.sort((a, b) => (a.alignment ?? 2) - (b.alignment ?? 2));
    } else if (sortBy === "latency") {
      list.sort((a, b) => b.latency_ms - a.latency_ms);
    } else if (sortBy === "severity") {
      const rank = { blocker: 0, major: 1, minor: 2 };
      list.sort(
        (a, b) =>
          (a.severity ? rank[a.severity] : 9) - (b.severity ? rank[b.severity] : 9),
      );
    }
    return list;
  }, [rows, search, filterOutcome, filterDept, filterCat, sortBy]);

  const activeRow = active ? filtered[active.row] : null;
  const formulaText = active && activeRow ? cellText(activeRow, active.col) : "";

  function patchRow(id: string, patch: Partial<EvalMatrixRow>) {
    onRowsChange(
      rows.map((r) => {
        if (r.id !== id) return r;
        const next = { ...r, ...patch };
        next.alignment = computeAlignment(next.model_outcome, next.human_outcome);
        return next;
      }),
    );
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  function bulkMarkGood() {
    onRowsChange(
      rows.map((r) => {
        if (!selected.has(r.id)) return r;
        const next = { ...r, human_outcome: "good" as OutcomeStatus, human_critique: r.human_critique ?? "Bulk marked GOOD" };
        next.alignment = computeAlignment(next.model_outcome, next.human_outcome);
        return next;
      }),
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 border border-surface-3 rounded-lg overflow-hidden bg-surface-1">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 px-3 py-2 border-b border-surface-3 bg-surface-2 text-xs">
        <div className="relative flex-1 min-w-[160px] max-w-xs">
          <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-text-muted" />
          <input
            className="w-full pl-7 pr-2 py-1 rounded bg-surface-0 border border-surface-3 text-text-primary"
            placeholder="Search query, loan, trace…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="bg-surface-0 border border-surface-3 rounded px-2 py-1"
          value={filterOutcome}
          onChange={(e) => setFilterOutcome(e.target.value as FilterOutcome)}
        >
          <option value="all">All outcomes</option>
          <option value="disagree">Disagreements (Alignment=0)</option>
          <option value="bad">Bad</option>
          <option value="needs_review">Needs review</option>
        </select>
        <select
          className="bg-surface-0 border border-surface-3 rounded px-2 py-1"
          value={filterDept}
          onChange={(e) => setFilterDept(e.target.value as Department | "all")}
        >
          <option value="all">All departments</option>
          {(["Engineering", "QA", "Product", "Operations", "Compliance"] as Department[]).map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <select
          className="bg-surface-0 border border-surface-3 rounded px-2 py-1"
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value as FailureCategory | "all")}
        >
          <option value="all">All categories</option>
          {(Object.keys(FAILURE_CATEGORY_LABELS) as FailureCategory[]).map((c) => (
            <option key={c} value={c}>
              {FAILURE_CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
        <select
          className="bg-surface-0 border border-surface-3 rounded px-2 py-1"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
        >
          <option value="none">Sort…</option>
          <option value="alignment">Alignment</option>
          <option value="severity">Severity</option>
          <option value="latency">Latency</option>
        </select>
        <button
          type="button"
          className="px-2 py-1 rounded border border-surface-3 hover:bg-surface-3 disabled:opacity-40"
          disabled={selected.size === 0}
          onClick={bulkMarkGood}
        >
          Mark Good ({selected.size})
        </button>
      </div>

      {/* Formula bar */}
      <div className="flex items-stretch border-b border-surface-3 bg-[#0b1220] text-xs font-mono">
        <div className="px-3 py-1.5 text-text-muted border-r border-surface-3 w-16 shrink-0">
          {active ? `${active.col}${active.row + 2}` : "fx"}
        </div>
        <div className="px-3 py-1.5 text-text-secondary truncate flex-1">{formulaText || "Select a cell"}</div>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-auto min-h-0">
        <table className="border-collapse text-xs w-max min-w-full">
          <thead className="sticky top-0 z-20">
            <tr className="bg-[#111827] text-white">
              <th className="sticky left-0 z-30 bg-[#111827] w-10 border border-gray-700 px-1 py-2" />
              <th className="sticky left-10 z-30 bg-[#111827] w-8 border border-gray-700 px-1">#</th>
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={`border border-gray-700 px-2 py-2 text-left font-bold tracking-wide ${
                    c.key === "I" ? "sticky right-0 z-30 bg-[#111827]" : ""
                  }`}
                  style={{ minWidth: c.width, width: c.width }}
                >
                  <span className="text-gray-400 mr-1">{c.key}</span>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, ri) => {
              const isSel = selected.has(row.id);
              return (
                <tr
                  key={row.id}
                  className={`align-top ${isSel ? "bg-brand-500/10" : "hover:bg-surface-2/60"}`}
                  onDoubleClick={() => onInspect(row)}
                >
                  <td className="sticky left-0 z-10 bg-surface-1 border border-surface-3 px-1 text-center">
                    <input
                      type="checkbox"
                      checked={isSel}
                      onChange={() => toggleSelect(row.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td className="sticky left-10 z-10 bg-surface-1 border border-surface-3 px-1 text-center text-text-muted font-mono">
                    {ri + 1}
                  </td>

                  {/* A */}
                  <td
                    className="border border-surface-3 px-2 py-2 cursor-cell"
                    style={{ minWidth: "260px", maxWidth: "260px" }}
                    onClick={() => setActive({ row: ri, col: "A" })}
                  >
                    <p className="text-text-primary font-medium leading-snug">{row.user_query}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {row.loan_id && (
                        <span className="px-1.5 py-0.5 rounded bg-sky-900/50 text-sky-200 border border-sky-700/50 font-mono">
                          loan {row.loan_id}
                        </span>
                      )}
                      {row.department && (
                        <span className="px-1.5 py-0.5 rounded bg-violet-900/40 text-violet-200 border border-violet-700/40">
                          {row.department}
                        </span>
                      )}
                      {row.demo && (
                        <span className="px-1.5 py-0.5 rounded bg-surface-3 text-text-muted">DEMO</span>
                      )}
                    </div>
                    <p className="mt-1 text-[10px] text-text-muted">
                      {row.agent_version} · {row.mcp_version}
                    </p>
                  </td>

                  {/* B */}
                  <td
                    className="border border-surface-3 px-2 py-2 cursor-cell"
                    style={{ minWidth: "320px", maxWidth: "320px" }}
                    onClick={() => setActive({ row: ri, col: "B" })}
                  >
                    <HighlightedAnswer text={row.final_answer} spanRefs={row.span_refs} />
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {row.citations.map((c) => (
                        <span
                          key={c.id}
                          className="px-1.5 py-0.5 rounded-full bg-surface-3 text-[10px] text-brand-300 border border-surface-3"
                          title={c.snippet}
                        >
                          [{c.id}] {c.source}
                        </span>
                      ))}
                    </div>
                  </td>

                  {/* C */}
                  <td
                    className="border border-surface-3 px-2 py-2 cursor-cell text-text-secondary"
                    style={{ minWidth: "280px", maxWidth: "280px" }}
                    onClick={() => setActive({ row: ri, col: "C" })}
                  >
                    {row.model_critique ?? <span className="text-text-muted italic">No AI critique</span>}
                  </td>

                  {/* D */}
                  <td
                    className="border border-surface-3 px-2 py-2"
                    style={{ minWidth: "140px" }}
                    onClick={() => setActive({ row: ri, col: "D" })}
                  >
                    <OutcomePill
                      value={row.model_outcome}
                      onChange={(v) => patchRow(row.id, { model_outcome: v })}
                    />
                  </td>

                  {/* E */}
                  <td
                    className="border border-surface-3 px-1 py-1"
                    style={{ minWidth: "320px", maxWidth: "320px" }}
                    onClick={() => setActive({ row: ri, col: "E" })}
                  >
                    <textarea
                      className="w-full min-h-[72px] resize-y bg-transparent border-0 outline-none text-text-primary p-1"
                      value={row.human_critique ?? ""}
                      placeholder="Add human critique…"
                      onChange={(e) => patchRow(row.id, { human_critique: e.target.value })}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>

                  {/* F */}
                  <td
                    className="border border-surface-3 px-2 py-2"
                    style={{ minWidth: "140px" }}
                    onClick={() => setActive({ row: ri, col: "F" })}
                  >
                    <OutcomePill
                      value={row.human_outcome}
                      onChange={(v) => patchRow(row.id, { human_outcome: v })}
                    />
                  </td>

                  {/* G */}
                  <td
                    className={`border border-surface-3 px-2 py-2 text-center font-mono text-sm font-bold ${
                      row.alignment === 0
                        ? "bg-rose-950/50 text-rose-300"
                        : row.alignment === 1
                          ? "text-emerald-400"
                          : "text-text-muted"
                    }`}
                    style={{ minWidth: "100px" }}
                    onClick={() => setActive({ row: ri, col: "G" })}
                  >
                    {row.alignment == null ? "—" : row.alignment}
                  </td>

                  {/* H */}
                  <td
                    className="border border-surface-3 px-2 py-2"
                    style={{ minWidth: "150px" }}
                    onClick={() => setActive({ row: ri, col: "H" })}
                  >
                    <p className="text-text-secondary">
                      {row.spans.length} steps · {Math.round(row.latency_ms)}ms
                    </p>
                    <p className="text-text-muted">{row.citations.length} cites</p>
                    {row.primary_category && (
                      <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-amber-900/40 text-amber-200 text-[10px]">
                        {FAILURE_CATEGORY_LABELS[row.primary_category]}
                      </span>
                    )}
                    <button
                      type="button"
                      className="mt-1.5 flex items-center gap-0.5 text-brand-400 hover:text-brand-300 font-medium"
                      onClick={(e) => {
                        e.stopPropagation();
                        onInspect(row);
                      }}
                    >
                      Inspect <ChevronRight className="h-3 w-3" />
                    </button>
                  </td>

                  {/* I sticky */}
                  <td
                    className="sticky right-0 z-10 border border-surface-3 px-2 py-2 bg-surface-2 text-center"
                    style={{ minWidth: "120px" }}
                    onClick={() => setActive({ row: ri, col: "I" })}
                  >
                    <div className="text-lg font-bold text-text-primary tabular-nums">
                      {(agreementRate * 100).toFixed(2)}%
                    </div>
                    <div className="text-[10px] text-text-muted">AI↔Human</div>
                    {row.reviewer && (
                      <div className="mt-1 text-[10px] text-text-secondary truncate" title={row.reviewer}>
                        {row.reviewer}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="p-8 text-center text-text-muted text-sm">No rows match filters.</p>
        )}
      </div>
    </div>
  );
}
