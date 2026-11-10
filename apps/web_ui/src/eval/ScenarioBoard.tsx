import { useMemo, useState } from "react";
import {
  TEST_SCENARIOS,
  type ScenarioPhase,
  type TestScenario,
} from "./scenarios";

const PHASE_LABEL: Record<ScenarioPhase, string> = {
  one_tool: "Phase 1 — one tool (isolated)",
  chain: "Phase 2 — tool chain (one turn)",
  gap: "Known gaps (expect weak)",
};

function statusBadge(s: TestScenario["status"]): string {
  if (s === "ok") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/40";
  if (s === "partial") return "bg-amber-500/15 text-amber-200 border-amber-500/40";
  return "bg-surface-3 text-text-secondary border-surface-3";
}

export function ScenarioBoard({
  reviewer,
  onPickQuery,
}: {
  reviewer: string;
  onPickQuery?: (query: string) => void;
}) {
  const [ownerFilter, setOwnerFilter] = useState("all");
  const [copied, setCopied] = useState<string | null>(null);

  const owners = useMemo(() => {
    const set = new Set(TEST_SCENARIOS.map((s) => s.ownerHint));
    return ["all", ...Array.from(set).sort()];
  }, []);

  const grouped = useMemo(() => {
    const list =
      ownerFilter === "all"
        ? TEST_SCENARIOS
        : TEST_SCENARIOS.filter((s) => s.ownerHint === ownerFilter);
    const byPhase: Record<ScenarioPhase, TestScenario[]> = {
      one_tool: [],
      chain: [],
      gap: [],
    };
    for (const s of list) byPhase[s.phase].push(s);
    return byPhase;
  }, [ownerFilter]);

  async function copyQuery(s: TestScenario) {
    try {
      await navigator.clipboard.writeText(s.query);
      setCopied(s.id);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setCopied(null);
    }
    onPickQuery?.(s.query);
  }

  return (
    <div className="flex-1 min-h-0 overflow-auto space-y-4 text-sm">
      <div className="rounded border border-surface-3 bg-surface-1 p-3 text-xs text-text-secondary space-y-1">
        <p>
          <span className="text-text-primary font-medium">Multi-user protocol:</span>{" "}
          set your reviewer name above · turn on <em>Isolated (no memory)</em> in Chat ·
          copy a scenario · run it · open Eval Matrix and leave feedback with your name.
        </p>
        <p>
          Reviewer:{" "}
          <span className="font-mono text-brand-300">
            {reviewer.trim() || "(set name in header)"}
          </span>
          {" · "}Loan under test: <span className="font-mono">1000002245</span>
        </p>
      </div>

      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Owner filter
        <select
          className="bg-surface-0 border border-surface-3 rounded px-2 py-1 text-text-primary"
          value={ownerFilter}
          onChange={(e) => setOwnerFilter(e.target.value)}
        >
          {owners.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </label>

      {(["one_tool", "chain", "gap"] as const).map((phase) => (
        <section key={phase} className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            {PHASE_LABEL[phase]}
          </h2>
          <ul className="space-y-2">
            {grouped[phase].map((s) => (
              <li
                key={s.id}
                className="rounded border border-surface-3 bg-surface-0/40 p-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-brand-300">{s.id}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded border ${statusBadge(s.status)}`}
                    >
                      {s.status}
                    </span>
                    <span className="text-[10px] text-text-muted">owner: {s.ownerHint}</span>
                  </div>
                  <p className="font-medium text-text-primary">{s.title}</p>
                  <p className="text-xs text-text-secondary font-mono whitespace-pre-wrap">
                    {s.query}
                  </p>
                  <p className="text-[11px] text-text-muted">Expect: {s.expectTools}</p>
                  {s.note ? (
                    <p className="text-[11px] text-amber-200/80">{s.note}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="shrink-0 self-start text-xs px-3 py-1.5 rounded border border-brand-500/50 text-brand-300 hover:bg-brand-500/10"
                  onClick={() => void copyQuery(s)}
                >
                  {copied === s.id ? "Copied" : "Copy query"}
                </button>
              </li>
            ))}
            {grouped[phase].length === 0 ? (
              <li className="text-xs text-text-muted">No scenarios for this filter.</li>
            ) : null}
          </ul>
        </section>
      ))}
    </div>
  );
}
