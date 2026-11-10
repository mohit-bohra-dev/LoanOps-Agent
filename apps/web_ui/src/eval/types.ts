export type OutcomeStatus = "good" | "bad" | "needs_review";
export type Severity = "blocker" | "major" | "minor";
export type Department = "Engineering" | "QA" | "Product" | "Operations" | "Compliance";

export type FailureCategory =
  | "wrong_api_selected"
  | "missing_api"
  | "incorrect_arguments"
  | "missing_policy_context"
  | "incorrect_answer"
  | "unauthorized_access"
  | "unnecessary_tool_calls"
  | "hallucination"
  | "sop_violation"
  | "tool_error_unhandled"
  | "other";

export type RecommendedAction =
  | "add_mcp_tool"
  | "remove_redundant_tool"
  | "improve_tool_schema"
  | "fix_retrieval_gap"
  | "improve_prompt"
  | "update_sop";

export type HighlightKind = "hallucinated" | "incorrect" | "incomplete" | "irrelevant";

export interface EvalCitation {
  id: number;
  source: string;
  snippet: string;
}

export type SpanKind = "turn" | "llm" | "tool" | "subtool" | "safety" | "validator";

export interface EvalSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  kind?: SpanKind;
  tool?: string | null;
  args?: Record<string, unknown>;
  result?: string | null;
  result_summary?: string | null;
  start_offset_ms?: number;
  latency_ms?: number;
  is_error?: boolean;
  error_message?: string | null;
  attributes?: Record<string, unknown>;
  token_usage?: Record<string, number>;
  model?: string | null;
}

export interface PipelineHits {
  eakg: Record<string, unknown>[];
  api_index: Record<string, unknown>[];
  docs: Record<string, unknown>[];
  graph_rag: Record<string, unknown>[];
  code: Record<string, unknown>[];
}

export interface EvalMatrixRow {
  id: string;
  trace_id: string;
  user_query: string;
  final_answer: string;
  citations: EvalCitation[];
  spans: EvalSpan[];
  latency_ms: number;
  token_usage: Record<string, number>;
  pipeline_hits?: PipelineHits;
  model?: string | null;
  rounds_used?: number;
  validation_retries?: number;
  confidence?: number | null;
  status?: string | null;
  model_critique: string | null;
  model_outcome: OutcomeStatus | null;
  human_critique: string | null;
  human_outcome: OutcomeStatus | null;
  alignment: number | null;
  primary_category: FailureCategory | null;
  severity: Severity | null;
  root_component: string | null;
  department: Department | null;
  recommended_action: RecommendedAction | null;
  suggested_answer: string | null;
  flags: string[];
  span_refs: string[];
  reviewer: string | null;
  promoted_draft: boolean;
  agent_version: string;
  mcp_version: string;
  loan_id: string | null;
  demo?: boolean;
}

export interface EvalInsightsSummary {
  agreementRate: number;
  totalReviewed: number;
  goodCount: number;
  badCount: number;
  needsReviewCount: number;
  disagreeCount: number;
  topCategories: { category: string; count: number }[];
  byDepartment: { department: string; reviewed: number; agreement: number }[];
}

export interface MatrixApiResponse {
  rows: EvalMatrixRow[];
  agreement_rate: number;
  total_reviewed: number;
}

export const FAILURE_CATEGORY_LABELS: Record<FailureCategory, string> = {
  wrong_api_selected: "Wrong API selected",
  missing_api: "Missing API",
  incorrect_arguments: "Incorrect arguments",
  missing_policy_context: "Missing policy context",
  incorrect_answer: "Incorrect answer",
  unauthorized_access: "Unauthorized access",
  unnecessary_tool_calls: "Unnecessary tool calls",
  hallucination: "Hallucination",
  sop_violation: "SOP violation",
  tool_error_unhandled: "Unhandled tool error",
  other: "Other",
};

export const ACTION_LABELS: Record<RecommendedAction, string> = {
  add_mcp_tool: "Add missing MCP tool",
  remove_redundant_tool: "Remove redundant tool",
  improve_tool_schema: "Improve tool schema/description",
  fix_retrieval_gap: "Fix retrieval/knowledge gap",
  improve_prompt: "Improve agent prompt/orchestration",
  update_sop: "Update SOP/business rule",
};

export function outcomeFromHumanLabel(label: OutcomeStatus): string {
  if (label === "good") return "pass";
  if (label === "bad") return "fail";
  return "needs_review";
}

export function computeAlignment(
  model: OutcomeStatus | null,
  human: OutcomeStatus | null,
): number | null {
  if (!model || !human) return null;
  if (model === "needs_review" || human === "needs_review") return null;
  return model === human ? 1 : 0;
}

export function summarizeInsights(rows: EvalMatrixRow[]): EvalInsightsSummary {
  let good = 0;
  let bad = 0;
  let needs = 0;
  let disagree = 0;
  let aligned = 0;
  let compared = 0;
  const cats = new Map<string, number>();
  const dept = new Map<string, { reviewed: number; aligned: number; compared: number }>();

  for (const r of rows) {
    const outcome = r.human_outcome ?? r.model_outcome;
    if (outcome === "good") good += 1;
    else if (outcome === "bad") bad += 1;
    else if (outcome === "needs_review") needs += 1;

    if (r.alignment === 0) disagree += 1;
    if (r.alignment === 0 || r.alignment === 1) {
      compared += 1;
      aligned += r.alignment;
    }
    if (r.primary_category) {
      cats.set(r.primary_category, (cats.get(r.primary_category) ?? 0) + 1);
    }
    if (r.department && r.human_outcome) {
      const d = dept.get(r.department) ?? { reviewed: 0, aligned: 0, compared: 0 };
      d.reviewed += 1;
      if (r.alignment === 0 || r.alignment === 1) {
        d.compared += 1;
        d.aligned += r.alignment;
      }
      dept.set(r.department, d);
    }
  }

  return {
    agreementRate: compared ? aligned / compared : 0,
    totalReviewed: compared,
    goodCount: good,
    badCount: bad,
    needsReviewCount: needs,
    disagreeCount: disagree,
    topCategories: [...cats.entries()]
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5),
    byDepartment: [...dept.entries()].map(([department, v]) => ({
      department,
      reviewed: v.reviewed,
      agreement: v.compared ? v.aligned / v.compared : 0,
    })),
  };
}
