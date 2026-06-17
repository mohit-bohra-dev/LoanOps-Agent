import { useState } from "react";
import { Search, User, Home, AlertCircle } from "lucide-react";
import type { LoanSummary } from "../types";
import { lookupLoan } from "../lib/api";

export function BorrowerContextPane({ onLoanLoaded }: { onLoanLoaded?: (id: string) => void }) {
  const [loanId, setLoanId] = useState("100245");
  const [loan, setLoan] = useState<LoanSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loanId.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await lookupLoan(loanId.trim());
      setLoan(data);
      onLoanLoaded?.(data.loan_id);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
      setLoan(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full w-80 flex-col border-r border-surface-3 bg-surface-1">
      <div className="p-4 border-b border-surface-3">
        <h2 className="text-sm font-semibold tracking-wide text-text-secondary uppercase mb-4">
          Borrower Context
        </h2>
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={loanId}
            onChange={(e) => setLoanId(e.target.value)}
            placeholder="Enter Loan ID..."
            className="w-full bg-surface-2 border border-surface-4 rounded-md py-2 pl-9 pr-4 text-sm text-text-primary focus:outline-none focus:border-brand-500 transition-colors"
          />
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
          <button type="submit" className="hidden">Search</button>
        </form>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex justify-center p-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-danger p-4 bg-danger/10 rounded-md text-sm">
            <AlertCircle className="h-4 w-4" />
            <p>{error}</p>
          </div>
        )}

        {loan && !loading && (
          <div className="space-y-6 animate-fade-in">
            {/* Header section */}
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-peach-500/20 text-peach-300">
                <User className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-medium text-text-primary">{loan.borrower_first_name}</h3>
                <p className="text-xs text-text-muted">Loan {loan.loan_id}</p>
              </div>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-2 p-3 rounded-md border border-surface-3">
                <p className="text-xs text-text-muted mb-1">State</p>
                <p className="font-medium">{loan.state}</p>
              </div>
              <div className="bg-surface-2 p-3 rounded-md border border-surface-3">
                <p className="text-xs text-text-muted mb-1">Status</p>
                <p className="font-medium capitalize">{loan.status.replace(/_/g, " ")}</p>
              </div>
              <div className="bg-surface-2 p-3 rounded-md border border-surface-3 col-span-2">
                <p className="text-xs text-text-muted mb-1">Current Balance</p>
                <p className="font-medium text-lg">
                  ${loan.current_balance_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>

            {/* Additional Info */}
            <div className="space-y-3 pt-2 border-t border-surface-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-muted">Product</span>
                <span>{loan.product}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-muted">Escrowed</span>
                <span>{loan.escrowed ? "Yes" : "No"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-muted">Next Due</span>
                <span>{loan.next_due_date || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-text-muted">Delinquency</span>
                <span className={loan.delinquency_days > 0 ? "text-warning" : "text-success"}>
                  {loan.delinquency_days} days
                </span>
              </div>
            </div>

            {/* Flags */}
            {loan.flags.length > 0 && (
              <div className="pt-2 border-t border-surface-3">
                <p className="text-xs text-text-muted mb-2">Flags</p>
                <div className="flex flex-wrap gap-2">
                  {loan.flags.map((flag) => (
                    <span
                      key={flag}
                      className="px-2 py-1 bg-surface-3 text-xs rounded text-text-secondary"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!loan && !loading && !error && (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 text-text-muted">
            <Home className="h-8 w-8 mb-3 opacity-50" />
            <p className="text-sm">Search for a loan to view borrower context</p>
          </div>
        )}
      </div>
    </div>
  );
}
