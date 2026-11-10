import { useCallback, useEffect, useState } from "react";

const API = import.meta.env.VITE_AGENT_API_URL ?? "http://127.0.0.1:8000";

type PipelineCard = {
  pipeline_id: string;
  title: string;
  description: string;
  last_run: Record<string, unknown> | null;
};

type RunRow = Record<string, unknown> & {
  run_id?: string;
  pipeline_id?: string;
  status?: string;
  finished_at?: string | null;
  duration_ms?: number | null;
  report?: { operations?: number; status?: string } | null;
  logs?: string[];
  error?: string | null;
};

type Props = {
  reviewer: string;
};

export function PipelinesView({ reviewer }: Props) {
  const [catalog, setCatalog] = useState<PipelineCard[]>([]);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [env, setEnv] = useState("dev");
  const [repositoryId, setRepositoryId] = useState("");
  const [note, setNote] = useState("");
  const [inspect, setInspect] = useState<RunRow | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [catRes, runRes] = await Promise.all([
        fetch(`${API}/pipelines/catalog`),
        fetch(`${API}/pipelines/runs?limit=30`),
      ]);
      if (catRes.ok) {
        const body = (await catRes.json()) as { pipelines: PipelineCard[] };
        setCatalog(body.pipelines ?? []);
      }
      if (runRes.ok) {
        const body = (await runRes.json()) as { runs: RunRow[] };
        setRuns(body.runs ?? []);
      }
      setNote("");
    } catch {
      setNote("Agent API unreachable");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const active = runs.some((r) => r.status === "queued" || r.status === "running");
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(id);
  }, [active, load]);

  async function onRun(pipelineId: string) {
    setBusy(true);
    try {
      const res = await fetch(`${API}/pipelines/${pipelineId}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          environment: env,
          repository_id: repositoryId.trim() || null,
          sidecar_only: false,
          triggered_by: reviewer || "anonymous",
        }),
      });
      if (res.status === 202) {
        const body = (await res.json()) as { run_id: string };
        setNote(`Started ${body.run_id}`);
        await load();
      } else {
        const text = await res.text();
        setNote(`HTTP ${res.status}: ${text.slice(0, 200)}`);
      }
    } catch (err) {
      setNote(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openRun(runId: string) {
    try {
      const res = await fetch(`${API}/pipelines/runs/${runId}`);
      if (res.ok) setInspect((await res.json()) as RunRow);
    } catch {
      setNote("Failed to load run detail");
    }
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-hidden">
      <p className="text-xs text-text-secondary shrink-0">
        Knowledge pipelines control plane (ADR-033). Phase 1: OpenAPI → ApiIndex only.
        {note ? ` — ${note}` : ""}
      </p>

      <div className="flex flex-wrap gap-2 items-end text-xs shrink-0">
        <label className="flex flex-col gap-1 text-text-secondary">
          Environment
          <select
            className="bg-surface-0 border border-surface-3 rounded px-2 py-1 text-text-primary"
            value={env}
            onChange={(e) => setEnv(e.target.value)}
          >
            {["local", "dev", "stage", "prod"].map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-text-secondary">
          Repository id (optional)
          <input
            type="text"
            value={repositoryId}
            placeholder="leave empty = all"
            className="w-40 bg-surface-0 border border-surface-3 rounded px-2 py-1 text-text-primary"
            onChange={(e) => setRepositoryId(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="text-xs text-text-secondary underline"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 shrink-0">
        {catalog.map((p) => {
          const last = p.last_run;
          const status = String(last?.status ?? "never");
          const ops = (last?.report as { operations?: number } | undefined)?.operations;
          return (
            <div
              key={p.pipeline_id}
              className="rounded border border-surface-3 bg-surface-1 p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="text-sm font-medium truncate">{p.title}</h3>
                  <p className="text-[11px] text-text-muted font-mono">{p.pipeline_id}</p>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full border border-surface-3 text-text-secondary shrink-0">
                  {status}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary line-clamp-2">{p.description}</p>
              <p className="text-[11px] text-text-muted">
                Last finished: {String(last?.finished_at ?? "—")}
                {ops != null ? ` · ops ${ops}` : ""}
              </p>
              <button
                type="button"
                disabled={busy}
                className="text-xs px-3 py-1.5 rounded border border-brand-500 text-brand-300 bg-brand-500/10 disabled:opacity-50"
                onClick={() => void onRun(p.pipeline_id)}
              >
                Run
              </button>
            </div>
          );
        })}
        {catalog.length === 0 && (
          <p className="text-sm text-text-muted">No pipelines in catalog.</p>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-auto rounded border border-surface-3 bg-surface-1">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-surface-1 text-left text-text-muted">
            <tr>
              <th className="px-3 py-2">Run</th>
              <th>Pipeline</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Finished</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr
                key={String(r.run_id)}
                className="border-t border-surface-3 hover:bg-surface-2 cursor-pointer"
                onClick={() => void openRun(String(r.run_id))}
              >
                <td className="px-3 py-1.5 font-mono">{String(r.run_id)}</td>
                <td>{String(r.pipeline_id ?? "")}</td>
                <td>{String(r.status ?? "")}</td>
                <td className="font-mono">
                  {r.duration_ms != null ? `${Number(r.duration_ms).toFixed(0)}ms` : "—"}
                </td>
                <td>{String(r.finished_at ?? "—")}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-text-muted">
                  No runs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {inspect && (
        <div className="fixed inset-y-0 right-0 w-full max-w-lg z-[60] border-l border-surface-3 bg-surface-0 shadow-xl flex flex-col">
          <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-surface-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold truncate">{String(inspect.run_id)}</h2>
              <p className="text-[11px] text-text-muted">
                {String(inspect.pipeline_id)} · {String(inspect.status)}
              </p>
            </div>
            <button
              type="button"
              className="text-sm text-text-secondary underline"
              onClick={() => setInspect(null)}
            >
              Close
            </button>
          </header>
          <div className="flex-1 overflow-auto p-4 space-y-3 text-xs">
            {inspect.error ? (
              <p className="text-red-300">Error: {String(inspect.error)}</p>
            ) : null}
            <div>
              <h3 className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Report</h3>
              <pre className="bg-surface-1 border border-surface-3 rounded p-2 overflow-auto max-h-64 whitespace-pre-wrap">
                {JSON.stringify(inspect.report ?? {}, null, 2)}
              </pre>
            </div>
            <div>
              <h3 className="text-[10px] uppercase tracking-wider text-text-muted mb-1">
                Log tail
              </h3>
              <pre className="bg-surface-1 border border-surface-3 rounded p-2 overflow-auto max-h-80 whitespace-pre-wrap font-mono">
                {(inspect.logs ?? []).join("\n") || "(empty)"}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
