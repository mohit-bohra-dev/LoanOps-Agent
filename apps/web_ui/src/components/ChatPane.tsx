import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Plus, Brain } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import type { AgentTurnOutput } from "../types";
import type { ChatMemoryResponse } from "../types/memory";

interface Message {
  id: string;
  role: "user" | "agent" | "error";
  text?: string;
  output?: AgentTurnOutput;
}

export function ChatPane({ activeLoanId }: { activeLoanId?: string }) {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "agent",
      text: "Hello. I am the Servicing Agent. How can I assist you with this borrower today?",
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showMemoryViewer, setShowMemoryViewer] = useState(false);
  const [memoryData, setMemoryData] = useState<ChatMemoryResponse | null>(null);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchMemoryData = async () => {
    if (!sessionId) return;

    setMemoryLoading(true);
    try {
      const res = await fetch(`/api/chat/memory/${sessionId}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch memory data: ${res.statusText}`);
      }
      const data: ChatMemoryResponse = await res.json();
      setMemoryData(data);
    } catch (err) {
      console.error("Error fetching memory data:", err);
    } finally {
      setMemoryLoading(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    let active = true;
    if (showMemoryViewer && sessionId) {
      setMemoryLoading(true);
      fetch(`/api/chat/memory/${sessionId}`)
        .then((res) => {
          if (!res.ok) throw new Error(res.statusText);
          return res.json();
        })
        .then((data: ChatMemoryResponse) => {
          if (active) setMemoryData(data);
        })
        .catch((err) => {
          if (active) console.error("Error fetching memory data:", err);
        })
        .finally(() => {
          if (active) setMemoryLoading(false);
        });
    }
    return () => { active = false; };
  }, [showMemoryViewer, sessionId]);

  const handleNewConversation = () => {
    setSessionId(crypto.randomUUID());
    setMessages([
      {
        id: "init",
        role: "agent",
        text: "Hello. I am the Servicing Agent. How can I assist you with this borrower today?",
      }
    ]);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");

    // Add user message
    const userMsgId = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", text: userText }
    ]);

    setLoading(true);

    try {
      // Create a POST request to /api/chat with SSE
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userText,
          session_id: sessionId,
          rep_id: "rep-456",
          loan_id: activeLoanId,
        }),
      });

      if (!res.ok) {
        throw new Error(`API Error: ${res.statusText}`);
      }

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let agentOutput: AgentTurnOutput | null = null;
      let errorOccurred = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.replace("data: ", "").trim();
              if (!dataStr) continue;
              try {
                const data = JSON.parse(dataStr);
                if (data.error) {
                  errorOccurred = true;
                  setMessages((prev) => [
                    ...prev,
                    { id: Date.now().toString(), role: "error", text: data.error }
                  ]);
                } else {
                  agentOutput = data as AgentTurnOutput;
                }
              } catch {
                console.error("Failed to parse SSE data:", dataStr);
              }
            }
          }
        }
      }

      if (agentOutput) {
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), role: "agent", output: agentOutput! }
        ]);
      } else if (!errorOccurred) {
        throw new Error("No valid agent output received.");
      }

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "error", text: errorMessage }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col h-full bg-surface-0">
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b border-surface-3 px-6 bg-surface-1">
        <h2 className="text-sm font-semibold tracking-wide text-text-secondary uppercase">
          Conversation
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowMemoryViewer(true)}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-3 hover:text-text-primary transition-colors"
          >
            <Brain className="h-4 w-4" />
            Memory
          </button>
          <button
            onClick={handleNewConversation}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-3 hover:text-text-primary transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto divide-y divide-surface-2/50">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} role={msg.role} text={msg.text} output={msg.output} />
          ))}
          {loading && (
            <div className="py-6 flex gap-4 bg-surface-0">
              <div className="flex-shrink-0 ml-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 border border-brand-500/30">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
              <div className="flex items-center text-sm text-text-muted italic">
                Agent is typing...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-surface-1 border-t border-surface-3">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the servicing agent..."
              disabled={loading}
              className="w-full bg-surface-2 border border-surface-4 rounded-lg py-3 pl-4 pr-12 text-sm text-text-primary focus:outline-none focus:border-brand-500 transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="absolute right-2 p-1.5 rounded-md bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 disabled:hover:bg-brand-500 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-2 text-center text-[10px] text-text-muted">
            Servicing Agent can make mistakes. Verify important information.
          </div>
        </div>
      </div>
          {/* Memory Viewer Modal */}
      {showMemoryViewer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-surface-1 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-surface-3 px-6 py-4">
              <h3 className="text-lg font-semibold text-text-primary">🧠 Memory Viewer</h3>
              <button
                onClick={() => setShowMemoryViewer(false)}
                className="rounded-md p-1 text-text-secondary hover:bg-surface-3 hover:text-text-primary"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {memoryLoading ? (
                <div className="flex h-32 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
                </div>
              ) : memoryData ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-surface-2 p-3 rounded-md">
                      <p className="text-xs text-text-secondary">Session ID</p>
                      <p className="text-sm font-mono truncate">{memoryData.session_id.substring(0, 8)}...</p>
                    </div>
                    <div className="bg-surface-2 p-3 rounded-md">
                      <p className="text-xs text-text-secondary">Total Messages</p>
                      <p className="text-lg font-semibold">{memoryData.total_messages}</p>
                    </div>
                    <div className="bg-surface-2 p-3 rounded-md">
                      <p className="text-xs text-text-secondary">Active Messages</p>
                      <p className="text-lg font-semibold text-green-600">{memoryData.active_messages}</p>
                    </div>
                    <div className="bg-surface-2 p-3 rounded-md">
                      <p className="text-xs text-text-secondary">Token Budget</p>
                      <p className="text-lg font-semibold">{memoryData.max_history_tokens}</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold mb-3 text-text-primary">Message History</h4>
                    <div className="space-y-3">
                      {memoryData.messages.map((msg, index) => (
                        <div
                          key={index}
                          className={`border rounded-md p-3 ${
                            msg.is_active
                              ? "border-green-500/30 bg-green-500/5"
                              : "border-gray-300 bg-gray-100 opacity-70"
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                              msg.role === "user"
                                ? "bg-blue-100 text-blue-800"
                                : msg.role === "assistant"
                                  ? "bg-purple-100 text-purple-800"
                                  : "bg-gray-100 text-gray-800"
                            }`}>
                              {msg.role}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-text-secondary">
                                {msg.token_count} tokens
                              </span>
                              {!msg.is_active && (
                                <span className="inline-flex items-center rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                                  Dropped
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="mt-2 text-sm text-text-primary whitespace-pre-wrap">
                            {msg.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-text-secondary">No memory data available</p>
                </div>
              )}
            </div>

            <div className="border-t border-surface-3 px-6 py-4 flex justify-end">
              <button
                onClick={fetchMemoryData}
                disabled={memoryLoading}
                className="flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {memoryLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                Refresh
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
