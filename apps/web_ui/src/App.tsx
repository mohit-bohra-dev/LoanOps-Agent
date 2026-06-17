import { useState } from "react";
import { BorrowerContextPane } from "./components/BorrowerContextPane";
import { ChatPane } from "./components/ChatPane";

function App() {
  const [activeLoanId, setActiveLoanId] = useState<string | undefined>();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-surface-0 font-sans text-text-primary">
      <BorrowerContextPane onLoanLoaded={setActiveLoanId} />
      <ChatPane activeLoanId={activeLoanId} />
      <a
        href="/docs/"
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-4 right-4 text-xs text-text-secondary hover:text-text-primary transition-colors underline decoration-dotted"
      >
        API Docs
      </a>
    </div>
  );
}

export default App;
