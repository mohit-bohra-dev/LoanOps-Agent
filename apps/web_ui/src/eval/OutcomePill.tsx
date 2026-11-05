import type { OutcomeStatus } from "./types";

const STYLES: Record<OutcomeStatus, string> = {
  good: "bg-emerald-600/90 text-white border-emerald-500",
  bad: "bg-rose-600/90 text-white border-rose-500",
  needs_review: "bg-amber-500/90 text-gray-900 border-amber-400",
};

const LABELS: Record<OutcomeStatus, string> = {
  good: "GOOD",
  bad: "BAD",
  needs_review: "NEEDS REVIEW",
};

export function OutcomePill({
  value,
  onChange,
  readOnly = false,
}: {
  value: OutcomeStatus | null;
  onChange?: (v: OutcomeStatus) => void;
  readOnly?: boolean;
}) {
  if (readOnly || !onChange) {
    if (!value) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border border-surface-3 text-text-muted">
          —
        </span>
      );
    }
    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide border ${STYLES[value]}`}
      >
        {LABELS[value]}
      </span>
    );
  }

  return (
    <select
      className={`w-full appearance-none cursor-pointer rounded-full px-2.5 py-1.5 text-[10px] font-bold tracking-wide border outline-none ${
        value ? STYLES[value] : "bg-surface-2 text-text-muted border-surface-3"
      }`}
      value={value ?? ""}
      onChange={(e) => {
        const v = e.target.value as OutcomeStatus;
        if (v) onChange(v);
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <option value="" disabled>
        Select…
      </option>
      <option value="good">GOOD</option>
      <option value="bad">BAD</option>
      <option value="needs_review">NEEDS REVIEW</option>
    </select>
  );
}
