import { Bot, User, Check, AlertTriangle, ShieldAlert, FileText } from "lucide-react";
import type { AgentTurnOutput } from "../types";
import { AgentSteps } from "./AgentSteps";

interface ChatMessageProps {
  role: "user" | "agent" | "error";
  text?: string;
  output?: AgentTurnOutput;
}

export function ChatMessage({ role, text, output }: ChatMessageProps) {
  const isAgent = role === "agent";
  const isError = role === "error";

  return (
    <div className={`py-6 flex gap-4 ${isAgent ? "bg-surface-0" : "bg-surface-1"}`}>
      <div className="flex-shrink-0 ml-4">
        {isAgent ? (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 border border-brand-500/30">
            <Bot className="h-5 w-5" />
          </div>
        ) : isError ? (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-danger/20 text-danger border border-danger/30">
            <AlertTriangle className="h-5 w-5" />
          </div>
        ) : (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-peach-500/20 text-peach-300 border border-peach-500/30">
            <User className="h-5 w-5" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0 pr-4">
        <div className="prose prose-invert max-w-none text-text-primary text-sm leading-relaxed">
          {/* Main message text */}
          <div className="whitespace-pre-wrap">{text || output?.answer}</div>

          {/* Error display */}
          {isError && (
            <div className="mt-2 text-danger font-medium text-sm">
              An error occurred while generating the response.
            </div>
          )}

          {/* Agent specific formatting */}
          {isAgent && output && (
            <div className="mt-4 space-y-4">
            
              {/* Agent Steps Timeline */}
              <AgentSteps toolCalls={output.tool_calls} />

              {/* Citations */}
              {output.citations.length > 0 && (
                <div className="bg-surface-2 rounded-md border border-surface-3 p-3 space-y-2 mt-2">
                  <p className="text-xs font-medium text-text-secondary flex items-center gap-1.5 uppercase tracking-wide">
                    <FileText className="h-3 w-3" /> Citations
                  </p>
                  <div className="space-y-2">
                    {output.citations.map((cit) => (
                      <div key={cit.id} className="text-xs bg-surface-3 p-2 rounded border border-surface-4">
                        <span className="text-brand-400 font-mono mr-2">[{cit.id}]</span>
                        <span className="text-text-muted">{cit.source}</span>
                        <p className="mt-1 text-text-secondary italic border-l-2 border-surface-4 pl-2 ml-1">
                          "{cit.snippet}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Escalation */}
              {output.escalation && (
                <div className="bg-warning/10 rounded-md border border-warning/30 p-3 mt-2 flex items-start gap-3">
                  <ShieldAlert className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-warning uppercase">Escalation Required: {output.escalation.category.replace(/_/g, " ")}</p>
                    <p className="text-sm text-warning/80 mt-1">{output.escalation.reason}</p>
                  </div>
                </div>
              )}

              {/* Refusal */}
              {output.refusal && (
                <div className="bg-danger/10 rounded-md border border-danger/30 p-3 mt-2 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-danger flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-danger uppercase">Request Refused</p>
                    <p className="text-sm text-danger/80 mt-1">{output.refusal}</p>
                  </div>
                </div>
              )}

              {/* Footer: Confidence & Actions */}
              <div className="flex items-center justify-between pt-2 border-t border-surface-3 mt-4">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className={`inline-block h-2 w-2 rounded-full ${output.confidence > 0.8 ? "bg-success" : "bg-warning"}`} />
                  Confidence: {Math.round(output.confidence * 100)}%
                </div>

                {!output.escalation && !output.refusal && (
                  <button
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-500/20 text-brand-300 hover:bg-brand-500/30 transition-colors rounded text-xs font-medium"
                    onClick={() => navigator.clipboard.writeText(output.answer)}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Approve & Copy
                  </button>
                )}
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
