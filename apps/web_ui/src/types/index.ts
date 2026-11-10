export interface CitationItem {
  id: number;
  source: string;
  snippet: string;
}

export interface ToolCallItem {
  name: string;
  args: Record<string, unknown>;
  result_summary: string;
  latency_ms?: number;
  is_error?: boolean;
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
