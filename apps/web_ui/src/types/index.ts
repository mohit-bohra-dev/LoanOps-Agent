export interface LoanSummary {
  loan_id: string;
  borrower_first_name: string;
  state: string;
  status: string;
  product: string;
  escrowed: boolean;
  current_balance_usd: number;
  next_due_date: string | null;
  delinquency_days: number;
  flags: string[];
}

export interface CitationItem {
  id: number;
  source: string;
  snippet: string;
}

export interface ToolCallItem {
  name: string;
  args: Record<string, unknown>;
  result_summary: string;
}

export interface EscalationItem {
  category: "safety" | "complaint_or_regulatory" | "legal_status" | "fraud" | "identity";
  reason: string;
}

export interface AgentTurnOutput {
  answer: string;
  citations: CitationItem[];
  tool_calls: ToolCallItem[];
  requires_human_approval: boolean;
  confidence: number;
  refusal: string | null;
  escalation: EscalationItem | null;
}
