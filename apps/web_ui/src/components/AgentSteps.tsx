import { useState } from "react";
import { 
  ChevronDown, 
  ChevronRight, 
  Search, 
  User, 
  Calendar, 
  DollarSign, 
  ShieldCheck, 
  FileText, 
  Wrench 
} from "lucide-react";
import type { ToolCallItem } from "../types";

interface AgentStepsProps {
  toolCalls: ToolCallItem[];
}

export function AgentSteps({ toolCalls }: AgentStepsProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="my-4 rounded-lg border border-surface-3 bg-surface-1/50 overflow-hidden">
      <div className="bg-surface-2 px-4 py-2 border-b border-surface-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Agent Steps
        </span>
      </div>
      
      <div className="p-4 space-y-4">
        {toolCalls.map((tool, index) => (
          <AgentStepItem key={index} tool={tool} index={index} />
        ))}
      </div>
      
      <div className="bg-surface-2/50 px-4 py-2 border-t border-surface-3 text-xs text-text-muted flex justify-between">
        <span>{toolCalls.length} step{toolCalls.length !== 1 ? 's' : ''} taken</span>
        <span>~{(toolCalls.length * 0.4).toFixed(1)}s</span>
      </div>
    </div>
  );
}

function AgentStepItem({ tool, index }: { tool: ToolCallItem; index: number }) {
  const [expanded, setExpanded] = useState(false);

  // Map tool names to human-readable labels and icons
  let label = "Called tool";
  let Icon = Wrench;
  let iconColor = "text-brand-400";

  switch (tool.name) {
    case "lookup_loan":
      label = "Looked up loan details";
      Icon = Search;
      iconColor = "text-blue-400";
      break;
    case "search_borrower":
      label = "Searched by borrower name";
      Icon = User;
      iconColor = "text-indigo-400";
      break;
    case "get_payment_schedule":
      label = "Retrieved payment schedule";
      Icon = Calendar;
      iconColor = "text-emerald-400";
      break;
    case "get_escrow_breakdown":
      label = "Checked escrow breakdown";
      Icon = DollarSign;
      iconColor = "text-amber-400";
      break;
    case "check_hardship_eligibility":
      label = "Checked hardship eligibility";
      Icon = ShieldCheck;
      iconColor = "text-rose-400";
      break;
    case "search_policy":
      label = "Searched policy documents";
      Icon = FileText;
      iconColor = "text-purple-400";
      break;
  }

  // Format arguments concisely for the summary row
  const formatArgsSummary = (args: Record<string, unknown>) => {
    if (!args || Object.keys(args).length === 0) return "no arguments";
    return Object.entries(args)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
      .join(", ");
  };

  return (
    <div 
      className="flex gap-3 animate-step-in"
      style={{ animationDelay: `${index * 80}ms`, animationFillMode: 'both' }}
    >
      {/* Number Badge */}
      <div className="flex flex-col items-center mt-0.5">
        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-3 text-[10px] font-bold text-text-secondary ring-2 ring-surface-1">
          {index + 1}
        </div>
        {/* Connector line (hide on last item via CSS if we wanted, but we'll keep it simple here) */}
      </div>

      <div className="flex-1 min-w-0 pb-1">
        {/* Header Row */}
        <div 
          className="flex items-center gap-2 cursor-pointer select-none group"
          onClick={() => setExpanded(!expanded)}
        >
          <Icon className={`h-4 w-4 ${iconColor}`} />
          <span className="text-sm font-medium text-text-primary group-hover:text-brand-300 transition-colors">
            {label}
          </span>
          {expanded ? (
            <ChevronDown className="h-3 w-3 text-text-muted ml-auto" />
          ) : (
            <ChevronRight className="h-3 w-3 text-text-muted ml-auto" />
          )}
        </div>

        {/* Concise Summary (visible when collapsed or expanded) */}
        <div className="mt-1 space-y-1">
          <div className="text-xs font-mono text-text-muted truncate">
            {formatArgsSummary(tool.args)}
          </div>
          <div className="text-xs text-text-secondary flex gap-1.5 items-start">
            <span className="text-brand-500 font-bold">→</span>
            <span className="line-clamp-2">{tool.result_summary}</span>
          </div>
        </div>

        {/* Expanded Raw JSON */}
        {expanded && (
          <div className="mt-3 space-y-2">
            <div className="rounded border border-surface-3 bg-surface-0 p-2 overflow-x-auto">
              <span className="text-[10px] uppercase tracking-wider text-text-muted block mb-1">Complete JSON</span>
              <pre className="text-[11px] font-mono text-brand-200">
                {JSON.stringify(tool, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
