export interface MemoryMessage {
  role: string;
  content: string;
  is_active: boolean;
  token_count: number;
}

export interface ChatMemoryResponse {
  session_id: string;
  total_messages: number;
  active_messages: number;
  max_history_tokens: number;
  current_prompt_tokens: number;
  messages: MemoryMessage[];
}
