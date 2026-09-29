import type { LoanSummary } from "../types";

type McpCallResponse = {
  success: boolean;
  data?: { text?: string };
  error?: string | null;
};

type SseInvokePayload = {
  ok?: boolean;
  status?: number;
  data?: Record<string, unknown> | null;
  error?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function pickString(obj: Record<string, unknown>, keys: string[], fallback = "—"): string {
  for (const key of keys) {
    const v = obj[key];
    if (v === null || v === undefined || v === "") continue;
    return String(v);
  }
  return fallback;
}

function pickNumber(obj: Record<string, unknown>, keys: string[], fallback = 0): number {
  for (const key of keys) {
    const v = obj[key];
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  }
  return fallback;
}

function pickBool(obj: Record<string, unknown>, keys: string[], fallback = false): boolean {
  for (const key of keys) {
    const v = obj[key];
    if (typeof v === "boolean") return v;
  }
  return fallback;
}

async function callSseApi(
  operationId: string,
  loanId: string,
): Promise<Record<string, unknown>> {
  const res = await fetch("/api/mcp/tools/call", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "call_sse_api",
      arguments: {
        operation_id: operationId,
        path_params: { loan_id: loanId },
      },
    }),
  });
  if (!res.ok) {
    throw new Error(`SSE tool call failed: ${res.status} ${res.statusText}`);
  }
  const mcp = (await res.json()) as McpCallResponse;
  if (!mcp.success) {
    throw new Error(mcp.error || "SSE tool call unsuccessful");
  }
  const text = mcp.data?.text;
  if (!text) {
    throw new Error("Empty SSE tool response");
  }
  let payload: SseInvokePayload;
  try {
    payload = JSON.parse(text) as SseInvokePayload;
  } catch {
    throw new Error("SSE tool returned non-JSON payload");
  }
  if (!payload.ok || payload.status !== 200) {
    throw new Error(
      `Live Loan Services ${payload.status ?? "error"}: ${payload.error || "request failed"}`,
    );
  }
  return asRecord(payload.data);
}

/** Map live Loan Services payloads into the sidebar LoanSummary shape. */
function toLoanSummary(
  loanId: string,
  summary: Record<string, unknown>,
  borrower: Record<string, unknown>,
): LoanSummary {
  const first = pickString(
    borrower,
    ["BorrowerFirstName", "FirstName", "first_name", "borrower_first_name"],
    pickString(summary, ["BorrowerFirstName", "FirstName"], "Borrower"),
  );
  const active = pickBool(summary, ["LoanActiveFlag", "loan_active"], true);
  return {
    loan_id: pickString(summary, ["LoanId", "loan_id"], loanId),
    borrower_first_name: first,
    state: pickString(summary, ["PropertyState", "State", "state"], "—"),
    status: active ? "active" : "inactive",
    product: pickString(summary, ["ProductType", "Product", "product"], "—"),
    escrowed: pickNumber(summary, ["PendingEscrowPaymentAmount", "MonthlyEscrowAmount"], 0) > 0,
    current_balance_usd: pickNumber(
      summary,
      ["CurrentPrincipalBalance", "UnpaidPrincipalBalance", "current_balance_usd"],
      pickNumber(summary, ["CurrentTotalMonthlyPaymentAmount"], 0),
    ),
    next_due_date: pickString(
      summary,
      ["NextPaymentDueDate", "InterestPaidThroughDate", "next_due_date"],
      "",
    ) || null,
    delinquency_days: pickNumber(summary, ["DaysDelinquent", "delinquency_days"], 0),
    flags: active ? [] : ["inactive"],
  };
}

/** Loan lookup via Agent MCP → live SSE OpenAPI (no tools_api). */
export async function lookupLoan(loanId: string): Promise<LoanSummary> {
  const summary = await callSseApi("getLoanSummary", loanId);
  let borrower: Record<string, unknown> = {};
  try {
    borrower = await callSseApi("getBorrowerSummary", loanId);
  } catch {
    // Borrower endpoint optional for sidebar display.
  }
  return toLoanSummary(loanId, summary, borrower);
}
