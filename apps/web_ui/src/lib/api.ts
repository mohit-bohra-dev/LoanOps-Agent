import type { LoanSummary } from "../types";

export const TOOLS_API_TOKEN = "dev-token";

export async function lookupLoan(loanId: string): Promise<LoanSummary> {
  const res = await fetch("/tools/lookup_loan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOOLS_API_TOKEN}`,
    },
    body: JSON.stringify({ loan_id: loanId }),
  });

  if (!res.ok) {
    throw new Error(`Failed to lookup loan: ${res.statusText}`);
  }
  return res.json();
}
