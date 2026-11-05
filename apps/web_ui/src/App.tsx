import { useState } from "react";
import { ChatPane } from "./components/ChatPane";
import { EvalPortal } from "./components/EvalPortal";

function App() {
  const [showEval, setShowEval] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-surface-0 font-sans text-text-primary">
      <ChatPane />
      <button
        type="button"
        onClick={() => setShowEval(true)}
        className="fixed bottom-4 right-28 text-xs text-text-secondary hover:text-text-primary transition-colors underline decoration-dotted"
      >
        Eval Portal
      </button>
      <a
        href="/docs/"
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-4 right-4 text-xs text-text-secondary hover:text-text-primary transition-colors underline decoration-dotted"
      >
        API Docs
      </a>
      {showEval && <EvalPortal onClose={() => setShowEval(false)} />}
    </div>
  );
}

export default App;
