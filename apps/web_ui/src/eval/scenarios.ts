/**
 * Shared scenario board for multi-user isolated testing.
 * Keep in sync with docs/query-checklist.md / docs/test-queries.txt.
 */

export type ScenarioPhase = "one_tool" | "chain" | "gap";
export type ScenarioStatus = "open" | "ok" | "partial";

export type TestScenario = {
  id: string;
  phase: ScenarioPhase;
  title: string;
  query: string;
  expectTools: string;
  ownerHint: string;
  status: ScenarioStatus;
  note?: string;
};

export const TEST_SCENARIOS: TestScenario[] = [
  {
    id: "S3",
    phase: "one_tool",
    title: "ApiIndex search only",
    query: "Which API returns the payment schedule for a loan? Don't call it.",
    expectTools: "search_sse_apis only",
    ownerHint: "retrieval",
    status: "open",
  },
  {
    id: "S4",
    phase: "one_tool",
    title: "Catalog listing (Fees)",
    query: "List the operations available in the Fees app.",
    expectTools: "list_sse_apis",
    ownerHint: "catalog",
    status: "open",
  },
  {
    id: "S5",
    phase: "one_tool",
    title: "EAKG capabilities",
    query: "Which application provides escrow disbursement capabilities?",
    expectTools: "search_sse_apis or search_capabilities",
    ownerHint: "eakg",
    status: "open",
  },
  {
    id: "S7",
    phase: "one_tool",
    title: "Escrow interface surface",
    query: "Which SDK packages and event topics does escrow use?",
    expectTools: "describe_application (escrow)",
    ownerHint: "eakg",
    status: "open",
  },
  {
    id: "S8",
    phase: "one_tool",
    title: "SOP — escrow dispute",
    query: "What is the procedure for an escrow dispute?",
    expectTools: "search_docs → escrow/escrow-dispute.md",
    ownerHint: "docs",
    status: "open",
  },
  {
    id: "S9",
    phase: "one_tool",
    title: "SOP — California late fees",
    query: "What does the California policy say about late fees?",
    expectTools: "search_docs → state-specific/california-policy.md",
    ownerHint: "docs",
    status: "partial",
    note: "Wrong hit previously (disaster forbearance).",
  },
  {
    id: "S10",
    phase: "one_tool",
    title: "SOP — military SCRA",
    query: "What forbearance options exist for military borrowers (SCRA)?",
    expectTools: "search_docs → hardship/military-scra.md",
    ownerHint: "docs",
    status: "open",
  },
  {
    id: "Q8",
    phase: "one_tool",
    title: "Facades via AST",
    query: "Does loanservices use any Facades? List them.",
    expectTools: "search_code",
    ownerHint: "eakg",
    status: "partial",
    note: "Needs EAKG__ENGINEERING_GRAPH onboard.",
  },
  {
    id: "S1",
    phase: "chain",
    title: "Live loan summary",
    query: "Show me the loan summary for 1000002245",
    expectTools: "search_sse_apis → call_sse_api",
    ownerHint: "sse",
    status: "open",
  },
  {
    id: "S2",
    phase: "chain",
    title: "Live escrow details",
    query: "Get escrow details for loan 1000002245",
    expectTools: "search_sse_apis → call_sse_api GetEscrowByLoanNumber",
    ownerHint: "sse",
    status: "ok",
  },
  {
    id: "S11",
    phase: "chain",
    title: "Escrow live + annual analysis SOP",
    query:
      "Loan 1000002245 escrow jumped. Pull the escrow record and explain what the annual analysis SOP says.",
    expectTools: "call_sse_api + search_docs",
    ownerHint: "combo",
    status: "open",
  },
  {
    id: "S12",
    phase: "chain",
    title: "Proxies + disbursement SOP",
    query:
      "Which apps does loanservices call outbound, and is there an SOP for escrow disbursements?",
    expectTools: "describe_application + search_docs",
    ownerHint: "combo",
    status: "open",
  },
  {
    id: "gap-process",
    phase: "gap",
    title: "Process KG (not wired)",
    query: "What must happen before escrow analysis?",
    expectTools: "none — process edges not exposed",
    ownerHint: "gap",
    status: "open",
    note: "Expect weak/wrong until process tool exists.",
  },
];

export const REVIEWER_STORAGE_KEY = "loanops.eval.reviewer";

export function loadReviewerName(): string {
  try {
    return localStorage.getItem(REVIEWER_STORAGE_KEY)?.trim() || "";
  } catch {
    return "";
  }
}

export function saveReviewerName(name: string): void {
  try {
    localStorage.setItem(REVIEWER_STORAGE_KEY, name.trim());
  } catch {
    /* ignore */
  }
}
